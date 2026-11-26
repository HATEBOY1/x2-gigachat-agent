# local_asr.py
import json
import logging
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

# Укажите путь к распакованной модели Vosk
MODEL_PATH = r"C:\vosk\vosk-model-small-ru-0.22"

_model = None

def _get_model():
    global _model
    if _model is None:
        logger.info("Загрузка локальной модели Vosk из %s ...", MODEL_PATH)
        _model = Model(MODEL_PATH)
        logger.info("Модель Vosk загружена.")
    return _model

def transcribe(pcm_bytes: bytes) -> str:
    """Принимает сырые PCM-байты (16kHz, 16bit, mono) и возвращает распознанный текст."""
    model = _get_model()
    rec = KaldiRecognizer(model, 16000)
    
    # Vosk ожидает байты, можно скормить всё сразу в режиме after-commit
    rec.AcceptWaveform(pcm_bytes)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()
    logger.info("Локальный ASR распознал: %r", text)
    return text