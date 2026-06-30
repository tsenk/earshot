#pragma once

#include <cstddef>
#include <cstdint>

using Sample = float;

constexpr uint32_t SAMPLE_RATE_HZ = 16000;
constexpr uint32_t CHANNELS = 1;
constexpr uint32_t BYTES_PER_SAMPLE = sizeof(Sample);

inline void toFloat(const int16_t* in, float* out, size_t n) {
	constexpr float scale = 1.0f/32768.0f;
	for (size_t i = 0; i < n; i++)
		out[i] = in[i]*scale;
}

inline void downmixStereoToMono(const float* in, float* out, size_t frames) {
	for (size_t i = 0; i < frames; i++)
		out[i] = (in[2*i]+in[2*i+1])*0.5f;
}
