from dataclasses import dataclass

import numpy as np
from loguru import logger


@dataclass(frozen=True)
class Match:
	label: str
	sim: float
	highConf: bool


class CentroidDb:
	def __init__(self, cfg):
		self.c: dict[str, np.ndarray] = {}
		self.tauA = cfg.tauAccept
		self.tauM = cfg.tauMargin
		self.tauH = cfg.tauHighConfidence
		self.a = cfg.adaptationAlpha

	def enroll(self, label: str, emb: np.ndarray) -> None:
		self.c[label] = emb / np.linalg.norm(emb)
		logger.info("Enrolled {}", label)

	def match(self, emb: np.ndarray) -> Match:
		if not self.c:
			return Match("Unknown", 0.0, False)

		e = emb / np.linalg.norm(emb)
		sims = sorted(((k, float(np.dot(v, e))) for k, v in self.c.items()), key=lambda x: x[1], reverse=True)

		best, bestSim = sims[0]
		second = sims[1][1] if len(sims) > 1 else 0.0

		if bestSim < self.tauA or bestSim - second < self.tauM:
			return Match("Unknown", bestSim, False)

		return Match(best, bestSim, bestSim >= self.tauH)

	def adapt(self, label: str, emb: np.ndarray) -> None:
		if label not in self.c:
			return

		e = emb / np.linalg.norm(emb)
		updated = (1 - self.a) * self.c[label] + self.a * e
		self.c[label] = updated / np.linalg.norm(updated)

	def all(self) -> dict[str, np.ndarray]:
		return dict(self.c)
