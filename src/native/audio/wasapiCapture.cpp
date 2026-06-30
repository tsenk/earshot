#include "wasapiCapture.hpp"

#include <audioclient.h>
#include <mmdeviceapi.h>
#include <windows.h>

#include <stdexcept>
#include <string>

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
		
	buf = std::make_unique<RingBuf>(15*16000);
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

	SetEvent(impl->readyEvent);

	if (captureThread.joinable())
		captureThread.join();

	impl->client->Stop();
}

void WasapiCapture::captureLoop() {
	while (running.load()) {
		auto waitResult = WaitForSingleObject(impl->readyEvent, 200);
		if (waitResult != WAIT_OBJECT_0)
			continue;
		if (!running.load())
			break;

		UINT32 packetSize = 0;
		auto hr = impl->capture->GetNextPacketSize(&packetSize);
		while (SUCCEEDED(hr) && packetSize > 0) {
			BYTE* data = nullptr;
			UINT32 frames = 0;
			DWORD flags = 0;
			hr = impl->capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
			if (SUCCEEDED(hr)) {
				auto n = static_cast<size_t>(frames)*impl->mixFormat->nChannels;
				if (!(flags & AUDCLNT_BUFFERFLAGS_SILENT))
					buf->write(reinterpret_cast<const float*>(data), n);
				else
					buf->writeSilence(n);
				impl->capture->ReleaseBuffer(frames);
			}
			hr = impl->capture->GetNextPacketSize(&packetSize);
		}
	}
}

void WasapiCapture::readLatestRaw(float* out, size_t n) const {
	buf->readLatest(out, n);
}

uint64_t WasapiCapture::totalSamplesCaptured() const {
	return buf->total.load(std::memory_order_acquire);
}
