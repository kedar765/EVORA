"""
EVORA Supabase Storage Integration
==================================
Provides secure, persistent cloud storage for business datasets using Supabase Storage.
Ensures persistent dataset availability across ephemeral cloud container restarts (e.g. Render).

Key Features:
- Private bucket (`evora-datasets`) storage
- Local caching layer for fast repeated agent reads
- Auto-sync: automatically fetches missing dataset files from Supabase Storage on demand
- Zero external heavy dependencies: uses standard `httpx` with system trust certificates
"""

from __future__ import annotations

import logging
import os
import ssl
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("evora.storage")

ROOT_DIR = Path(__file__).resolve().parent.parent
UPLOAD_STORAGE_DIR = (ROOT_DIR / "backend" / "storage" / "uploads").resolve()

BUCKET_NAME = os.getenv("EVORA_STORAGE_BUCKET", "evora-datasets")


def _get_ssl_context() -> ssl.SSLContext:
    """Returns an SSL context with the local/system default certificates loaded."""
    ctx = ssl.create_default_context()
    ctx.load_default_certs()
    return ctx


def is_supabase_storage_enabled() -> bool:
    """Returns True if Supabase Storage credentials are configured."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    return bool(url and key)


def _get_auth_headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def upload_dataset_to_storage(stored_filename: str, file_contents: bytes) -> bool:
    """
    Uploads a dataset file to the private Supabase Storage bucket.
    Returns True on success, False if storage is disabled or request fails.
    """
    if not is_supabase_storage_enabled():
        return False

    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    url = f"{supabase_url}/storage/v1/object/{BUCKET_NAME}/{stored_filename}"

    headers = {
        **_get_auth_headers(),
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",
    }

    try:
        ctx = _get_ssl_context()
        resp = httpx.post(url, headers=headers, content=file_contents, verify=ctx, timeout=30.0)
        if resp.status_code in (200, 201):
            logger.info("Uploaded %s to Supabase Storage bucket '%s'.", stored_filename, BUCKET_NAME)
            return True
        else:
            logger.warning("Supabase Storage upload returned HTTP %d: %s", resp.status_code, resp.text)
            return False
    except Exception as exc:
        logger.warning("Failed to upload %s to Supabase Storage: %s", stored_filename, exc)
        return False


def download_dataset_from_storage(stored_filename: str, destination_path: Path) -> bool:
    """
    Downloads a dataset file from Supabase Storage and saves it to destination_path.
    Returns True on success, False otherwise.
    """
    if not is_supabase_storage_enabled():
        return False

    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    headers = _get_auth_headers()
    ctx = _get_ssl_context()

    # Try authenticated route first, fall back to standard object endpoint with auth header
    endpoints = [
        f"{supabase_url}/storage/v1/object/authenticated/{BUCKET_NAME}/{stored_filename}",
        f"{supabase_url}/storage/v1/object/{BUCKET_NAME}/{stored_filename}",
    ]

    for url in endpoints:
        try:
            resp = httpx.get(url, headers=headers, verify=ctx, timeout=30.0)
            if resp.status_code == 200 and resp.content:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                destination_path.write_bytes(resp.content)
                logger.info("Successfully fetched and cached %s from Supabase Storage.", stored_filename)
                return True
        except Exception as exc:
            logger.debug("Failed endpoint %s: %s", url, exc)

    return False


def ensure_dataset_available(storage_path_str: str) -> Path:
    """
    Ensures that a dataset file exists on the local filesystem.
    If absent locally (e.g. following a Render container redeploy),
    it transparently downloads it from Supabase Storage into the uploads cache.
    """
    stored_path = Path(storage_path_str)
    if stored_path.is_absolute():
        resolved_path = stored_path.resolve()
    else:
        resolved_path = (ROOT_DIR / stored_path).resolve()

    # If the file already exists locally, return it immediately
    if resolved_path.is_file():
        return resolved_path

    # Check by filename inside UPLOAD_STORAGE_DIR
    filename = stored_path.name
    cached_path = (UPLOAD_STORAGE_DIR / filename).resolve()
    if cached_path.is_file():
        return cached_path

    # File missing locally -> attempt cloud download from Supabase Storage
    if is_supabase_storage_enabled():
        logger.info("Dataset file %s missing from local disk. Attempting Supabase Storage download...", filename)
        success = download_dataset_from_storage(filename, cached_path)
        if success and cached_path.is_file():
            return cached_path

    return resolved_path


def list_storage_filenames() -> set[str]:
    """Returns the set of filenames currently present in the Supabase Storage bucket."""
    if not is_supabase_storage_enabled():
        return set()

    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    headers = {
        **_get_auth_headers(),
        "Content-Type": "application/json",
    }
    ctx = _get_ssl_context()

    try:
        with httpx.Client(verify=ctx, timeout=15.0) as client:
            resp = client.post(
                f"{supabase_url}/storage/v1/object/list/{BUCKET_NAME}",
                headers=headers,
                json={"prefix": "", "limit": 1000},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {item["name"] for item in data if isinstance(item, dict) and "name" in item}
    except Exception as exc:
        logger.warning("Error listing Supabase Storage objects: %s", exc)

    return set()


def sync_all_local_files_to_storage() -> int:
    """
    Syncs local files in `backend/storage/uploads` to Supabase Storage.
    Skips any files already present in the cloud bucket.
    Preserves all local files. Returns count of newly uploaded files.
    """
    if not is_supabase_storage_enabled():
        logger.warning("Supabase Storage is not configured. Cannot sync local files.")
        return 0

    if not UPLOAD_STORAGE_DIR.is_dir():
        return 0

    existing_remote = list_storage_filenames()
    local_files = [
        f for f in UPLOAD_STORAGE_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.name not in existing_remote
    ]
    logger.info(
        "Sync check: %d local files require upload (%d already exist in bucket).",
        len(local_files),
        len(existing_remote),
    )

    if not local_files:
        return 0

    ctx = _get_ssl_context()
    synced_count = 0
    with httpx.Client(
        verify=ctx,
        timeout=httpx.Timeout(connect=15.0, read=45.0, write=60.0, pool=15.0),
    ) as client:
        for file_path in local_files:
            try:
                content = file_path.read_bytes()
                supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
                url = f"{supabase_url}/storage/v1/object/{BUCKET_NAME}/{file_path.name}"
                headers = {
                    **_get_auth_headers(),
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "true",
                }
                resp = client.post(url, headers=headers, content=content)
                if resp.status_code in (200, 201):
                    synced_count += 1
                else:
                    logger.warning("Upload %s returned %d", file_path.name, resp.status_code)
            except Exception as exc:
                logger.warning("Error syncing %s: %s", file_path.name, exc)

    logger.info("Synced %d of %d dataset files to Supabase Storage.", synced_count, len(local_files))
    return synced_count
