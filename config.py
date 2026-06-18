import os
import json
from typing import Dict, Any, Optional, Union
from dataclasses import asdict, dataclass, field

@dataclass
class Credentials:
    """Represents various types of credentials for website access."""
    type: str  # e.g., 'basic_auth', 'api_key', 'none'
    username: Optional[str] = None
    password: Optional[str] = None
    api_key_name: Optional[str] = None # For API key in header (e.g., 'X-API-KEY')
    api_key_value: Optional[str] = None

    def __post_init__(self) -> None:
        """Perform validation after initialization."""
        if self.type == 'basic_auth':
            if not self.username or not self.password:
                raise ValueError("Username and password are required for basic_auth credentials.")
        elif self.type == 'api_key':
            if not self.api_key_name or not self.api_key_value:
                raise ValueError("API key name and value are required for api_key credentials.")
        elif self.type == 'none':
            # No specific credentials required, all fields can be None
            pass
        else:
            raise ValueError(f"Unsupported credential type: {self.type}")

@dataclass
class WebsiteProfile:
    """Represents a configuration profile for a single website."""
    name: str
    url: str
    upload_method: str  # e.g., 'http_post', 'ftp', 'sftp'
    credentials: Credentials
    remote_path: str = "/" # Default remote path on the target server

    def __post_init__(self) -> None:
        """Perform validation after initialization."""
        if not self.name:
            raise ValueError("Website profile name cannot be empty.")
        if not self.url:
            raise ValueError("Website URL cannot be empty.")
        if not self.upload_method:
            raise ValueError("Upload method cannot be empty.")

