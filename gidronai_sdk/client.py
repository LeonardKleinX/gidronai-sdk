"""HTTP client for the GidronAI API."""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from gidronai_sdk.types import (
    AuthenticationError,
    GidronError,
    JobStatus,
    NotFoundError,
    RateLimitError,
    SceneJob,
    SceneResult,
    UsageInfo,
    ValidationError,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.gidronai.me/v1"
_DEFAULT_TIMEOUT = 60.0


class GidronClient:
    """Official Python client for the GidronAI API.

    Parameters
    ----------
    api_key : str
        Your GidronAI API key.
    base_url : str, optional
        API base URL. Defaults to ``https://api.gidronai.me/v1``.
    timeout : float, optional
        HTTP request timeout in seconds. Defaults to 60.
    max_retries : int, optional
        Number of automatic retries on transient failures. Defaults to 3.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise AuthenticationError("api_key must not be empty")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "gidronai-sdk/0.3.0",
            },
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make an HTTP request with retry logic and error mapping."""
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(method, path, **kwargs)

                if response.status_code == 200 or response.status_code == 201:
                    return response.json()

                body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                message = body.get("error", {}).get("message", response.text[:200])

                if response.status_code == 401:
                    raise AuthenticationError(message)
                elif response.status_code == 404:
                    raise NotFoundError(message)
                elif response.status_code == 422:
                    raise ValidationError(message, errors=body.get("error", {}).get("details", []))
                elif response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "60"))
                    if attempt < self._max_retries:
                        logger.warning("Rate limited. Sleeping %.1fs (attempt %d/%d)", retry_after, attempt + 1, self._max_retries)
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(retry_after=retry_after)
                elif response.status_code >= 500:
                    last_error = GidronError(message, status_code=response.status_code, response_body=body)
                    if attempt < self._max_retries:
                        backoff = 2 ** attempt
                        logger.warning("Server error %d. Retrying in %ds (attempt %d/%d)", response.status_code, backoff, attempt + 1, self._max_retries)
                        time.sleep(backoff)
                        continue
                    raise last_error
                else:
                    raise GidronError(message, status_code=response.status_code, response_body=body)

            except httpx.TransportError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    backoff = 2 ** attempt
                    logger.warning("Transport error: %s. Retrying in %ds", exc, backoff)
                    time.sleep(backoff)
                    continue
                raise GidronError(f"Connection failed after {self._max_retries} retries: {exc}") from exc

        raise last_error or GidronError("Unknown error")

    # -- Scene generation ---------------------------------------------------

    def generate_scene(
        self,
        scene_type: str = "urban_intersection",
        size: tuple[float, float, float] = (200, 200, 50),
        num_agents: int = 10,
        agent_behavior: str = "social_force",
        weather: str = "clear",
        time_of_day: str = "12:00",
        export_format: str = "coco",
        resolution: tuple[int, int] = (1920, 1080),
        num_frames: int = 500,
        physics_dt: float = 0.004167,
        **extra_params: Any,
    ) -> SceneJob:
        """Submit a scene generation job.

        Returns a ``SceneJob`` with the job ID and initial status.
        """
        payload = {
            "scene_type": scene_type,
            "size": list(size),
            "num_agents": num_agents,
            "agent_behavior": agent_behavior,
            "weather": weather,
            "time_of_day": time_of_day,
            "export_format": export_format,
            "resolution": list(resolution),
            "num_frames": num_frames,
            "physics_dt": physics_dt,
            **extra_params,
        }
        data = self._request("POST", "/scenes/generate", json=payload)
        return SceneJob(**data)

    def get_job(self, job_id: str) -> SceneJob:
        """Get the current status of a generation job."""
        data = self._request("GET", f"/jobs/{job_id}")
        return SceneJob(**data)

    def wait_for_job(
        self,
        job_id: str,
        timeout: float = 600,
        poll_interval: float = 5.0,
    ) -> SceneResult:
        """Block until a job reaches a terminal state.

        Parameters
        ----------
        job_id : str
            The job to wait for.
        timeout : float
            Maximum seconds to wait before raising TimeoutError.
        poll_interval : float
            Seconds between status polls.

        Returns
        -------
        SceneResult
            The completed job result.

        Raises
        ------
        TimeoutError
            If the job does not complete within the timeout.
        GidronError
            If the job fails.
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            job = self.get_job(job_id)
            logger.debug("Job %s status: %s", job_id, job.status.value)

            if job.status == JobStatus.COMPLETED:
                result_data = self._request("GET", f"/jobs/{job_id}/result")
                return SceneResult(**result_data)
            elif job.status == JobStatus.FAILED:
                raise GidronError(f"Job {job_id} failed", response_body=job.params)
            elif job.status == JobStatus.CANCELLED:
                raise GidronError(f"Job {job_id} was cancelled")

            time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SceneJob]:
        """List recent jobs, optionally filtered by status."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        data = self._request("GET", "/jobs", params=params)
        return [SceneJob(**j) for j in data.get("jobs", [])]

    def cancel_job(self, job_id: str) -> SceneJob:
        """Cancel a queued or running job."""
        data = self._request("POST", f"/jobs/{job_id}/cancel")
        return SceneJob(**data)

    # -- Data export --------------------------------------------------------

    def export_data(self, job_id: str, format: str = "coco") -> str:
        """Request dataset export in a specific format.

        Returns the download URL for the exported archive.
        """
        data = self._request("POST", f"/jobs/{job_id}/export", json={"format": format})
        return data["download_url"]

    def download(self, url: str, dest: str | Path = ".") -> Path:
        """Download a file from a GidronAI URL to a local path."""
        dest_path = Path(dest)
        if dest_path.is_dir():
            filename = url.split("/")[-1] or "download.tar.gz"
            dest_path = dest_path / filename

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            with dest_path.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        logger.info("Downloaded %s -> %s", url, dest_path)
        return dest_path

    # -- Account ------------------------------------------------------------

    def get_usage(self) -> UsageInfo:
        """Get usage information for the current billing period."""
        data = self._request("GET", "/usage")
        return UsageInfo(**data)

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> GidronClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
