import numpy as np
import torch
from loguru import logger

from src.centroids import CentroidDb
from src.display import DisplayState, RenderedLine
from src.models import Models
from src.translation import Translator

# powerset classes for segmentation-3.0: 0=silence, 1-3=single speakers, 4-6=pairs
# https://huggingface.co/pyannote/segmentation-3.0
POWERSET_TO_COUNT = {0: 0, 1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3}


def _segmentationOutput(models: Models, samples: np.ndarray) -> np.ndarray:
	with torch.no_grad():
		x = torch.from_numpy(samples).unsqueeze(0).unsqueeze(0).to(next(models.pyannote.parameters()).device)
		out = models.pyannote(x)
	return out.argmax(dim=-1).squeeze(0).cpu().numpy()


def _nSpeakersActive(classes: np.ndarray) -> int:
	maxN = 0
	for c in classes:
		n = POWERSET_TO_COUNT.get(int(c), 0)
		if n > maxN:
			maxN = n
	return maxN


def _embed(models: Models, samples: np.ndarray) -> np.ndarray:
	with torch.no_grad():
		t = torch.from_numpy(samples).unsqueeze(0).to(models.titanet.device)
		lengths = torch.tensor([samples.shape[0]]).to(models.titanet.device)
		_, emb = models.titanet.forward(input_signal=t, input_signal_length=lengths)
	return emb.squeeze(0).cpu().numpy()


def _separate(models: Models, mixSamples: np.ndarray) -> list[np.ndarray]:
	n = mixSamples.shape[0]
	out = models.clearvoice(mixSamples[None, :])

	streams = []
	for s in out:
		stream = np.asarray(s, dtype=np.float32).squeeze()[:n]
		streams.append(stream)
	return streams


def _transcribe(models: Models, samples: np.ndarray) -> tuple[str, str]:
	segments, info = models.whisper.transcribe(samples, beam_size=5)
	text = " ".join(s.text for s in segments).strip()
	return text, info.language


def _translateIfNeeded(
	translator: Translator, text: str, srcLang: str, tgtLang: str, displayState: DisplayState
) -> str:
	if not text:
		return ""
	if srcLang == tgtLang:
		return text

	translated, ok = translator.translateWithRetry(text, srcLang, tgtLang)
	if not ok:
		displayState.setTranslationFailure(True)
	return translated


def _processSingle(window, models, db, translator, cfg, displayState):
	samples = np.asarray(window.samples, dtype=np.float32)
	emb = _embed(models, samples)
	m = db.match(emb)

	if m.highConf:
		db.adapt(m.label, emb)

	try:
		text, lang = _transcribe(models, samples)
	except Exception as e:
		logger.error("Whisper failed: {}", e)
		return

	if not text:
		return

	translated = _translateIfNeeded(translator, text, lang, cfg.targetLanguage, displayState)

	displayState.push(
		RenderedLine(
			speakerLabel=m.label,
			sourceLang=lang,
			originalText=text,
			translatedText=translated,
			timestampNs=window.startTimeNs,
		)
	)


def _processOverlap(window, models, db, translator, cfg, displayState):
	mixSamples = np.asarray(window.samples, dtype=np.float32)

	try:
		streams = _separate(models, mixSamples)
	except Exception as e:
		logger.error("Separation failed: {}", e)
		return

	for i, stream in enumerate(streams):
		try:
			emb = _embed(models, stream)
			m = db.match(emb)

			if m.highConf:
				db.adapt(m.label, emb)

			text, lang = _transcribe(models, stream)
			if not text:
				continue

			translated = _translateIfNeeded(translator, text, lang, cfg.targetLanguage, displayState)

			displayState.push(
				RenderedLine(
					speakerLabel=m.label,
					sourceLang=lang,
					originalText=text,
					translatedText=translated,
					timestampNs=window.startTimeNs,
				)
			)
		except Exception as e:
			logger.error("Failed processing stream {}: {}", i, e)
			continue


def processWindow(
	window, models: Models, db: CentroidDb, translator: Translator, cfg, displayState: DisplayState
) -> None:
	classes = _segmentationOutput(models, np.asarray(window.samples, dtype=np.float32))

	n = _nSpeakersActive(classes)
	if n == 0:
		return

	if n == 1:
		_processSingle(window, models, db, translator, cfg, displayState)
	else:
		_processOverlap(window, models, db, translator, cfg, displayState)
		if n >= 3:
			displayState.setCrosstalk(True)
