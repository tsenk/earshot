import sys

import numpy as np
from loguru import logger


def _embedSamples(titanet, samples: np.ndarray) -> np.ndarray:
	import torch

	with torch.no_grad():
		t = torch.from_numpy(samples).unsqueeze(0).to(titanet.device)
		lengths = torch.tensor([samples.shape[0]]).to(titanet.device)
		_, emb = titanet.forward(input_signal=t, input_signal_length=lengths)
	return emb.squeeze(0).cpu().numpy()


def runEnrollment(cap, titanet, db, speakerCount: int) -> None:
	i = 1
	while i <= speakerCount:
		defaultLabel = f"Speaker {i}"

		print(f"\nPress Enter to start recording {defaultLabel}.", file=sys.stderr)
		input()

		print("Recording 15s...", file=sys.stderr)
		samples = cap.recordSeconds(15)
		logger.info("Captured 15s for speaker {}, samples={}", i, samples.shape[0])

		emb = _embedSamples(titanet, samples)
		logger.debug("Embedded speaker {}, embedding shape={}", i, emb.shape)

		print(
			f"Name for {defaultLabel}? ('r' to redo, Enter to keep as '{defaultLabel}', or type a custom name)",
			file=sys.stderr,
		)
		response = input().strip()

		if response == "r":
			logger.info("Redoing enrollment for {}", defaultLabel)
			continue

		label = response if response else defaultLabel
		db.enroll(label, emb)
		i += 1
