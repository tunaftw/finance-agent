"""Audio file downloader for PodStock.

This module handles downloading podcast audio files with progress indication.
Supports resume for interrupted downloads and automatic retries.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import requests
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from podstock.core.exceptions import DownloadError
from podstock.core.models import Episode

# Default settings
DEFAULT_TIMEOUT = 300  # 5 minutes
DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 5  # seconds

# User-Agent header to avoid blocks from podcast hosts (Acast, Buzzsprout, etc.)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _get_filename_from_episode(episode: Episode) -> str:
    """Generate a filename for an episode.

    Args:
        episode: Episode to generate filename for.

    Returns:
        Filename string (e.g., "bp-2024-12-18-a1b2.mp3").
    """
    # Get extension from URL
    url_path = str(episode.audio_url).split("?")[0]  # Remove query params
    extension = Path(url_path).suffix or ".mp3"

    return f"{episode.id}{extension}"


def download_episode(
    episode: Episode,
    dest_dir: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    show_progress: bool = True,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    """Download an episode's audio file.

    Args:
        episode: Episode to download.
        dest_dir: Directory to save the file.
        timeout: Request timeout in seconds.
        chunk_size: Size of download chunks.
        retry_attempts: Number of retry attempts on failure.
        show_progress: Whether to show progress bar.
        progress_callback: Optional callback(downloaded, total) for progress.

    Returns:
        Path to the downloaded file.

    Raises:
        DownloadError: If download fails after all retries.

    Example:
        >>> path = download_episode(episode, Path("data/audio/borspodden"))
        >>> path.exists()
        True
    """
    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = _get_filename_from_episode(episode)
    dest_path = dest_dir / filename
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

    url = str(episode.audio_url)
    last_error: Exception | None = None

    for attempt in range(retry_attempts):
        try:
            _download_file(
                url=url,
                dest_path=dest_path,
                temp_path=temp_path,
                timeout=timeout,
                chunk_size=chunk_size,
                show_progress=show_progress,
                progress_callback=progress_callback,
                episode_title=episode.title,
            )
            return dest_path

        except (requests.RequestException, OSError) as e:
            last_error = e
            if attempt < retry_attempts - 1:
                time.sleep(DEFAULT_RETRY_DELAY)
            # Clean up partial download
            if temp_path.exists():
                temp_path.unlink()

    raise DownloadError(f"Failed to download after {retry_attempts} attempts: {last_error}")


def _download_file(
    url: str,
    dest_path: Path,
    temp_path: Path,
    timeout: int,
    chunk_size: int,
    show_progress: bool,
    progress_callback: Callable[[int, int], None] | None,
    episode_title: str,
) -> None:
    """Internal function to download a file.

    Args:
        url: URL to download.
        dest_path: Final destination path.
        temp_path: Temporary path during download.
        timeout: Request timeout.
        chunk_size: Download chunk size.
        show_progress: Whether to show progress bar.
        progress_callback: Optional progress callback.
        episode_title: Title for progress display.

    Raises:
        requests.RequestException: On network errors.
        OSError: On file system errors.
    """
    # Check if file already exists and is complete
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    resume_position = 0

    if temp_path.exists():
        resume_position = temp_path.stat().st_size
        headers["Range"] = f"bytes={resume_position}-"

    response = requests.get(url, headers=headers, stream=True, timeout=timeout, allow_redirects=True)

    # Handle resume response
    if response.status_code == 416:
        # Range not satisfiable - file is complete
        if temp_path.exists():
            temp_path.rename(dest_path)
            return
        headers_no_range = {"User-Agent": DEFAULT_USER_AGENT}
        response = requests.get(url, headers=headers_no_range, stream=True, timeout=timeout, allow_redirects=True)
        resume_position = 0

    response.raise_for_status()

    # Get total size
    if response.status_code == 206:
        # Partial content - resuming
        content_range = response.headers.get("Content-Range", "")
        if "/" in content_range:
            total_size = int(content_range.split("/")[-1])
        else:
            total_size = resume_position + int(response.headers.get("Content-Length", 0))
    else:
        total_size = int(response.headers.get("Content-Length", 0))
        resume_position = 0  # Not resuming, start fresh

    # Download with progress
    if show_progress and total_size > 0:
        _download_with_progress(
            response=response,
            temp_path=temp_path,
            total_size=total_size,
            resume_position=resume_position,
            chunk_size=chunk_size,
            episode_title=episode_title,
            progress_callback=progress_callback,
        )
    else:
        _download_simple(
            response=response,
            temp_path=temp_path,
            resume_position=resume_position,
            chunk_size=chunk_size,
            progress_callback=progress_callback,
            total_size=total_size,
        )

    # Verify download
    if total_size > 0:
        actual_size = temp_path.stat().st_size
        if actual_size != total_size:
            raise DownloadError(f"Size mismatch: expected {total_size}, got {actual_size}")

    # Move to final destination
    temp_path.rename(dest_path)


def _download_with_progress(
    response: requests.Response,
    temp_path: Path,
    total_size: int,
    resume_position: int,
    chunk_size: int,
    episode_title: str,
    progress_callback: Callable[[int, int], None] | None,
) -> None:
    """Download with rich progress bar.

    Args:
        response: Streaming response.
        temp_path: Path to write to.
        total_size: Total file size.
        resume_position: Bytes already downloaded.
        chunk_size: Chunk size for iteration.
        episode_title: Title to display.
        progress_callback: Optional callback for progress.
    """
    # Truncate title for display
    display_title = episode_title[:40] + "..." if len(episode_title) > 40 else episode_title

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task_id: TaskID = progress.add_task(display_title, total=total_size)

        # Update for already downloaded portion
        if resume_position > 0:
            progress.update(task_id, completed=resume_position)

        mode = "ab" if resume_position > 0 else "wb"
        downloaded = resume_position

        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.update(task_id, completed=downloaded)
                    if progress_callback:
                        progress_callback(downloaded, total_size)


def _download_simple(
    response: requests.Response,
    temp_path: Path,
    resume_position: int,
    chunk_size: int,
    progress_callback: Callable[[int, int], None] | None,
    total_size: int,
) -> None:
    """Download without progress bar.

    Args:
        response: Streaming response.
        temp_path: Path to write to.
        resume_position: Bytes already downloaded.
        chunk_size: Chunk size for iteration.
        progress_callback: Optional callback for progress.
        total_size: Total size (for callback).
    """
    mode = "ab" if resume_position > 0 else "wb"
    downloaded = resume_position

    with open(temp_path, mode) as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total_size)


def verify_download(path: Path, expected_size: int | None = None) -> bool:
    """Verify a downloaded file.

    Args:
        path: Path to the file.
        expected_size: Expected file size (optional).

    Returns:
        True if file exists and size matches (if provided).

    Example:
        >>> verify_download(Path("episode.mp3"), expected_size=50000000)
        True
    """
    if not path.exists():
        return False

    if expected_size is not None:
        actual_size = path.stat().st_size
        return actual_size == expected_size

    # Just check it's non-empty
    return path.stat().st_size > 0
