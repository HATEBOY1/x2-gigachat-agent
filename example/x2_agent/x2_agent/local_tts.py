import asyncio
import logging
import os
import tempfile
import wave
import pyttsx3
import audioop  # Встроен в Python 3.10. Если у вас 3.13+, замените на pip install audioop-lts

logger = logging.getLogger(__name__)

# Размер фрагмента для отправки в Unity (в сэмплах) ~200 мс при 16kHz
CHUNK_SAMPLES = 3200


async def local_tts_stream(text: str, *args, **kwargs):
    """
    Асинхронный генератор PCM-фрагментов (bytes) с частотой 16000 Гц.
    Совместим с тем, как agent.py использует speech_stream.
    """
    if not text.strip():
        return

    # 1. Генерация WAV через pyttsx3 (блокирующая операция — выносим в executor)
    loop = asyncio.get_running_loop()
    wav_path, temp_files = await loop.run_in_executor(None, _synthesize_to_16k_wav, text)

    try:
        # 2. Чтение WAV и отправка фрагментами
        with wave.open(wav_path, "rb") as wf:
            # Проверяем параметры (должны быть 16000 Гц, 16bit, mono)
            if wf.getframerate() != 16000 or wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                logger.warning(
                    "Параметры WAV (%d Hz, %d ch, %d bytes) всё ещё не 16k/1ch/16bit!",
                    wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
                )

            total_frames = wf.getnframes()
            frames_read = 0
            while frames_read < total_frames:
                frames = wf.readframes(CHUNK_SAMPLES)
                if not frames:
                    break
                frames_read += CHUNK_SAMPLES
                yield frames
                # Небольшая пауза, чтобы не заблокировать event loop
                await asyncio.sleep(0)
    finally:
        # Удаляем временные файлы
        for path in temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass


def _synthesize_to_16k_wav(text: str) -> tuple[str, list[str]]:
    """Синтезирует текст, конвертирует в 16kHz и возвращает путь к файлу и список временных файлов."""
    # Создаём временный файл для исходного WAV (22050 Гц)
    fd, raw_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    engine = pyttsx3.init()
    
    # Попытка выбрать русский голос
    voices = engine.getProperty("voices")
    selected = None
    for v in voices:
        info = f"{v.id} {v.name} {v.languages}".lower()
        if "ru" in info or "russian" in info or "рус" in info:
            selected = v.id
            break
    if selected:
        engine.setProperty("voice", selected)
    else:
        logger.warning("Русский голос не найден в системе. Будет использован голос по умолчанию.")
    
    engine.setProperty("rate", 180)
    engine.save_to_file(text, raw_path)
    engine.runAndWait()
    engine.stop()

    # Конвертация в 16kHz
    fd, target_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    _convert_to_16k(raw_path, target_path)
    
    return target_path, [raw_path, target_path]


def _convert_to_16k(src_path: str, dst_path: str):
    """Конвертирует WAV из 22050 Гц в 16000 Гц, 1 канал, 16 бит."""
    try:
        with wave.open(src_path, "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(params.nframes)
            
            # Если частота уже 16000 и параметры совпадают, просто копируем
            if params.framerate == 16000 and params.nchannels == 1 and params.sampwidth == 2:
                with wave.open(dst_path, "wb") as out:
                    out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                    out.writeframes(frames)
                return

            # Конвертируем частоту
            converted, _ = audioop.ratecv(frames, params.sampwidth, params.nchannels, params.framerate, 16000, None)
            
            # Если стерео, конвертируем в моно (на всякий случай)
            if params.nchannels == 2:
                converted = audioop.tomono(converted, params.sampwidth, 0.5, 0.5)
                
            with wave.open(dst_path, "wb") as out:
                out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                out.writeframes(converted)
                
    except Exception as e:
        logger.error(f"Ошибка конвертации WAV: {e}")
        # В случае ошибки просто копируем исходный файл
        with open(src_path, "rb") as f_in, open(dst_path, "wb") as f_out:
            f_out.write(f_in.read())