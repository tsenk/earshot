from dataclasses import dataclass

import numpy as np

from src.centroids import CentroidDb


@dataclass(frozen=True)
class _ThresholdsCfg:
	tauAccept: float
	tauMargin: float
	tauHighConfidence: float
	adaptationAlpha: float


def _makeCfg(alpha=0.03):
	return _ThresholdsCfg(tauAccept=0.50, tauMargin=0.05, tauHighConfidence=0.65, adaptationAlpha=alpha)


def _randomUnitVec(rng, dim=192):
	v = rng.standard_normal(dim).astype(np.float32)
	return v / np.linalg.norm(v)


def testAdaptMovesCentroid():
	rng = np.random.default_rng(0)
	db = CentroidDb(_makeCfg(alpha=0.1))

	a = _randomUnitVec(rng)
	db.enroll("Alice", a)
	before = db.c["Alice"].copy()

	b = _randomUnitVec(rng)
	db.adapt("Alice", b)
	after = db.c["Alice"]

	simBefore = float(np.dot(before, b))
	simAfter = float(np.dot(after, b))
	assert simAfter > simBefore


def testAdaptUnknownLabelNoop():
	rng = np.random.default_rng(0)
	db = CentroidDb(_makeCfg())

	b = _randomUnitVec(rng)
	db.adapt("Nobody", b)
	assert "Nobody" not in db.c


def testCentroidStaysNormalized():
	rng = np.random.default_rng(0)
	db = CentroidDb(_makeCfg(alpha=0.1))

	a = _randomUnitVec(rng)
	db.enroll("Alice", a)

	for _ in range(10):
		v = _randomUnitVec(rng)
		db.adapt("Alice", v)
		norm = float(np.linalg.norm(db.c["Alice"]))
		assert abs(norm - 1.0) < 1e-6
