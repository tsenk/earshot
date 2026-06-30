#include "wasapiCapture.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

namespace nb = nanobind;

NB_MODULE(_native_audio, m) {
	nb::class_<WasapiCapture>(m, "WasapiCapture")
		.def(nb::init<>())
		.def("start", &WasapiCapture::start)
		.def("stop", &WasapiCapture::stop)
		.def("totalSamplesCaptured", &WasapiCapture::totalSamplesCaptured)
		.def("readLatestRaw", [](const WasapiCapture& self, size_t n) {
			auto* data = new float[n];
			auto capsule = nb::capsule(data, [](void* p) noexcept { delete[] static_cast<float*>(p); });
			self.readLatestRaw(data, n);
			return nb::ndarray<float, nb::numpy, nb::c_contig>(data, {n}, capsule);
		}, nb::arg("n"));
}
