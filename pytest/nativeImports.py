def testWasapiCaptureConstructs():
	from src._native import CaptureCfg, CaptureType, WasapiCapture

	cfg = CaptureCfg()
	cfg.type = CaptureType.Desktop
	cfg.pid = 0

	cap = WasapiCapture(cfg)
	assert cap is not None
