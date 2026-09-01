import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

SUPPORTED_UPLOAD_METHODS = {"http_multipart", "tkws_signed"}


@dataclass
class Credentials:
    """Authentication configuration without requiring secrets in the repository."""

    type: str = "none"
    username: Optional[str] = None
    password_env: Optional[str] = None
    api_key_name: Optional[str] = None
    api_key_env: Optional[str] = None
    # Legacy fields are accepted when reading older local configs, but are never saved.
    password: Optional[str] = field(default=None, repr=False)
    api_key_value: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.type not in {"none", "basic_auth", "api_key"}:
            raise ValueError(f"Unsupported credential type: {self.type}")
        if self.type == "basic_auth" and not self.username:
            raise ValueError("basic_auth requires a username")
        if self.type == "api_key" and not self.api_key_name:
            raise ValueError("api_key requires api_key_name")

    def resolve_password(self) -> Optional[str]:
        if self.password_env:
            return os.getenv(self.password_env)
        return self.password

    def resolve_api_key(self) -> Optional[str]:
        if self.api_key_env:
            return os.getenv(self.api_key_env)
        return self.api_key_value

    def safe_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "username": self.username,
            "password_env": self.password_env,
            "api_key_name": self.api_key_name,
            "api_key_env": self.api_key_env,
        }


@dataclass
class WebsiteProfile:
    name: str
    url: str
    upload_method: str = "http_multipart"
    credentials: Credentials = field(default_factory=Credentials)
    remote_path: str = "/"
    customer_id_env: Optional[str] = None
    supabase_anon_key_env: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Website profile name cannot be empty")
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("Website URL must start with http:// or https://")
        if self.upload_method not in SUPPORTED_UPLOAD_METHODS:
            raise ValueError(
                f"Unsupported upload method '{self.upload_method}'. "
                f"Choose one of: {', '.join(sorted(SUPPORTED_UPLOAD_METHODS))}"
            )
        if not self.remote_path.startswith("/"):
            self.remote_path = f"/{self.remote_path}"

    def safe_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "upload_method": self.upload_method,
            "credentials": self.credentials.safe_dict(),
            "remote_path": self.remote_path,
            "customer_id_env": self.customer_id_env,
            "supabase_anon_key_env": self.supabase_anon_key_env,
        }


class ConfigManager:
    def __init__(self) -> None:
        self._default_local_upload_path = os.path.join(
            os.path.expanduser("~"), "uploader_content"
        )
        self._website_profiles: Dict[str, WebsiteProfile] = {}

    @property
    def default_local_upload_path(self) -> str:
        return self._default_local_upload_path

    @default_local_upload_path.setter
    def default_local_upload_path(self, path: str) -> None:
        self._default_local_upload_path = os.path.abspath(os.path.expanduser(path))

    def load_config(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError("Configuration root must be a JSON object")

        default_path = data.get("default_local_upload_path")
        if default_path:
            self.default_local_upload_path = default_path

        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError("'profiles' must be an object keyed by profile name")

        loaded: Dict[str, WebsiteProfile] = {}
        for key, value in profiles.items():
            if not isinstance(value, dict):
                raise ValueError(f"Profile '{key}' must be an object")

            credentials_data = value.get("credentials") or {"type": "none"}
            credentials = Credentials(**credentials_data)

            method = value.get("upload_method", "http_multipart")
            # Keep old configs usable: historical http_post meant the TKWS signed flow.
            if method == "http_post":
                method = "tkws_signed"

            profile = WebsiteProfile(
                name=value.get("name", key),
                url=value["url"],
                upload_method=method,
                credentials=credentials,
                remote_path=value.get("remote_path", "/"),
                customer_id_env=value.get("customer_id_env"),
                supabase_anon_key_env=value.get("supabase_anon_key_env"),
            )
            loaded[profile.name] = profile

        self._website_profiles = loaded

    def save_config(self, file_path: str) -> None:
        directory = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(directory, exist_ok=True)
        payload = {
            "default_local_upload_path": self.default_local_upload_path,
            "profiles": {
                name: profile.safe_dict()
                for name, profile in sorted(self._website_profiles.items())
            },
        }
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def add_profile(self, profile: WebsiteProfile, *, replace: bool = False) -> None:
        if profile.name in self._website_profiles and not replace:
            raise ValueError(f"Profile '{profile.name}' already exists")
        self._website_profiles[profile.name] = profile

    def get_profile(self, name: str) -> WebsiteProfile:
        try:
            return self._website_profiles[name]
        except KeyError as exc:
            raise KeyError(f"No website profile found with name '{name}'") from exc

    def delete_profile(self, name: str) -> None:
        if name not in self._website_profiles:
            raise KeyError(f"No website profile found with name '{name}'")
        del self._website_profiles[name]

    def list_profiles(self) -> Dict[str, WebsiteProfile]:
        return dict(self._website_profiles)