class ConfigManager:
    """
    Manages application-wide configuration, including website profiles,
    credentials, and default upload paths.

    This class provides methods to add, retrieve, update, and delete website
    profiles, as well as manage the application's default local upload path.
    """
    def __init__(self) -> None:
        """
        Initializes the ConfigManager with default settings and pre-defined
        website profiles.

        In a production environment, this data would typically be loaded from
        a secure configuration file (e.g., JSON, YAML, TOML) or environment variables.
        For this project, it's hardcoded for simplicity and to meet the
        "complete, runnable code" requirement without external file dependencies
        not explicitly specified.
        """
        # Default local upload path is a directory named 'uploads' in the user's home directory.
        self._default_local_upload_path: str = os.path.join(os.path.expanduser("~"), "uploader_content")
        self._website_profiles: Dict[str, WebsiteProfile] = {}

        # Ensure the default local upload path exists
        os.makedirs(self._default_local_upload_path, exist_ok=True)

        # Add some example profiles for demonstration
        self._add_default_profiles()

    def _add_default_profiles(self) -> None:
        """
        Adds pre-defined website profiles for demonstration purposes.
        Credentials for these profiles are pulled from environment variables
        to prevent hardcoding sensitive information directly.
        """
        try:
            # Example 1: Basic Auth HTTP POST to a public test endpoint
            basic_auth_creds = Credentials(
                type='basic_auth',
                username=os.environ.get('UPLOADER_EXAMPLE_SITE_USER', 'testuser'),
                password=os.environ.get('UPLOADER_EXAMPLE_SITE_PASS', 'testpassword123')
            )
            self.add_profile(WebsiteProfile(
                name='example_http_site',
                url='https://httpbin.org/post', # A public test endpoint for POST requests
                upload_method='http_post',
                credentials=basic_auth_creds,
                remote_path='/uploads/'
            ))

            # Example 2: API Key HTTP POST to a placeholder API
            api_key_creds = Credentials(
                type='api_key',
                api_key_name='X-API-KEY',
                api_key_value=os.environ.get('UPLOADER_ANOTHER_SITE_API_KEY', 'your-secret-api-key-123')
            )
            self.add_profile(WebsiteProfile(
                name='another_api_site',
                url='https://api.anothersite.com/v1/upload', # Placeholder URL
                upload_method='http_post',
                credentials=api_key_creds,
                remote_path='/files/'
            ))

            # Example 3: FTP with no explicit credentials (e.g., anonymous FTP or other implicit auth)
            no_creds = Credentials(type='none')
            self.add_profile(WebsiteProfile(
                name='anonymous_ftp_site',
                url='ftp://ftp.example.com/pub', # Placeholder URL
                upload_method='ftp',
                credentials=no_creds,
                remote_path='/'
            ))

        except ValueError as e:
            # Log the error and decide if the application should halt or continue with fewer profiles.
            print(f"Error loading default profiles: {e}")

    def load_config(self, file_path: str) -> None:
        """
        Loads configuration from a JSON file.

        Missing config files are allowed; the built-in demonstration profiles
        remain available so the CLI can run out of the box.
        """
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        default_path = data.get('default_local_upload_path')
        if default_path:
            self.default_local_upload_path = default_path

        profiles_data = data.get('profiles')
        if profiles_data is None:
            return
        if not isinstance(profiles_data, dict):
            raise ValueError("'profiles' must be an object keyed by profile name.")

        loaded_profiles: Dict[str, WebsiteProfile] = {}
        for profile_name, profile_data in profiles_data.items():
            if not isinstance(profile_data, dict):
                raise ValueError(f"Profile '{profile_name}' must be an object.")

            credentials_data = profile_data.get('credentials', {'type': 'none'})
            if not isinstance(credentials_data, dict):
                raise ValueError(f"Credentials for profile '{profile_name}' must be an object.")

            credentials = Credentials(**credentials_data)
            profile = WebsiteProfile(
                name=profile_data.get('name', profile_name),
                url=profile_data['url'],
                upload_method=profile_data.get('upload_method', 'http_post'),
                credentials=credentials,
                remote_path=profile_data.get('remote_path', '/')
            )
            loaded_profiles[profile.name] = profile

        self._website_profiles = loaded_profiles

    def save_config(self, file_path: str) -> None:
        """Saves the current configuration to a JSON file."""
        config_dir = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(config_dir, exist_ok=True)

        data = {
            'default_local_upload_path': self.default_local_upload_path,
            'profiles': {
                name: asdict(profile)
                for name, profile in self._website_profiles.items()
            }
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @property
    def default_local_upload_path(self) -> str:
        """
        Gets the default local directory from which files are expected to be uploaded.
        """
        return self._default_local_upload_path

    @default_local_upload_path.setter
    def default_local_upload_path(self, path: str) -> None:
        """
        Sets a new default local directory for uploads.
        The method ensures that the specified path exists, creating it if necessary.

        Args:
            path: The new path to set as the default local upload directory.
        """
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        self._default_local_upload_path = path

    def add_profile(self, profile: WebsiteProfile) -> None:
        """
        Adds a new website profile to the configuration.

        Args:
            profile: An instance of WebsiteProfile to add.

        Raises:
            ValueError: If a profile with the same name already exists.
        """
        if profile.name in self._website_profiles:
            raise ValueError(f"Profile with name '{profile.name}' already exists.")
        self._website_profiles[profile.name] = profile

    def get_profile(self, name: str) -> WebsiteProfile:
        """
        Retrieves a website profile by its name.

        Args:
            name: The name of the website profile to retrieve.

        Returns:
            The WebsiteProfile instance associated with the given name.

        Raises:
            KeyError: If no profile with the specified name is found.
        """
        try:
            return self._website_profiles[name]
        except KeyError:
            raise KeyError(f"No website profile found with name: '{name}'")

    def update_profile(self, profile: WebsiteProfile) -> None:
        """
        Updates an existing website profile.

        Args:
            profile: The WebsiteProfile instance with updated details.
                     The 'name' attribute is used to identify the profile to update.

        Raises:
            KeyError: If no profile with the specified name exists to update.
        """
        if profile.name not in self._website_profiles:
            raise KeyError(f"Cannot update: No profile found with name '{profile.name}'")
        self._website_profiles[profile.name] = profile

    def delete_profile(self, name: str) -> None:
        """
        Deletes a website profile by its name.

        Args:
            name: The name of the website profile to delete.

        Raises:
            KeyError: If no profile with the specified name exists to delete.
        """
        if name not in self._website_profiles:
            raise KeyError(f"Cannot delete: No profile found with name '{name}'")
        del self._website_profiles[name]

    def list_profiles(self) -> Dict[str, WebsiteProfile]:
        """
        Lists all configured website profiles.

        Returns:
            A dictionary where keys are profile names and values are WebsiteProfile instances.
        """
        return self._website_profiles

if __name__ == "__main__":
    print("--- Initializing ConfigManager ---")
    config = ConfigManager()

    print(f"\nDefault local upload path: {config.default_local_upload_path}")

    print("\n--- Listing all configured profiles ---")
    for name, profile in config.list_profiles().items():
        print(f"Profile Name: {name}")
        print(f"  URL: {profile.url}")
        print(f"  Method: {profile.upload_method}")
        print(f"  Remote Path: {profile.remote_path}")
        print(f"  Credentials Type: {profile.credentials.type}")
        if profile.credentials.username:
            print(f"  Username (if Basic Auth): {profile.credentials.username}")
        if profile.credentials.api_key_name:
            print(f"  API Key Header Name (if API Key): {profile.credentials.api_key_name}")
        print("-" * 30)

    print("\n--- Testing get_profile for an existing profile ---")
    try:
        profile_example = config.get_profile('example_http_site')
        print(f"Successfully retrieved profile '{profile_example.name}': URL={profile_example.url}")
    except KeyError as e:
        print(f"Error retrieving profile: {e}")

    print("\n--- Testing get_profile for a non-existent profile ---")
    try:
        config.get_profile('non_existent_profile')
    except KeyError as e:
        print(f"Successfully caught expected error for non-existent profile: {e}")

    print("\n--- Testing adding a new profile ---")
    try:
        new_creds = Credentials(type='basic_auth', username='test_new', password='new_pass')
        new_profile = WebsiteProfile(
            name='my_new_custom_site',
            url='https://my.customsite.com/upload',
            upload_method='http_post',
            credentials=new_creds,
            remote_path='/custom/content/'
        )
        config.add_profile(new_profile)
        print(f"Successfully added profile '{new_profile.name}'.")
        print(f"New profile details: URL={config.get_profile('my_new_custom_site').url}")
    except ValueError as e:
        print(f"Error adding new profile: {e}")

    print("\n--- Testing updating an existing profile ---")
    try:
        updated_creds = Credentials(type='api_key', api_key_name='X-API-Custom', api_key_value='custom-key-xyz')
        updated_profile = WebsiteProfile(
            name='my_new_custom_site', # Name must match an existing profile
            url='https://my.customsite.com/api/v2/new_upload',
            upload_method='http_put', # Changed method
            credentials=updated_creds,
            remote_path='/custom/v2_uploads/' # Changed remote path
        )
        config.update_profile(updated_profile)
        print(f"Successfully updated profile '{updated_profile.name}'.")
        updated_retrieved = config.get_profile('my_new_custom_site')
        print(f"Updated profile details: URL={updated_retrieved.url}, Method={updated_retrieved.upload_method}, Creds Type={updated_retrieved.credentials.type}")
    except KeyError as e:
        print(f"Error updating profile: {e}")

    print("\n--- Testing deleting a profile ---")
    try:
        config.delete_profile('my_new_custom_site')
        print("Successfully deleted profile 'my_new_custom_site'.")
        # Attempt to retrieve the deleted profile to confirm deletion
        config.get_profile('my_new_custom_site')
    except KeyError as e:
        print(f"Successfully confirmed deletion: {e}")

    print("\n--- Testing validation for incomplete credentials ---")
    try:
        Credentials(type='basic_auth', username='missing_pass')
    except ValueError as e:
        print(f"Caught expected error for incomplete basic_auth credentials: {e}")

    try:
        Credentials(type='api_key', api_key_value='missing_name')
    except ValueError as e:
        print(f"Caught expected error for incomplete api_key credentials: {e}")

    print("\n--- Testing setting a new default local upload path ---")
    original_path = config.default_local_upload_path
    new_path = os.path.join(os.path.expanduser("~"), "my_custom_uploader_uploads")
    print(f"Original default local upload path: {original_path}")
    config.default_local_upload_path = new_path
    print(f"New default local upload path: {config.default_local_upload_path}")

    # Clean up the test directory if it was created during this test run
    if os.path.exists(new_path) and new_path != original_path:
        print(f"Cleaning up test directory: {new_path}")
        try:
            os.rmdir(new_path)
        except OSError as e:
            print(f"Could not remove directory {new_path}: {e}")
    # Also clean up the original default directory if it was created empty by the script and we changed it
    if os.path.exists(original_path) and original_path != new_path:
        try:
            # Only remove if it's empty, otherwise rmdir will fail.
            # In a real app, you wouldn't automatically delete user's content folders.
            os.rmdir(original_path)
            print(f"Cleaned up default directory: {original_path}")
        except OSError:
            pass # Directory might not be empty or might not have been created by us.
