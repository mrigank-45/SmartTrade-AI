from typing import Any, Optional

from langchain_groq import ChatGroq

from .base_client import BaseLLMClient, normalize_content
from .validators import validate_model


class NormalizedChatGroq(ChatGroq):
    """ChatGroq with normalized content output."""

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))


class GroqClient(BaseLLMClient):
    """Client for Groq-hosted models with strict parameter whitelisting."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        """Return configured ChatGroq instance with capability-based filtering."""
        llm_kwargs = {
            "model": self.model,
            "api_key": self.kwargs.get("groq_api_key") or self.kwargs.get("api_key")
        }

        # Standard parameters safe for ALL models
        for key in ("timeout", "max_retries", "callbacks", "temperature", "max_tokens"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]
        
        if self.base_url:
            llm_kwargs["base_url"] = self.base_url

        # Logic for Reasoning/Thinking parameters
        thinking_level = self.kwargs.get("thinking_level")
        model_lower = self.model.lower()

        # 1. Define Model Capabilities (2026 Production Standards)
        # These models support the <think> blocks and reasoning_format
        reasoning_capable_models = ("gpt-oss", "deepseek-r1", "qwen-qwq", "qwen3")
        
        # These models specifically support the reasoning_effort parameter
        effort_capable_models = ("gpt-oss", "qwen-qwq", "qwen3")

        is_reasoning_model = any(m in model_lower for m in reasoning_capable_models)
        supports_effort = any(m in model_lower for m in effort_capable_models)

        # 2. Only apply "Thinking" params if the model supports them
        if thinking_level and is_reasoning_model:
            # FIX: Only send reasoning_format to models that support CoT
            llm_kwargs["reasoning_format"] = "parsed"
            
            if supports_effort:
                # Map specific levels for GPT-OSS and Qwen
                if "qwen" in model_lower:
                    llm_kwargs["reasoning_effort"] = "none" if thinking_level == "minimal" else "default"
                else:
                    llm_kwargs["reasoning_effort"] = "low" if thinking_level == "minimal" else thinking_level
            # Note: DeepSeek-R1 ignores reasoning_effort but accepts reasoning_format
        
        # 3. If it's a standard Llama model, we ignore 'thinking_level' entirely 
        # to prevent the 400 Bad Request error you encountered.

        return NormalizedChatGroq(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for Groq."""
        return validate_model("groq", self.model)