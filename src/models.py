from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass(frozen=True)
class Models:
	pyannote: Any
	titanet: Any
	clearvoice: Any
	whisper: Any


def loadPyannote(deviceIndex: int) -> Any:
	import torch
	from pyannote.audio import Model

	logger.info("loading Pyannote segmentation-3.0")
	m = Model.from_pretrained("pyannote/segmentation-3.0")
	m.to(torch.device(f"cuda:{deviceIndex}"))
	m.eval()
	return m


def loadTitanet(deviceIndex: int) -> Any:
	import torch
	from nemo.collections.asr.models import EncDecSpeakerLabelModel

	logger.info("loading TitaNet-Large")
	m = EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")
	m.to(torch.device(f"cuda:{deviceIndex}"))
	m.eval()
	return m


def loadClearVoice(deviceIndex: int) -> Any:
	from clearvoice import ClearVoice

	logger.info("loading ClearerVoice speech separation")
	m = ClearVoice(task="speech_separation", model_names=["MossFormer2_SS_16K"])
	return m


def loadWhisper(deviceIndex: int) -> Any:
	from faster_whisper import WhisperModel

	logger.info("loading faster-whisper large-v3-turbo")
	m = WhisperModel("large-v3-turbo", device="cuda", device_index=deviceIndex, compute_type="int8_float16")
	return m


def loadAll(deviceIndex: int) -> Models:
	pyannote = loadPyannote(deviceIndex)
	titanet = loadTitanet(deviceIndex)
	clearvoice = loadClearVoice(deviceIndex)
	whisper = loadWhisper(deviceIndex)
	logger.info("all models loaded")
	return Models(pyannote=pyannote, titanet=titanet, clearvoice=clearvoice, whisper=whisper)
