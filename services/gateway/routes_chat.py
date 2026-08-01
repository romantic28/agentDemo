"""对话交互路由"""

import base64
import json
import traceback
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticBaseModel

from shared.schemas.message import Message, MessageRole, ModalityType, ModalityContent, ConversationContext
from shared.utils import get_logger
from services.auth.jwt_handler import get_current_user

logger = get_logger(__name__)

router = APIRouter()


class ChatRequest(PydanticBaseModel):
    conversation_id: str | None = None
    content: str
    modality: ModalityType = ModalityType.TEXT


class ChatResponse(PydanticBaseModel):
    conversation_id: str
    message: Message
    task_id: str | None = None


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """处理用户对话请求，路由到核心编排层"""
    conversation_id = request.conversation_id or str(uuid4())
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    logger.info(
        "Chat request received",
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=user_id,
        modality=request.modality,
    )

    from services.orchestrator.service import process_message

    try:
        response_content = await process_message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
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


@router.post("/completions/stream")
async def chat_completions_stream(
    request: ChatRequest, raw_request: Request, current_user: dict = Depends(get_current_user)
):
    """流式对话端点，使用 Server-Sent Events 协议逐 token 返回"""
    conversation_id = request.conversation_id or str(uuid4())
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    logger.info(
        "Stream chat request received",
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    from services.orchestrator.service import stream_message

    async def event_generator():
        try:
            start_event = json.dumps({
                "event": "start",
                "conversation_id": conversation_id,
            })
            yield f"data: {start_event}\n\n"

            async for token in stream_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=request.content,
            ):
                if await raw_request.is_disconnected():
                    logger.info("Client disconnected", conversation_id=conversation_id)
                    break
                chunk = json.dumps({"event": "token", "data": token})
                yield f"data: {chunk}\n\n"

            done_event = json.dumps({"event": "done"})
            yield f"data: {done_event}\n\n"

        except Exception as e:
            logger.error("Stream error", error=str(e), tb=traceback.format_exc())
            error_event = json.dumps({"event": "error", "data": str(e)})
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(None),
    message: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """上传文件+用户消息，解析文件内容后结合用户指令流式返回LLM响应"""
    conv_id = conversation_id or str(uuid4())
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    logger.info(
        "File upload received",
        filename=file.filename,
        content_type=file.content_type,
        conversation_id=conv_id,
        tenant_id=tenant_id,
        user_id=user_id,
        user_message=message,
    )

    from services.multimodal.router import ModalityRouter
    from services.multimodal.service import create_modality_router
    from services.orchestrator.service import get_llm_router, stream_message
    from services.orchestrator.llm_router import ModelCapability

    file_content = await file.read()
    modality_router = create_modality_router()

    detected_modality = modality_router.detect_modality(
        content_type=file.content_type,
        filename=file.filename,
    )

    is_image = detected_modality == ModalityType.IMAGE

    if is_image:
        return await _handle_image_upload(file_content, file.filename, conv_id, message)

    return await _handle_document_upload(
        file_content, file.filename, conv_id, tenant_id, user_id, message, modality_router, detected_modality
    )


async def _handle_image_upload(
    file_content: bytes, filename: str, conv_id: str, message: str | None
):
    """图片走视觉模型做多模态问答"""
    from services.orchestrator.service import get_llm_router
    from services.orchestrator.llm_router import ModelCapability

    b64_image = base64.b64encode(file_content).decode("utf-8")
    content_type = "image/png"
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}
        content_type = mime_map.get(ext, "image/png")

    image_url = f"data:{content_type};base64,{b64_image}"
    user_text = message.strip() if message and message.strip() else "请详细描述这张图片的内容，提取其中的关键信息。"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }
    ]

    llm = get_llm_router()

    async def event_generator():
        yield f"data: {json.dumps({'event': 'start', 'conversation_id': conv_id})}\n\n"

        try:
            async for token in llm.stream(
                messages=messages, capability=ModelCapability.VISION
            ):
                yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
        except Exception as e:
            logger.error("Vision stream error", error=str(e), tb=traceback.format_exc())
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _handle_document_upload(
    file_content: bytes,
    filename: str,
    conv_id: str,
    tenant_id: str,
    user_id: str,
    message: str | None,
    modality_router,
    detected_modality,
):
    """文档类文件走文本提取+LLM分析"""
    from services.orchestrator.service import stream_message

    try:
        processing_result = await modality_router.process(
            modality=detected_modality,
            content=file_content,
            metadata={
                "filename": filename,
                "content_type": "",
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )
    except Exception as e:
        logger.error("Multimodal processing failed", error=str(e), filename=filename)
        processing_result = {"text": "", "error": str(e)}

    extracted_text = processing_result.get("text", "")

    if not extracted_text:
        error_msg = processing_result.get("error", "无法提取文件内容")

        async def error_stream():
            yield f"data: {json.dumps({'event': 'start', 'conversation_id': conv_id})}\n\n"
            yield f"data: {json.dumps({'event': 'error', 'data': f'文件解析失败: {error_msg}'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    max_len = 8000
    truncated = extracted_text[:max_len]
    if len(extracted_text) > max_len:
        truncated += "\n...(内容过长，已截断)"

    user_instruction = (
        message.strip()
        if message and message.strip()
        else "请对这份文件进行全面分析和总结，包括主要内容、关键信息、结构概述等。"
    )

    prompt = (
        f"用户上传了文件「{filename}」，以下是提取的文件内容：\n\n"
        f"---\n{truncated}\n---\n\n"
        f"用户的要求：{user_instruction}"
    )

    async def event_generator():
        yield f"data: {json.dumps({'event': 'start', 'conversation_id': conv_id})}\n\n"

        try:
            async for token in stream_message(
                conversation_id=conv_id,
                tenant_id=tenant_id,
                user_id=user_id,
                content=prompt,
            ):
                yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
        except Exception as e:
            logger.error("Stream error during file analysis", error=str(e))
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
