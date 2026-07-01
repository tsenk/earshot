from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_ISO_639_1 = frozenset(
	{
		"cs",
		"sk",
		"en",
		"de",
		"fr",
		"es",
		"it",
		"pt",
		"nl",
		"pl",
		"ru",
		"uk",
		"sv",
		"no",
		"da",
		"fi",
		"ro",
		"hu",
		"el",
		"tr",
		"ja",
		"ko",
		"zh",
		"ar",
		"he",
		"hi",
		"th",
		"vi",
		"id",
		"ms",
		"bg",
		"hr",
		"sl",
		"sr",
		"et",
		"lv",
		"lt",
		"ca",
		"eu",
		"gl",
		"is",
		"mt",
		"sq",
		"mk",
		"bs",
	}
)


@dataclass(frozen=True)
class CaptureCfg:
	type: str
	pid: int | None


@dataclass(frozen=True)
class EnrollmentCfg:
	speakerCount: int


@dataclass(frozen=True)
class ThresholdsCfg:
	tauAccept: float
	tauMargin: float
	tauHighConfidence: float
	adaptationAlpha: float


@dataclass(frozen=True)
class LmStudioCfg:
	baseUrl: str
	model: str


@dataclass(frozen=True)
class Cfg:
	capture: CaptureCfg
	enrollment: EnrollmentCfg
	targetLanguage: str
	thresholds: ThresholdsCfg
	lmStudio: LmStudioCfg
	cudaDeviceIndex: int


class CfgError(Exception):
	pass


def _require(d: dict, key: str, path: str) -> Any:
	if key not in d:
		raise CfgError(f"missing required key: {path}.{key}" if path else f"missing required key: {key}")
	return d[key]


def _parseCapture(d: dict) -> CaptureCfg:
	t = _require(d, "type", "capture")
	if t not in ("desktop", "process"):
		raise CfgError(f"capture.type must be 'desktop' or 'process', got {t!r}")

	pid = d.get("pid")
	if t == "process":
		if pid is None or not isinstance(pid, int) or pid <= 0:
			raise CfgError("capture.pid must be a positive integer when capture.type is 'process'")
	else:
		if pid is not None:
			raise CfgError("capture.pid must be null or absent when capture.type is 'desktop'")

	return CaptureCfg(type=t, pid=pid)


def _parseEnrollment(d: dict) -> EnrollmentCfg:
	n = _require(d, "speaker-count", "enrollment")
	if not isinstance(n, int) or n < 1 or n > 10:
		raise CfgError(f"enrollment.speaker-count must be an integer in [1, 10], got {n!r}")
	return EnrollmentCfg(speakerCount=n)


def _parseThresholds(d: dict) -> ThresholdsCfg:
	a = _require(d, "tau-accept", "thresholds")
	m = _require(d, "tau-margin", "thresholds")
	h = _require(d, "tau-high-confidence", "thresholds")
	al = _require(d, "adaptation-alpha", "thresholds")

	for name, v in (("tau-accept", a), ("tau-margin", m), ("tau-high-confidence", h)):
		if not isinstance(v, (int, float)) or v < 0.0 or v > 1.0:
			raise CfgError(f"thresholds.{name} must be in [0.0, 1.0], got {v!r}")

	if not isinstance(al, (int, float)) or al <= 0.0 or al > 1.0:
		raise CfgError(f"thresholds.adaptation-alpha must be in (0.0, 1.0], got {al!r}")

	return ThresholdsCfg(tauAccept=float(a), tauMargin=float(m), tauHighConfidence=float(h), adaptationAlpha=float(al))


def _parseLmStudio(d: dict) -> LmStudioCfg:
	u = _require(d, "base-url", "lm-studio")
	if not isinstance(u, str) or not (u.startswith("http://") or u.startswith("https://")):
		raise CfgError(f"lm-studio.base-url must be a valid http/https URL, got {u!r}")

	m = _require(d, "model", "lm-studio")
	if not isinstance(m, str) or not m:
		raise CfgError("lm-studio.model must be a non-empty string")

	return LmStudioCfg(baseUrl=u, model=m)


def loadCfg(path: str | Path) -> Cfg:
	p = Path(path)
	if not p.exists():
		raise CfgError(f"config file not found: {p}")

	with p.open("r", encoding="utf-8") as f:
		raw = yaml.safe_load(f)

	if not isinstance(raw, dict):
		raise CfgError("config file must be a YAML mapping at the top level")

	capture = _parseCapture(_require(raw, "capture", ""))
	enrollment = _parseEnrollment(_require(raw, "enrollment", ""))

	lang = _require(raw, "target-language", "")
	if not isinstance(lang, str) or lang not in VALID_ISO_639_1:
		raise CfgError(f"target-language must be a valid ISO 639-1 code, got {lang!r}")

	thresholds = _parseThresholds(_require(raw, "thresholds", ""))
	lm = _parseLmStudio(_require(raw, "lm-studio", ""))

	idx = _require(raw, "cuda-device-index", "")
	if not isinstance(idx, int) or idx < 0:
		raise CfgError(f"cuda-device-index must be a non-negative integer, got {idx!r}")

	return Cfg(
		capture=capture,
		enrollment=enrollment,
		targetLanguage=lang,
		thresholds=thresholds,
		lmStudio=lm,
		cudaDeviceIndex=idx,
	)
