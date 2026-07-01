import logging
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger


class InterceptHandler(logging.Handler):
	def emit(self, record: logging.LogRecord) -> None:
		try:
			level = logger.level(record.levelname).name
		except ValueError:
			level = record.levelno

		frame, depth = logging.currentframe(), 2
		while frame and frame.f_code.co_filename == logging.__file__:
			frame = frame.f_back
			depth += 1

		logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setupLogging() -> Path:
	logger.remove()

	timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	logDir = Path("logs")
	logDir.mkdir(exist_ok=True)
	logPath = logDir / f"{timestamp}.log"

	logger.add(
		logPath,
		level="DEBUG",
		format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
		enqueue=True,
	)

	logger.add(
		sys.stderr,
		level="ERROR",
		format="<red>{level}</red> | {name}:{function}:{line} - {message}",
		colorize=True,
	)

	logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

	for name in ["urllib3", "httpx", "asyncio", "matplotlib"]:
		logging.getLogger(name).setLevel(logging.WARNING)

	return logPath
