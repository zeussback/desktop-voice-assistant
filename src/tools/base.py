"""Base classes and schemas for Jarvis tools."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ConfirmationPolicy(str, Enum):
    """Execution policy for tools."""
    IMMEDIATE = "immediate"                  # Execute immediately without confirmation
    REQUIRE_CONFIRMATION = "confirmation"     # Must prompt user for spoken confirmation first


class ToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool = True
    message: str = Field(description="Spoken message or summary for Jarvis to speak")
    data: Optional[Dict[str, Any]] = None
    needs_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class BaseTool(ABC):
    """Abstract base class for all tools."""
    name: str
    description: str
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.IMMEDIATE

    @abstractmethod
    def get_declaration(self) -> Dict[str, Any]:
        """Return the function declaration schema suitable for Gemini Tool calling."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""
        pass
