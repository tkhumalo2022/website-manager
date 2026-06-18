import os
import base64
import mimetypes
from urllib.parse import urljoin
from typing import Optional, Dict, Tuple

import requests

from config import WebsiteProfile
from utils.file_operations import get_file_name


SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

DEFAULT_CUSTOMER_ID = os.getenv("TKWS_CUSTOMER_ID", "TKWS-20260618-TEST")


class Uploader:
    def __init__(self, profile: WebsiteProfile):
        self.profile = profile

    def upload_file(self, local_file_path: str, remote_file_name: Optional[str] = None) -> bool:
        if not os.path.exists(local_file_path):
            print(f"Error: Local file not found at '{local_file_path}'.")
            return False

        if not os.path.isfile(local_file_path):
            print(f"Error: '{local_file_path}' is not a file.")
            return False

        if remote_file_name is None:
            remote_file_name = get_file_name(local_file_path)

        print(f"Attempting to upload '{local_file_path}' as '{remote_file_name}' using method '{self.profile.upload_method}'...")

        if self.profile.upload_method == "http_post":
            return self._upload_http_post(local_file_path, remote_file_name)

        print(f"Error: Unsupported upload method '{self.profile.upload_method}'.")
        return False

    def _get_auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        creds = self.profile.credentials

        if creds.type == "basic_auth":
            if creds.username and creds.password:
                auth_string = f"{creds.username}:{creds.password}"
                encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
                headers["Authorization"] = f"Basic {encoded_auth_string}"
            else:
                print("Warning: Basic Auth selected, but username or password is missing.")

        elif creds.type == "api_key":
            if creds.api_key_name and creds.api_key_value:
                headers[creds.api_key_name] = creds.api_key_value
            else:
                print("Warning: API Key selected, but API key name or value is missing.")

        elif creds.type == "none":
            pass

        else:
            print(f"Warning: Unknown credential type '{creds.type}'.")

        return headers

    def _detect_upload_metadata(self, file_path: str, file_name: str) -> Tuple[str, str]:
        extension = os.path.splitext(file_name)[1].lower()

        mime_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
        }

        mime_type = mime_map.get(extension)

        if not mime_type:
            guessed_type, _ = mimetypes.guess_type(file_path)
            mime_type = guessed_type or "application/octet-stream"

        if extension in [".pdf", ".doc", ".docx"]:
            category = "documents"
        elif extension in [".jpg", ".jpeg", ".png", ".webp"]:
            category = "logo" if "logo" in file_name.lower() else "images"
        elif extension in [".mp4", ".webm", ".mov"]:
            category = "videos"
        else:
            print(f"Error: Unsupported file type '{extension}'.")
            print("Allowed: PDF, DOC, DOCX, JPG, PNG, WEBP, MP4, WEBM, MOV.")
            return "", ""

        return category, mime_type

    def _upload_http_post(self, local_file_path: str, remote_file_name: str) -> bool:
        target_url = urljoin(self.profile.url, self.profile.remote_path)

        try:
            category, mime_type = self._detect_upload_metadata(local_file_path, remote_file_name)

            if not category or not mime_type:
                return False

            file_size = os.path.getsize(local_file_path)

            metadata_payload = {
                "category": category,
                "fileName": remote_file_name,
                "mimeType": mime_type,
                "fileSize": file_size,
                "customerId": DEFAULT_CUSTOMER_ID,
            }

            metadata_headers = self._get_auth_headers()
            metadata_headers["User-Agent"] = "Jarvis-Website-Manager/1.0"
            metadata_headers["Content-Type"] = "application/json"

            print("Creating signed upload URL...")
            print(f"Category: {category}")
            print(f"MIME Type: {mime_type}")
            print(f"Customer ID: {DEFAULT_CUSTOMER_ID}")

            metadata_response = requests.post(
                url=target_url,
                headers=metadata_headers,
                json=metadata_payload,
                timeout=30,
            )

            if not metadata_response.ok:
                print(f"Error creating signed upload URL: HTTP {metadata_response.status_code} - {metadata_response.reason}")
                print(f"Response content: {metadata_response.text}")
                return False

            metadata = metadata_response.json()

            if not metadata.get("success"):
                print("Error: Backend did not return success.")
                print(metadata)
                return False

            signed_url = metadata.get("signedUrl")
            object_path = metadata.get("objectPath")
            bucket = metadata.get("bucket")

            if not signed_url:
                print("Error: Backend response did not include signedUrl.")
                print(metadata)
                return False

            upload_headers = {
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": mime_type,
            }

            print("Uploading file to Supabase...")

            with open(local_file_path, "rb") as file_data:
                upload_response = requests.put(
                    url=signed_url,
                    headers=upload_headers,
                    data=file_data,
                    timeout=60,
                )

            if not upload_response.ok:
                print(f"Error uploading file: HTTP {upload_response.status_code} - {upload_response.reason}")
                print(f"Response content: {upload_response.text}")
                return False

            print("UPLOAD SUCCESS")
            print(f"Bucket: {bucket}")
            print(f"Object Path: {object_path}")
            return True

        except requests.exceptions.ConnectionError as e:
            print(f"Connection failed: {e}")
            return False

        except requests.exceptions.Timeout as e:
            print(f"Request timed out: {e}")
            return False

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return False

        except FileNotFoundError:
            print(f"Error: Local file '{local_file_path}' not found.")
            return False

        except IOError as e:
            print(f"Error accessing local file '{local_file_path}': {e}")
            return False

        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

