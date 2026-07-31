"""多模型路由服务 - 根据任务类型动态选择最优模型"""

from enum import Enum
from typing import AsyncIterator

from openai import AsyncOpenAI

from shared.config import get_settings
from shared.utils import get_logger

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    QWEN = "qwen"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class ModelCapability(str, Enum):
    REASONING = "reasoning"
    VISION = "vision"
    GENERAL = "general"
    CODE = "code"


# 默认路由表：千问作为主模型
MODEL_ROUTING_TABLE: dict[ModelCapability, ModelProvider] = {
    ModelCapability.REASONING: ModelProvider.QWEN,
    ModelCapability.VISION: ModelProvider.QWEN,
    ModelCapability.GENERAL: ModelProvider.QWEN,
    ModelCapability.CODE: ModelProvider.QWEN,
}


class LLMRouter:
    """LLM 多模型路由器"""

    def __init__(self):
        self._settings = get_settings()
        self._clients: dict[ModelProvider, AsyncOpenAI] = {}

    def _get_client(self, provider: ModelProvider) -> AsyncOpenAI:
        if provider not in self._clients:
            if provider == ModelProvider.QWEN:
                self._clients[provider] = AsyncOpenAI(
                    api_key=self._settings.qwen_api_key,
                    base_url=self._settings.qwen_base_url,
                )
            elif provider == ModelProvider.OPENAI:
                self._clients[provider] = AsyncOpenAI(
                    api_key=self._settings.openai_api_key,
                )
            elif provider == ModelProvider.DEEPSEEK:
                self._clients[provider] = AsyncOpenAI(
                    api_key=self._settings.deepseek_api_key,
                    base_url=self._settings.deepseek_base_url,
                )
        return self._clients[provider]

    def _get_model_name(self, provider: ModelProvider, capability: ModelCapability) -> str:
        if provider == ModelProvider.QWEN:
            if capability == ModelCapability.VISION:
                return self._settings.qwen_vision_model
            return self._settings.qwen_model
        elif provider == ModelProvider.OPENAI:
            return self._settings.openai_model
        return self._settings.deepseek_model

    def route(self, capability: ModelCapability) -> ModelProvider:
        return MODEL_ROUTING_TABLE.get(capability, ModelProvider.QWEN)

    async def complete(
        self,
        messages: list[dict],
        capability: ModelCapability = ModelCapability.GENERAL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> dict:
        provider = self.route(capability)
        client = self._get_client(provider)
        model = self._get_model_name(provider, capability)

        logger.info("LLM call", provider=provider.value, model=model, capability=capability.value)

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # qwen3 系列默认开启思考模式，返回 <think> 标签会干扰 JSON 解析
        if provider == ModelProvider.QWEN and "qwen3" in model.lower():
            kwargs["extra_body"] = {"enable_thinking": False}

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        return {
            "content": choice.message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in (choice.message.tool_calls or [])
            ],
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            "provider": provider.value,
            "model": model,
        }

    async def stream(
        self,
        messages: list[dict],
        capability: ModelCapability = ModelCapability.GENERAL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        provider = self.route(capability)
        client = self._get_client(provider)
        model = self._get_model_name(provider, capability)

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
