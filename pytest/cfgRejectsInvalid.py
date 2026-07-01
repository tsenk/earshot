from pathlib import Path

import pytest
from src.cfg import CfgError, loadCfg

ASSETS = Path(__file__).parent / "assets"


def testInvalidCfgRejected():
	with pytest.raises(CfgError, match="target-language"):
		loadCfg(ASSETS / "invalidCfg.yaml")


def testMissingCfgRejected(tmp_path):
	nonexistent = tmp_path / "nope.yaml"
	with pytest.raises(CfgError, match="not found"):
		loadCfg(nonexistent)


def testMalformedYamlRejected(tmp_path):
	bad = tmp_path / "bad.yaml"
	bad.write_text("just a string not a mapping", encoding="utf-8")
	with pytest.raises(CfgError, match="mapping"):
		loadCfg(bad)


def testCaptureTypeInvalid(tmp_path):
	bad = tmp_path / "bad.yaml"
	bad.write_text(
		"""
capture:
  type: microphone
  pid: null
enrollment:
  speaker-count: 4
target-language: cs
thresholds:
  tau-accept: 0.50
  tau-margin: 0.05
  tau-high-confidence: 0.65
  adaptation-alpha: 0.03
lm-studio:
  base-url: http://localhost:1234
  model: qwen3.5-4b-instruct-abliterated
cuda-device-index: 0
""",
		encoding="utf-8",
	)
	with pytest.raises(CfgError, match="capture.type"):
		loadCfg(bad)


def testProcessMissingPidRejected(tmp_path):
	bad = tmp_path / "bad.yaml"
	bad.write_text(
		"""
capture:
  type: process
  pid: null
enrollment:
  speaker-count: 4
target-language: cs
thresholds:
  tau-accept: 0.50
  tau-margin: 0.05
  tau-high-confidence: 0.65
  adaptation-alpha: 0.03
lm-studio:
  base-url: http://localhost:1234
  model: qwen3.5-4b-instruct-abliterated
cuda-device-index: 0
""",
		encoding="utf-8",
	)
	with pytest.raises(CfgError, match="capture.pid"):
		loadCfg(bad)


def testThresholdOutOfRangeRejected(tmp_path):
	bad = tmp_path / "bad.yaml"
	bad.write_text(
		"""
capture:
  type: desktop
  pid: null
enrollment:
  speaker-count: 4
target-language: cs
thresholds:
  tau-accept: 1.5
  tau-margin: 0.05
  tau-high-confidence: 0.65
  adaptation-alpha: 0.03
lm-studio:
  base-url: http://localhost:1234
  model: qwen3.5-4b-instruct-abliterated
cuda-device-index: 0
""",
		encoding="utf-8",
	)
	with pytest.raises(CfgError, match="tau-accept"):
		loadCfg(bad)
