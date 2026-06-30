import numpy as np


def testWindowShape():
	from src._native import WasapiCapture

	cap = WasapiCapture()
	cap.start()
	try:
		w = cap.getNextWindow()
		assert w.samples.shape == (80000,)
		assert w.samples.dtype == np.float32
		assert w.startSampleIdx >= 0
		assert w.startTimeNs > 0
	finally:
		cap.stop()


def testRecordSecondsShape():
	from src._native import WasapiCapture

	cap = WasapiCapture()
	cap.start()
	try:
		samples = cap.recordSeconds(1)
		assert samples.shape == (16000,)
		assert samples.dtype == np.float32
	finally:
		cap.stop()


def testStatsAdvance():
	from src._native import WasapiCapture

	cap = WasapiCapture()
	cap.start()
	try:
		cap.getNextWindow()
		cap.recordSeconds(1)
		stats = cap.getStats()
		assert stats.totalSamplesCaptured >= 16000
		assert stats.totalWindowsEmitted >= 1
	finally:
		cap.stop()
