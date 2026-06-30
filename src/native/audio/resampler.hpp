#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>

struct Resampler {
	Resampler(uint32_t srcRate, uint32_t srcChannels, uint32_t dstRate, uint32_t dstChannels);
	~Resampler();

	size_t process(const float* in, size_t n, float* out, size_t outCap);

	Resampler(const Resampler&) = delete;
	Resampler& operator=(const Resampler&) = delete;

private:
	struct Impl;
	std::unique_ptr<Impl> impl;
};
