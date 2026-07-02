import signal
import sys
import time

import httpx
from loguru import logger

from src._native import CaptureCfg, CaptureType, WasapiCapture
from src.centroids import CentroidDb
from src.cfg import CfgError, loadCfg
from src.core import PipelineThread
from src.display import DisplayState
from src.enroll import runEnrollment
from src.log import setupLogging
from src.models import loadAll
from src.translation import Translator


def _handleSigint(signum, frame) -> None:
	logger.info("SIGINT received, exiting")
	sys.exit(0)


def _probeLmStudio(baseUrl: str) -> None:
	url = baseUrl.rstrip("/") + "/v1/models"
	logger.info("probing LM Studio at {}", url)
	try:
		r = httpx.get(url, timeout=5.0)
		r.raise_for_status()
	except Exception as e:
		raise RuntimeError(f"LM Studio not reachable at {baseUrl} — start it first") from e
	logger.info("LM Studio reachable")


def _buildCaptureCfg(cfg) -> CaptureCfg:
	nCfg = CaptureCfg()
	nCfg.type = CaptureType.Desktop if cfg.capture.type == "desktop" else CaptureType.Process
	nCfg.pid = cfg.capture.pid if cfg.capture.pid is not None else 0
	return nCfg


def _renderLine(line, tgtLang: str) -> str:
	if line.sourceLang == tgtLang:
		return f"[{line.speakerLabel}] {line.originalText}"
	return f"[{line.speakerLabel}] ({line.sourceLang}→{tgtLang}) {line.translatedText}"


def _inputLoop(displayState: DisplayState, tgtLang: str) -> None:
	logger.info("entering input loop")
	while True:
		time.sleep(0.5)
		lines, crosstalk, failure = displayState.drainNew()

		for line in lines:
			print(_renderLine(line, tgtLang), file=sys.stderr, flush=True)

		if crosstalk:
			print("(crosstalk, accuracy reduced)", file=sys.stderr, flush=True)

		if failure:
			print("[warning] translation service unreachable", file=sys.stderr, flush=True)


def main() -> None:
	logPath = setupLogging()
	logger.info("Earshot starting, logging to {}", logPath)
	print(f"Earshot: logging to {logPath}", file=sys.stderr)

	try:
		cfg = loadCfg("config.yaml")
	except CfgError as e:
		logger.error("config error: {}", e)
		print(f"Config error: {e}", file=sys.stderr)
		sys.exit(1)

	signal.signal(signal.SIGINT, _handleSigint)

	try:
		_probeLmStudio(cfg.lmStudio.baseUrl)
	except RuntimeError as e:
		logger.error("{}", e)
		print(str(e), file=sys.stderr)
		sys.exit(1)

	print("Loading models...", file=sys.stderr)
	try:
		models = loadAll(cfg.cudaDeviceIndex)
	except Exception as e:
		logger.exception("model loading failed")
		print(f"Model loading failed: {e}", file=sys.stderr)
		sys.exit(1)
	print("Models loaded.", file=sys.stderr)

	try:
		cap = WasapiCapture(_buildCaptureCfg(cfg))
		cap.start()
		logger.info("capture started")
	except Exception as e:
		logger.exception("capture construction failed")
		print(f"Capture construction failed: {e}", file=sys.stderr)
		sys.exit(1)

	db = CentroidDb(cfg.thresholds)

	try:
		runEnrollment(cap, models.titanet, db, cfg.enrollment.speakerCount)
	except KeyboardInterrupt:
		logger.info("enrollment interrupted, exiting")
		sys.exit(0)

	print(f"\nEnrolled {len(db.all())} speaker(s). Starting pipeline...\n", file=sys.stderr)

	displayState = DisplayState()
	translator = Translator(cfg.lmStudio.baseUrl, cfg.lmStudio.model)

	pipeline = PipelineThread(cap, models, db, translator, cfg, displayState)
	pipeline.start()

	try:
		_inputLoop(displayState, cfg.targetLanguage)
	except KeyboardInterrupt:
		logger.info("input loop interrupted by KeyboardInterrupt, exiting")
		sys.exit(0)


if __name__ == "__main__":
	main()
