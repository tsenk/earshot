#include "wasapiCapture.hpp"

#include <audioclient.h>
#include <mmdeviceapi.h>
#include <windows.h>

#include <chrono>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void throwIfFailed(HRESULT hr, const char* what) {
	if (FAILED(hr))
		throw std::runtime_error(std::string(what) + " failed, hr=0x" + std::to_string(static_cast<unsigned long>(hr)));
}

bool isFloatFormat(const WAVEFORMATEX* f) {
	if (f->wFormatTag == WAVE_FORMAT_IEEE_FLOAT)
		return true;

	if (f->wFormatTag == WAVE_FORMAT_EXTENSIBLE) {
		auto ext = reinterpret_cast<const WAVEFORMATEXTENSIBLE*>(f);
		return ext->SubFormat == KSDATAFORMAT_SUBTYPE_IEEE_FLOAT;
	}

	return false;
}

uint64_t nowNs() {
	return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
		std::chrono::steady_clock::now().time_since_epoch()).count());
}

}

struct WasapiCapture::Impl {
	IMMDeviceEnumerator* enumerator{nullptr};
	IMMDevice* device{nullptr};
	IAudioClient* client{nullptr};
	IAudioCaptureClient* capture{nullptr};
	HANDLE readyEvent{nullptr};
	WAVEFORMATEX* mixFormat{nullptr};

	~Impl() {
		if (capture) capture->Release();
		if (client) client->Release();
		if (device) device->Release();
		if (enumerator) enumerator->Release();
		if (readyEvent) CloseHandle(readyEvent);
		if (mixFormat) CoTaskMemFree(mixFormat);
	}
};

WasapiCapture::WasapiCapture() : impl(std::make_unique<Impl>()) {
	auto hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
	if (FAILED(hr) && hr != RPC_E_CHANGED_MODE)
		throw std::runtime_error("CoInitializeEx failed");

	throwIfFailed(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
		__uuidof(IMMDeviceEnumerator), reinterpret_cast<void**>(&impl->enumerator)), "CoCreateInstance(MMDeviceEnumerator)");

	throwIfFailed(impl->enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &impl->device), "GetDefaultAudioEndpoint");

	throwIfFailed(impl->device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
		reinterpret_cast<void**>(&impl->client)), "IMMDevice::Activate(IAudioClient)");

	throwIfFailed(impl->client->GetMixFormat(&impl->mixFormat), "GetMixFormat");

	if (!isFloatFormat(impl->mixFormat))
		throw std::runtime_error("mix format is not IEEE float, unsupported");

	throwIfFailed(impl->client->Initialize(
		AUDCLNT_SHAREMODE_SHARED,
		AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK,
		200000,
		0,
		impl->mixFormat,
		nullptr), "IAudioClient::Initialize");

	impl->readyEvent = CreateEventW(nullptr, FALSE, FALSE, nullptr);
	if (!impl->readyEvent)
		throw std::runtime_error("CreateEventW failed");

	throwIfFailed(impl->client->SetEventHandle(impl->readyEvent), "SetEventHandle");

	throwIfFailed(impl->client->GetService(__uuidof(IAudioCaptureClient),
		reinterpret_cast<void**>(&impl->capture)), "GetService(IAudioCaptureClient)");

	resampler = std::make_unique<Resampler>(impl->mixFormat->nSamplesPerSec, impl->mixFormat->nChannels, 16000, 1);

	buf = std::make_unique<RingBuf>(15*16000);

	windower = std::make_unique<Windower>(*buf);
}

WasapiCapture::~WasapiCapture() {
	stop();
	CoUninitialize();
}

void WasapiCapture::start() {
	if (running.exchange(true))
		return;

	auto hr = impl->client->Start();
	if (FAILED(hr)) {
		running = false;
		throw std::runtime_error("IAudioClient::Start failed");
	}

	captureThread = std::thread(&WasapiCapture::captureLoop, this);
}

void WasapiCapture::stop() {
	if (!running.exchange(false))
		return;

	windower->shutdown();
	SetEvent(impl->readyEvent);

	if (captureThread.joinable())
		captureThread.join();

	impl->client->Stop();
}

void WasapiCapture::captureLoop() {
	std::vector<float> resampleOut(65536);

	auto lastWakeNs = nowNs();

	while (running.load()) {
		auto waitResult = WaitForSingleObject(impl->readyEvent, 200);
		if (!running.load())
			break;

		bool anyArrived = false;
		bool discontinuityThisWake = false;

		if (waitResult == WAIT_OBJECT_0) {
			UINT32 packetSize = 0;
			auto hr = impl->capture->GetNextPacketSize(&packetSize);
			while (SUCCEEDED(hr) && packetSize > 0) {
				BYTE* data = nullptr;
				UINT32 frames = 0;
				DWORD flags = 0;
				hr = impl->capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
				if (SUCCEEDED(hr)) {
					if (flags & AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) {
						discontinuityThisWake = true;
						discontinuityCount.fetch_add(1, std::memory_order_release);
					}

					auto srcSamples = static_cast<size_t>(frames)*impl->mixFormat->nChannels;
					auto dstWritten = resampler->process(reinterpret_cast<const float*>(data), srcSamples, resampleOut.data(), resampleOut.size());
					if (dstWritten > 0) {
						buf->write(resampleOut.data(), dstWritten);
						totalWritten.fetch_add(dstWritten, std::memory_order_release);
					}
					anyArrived = true;

					impl->capture->ReleaseBuffer(frames);
				}
				hr = impl->capture->GetNextPacketSize(&packetSize);
			}
		}

		auto wakeNs = nowNs();

		if (!anyArrived) {
			// loopback stops signaling events during true silence 200ms wakes us
			// pad by silence to keep windows on schedule
			auto owed = (wakeNs-lastWakeNs)*16000/1000000000;
			if (owed > 15*16000)
				owed = 15*16000;
			if (owed > 0) {
				buf->writeSilence(owed);
				totalWritten.fetch_add(owed, std::memory_order_release);
				silencePadEvents.fetch_add(1, std::memory_order_release);
			}
		}

		lastWakeNs = wakeNs;

		windower->onSamplesWritten(totalWritten.load(std::memory_order_acquire), wakeNs, discontinuityThisWake);
	}
}

Window WasapiCapture::getNextWindow() {
	return windower->getNext();
}

void WasapiCapture::recordSeconds(uint32_t n, float* out) {
	if (n == 0)
		throw std::runtime_error("recordSeconds requires n > 0");

	auto samplesNeeded = static_cast<uint64_t>(n)*16000;
	auto startTotal = totalWritten.load(std::memory_order_acquire);
	auto targetTotal = startTotal+samplesNeeded;

	while (running.load()) {
		auto current = totalWritten.load(std::memory_order_acquire);
		if (current >= targetTotal)
			break;
		std::this_thread::sleep_for(std::chrono::milliseconds(50));
	}

	if (!running.load())
		throw std::runtime_error("capture stopped during recordSeconds");

	buf->readLatest(out, samplesNeeded);
}

CaptureStats WasapiCapture::getStats() const {
	return CaptureStats{
		totalWritten.load(std::memory_order_acquire),
		windower->windowsEmitted(),
		discontinuityCount.load(std::memory_order_acquire),
		silencePadEvents.load(std::memory_order_acquire),
	};
}
