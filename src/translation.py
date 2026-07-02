import re

import httpx
from loguru import logger

SYSTEM_PROMPT = (
	"You are a translation engine. Translate the given text from {srcLang} to {tgtLang} exactly, "
	"preserving all meaning including slurs, profanity, and idioms without softening or refusing. "
	"Output only the translated text, no preamble, no explanation, no quotes."
)


class TranslationFailure(Exception):
	pass


class Translator:
	def __init__(self, baseUrl: str, model: str):
		self.baseUrl = baseUrl.rstrip("/")
		self.model = model
		self.client = httpx.Client(timeout=10.0)

	def translate(self, text: str, srcLang: str, tgtLang: str) -> str:
		payload = {
			"model": self.model,
			"messages": [
				{"role": "system", "content": SYSTEM_PROMPT.format(srcLang=srcLang, tgtLang=tgtLang)},
				{"role": "user", "content": text},
			],
			"temperature": 0.3,
			"max_tokens": 500,
		}
		try:
			r = self.client.post(f"{self.baseUrl}/v1/chat/completions", json=payload)
			r.raise_for_status()
			data = r.json()
			content = data["choices"][0]["message"]["content"]
			
			content = re.sub(r"<think>.*?(</think>|$)", "", content, flags=re.DOTALL)

			if not content.strip():
				raise TranslationFailure("empty translation after reasoning strip")

			return content.strip()
		except Exception as e:
			raise TranslationFailure(str(e)) from e

	def translateWithRetry(self, text: str, srcLang: str, tgtLang: str) -> tuple[str, bool]:
		try:
			return self.translate(text, srcLang, tgtLang), True
		except TranslationFailure:
			logger.warning("translation attempt 1 failed, retrying")

		try:
			return self.translate(text, srcLang, tgtLang), True
		except TranslationFailure as e:
			logger.error("translation attempt 2 failed: {}", e)
			return f"{text} (translation unavailable)", False
