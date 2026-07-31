"""多模态服务初始化 - 注册所有处理器"""

from shared.schemas.message import ModalityType
from services.multimodal.router import ModalityRouter
from services.multimodal.vision.processor import VisionProcessor
from services.multimodal.speech.processor import SpeechProcessor
from services.multimodal.file.processor import FileProcessor


def create_modality_router() -> ModalityRouter:
    """创建并配置模态路由器"""
    router = ModalityRouter()
    router.register_processor(ModalityType.IMAGE, VisionProcessor())
    router.register_processor(ModalityType.AUDIO, SpeechProcessor())
    router.register_processor(ModalityType.FILE, FileProcessor())
    return router
