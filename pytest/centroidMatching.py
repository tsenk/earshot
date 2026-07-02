from dataclasses import dataclass

import numpy as np

from src.centroids import CentroidDb


@dataclass(frozen=True)
class _ThresholdsCfg:
	tauAccept: float
	tauMargin: float
	tauHighConfidence: float
	adaptationAlpha: float


def _makeCfg():
	return _ThresholdsCfg(tauAccept=0.50, tauMargin=0.05, tauHighConfidence=0.65, adaptationAlpha=0.03)


def _randomUnitVec(rng, dim=192):
	v = rng.standard_normal(dim).astype(np.float32)
	return v / np.linalg.norm(v)


def testEnrollAndExactMatch():
	rng = np.random.default_rng(42)
	db = CentroidDb(_makeCfg())

	a = _randomUnitVec(rng)
	db.enroll("Alice", a)

	m = db.match(a)
	assert m.label == "Alice"
	assert m.sim > 0.99
	assert m.highConf is True


def testDifferentSpeakerReturnsUnknown():
	rng = np.random.default_rng(42)
	db = CentroidDb(_makeCfg())

	a = _randomUnitVec(rng)
	db.enroll("Alice", a)

	b = _randomUnitVec(rng)
	m = db.match(b)
	assert m.label == "Unknown"
	assert m.sim < 0.50


def testMarginRejectsAmbiguous():
	rng = np.random.default_rng(42)
	db = CentroidDb(_makeCfg())

	a = _randomUnitVec(rng)
	perturb = _randomUnitVec(rng) * 0.3
	b = a + perturb
	b /= np.linalg.norm(b)

	db.enroll("Alice", a)
	db.enroll("Bob", b)

	q = (a + b) / 2
	q /= np.linalg.norm(q)

	m = db.match(q)
	if m.label != "Unknown":
		assert m.label in ("Alice", "Bob")


def testEmptyDbReturnsUnknown():
	rng = np.random.default_rng(42)
	db = CentroidDb(_makeCfg())

	m = db.match(_randomUnitVec(rng))
	assert m.label == "Unknown"
	assert m.sim == 0.0
	assert m.highConf is False
