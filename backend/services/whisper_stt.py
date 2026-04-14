"""
Whisper Speech-to-Text Service
================================
Uses faster-whisper (tiny model, CPU) for local offline transcription.
Converts browser WebM/Opus audio to WAV via ffmpeg before feeding to Whisper.
"""

import os
import subprocess
import tempfile
import logging

logger = logging.getLogger("whisper_stt")

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("Whisper tiny loaded (faster-whisper, cpu/int8)")
        return _model
    except Exception as e:
        logger.error(f"faster-whisper load failed: {e}")
        return None


def is_whisper_available() -> bool:
    return _load_model() is not None


def _convert_to_wav(input_path: str) -> str:
    """Convert any audio format (webm, ogg, mp4, etc.) to 16kHz mono WAV using ffmpeg."""
    output_path = input_path + ".wav"
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", "16000",   # 16kHz sample rate
                "-ac", "1",       # mono
                "-f", "wav",
                output_path,
            ],
            capture_output=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr.decode()}")
            return input_path  # fall back to original
        return output_path
    except Exception as e:
        logger.error(f"ffmpeg conversion failed: {e}")
        return input_path


async def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """
    Transcribe audio bytes to text.
    Accepts any browser MediaRecorder output (webm/opus, ogg, wav, mp4).
    Returns the transcribed string.
    """
    model = _load_model()
    if model is None:
        raise RuntimeError("Whisper model unavailable")

    if len(audio_bytes) < 500:
        return ""  # too short to contain speech

    # Pick suffix from content-type
    if "wav" in content_type:
        suffix = ".wav"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "mp4" in content_type:
        suffix = ".mp4"
    else:
        suffix = ".webm"  # default — browser MediaRecorder

    wav_path = None
    tmp_path = None
    try:
        # Write raw audio to temp file
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Convert to 16kHz WAV (Whisper works best with this)
        if suffix != ".wav":
            wav_path = _convert_to_wav(tmp_path)
        else:
            wav_path = tmp_path

        # Transcribe
        segments, info = model.transcribe(
            wav_path,
            language="en",
            beam_size=3,
            vad_filter=True,           # skip silence
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        
        # Filter common whisper-tiny silence hallucinations
        hallucinations = {"auto", "auto.", "ambo", "ambo.", "thank you.", "thank you", "you", "you.", "ah.", "ah", "bye.", "bye"}
        if text.lower() in hallucinations:
            logger.info(f"Filtered whisper hallucination: '{text}'")
            return ""

        logger.info(f"Transcribed {len(audio_bytes)} bytes → '{text[:80]}'")
        return text

    finally:
        for p in [tmp_path, wav_path]:
            if p and os.path.exists(p) and p != tmp_path:
                os.unlink(p)
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
