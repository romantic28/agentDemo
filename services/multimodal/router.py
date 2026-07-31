"""模态路由器 - 识别输入类型并分发到对应处理器"""

from enum import Enum

from shared.schemas.message import ModalityType
from shared.utils import get_logger

logger = get_logger(__name__)


class ModalityRouter:
    """多模态路由器 - 根据输入类型分发到对应处理器"""

    def __init__(self):
        self._processors: dict[ModalityType, "BaseProcessor"] = {}

    def register_processor(self, modality: ModalityType, processor: "BaseProcessor") -> None:
        self._processors[modality] = processor
        logger.info("Processor registered", modality=modality.value)

    def detect_modality(self, content_type: str | None = None, filename: str | None = None) -> ModalityType:
        """根据MIME类型或文件名推断模态类型"""
        if content_type:
            if content_type.startswith("image/"):
                return ModalityType.IMAGE
            if content_type.startswith("audio/"):
                return ModalityType.AUDIO
            if content_type.startswith("video/"):
                return ModalityType.VIDEO
            if content_type in (
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ):
                return ModalityType.FILE

        if filename:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            image_exts = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"}
            audio_exts = {"mp3", "wav", "ogg", "flac", "m4a", "aac"}
            video_exts = {"mp4", "avi", "mov", "mkv", "webm"}
            file_exts = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "txt"}

            if ext in image_exts:
                return ModalityType.IMAGE
            if ext in audio_exts:
                return ModalityType.AUDIO
            if ext in video_exts:
                return ModalityType.VIDEO
            if ext in file_exts:
                return ModalityType.FILE

        return ModalityType.TEXT

    async def process(
        self, modality: ModalityType, content: bytes | str, metadata: dict | None = None
    ) -> dict:
        """将输入路由到对应处理器"""
        processor = self._processors.get(modality)
        if processor is None:
            logger.warning("No processor for modality", modality=modality.value)
            return {"type": modality.value, "content": str(content)[:1000], "raw": True}

        result = await processor.process(content, metadata or {})
        return {"type": modality.value, **result}


class BaseProcessor:
    """处理器基类"""

    async def process(self, content: bytes | str, metadata: dict) -> dict:
        raise NotImplementedError
