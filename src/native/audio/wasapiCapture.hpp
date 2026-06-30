#pragma once

#include "ringBuf.hpp"

#include <atomic>
#include <cstdint>
#include <memory>
#include <thread>

struct WasapiCapture {
	WasapiCapture();
	~WasapiCapture();

	void start();
	void stop();

	void readLatestRaw(float* out, size_t n) const;

	uint64_t totalSamplesCaptured() const;

	WasapiCapture(const WasapiCapture&) = delete;
	WasapiCapture& operator=(const WasapiCapture&) = delete;

private:
	std::unique_ptr<RingBuf> buf;
	std::atomic<bool> running{false};
	std::thread captureThread;

	struct Impl;
	std::unique_ptr<Impl> impl;

	void captureLoop();
};
