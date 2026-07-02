import threading

from loguru import logger

from src.centroids import CentroidDb
from src.display import DisplayState
from src.inference import processWindow
from src.models import Models
from src.translation import Translator


class PipelineThread:
	def __init__(self, cap, models: Models, db: CentroidDb, translator: Translator, cfg, displayState: DisplayState):
		self.cap = cap
		self.models = models
		self.db = db
		self.translator = translator
		self.cfg = cfg
		self.displayState = displayState
		self.thread = threading.Thread(target=self._run, name="earshot-pipeline", daemon=True)

	def start(self) -> None:
		self.thread.start()
		logger.info("pipeline thread started")

	def _run(self) -> None:
		try:
			while True:
				try:
					window = self.cap.getNextWindow()
				except Exception as e:
					logger.error("getNextWindow failed, pipeline exiting: {}", e)
					return

				try:
					processWindow(window, self.models, self.db, self.translator, self.cfg, self.displayState)
				except Exception as e:
					logger.exception("processWindow failed: {}", e)
		except Exception as e:
			logger.exception("pipeline thread crashed: {}", e)
