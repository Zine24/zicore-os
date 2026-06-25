"""
Voice Engine - Speech Recognition + Text-to-Speech
Uses: whisper (STT), pyttsx3 (TTS), websockets for remote
"""
import os
import sys
import logging
import tempfile
import wave
import json
import asyncio
from pathlib import Path

logger = logging.getLogger("zicore.agent.voice")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class VoiceEngine:
    def __init__(self):
        self.tts_engine = None
        self.whisper_model = None
        self._init_tts()

    def _init_tts(self):
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty("voices")
            if voices:
                self.tts_engine.setProperty("voice", voices[0].id)
            self.tts_engine.setProperty("rate", 170)
            self.tts_engine.setProperty("volume", 0.9)
            logger.info("TTS engine initialized")
        except Exception as e:
            logger.warning(f"pyttsx3 not available: {e}")
            self.tts_engine = None

    def text_to_speech(self, text: str, save_path: str = None) -> dict:
        if not self.tts_engine:
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
            except ImportError:
                return {"error": "pyttsx3 not installed", "text": text, "status": "no_tts"}

        if save_path is None:
            save_path = str(OUTPUT_DIR / f"speech_{int(time.time())}.wav")

        try:
            self.tts_engine.save_to_file(text, save_path)
            self.tts_engine.runAndWait()
            return {"file": save_path, "text": text, "status": "ok"}
        except Exception as e:
            return {"error": str(e), "text": text, "status": "error"}

    def speech_to_text(self, audio_path: str = None) -> dict:
        if audio_path is None:
            audio_path = self._record_audio()

        if not audio_path:
            return {"error": "No audio available", "text": ""}

        if self.whisper_model is None:
            try:
                import whisper
                self.whisper_model = whisper.load_model("base")
            except ImportError:
                return {"error": "whisper not installed", "text": "", "hint": "pip install openai-whisper"}
            except Exception as e:
                return {"error": f"whisper load failed: {e}", "text": ""}

        try:
            result = self.whisper_model.transcribe(audio_path)
            return {"text": result["text"], "language": result.get("language", "?"), "status": "ok"}
        except Exception as e:
            return {"error": str(e), "text": ""}

    def _record_audio(self, duration: int = 5) -> str:
        try:
            import pyaudio
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            CHUNK = 1024
            RECORD_SECONDS = duration
            output_path = str(OUTPUT_DIR / f"recording_{int(time.time())}.wav")

            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                          input=True, frames_per_buffer=CHUNK)
            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()

            wf = wave.open(output_path, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            return output_path
        except ImportError:
            logger.warning("pyaudio not available for recording")
            return ""
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return ""
