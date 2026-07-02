import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedLine:
	speakerLabel: str
	sourceLang: str
	originalText: str
	translatedText: str
	timestampNs: int


class DisplayState:
	def __init__(self):
		self.lines: list[RenderedLine] = []
		self.crosstalk: bool = False
		self.translationFailure: bool = False
		self.lock = threading.Lock()

	def push(self, line: RenderedLine) -> None:
		with self.lock:
			self.lines.append(line)

	def setCrosstalk(self, on: bool) -> None:
		with self.lock:
			self.crosstalk = on

	def setTranslationFailure(self, on: bool) -> None:
		with self.lock:
			self.translationFailure = on

	def drainNew(self) -> tuple[list[RenderedLine], bool, bool]:
		with self.lock:
			new = self.lines[:]
			self.lines.clear()
			crosstalk = self.crosstalk
			failure = self.translationFailure
			self.crosstalk = False
			self.translationFailure = False
		return new, crosstalk, failure
