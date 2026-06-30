#pragma once

#include "ringBuf.hpp"
#include "resampler.hpp"
#include "windower.hpp"

#include <atomic>
#include <cstdint>
#include <memory>
#include <thread>

struct CaptureStats {
	uint64_t totalSamplesCaptured;
	uint64_t totalWindowsEmitted;
	uint64_t discontinuityCount;
	uint64_t silencePadEvents;
};

struct WasapiCapture {
	WasapiCapture();
	~WasapiCapture();

	void start();
	void stop();

	Window getNextWindow();

	void recordSeconds(uint32_t n, float* out);

	CaptureStats getStats() const;

	WasapiCapture(const WasapiCapture&) = delete;
	WasapiCapture& operator=(const WasapiCapture&) = delete;

private:
	std::unique_ptr<RingBuf> buf;
	std::unique_ptr<Resampler> resampler;
	std::unique_ptr<Windower> windower;

	std::atomic<uint64_t> totalWritten{0};
	std::atomic<uint64_t> silencePadEvents{0};
	std::atomic<uint64_t> discontinuityCount{0};
	std::atomic<bool> running{false};
	std::thread captureThread;

	struct Impl;
	std::unique_ptr<Impl> impl;

	void captureLoop();
};
