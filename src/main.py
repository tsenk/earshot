import signal
import sys

from loguru import logger

from src.cfg import CfgError, loadCfg
from src.log import setupLogging


def _handleSigint(signum, frame) -> None:
	logger.info("SIGINT received, exiting")
	sys.exit(0)


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

	logger.info(
		"config loaded: capture={} target={} speakerCount={}",
		cfg.capture.type,
		cfg.targetLanguage,
		cfg.enrollment.speakerCount,
	)

	signal.signal(signal.SIGINT, _handleSigint)
	logger.debug("SIGINT handler installed")

	logger.info("LM Studio probe skipped")
	print("Probe LM Studio here", file=sys.stderr)

	logger.info("model loading skipped")
	print("Load models here", file=sys.stderr)

	logger.info("Startup complete, exiting")
	print("Startup complete. Exiting.", file=sys.stderr)


if __name__ == "__main__":
	main()
