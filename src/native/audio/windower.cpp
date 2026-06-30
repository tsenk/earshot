#include "windower.hpp"

#include <stdexcept>

Windower::Windower(RingBuf& b) : buf(b) {}

void Windower::onSamplesWritten(uint64_t totalWritten, uint64_t nowNs, bool discontinuity) {
	while (totalWritten-lastEmit >= 8000) {
		lastEmit += 8000;
		if (totalWritten < 80000)
			continue;

		Window w{};
		buf.readLatest(w.samples, 80000);
		w.startSampleIdx = totalWritten-80000;
		w.startTimeNs = nowNs;
		w.followsDiscontinuity = discontinuity;

		{
			std::lock_guard lk(mu);
			if (queue.size() >= QUEUE_CAP)
				queue.pop_front();
			queue.push_back(w);
		}
		cv.notify_one();
		emitted.fetch_add(1, std::memory_order_release);
	}
}

Window Windower::getNext() {
	std::unique_lock lk(mu);
	cv.wait(lk, [this] { return !queue.empty() || stopped.load(); });

	if (stopped.load() && queue.empty())
		throw std::runtime_error("capture stopped");

	auto w = queue.front();
	queue.pop_front();
	return w;
}

void Windower::shutdown() {
	stopped.store(true);
	cv.notify_all();
}
