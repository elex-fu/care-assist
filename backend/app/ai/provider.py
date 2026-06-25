"""AI Provider abstract interface."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Union


class AIProvider(ABC):
    """Abstract interface for AI providers.

    All providers must implement chat, image analysis and summary generation.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Union[AsyncIterator[str], str]:
        """Generic chat completion interface.

        Args:
            messages: OpenAI/Anthropic format message list [{role, content}, ...].
            stream: Whether to stream the response.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            If stream=True: async iterator yielding text chunks.
            If stream=False: complete response string.
        """
        pass

    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """Analyze an image and return structured extraction.

        Args:
            image_url: Publicly accessible URL of the image.
            prompt: Analysis prompt.

        Returns:
            JSON string containing extracted structured data.
        """
        pass

    @abstractmethod
    async def generate_summary(self, context: dict) -> str:
        """Generate a summary from context.

        Args:
            context: Dict containing member info, indicators, abnormal items, etc.

        Returns:
            Markdown formatted summary text.
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass
