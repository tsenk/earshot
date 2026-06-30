def testWasapiCaptureConstructs():
	from src._native import WasapiCapture

	cap = WasapiCapture()
	assert cap is not None
