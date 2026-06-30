#pragma once

#include <atomic>
#include <cstdint>
#include <cstring>
#include <vector>

struct RingBuf {
	std::vector<float> data;
	std::atomic<size_t> w{0};
	std::atomic<uint64_t> total{0};

	explicit RingBuf(size_t cap) : data(cap, 0.0f) {}

	void write(const float* s, size_t n) {
		auto i = w.load(std::memory_order_relaxed);
		auto cap = data.size();

		if (i+n <= cap) {
			std::memcpy(&data[i], s, n*sizeof(float));
		} else {
			auto first = cap-i;
			std::memcpy(&data[i], s, first*sizeof(float));
			std::memcpy(&data[0], s+first, (n-first)*sizeof(float));
		}

		w.store((i+n)%cap, std::memory_order_release);
		total.fetch_add(n, std::memory_order_release);
	}

	void writeSilence(size_t n) {
		auto i = w.load(std::memory_order_relaxed);
		auto cap = data.size();

		if (i+n <= cap) {
			std::memset(&data[i], 0, n*sizeof(float));
		} else {
			auto first = cap-i;
			std::memset(&data[i], 0, first*sizeof(float));
			std::memset(&data[0], 0, (n-first)*sizeof(float));
		}

		w.store((i+n)%cap, std::memory_order_release);
		total.fetch_add(n, std::memory_order_release);
	}

	void readLatest(float* out, size_t n) const {
		auto i = w.load(std::memory_order_acquire);
		auto cap = data.size();
		auto start = (i+cap-n)%cap;

		if (start+n <= cap) {
			std::memcpy(out, &data[start], n*sizeof(float));
		} else {
			auto first = cap-start;
			std::memcpy(out, &data[start], first*sizeof(float));
			std::memcpy(out+first, &data[0], (n-first)*sizeof(float));
		}
	}
};
