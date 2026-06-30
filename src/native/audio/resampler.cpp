#include "resampler.hpp"

#include <windows.h>
#include <initguid.h>
#include <mfapi.h>
#include <mferror.h>
#include <mfidl.h>
#include <mftransform.h>
#include <propsys.h>
#include <propvarutil.h>
#include <wmcodecdsp.h>

#include <cstring>
#include <stdexcept>
#include <string>

namespace {

void throwIfFailed(HRESULT hr, const char* what) {
	if (FAILED(hr))
		throw std::runtime_error(std::string(what) + " failed, hr=0x" + std::to_string(static_cast<unsigned long>(hr)));
}

IMFMediaType* makeFloatType(uint32_t rate, uint32_t channels) {
	IMFMediaType* t = nullptr;
	throwIfFailed(MFCreateMediaType(&t), "MFCreateMediaType");

	t->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio);
	t->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_Float);
	t->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, rate);
	t->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, channels);
	t->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 32);
	t->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT, channels*4);
	t->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, rate*channels*4);
	t->SetUINT32(MF_MT_ALL_SAMPLES_INDEPENDENT, TRUE);

	return t;
}

constexpr DWORD IN_BUF_CAP = 1 << 20;
constexpr DWORD OUT_BUF_CAP = 1 << 20;

}

struct Resampler::Impl {
	IMFTransform* transform{nullptr};
	IMFMediaType* inputType{nullptr};
	IMFMediaType* outputType{nullptr};
	IMFSample* inputSample{nullptr};
	IMFSample* outputSample{nullptr};
	IMFMediaBuffer* inputBuffer{nullptr};
	IMFMediaBuffer* outputBuffer{nullptr};

	~Impl() {
		if (outputBuffer) outputBuffer->Release();
		if (inputBuffer) inputBuffer->Release();
		if (outputSample) outputSample->Release();
		if (inputSample) inputSample->Release();
		if (outputType) outputType->Release();
		if (inputType) inputType->Release();
		if (transform) transform->Release();
		MFShutdown();
	}
};

Resampler::Resampler(uint32_t srcRate, uint32_t srcChannels, uint32_t dstRate, uint32_t dstChannels) : impl(std::make_unique<Impl>()) {
	throwIfFailed(MFStartup(MF_VERSION, MFSTARTUP_LITE), "MFStartup");

	throwIfFailed(CoCreateInstance(CLSID_CResamplerMediaObject, nullptr, CLSCTX_INPROC_SERVER,
		__uuidof(IMFTransform), reinterpret_cast<void**>(&impl->transform)), "CoCreateInstance(Resampler)");

	// quality must be set before media types (60 best)
	IPropertyStore* props = nullptr;
	throwIfFailed(impl->transform->QueryInterface(__uuidof(IPropertyStore), reinterpret_cast<void**>(&props)), "QueryInterface(IPropertyStore)");

	PROPVARIANT v;
	InitPropVariantFromInt32(60, &v);
	auto hr = props->SetValue(MFPKEY_WMRESAMP_FILTERQUALITY, v);
	PropVariantClear(&v);
	props->Release();
	throwIfFailed(hr, "SetValue(FILTERQUALITY)");

	impl->inputType = makeFloatType(srcRate, srcChannels);
	impl->outputType = makeFloatType(dstRate, dstChannels);

	throwIfFailed(impl->transform->SetInputType(0, impl->inputType, 0), "SetInputType");
	throwIfFailed(impl->transform->SetOutputType(0, impl->outputType, 0), "SetOutputType");

	throwIfFailed(MFCreateSample(&impl->inputSample), "MFCreateSample(in)");
	throwIfFailed(MFCreateMemoryBuffer(IN_BUF_CAP, &impl->inputBuffer), "MFCreateMemoryBuffer(in)");
	throwIfFailed(impl->inputSample->AddBuffer(impl->inputBuffer), "AddBuffer(in)");

	throwIfFailed(MFCreateSample(&impl->outputSample), "MFCreateSample(out)");
	throwIfFailed(MFCreateMemoryBuffer(OUT_BUF_CAP, &impl->outputBuffer), "MFCreateMemoryBuffer(out)");
	throwIfFailed(impl->outputSample->AddBuffer(impl->outputBuffer), "AddBuffer(out)");

	impl->transform->ProcessMessage(MFT_MESSAGE_NOTIFY_BEGIN_STREAMING, 0);
	impl->transform->ProcessMessage(MFT_MESSAGE_NOTIFY_START_OF_STREAM, 0);
}

Resampler::~Resampler() = default;

size_t Resampler::process(const float* in, size_t n, float* out, size_t outCap) {
	auto bytes = static_cast<DWORD>(n*sizeof(float));
	if (bytes > IN_BUF_CAP)
		throw std::runtime_error("resampler input exceeds buffer capacity");

	BYTE* p = nullptr;
	throwIfFailed(impl->inputBuffer->Lock(&p, nullptr, nullptr), "Lock(in)");
	std::memcpy(p, in, bytes);
	impl->inputBuffer->Unlock();
	impl->inputBuffer->SetCurrentLength(bytes);

	throwIfFailed(impl->transform->ProcessInput(0, impl->inputSample, 0), "ProcessInput");

	size_t written = 0;

	while (true) {
		impl->outputBuffer->SetCurrentLength(0);

		MFT_OUTPUT_DATA_BUFFER outData{};
		outData.pSample = impl->outputSample;

		DWORD status = 0;
		auto hr = impl->transform->ProcessOutput(0, 1, &outData, &status);
		if (hr == MF_E_TRANSFORM_NEED_MORE_INPUT)
			break;
		throwIfFailed(hr, "ProcessOutput");

		DWORD outLen = 0;
		throwIfFailed(impl->outputBuffer->Lock(&p, nullptr, &outLen), "Lock(out)");
		auto outSamples = outLen/sizeof(float);
		if (written+outSamples > outCap) {
			impl->outputBuffer->Unlock();
			throw std::runtime_error("resampler output exceeds caller capacity");
		}
		std::memcpy(out+written, p, outLen);
		impl->outputBuffer->Unlock();

		written += outSamples;
	}

	return written;
}
