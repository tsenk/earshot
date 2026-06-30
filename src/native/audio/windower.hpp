#pragma once

#include "ringBuf.hpp"

#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <mutex>

struct Window {
	float samples[80000];
	uint64_t startSampleIdx;
	uint64_t startTimeNs;
	bool followsDiscontinuity;
};

struct Windower {
	explicit Windower(RingBuf& b);

	void onSamplesWritten(uint64_t totalWritten, uint64_t nowNs, bool discontinuity);

	Window getNext();

	void shutdown();

	uint64_t windowsEmitted() const { return emitted.load(std::memory_order_acquire); }

	Windower(const Windower&) = delete;
	Windower& operator=(const Windower&) = delete;

private:
	RingBuf& buf;
	uint64_t lastEmit{0};
	std::atomic<uint64_t> emitted{0};

	std::deque<Window> queue;
	std::mutex mu;
	std::condition_variable cv;
	std::atomic<bool> stopped{false};

	static constexpr size_t QUEUE_CAP = 10;
};
