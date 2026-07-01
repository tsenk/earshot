#include "enumerate.hpp"
#include "wasapiCapture.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;

NB_MODULE(_native_audio, m) {
	nb::enum_<CaptureType>(m, "CaptureType")
		.value("Desktop", CaptureType::Desktop)
		.value("Process", CaptureType::Process);

	nb::class_<CaptureCfg>(m, "CaptureCfg")
		.def(nb::init<>())
		.def_rw("type", &CaptureCfg::type)
		.def_rw("pid", &CaptureCfg::pid);

	nb::class_<ProcessAudioInfo>(m, "ProcessAudioInfo")
		.def_ro("pid", &ProcessAudioInfo::pid)
		.def_ro("executableName", &ProcessAudioInfo::executableName);

	m.def("listProcessesPlayingAudio", &listProcessesPlayingAudio);

	nb::class_<Window>(m, "Window")
		.def_ro("startSampleIdx", &Window::startSampleIdx)
		.def_ro("startTimeNs", &Window::startTimeNs)
		.def_ro("followsDiscontinuity", &Window::followsDiscontinuity)
		.def_prop_ro("samples", [](nb::handle_t<Window> self) {
			auto& w = nb::cast<Window&>(self);
			return nb::ndarray<float, nb::numpy, nb::shape<80000>, nb::c_contig>(w.samples, {80000}, self);
		});

	nb::class_<CaptureStats>(m, "CaptureStats")
		.def_ro("totalSamplesCaptured", &CaptureStats::totalSamplesCaptured)
		.def_ro("totalWindowsEmitted", &CaptureStats::totalWindowsEmitted)
		.def_ro("discontinuityCount", &CaptureStats::discontinuityCount)
		.def_ro("silencePadEvents", &CaptureStats::silencePadEvents);

	nb::class_<WasapiCapture>(m, "WasapiCapture")
		.def(nb::init<const CaptureCfg&>())
		.def("start", &WasapiCapture::start)
		.def("stop", &WasapiCapture::stop, nb::call_guard<nb::gil_scoped_release>())
		.def("getNextWindow", &WasapiCapture::getNextWindow, nb::call_guard<nb::gil_scoped_release>())
		.def("recordSeconds", [](WasapiCapture& self, uint32_t n) {
			auto samples = static_cast<size_t>(n)*16000;
			auto* data = new float[samples];
			auto capsule = nb::capsule(data, [](void* p) noexcept { delete[] static_cast<float*>(p); });
			try {
				nb::gil_scoped_release release;
				self.recordSeconds(n, data);
			} catch (...) {
				delete[] data;
				throw;
			}
			return nb::ndarray<float, nb::numpy, nb::c_contig>(data, {samples}, capsule);
		}, nb::arg("n"))
		.def("getStats", &WasapiCapture::getStats);
}
