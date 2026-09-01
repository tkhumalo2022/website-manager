import base64
import mimetypes
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

import requests

from config import WebsiteProfile


ALLOWED_EXTENSIONS = {
    ".pdf": ("documents", "application/pdf"),
    ".doc": ("documents", "application/msword"),
    ".docx": (
        "documents",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".jpg": ("images", "image/jpeg"),
    ".jpeg": ("images", "image/jpeg"),
    ".png": ("images", "image/png"),
    ".webp": ("images", "image/webp"),
    ".mp4": ("videos", "video/mp4"),
    ".webm": ("videos", "video/webm"),
    ".mov": ("videos", "video/quicktime"),
    ".txt": ("documents", "text/plain"),
}


class Uploader:
    def __init__(self, profile: WebsiteProfile, session: Optional[requests.Session] = None):
        self.profile = profile
        self.session = session or requests.Session()

    def upload_file(
        self,
        local_file_path: str,
        remote_file_name: Optional[str] = None,
        *,
        dry_run: bool = False,
    ) -> bool:
        path = Path(local_file_path).expanduser()
        if not path.is_file():
            print(f"Error: local file not found: {path}")
            return False

        remote_name = remote_file_name or path.name
        if dry_run:
            category, mime_type = self._detect_upload_metadata(path, remote_name)
            print("Dry run OK")
            print(f"Profile: {self.profile.name}")
            print(f"Method: {self.profile.upload_method}")
            print(f"Source: {path}")
            print(f"Remote name: {remote_name}")
            print(f"Category: {category}")
            print(f"MIME type: {mime_type}")
            return True

        if self.profile.upload_method == "http_multipart":
            return self._upload_http_multipart(path, remote_name)
        if self.profile.upload_method == "tkws_signed":
            return self._upload_tkws_signed(path, remote_name)

        print(f"Error: unsupported upload method '{self.profile.upload_method}'")
        return False

    def _get_auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        credentials = self.profile.credentials

        if credentials.type == "none":
            return headers

        if credentials.type == "basic_auth":
            password = credentials.resolve_password()
            if not password:
                raise RuntimeError(
                    "Basic-auth password is missing. Set the configured password environment variable."
                )
            token = base64.b64encode(
                f"{credentials.username}:{password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
            return headers

        if credentials.type == "api_key":
            value = credentials.resolve_api_key()
            if not value:
                raise RuntimeError(
                    "API key is missing. Set the configured API-key environment variable."
                )
            headers[credentials.api_key_name or "X-API-KEY"] = value
            return headers

        raise RuntimeError(f"Unsupported credential type '{credentials.type}'")

    @staticmethod
    def _detect_upload_metadata(path: Path, remote_name: str) -> Tuple[str, str]:
        extension = Path(remote_name).suffix.lower()
        category, mime_type = ALLOWED_EXTENSIONS.get(extension, ("documents", ""))
        if not mime_type:
            guessed, _ = mimetypes.guess_type(str(path))
            mime_type = guessed or "application/octet-stream"
        if extension in {".jpg", ".jpeg", ".png", ".webp"} and "logo" in remote_name.lower():
            category = "logo"
        return category, mime_type

    def _upload_http_multipart(self, path: Path, remote_name: str) -> bool:
        target_url = urljoin(self.profile.url.rstrip("/") + "/", self.profile.remote_path.lstrip("/"))
        _, mime_type = self._detect_upload_metadata(path, remote_name)
        headers = self._get_auth_headers()
        headers["User-Agent"] = "TK-Website-Manager/1.0"

        try:
            with path.open("rb") as handle:
                response = self.session.post(
                    target_url,
                    headers=headers,
                    files={"file": (remote_name, handle, mime_type)},
                    timeout=60,
                )
            if not response.ok:
                print(f"Upload failed: HTTP {response.status_code} {response.reason}")
                return False
            print(f"Upload complete: {remote_name}")
            return True
        except requests.RequestException as exc:
            print(f"Upload request failed: {exc}")
            return False

    def _upload_tkws_signed(self, path: Path, remote_name: str) -> bool:
        target_url = urljoin(self.profile.url.rstrip("/") + "/", self.profile.remote_path.lstrip("/"))
        category, mime_type = self._detect_upload_metadata(path, remote_name)

        if not self.profile.customer_id_env:
            print("Error: tkws_signed profile requires customer_id_env")
            return False
        customer_id = os.getenv(self.profile.customer_id_env)
        if not customer_id:
            print(f"Error: environment variable {self.profile.customer_id_env} is not set")
            return False

        if not self.profile.supabase_anon_key_env:
            print("Error: tkws_signed profile requires supabase_anon_key_env")
            return False
        anon_key = os.getenv(self.profile.supabase_anon_key_env)
        if not anon_key:
            print(f"Error: environment variable {self.profile.supabase_anon_key_env} is not set")
            return False

        metadata = {
            "category": category,
            "fileName": remote_name,
            "mimeType": mime_type,
            "fileSize": path.stat().st_size,
            "customerId": customer_id,
        }
        headers = self._get_auth_headers()
        headers.update({"Content-Type": "application/json", "User-Agent": "TK-Website-Manager/1.0"})

        try:
            signed_response = self.session.post(
                target_url,
                headers=headers,
                json=metadata,
                timeout=30,
            )
            if not signed_response.ok:
                print(
                    f"Signed URL request failed: HTTP {signed_response.status_code} "
                    f"{signed_response.reason}"
                )
                return False

            payload = signed_response.json()
            if not payload.get("success") or not payload.get("signedUrl"):
                print("Signed URL response did not contain a usable signedUrl")
                return False

            upload_headers = {
                "Authorization": f"Bearer {anon_key}",
                "apikey": anon_key,
                "Content-Type": mime_type,
            }
            with path.open("rb") as handle:
                upload_response = self.session.put(
                    payload["signedUrl"],
                    headers=upload_headers,
                    data=handle,
                    timeout=90,
                )
            if not upload_response.ok:
                print(
                    f"Storage upload failed: HTTP {upload_response.status_code} "
                    f"{upload_response.reason}"
                )
                return False

            print(f"Upload complete: {remote_name}")
            if payload.get("objectPath"):
                print(f"Object path: {payload['objectPath']}")
            return True
        except (requests.RequestException, ValueError) as exc:
            print(f"TKWS signed upload failed: {exc}")
            return False
