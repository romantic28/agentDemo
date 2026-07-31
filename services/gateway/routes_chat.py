"""对话交互路由"""

import traceback
from uuid import UUID, uuid4

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel as PydanticBaseModel

from shared.schemas.message import Message, MessageRole, ModalityType, ModalityContent, ConversationContext
from shared.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ChatRequest(PydanticBaseModel):
    conversation_id: UUID | None = None
    tenant_id: str = "default"
    user_id: str = "anonymous"
    content: str
    modality: ModalityType = ModalityType.TEXT


class ChatResponse(PydanticBaseModel):
    conversation_id: UUID
    message: Message
    task_id: UUID | None = None


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """处理用户对话请求，路由到核心编排层"""
    conversation_id = request.conversation_id or uuid4()

    logger.info(
        "Chat request received",
        conversation_id=str(conversation_id),
        tenant_id=request.tenant_id,
        modality=request.modality,
    )

    from services.orchestrator.service import process_message

    try:
        response_content = await process_message(
            conversation_id=str(conversation_id),
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            content=request.content,
        )
    except Exception as e:
        logger.error("Orchestrator error", error=str(e), tb=traceback.format_exc())
        response_content = f"[Agent] 收到您的消息: {request.content}"

    response_message = Message(
        role=MessageRole.ASSISTANT,
        content=response_content,
        modalities=[ModalityContent(type=ModalityType.TEXT, content=response_content)],
    )

    return ChatResponse(
        conversation_id=conversation_id,
        message=response_message,
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: UUID | None = Form(None),
    tenant_id: str = Form("default"),
    user_id: str = Form("anonymous"),
):
    """处理文件/图像/音频上传"""
    conv_id = conversation_id or uuid4()

    logger.info(
        "File upload received",
        filename=file.filename,
        content_type=file.content_type,
        conversation_id=str(conv_id),
    )

    return {
        "conversation_id": conv_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "status": "received",
    }
