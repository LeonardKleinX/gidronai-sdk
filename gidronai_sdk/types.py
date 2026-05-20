"""Data models and exception types for the GidronAI SDK."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Possible states of a scene generation job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SceneJob(BaseModel):
    """Represents a submitted scene generation job."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.QUEUED)
    scene_type: str = Field(..., description="Type of scene being generated")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


class SceneResult(BaseModel):
    """Result of a completed scene generation job."""

    job_id: str
    status: JobStatus = JobStatus.COMPLETED
    output_url: str = Field(..., description="URL to download the generated dataset")
    frame_count: int = Field(0, description="Number of frames generated")
    scene_type: str = ""
    duration_seconds: float = Field(0.0, description="Wall-clock generation time")
    metadata: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def frames_per_second(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return self.frame_count / self.duration_seconds


class UsageInfo(BaseModel):
    """Billing period usage information."""

    period_start: datetime
    period_end: datetime
    jobs_submitted: int = 0
    frames_generated: int = 0
    compute_seconds: float = 0.0
    storage_bytes: int = 0
    plan: str = "free"

    @property
    def storage_gb(self) -> float:
        return self.storage_bytes / (1024 ** 3)


class GidronError(Exception):
    """Base exception for GidronAI API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_body: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}


class AuthenticationError(GidronError):
    """Raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(GidronError):
    """Raised when the API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float = 60.0,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class NotFoundError(GidronError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "resource") -> None:
        super().__init__(f"{resource} not found", status_code=404)


class ValidationError(GidronError):
    """Raised when request parameters fail validation."""

    def __init__(self, message: str = "Validation error", errors: list[str] | None = None) -> None:
        super().__init__(message, status_code=422)
        self.errors = errors or []
