"""多模态路由器单元测试"""

import pytest

from shared.schemas.message import ModalityType
from services.multimodal.router import ModalityRouter, BaseProcessor


class MockProcessor(BaseProcessor):
    async def process(self, content, metadata):
        return {"processed": True, "content_type": type(content).__name__}


@pytest.fixture
def router():
    r = ModalityRouter()
    r.register_processor(ModalityType.IMAGE, MockProcessor())
    r.register_processor(ModalityType.AUDIO, MockProcessor())
    r.register_processor(ModalityType.FILE, MockProcessor())
    return r


def test_detect_modality_by_content_type(router):
    assert router.detect_modality(content_type="image/png") == ModalityType.IMAGE
    assert router.detect_modality(content_type="audio/wav") == ModalityType.AUDIO
    assert router.detect_modality(content_type="video/mp4") == ModalityType.VIDEO
    assert router.detect_modality(content_type="application/pdf") == ModalityType.FILE
    assert router.detect_modality(content_type="text/plain") == ModalityType.TEXT


def test_detect_modality_by_filename(router):
    assert router.detect_modality(filename="photo.jpg") == ModalityType.IMAGE
    assert router.detect_modality(filename="record.mp3") == ModalityType.AUDIO
    assert router.detect_modality(filename="clip.mp4") == ModalityType.VIDEO
    assert router.detect_modality(filename="report.pdf") == ModalityType.FILE
    assert router.detect_modality(filename="data.xlsx") == ModalityType.FILE
    assert router.detect_modality(filename="notes.txt") == ModalityType.FILE


def test_detect_modality_default(router):
    assert router.detect_modality() == ModalityType.TEXT
    assert router.detect_modality(filename="unknown") == ModalityType.TEXT


@pytest.mark.anyio
async def test_process_with_registered_processor(router):
    result = await router.process(ModalityType.IMAGE, b"fake_image_data", {})
    assert result["type"] == "image"
    assert result["processed"] is True


@pytest.mark.anyio
async def test_process_without_processor(router):
    result = await router.process(ModalityType.VIDEO, b"fake_video", {})
    assert result["type"] == "video"
    assert result["raw"] is True
