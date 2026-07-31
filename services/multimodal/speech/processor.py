"""语音处理器 - 语音转写与合成"""

import tempfile
import os

from shared.config import get_settings
from shared.utils import get_logger
from services.multimodal.router import BaseProcessor

logger = get_logger(__name__)


class SpeechProcessor(BaseProcessor):
    """语音处理器 - 基于Whisper实现语音转写"""

    def __init__(self):
        self._settings = get_settings()
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        return self._client

    async def process(self, content: bytes | str, metadata: dict) -> dict:
        """处理语音输入，返回转写文本"""
        if isinstance(content, str):
            return {"text": content, "source": "text_passthrough"}

        client = await self._get_client()

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=metadata.get("language", "zh"),
                )

            os.unlink(tmp_path)

            return {
                "text": response.text,
                "language": metadata.get("language", "zh"),
                "confidence": 0.95,
                "metadata": {"model": "whisper-1"},
            }

        except Exception as e:
            logger.error("Speech processing failed", error=str(e))
            if "tmp_path" in locals():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return {"text": "", "confidence": 0.0, "error": str(e)}

    async def synthesize(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes | None:
        """文本转语音 - 基于Edge TTS"""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            return audio_data if audio_data else None

        except Exception as e:
            logger.error("TTS synthesis failed", error=str(e))
            return None
