from pathlib import Path

from src.cfg import loadCfg

ASSETS = Path(__file__).parent / "assets"


def testValidCfgLoads():
	cfg = loadCfg(ASSETS / "validCfg.yaml")
	assert cfg.capture.type == "desktop"
	assert cfg.capture.pid is None
	assert cfg.enrollment.speakerCount == 4
	assert cfg.targetLanguage == "cs"
	assert cfg.thresholds.tauAccept == 0.50
	assert cfg.thresholds.tauMargin == 0.05
	assert cfg.thresholds.tauHighConfidence == 0.65
	assert cfg.thresholds.adaptationAlpha == 0.03
	assert cfg.lmStudio.baseUrl == "http://localhost:1234"
	assert cfg.lmStudio.model == "qwen3.5-4b-instruct-abliterated"
	assert cfg.cudaDeviceIndex == 0
