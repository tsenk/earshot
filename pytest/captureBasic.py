import numpy as np


def _desktopCfg():
	from src._native import CaptureCfg, CaptureType

	cfg = CaptureCfg()
	cfg.type = CaptureType.Desktop
	cfg.pid = 0
	return cfg


def testWindowShape():
	from src._native import WasapiCapture

	cap = WasapiCapture(_desktopCfg())
	cap.start()
	try:
		w = cap.getNextWindow()
		assert w.samples.shape == (80000,)
		assert w.samples.dtype == np.float32
		assert w.startTimeNs > 0
	finally:
		cap.stop()


def testRecordSecondsShape():
	from src._native import WasapiCapture

	cap = WasapiCapture(_desktopCfg())
	cap.start()
	try:
		samples = cap.recordSeconds(1)
		assert samples.shape == (16000,)
		assert samples.dtype == np.float32
	finally:
		cap.stop()


def testStatsAdvance():
	from src._native import WasapiCapture

	cap = WasapiCapture(_desktopCfg())
	cap.start()
	try:
		cap.recordSeconds(1)
		stats = cap.getStats()
		assert stats.totalSamplesCaptured >= 16000
	finally:
		cap.stop()


def testProcessEnumeration():
	from src._native import listProcessesPlayingAudio

	processes = listProcessesPlayingAudio()
	assert isinstance(processes, list)
	for p in processes:
		assert p.pid > 0
		assert isinstance(p.executableName, str)
		assert len(p.executableName) > 0


def testProcessLoopbackConstruction():
	from src._native import CaptureCfg, CaptureType, WasapiCapture, listProcessesPlayingAudio

	processes = listProcessesPlayingAudio()
	if not processes:
		import pytest

		pytest.skip("no audio-producing processes available")

	cfg = CaptureCfg()
	cfg.type = CaptureType.Process
	cfg.pid = processes[0].pid

	cap = WasapiCapture(cfg)
	cap.start()
	try:
		samples = cap.recordSeconds(1)
		assert samples.shape == (16000,)
	finally:
		cap.stop()
