"""视觉处理器 - 图像理解与OCR"""

import base64

from shared.config import get_settings
from shared.utils import get_logger
from services.multimodal.router import BaseProcessor

logger = get_logger(__name__)


class VisionProcessor(BaseProcessor):
    """视觉处理器 - 基于通义千问VL实现图像理解"""

    def __init__(self):
        self._settings = get_settings()
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._settings.qwen_api_key,
                base_url=self._settings.qwen_base_url,
            )
        return self._client

    async def process(self, content: bytes | str, metadata: dict) -> dict:
        """处理图像输入，返回结构化理解结果"""
        if isinstance(content, bytes):
            b64_image = base64.b64encode(content).decode("utf-8")
            image_url = f"data:image/png;base64,{b64_image}"
        else:
            image_url = content

        client = await self._get_client()
        model = self._settings.qwen_vision_model

        prompt = metadata.get("prompt", "请详细描述这张图片的内容，提取其中的关键信息。如果包含文字、表格或数据，请完整提取。")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=2048,
            )

            description = response.choices[0].message.content or ""

            return {
                "description": description,
                "structured_content": description,
                "confidence": 0.9,
                "metadata": {
                    "model": model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                },
            }

        except Exception as e:
            logger.error("Vision processing failed", error=str(e))
            return {
                "description": "",
                "structured_content": "",
                "confidence": 0.0,
                "error": str(e),
            }
