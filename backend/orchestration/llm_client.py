"""
ORCA LLM Client Abstraction — Phase 4
Provider-agnostic interface for structured generation and text synthesis.
Supports MockLLMClient for testing, OpenAILLMClient, GeminiLLMClient, and Generic HTTP endpoints.
"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Dict, Any, Callable
import json
import os
import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMClientError(Exception):
    """Raised when an LLM provider encounters an unrecoverable API error or validation failure."""
    pass


class LLMClient(ABC):
    """
    Abstract interface for LLM capabilities.
    The planner and synthesizer interact solely through this abstraction.
    """

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Request the LLM to generate output conforming strictly to the Pydantic schema T.

        Args:
            prompt: User/Task prompt with context and input data.
            schema: Pydantic model class to parse and validate into.
            system_prompt: Optional system grounding prompt.

        Returns:
            Validated instance of T.

        Raises:
            LLMClientError: If the LLM fails, times out, or returns invalid schema JSON.
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        """
        Request free-form text response from the LLM (e.g., natural-language synthesis).

        Args:
            prompt: Task prompt containing factual grounding.
            system_prompt: System role and instructions.
            max_tokens: Max completion tokens.

        Returns:
            Cleaned natural-language string.

        Raises:
            LLMClientError: If invocation fails.
        """
        pass


class MockLLMClient(LLMClient):
    """
    Deterministic mock client for testing.
    Can be configured with fixed responses, schemas, or callable hooks.
    Ensures unit and integration tests do not depend on external network APIs or billing keys.
    """

    def __init__(
        self,
        structured_response: Optional[BaseModel] = None,
        text_response: Optional[str] = None,
        structured_handler: Optional[Callable[[str, Type[BaseModel]], BaseModel]] = None,
        text_handler: Optional[Callable[[str], str]] = None,
        should_fail: bool = False,
        failure_message: str = "Simulated mock LLM failure",
    ):
        self.structured_response = structured_response
        self.text_response = text_response or "Mocked synthesized natural language response."
        self.structured_handler = structured_handler
        self.text_handler = text_handler
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.call_history: list = []

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        self.call_history.append({"type": "structured", "prompt": prompt, "schema": schema})
        if self.should_fail:
            raise LLMClientError(self.failure_message)

        if self.structured_handler:
            result = self.structured_handler(prompt, schema)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
            if isinstance(result, str):
                return schema.model_validate_json(result)

        if self.structured_response is not None:
            if isinstance(self.structured_response, schema):
                return self.structured_response
            if isinstance(self.structured_response, dict):
                return schema.model_validate(self.structured_response)
            if isinstance(self.structured_response, str):
                return schema.model_validate_json(self.structured_response)

        raise LLMClientError(
            f"MockLLMClient has no structured response or handler configured for schema {schema.__name__}"
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        self.call_history.append({"type": "text", "prompt": prompt, "system_prompt": system_prompt})
        if self.should_fail:
            raise LLMClientError(self.failure_message)

        if self.text_handler:
            return self.text_handler(prompt)

        return self.text_response


class OpenAILLMClient(LLMClient):
    """
    OpenAI API implementation using JSON mode / structured schema generation.
    Compatible with OpenAI and standard OpenAI-compatible endpoints (vLLM, Ollama, Groq).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.api_key:
            raise LLMClientError("OPENAI_API_KEY is not configured.")

        schema_json = json.dumps(schema.model_json_schema())
        system = (system_prompt or "") + (
            f"\n\nYou MUST respond with valid JSON strictly conforming to this JSON Schema:\n{schema_json}"
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if res.status_code != 200:
                    raise LLMClientError(f"OpenAI API returned HTTP {res.status_code}: {res.text}")

                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return schema.model_validate_json(content)
        except ValidationError as ve:
            raise LLMClientError(f"Model output violated required schema {schema.__name__}: {str(ve)}")
        except Exception as e:
            if isinstance(e, LLMClientError):
                raise
            raise LLMClientError(f"OpenAI request failed: {str(e)}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> str:
        if not self.api_key:
            raise LLMClientError("OPENAI_API_KEY is not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if res.status_code != 200:
                    raise LLMClientError(f"OpenAI API returned HTTP {res.status_code}: {res.text}")

                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMClientError(f"OpenAI text generation failed: {str(e)}")


def get_default_llm_client() -> Optional[LLMClient]:
    """
    Returns configured LLM client from environment, or None if no keys configured.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return OpenAILLMClient(api_key=openai_key)
    return None
