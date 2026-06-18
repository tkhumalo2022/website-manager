import argparse
import sys
import os
from typing import Optional

# Project imports
from config import ConfigManager, WebsiteProfile, Credentials
from core.uploader import Uploader

def main() -> None:
    """
    Main application entry point. Handles command-line argument parsing and
    orchestrates the content upload process.
    """
    parser = argparse.ArgumentParser(
        description="A command-line tool for managing website content uploads."
    )

    # Global options
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to the configuration file (default: config.json)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # --- Profile management commands ---
    profile_parser = subparsers.add_parser('profile', help='Manage website profiles.')
    profile_subparsers = profile_parser.add_subparsers(dest='profile_command', help='Profile commands')

    # Add profile
    add_profile_parser = profile_subparsers.add_parser('add', help='Add a new website profile.')
    add_profile_parser.add_argument('name', type=str, help='Unique name for the website profile.')
    add_profile_parser.add_argument('--url', type=str, required=True, help='Base URL of the website.')
    add_profile_parser.add_argument('--method', type=str, choices=['http_post'], default='http_post',
                                    help='Upload method (default: http_post).')
    add_profile_parser.add_argument('--remote-path', type=str, default='/',
                                    help='Default remote path on the server (default: /).')
    add_profile_parser.add_argument('--cred-type', type=str, choices=['none', 'basic_auth', 'api_key'],
                                    default='none', help='Type of credentials.')
    add_profile_parser.add_argument('--cred-user', type=str, help='Username for basic_auth.')
    add_profile_parser.add_argument('--cred-pass', type=str, help='Password for basic_auth.')
    add_profile_parser.add_argument('--api-key-name', type=str, help='Header name for API key (e.g., X-API-KEY).')
    add_profile_parser.add_argument('--api-key-value', type=str, help='Value for API key.')

    # List profiles
    list_profile_parser = profile_subparsers.add_parser('list', help='List all configured website profiles.')

    # Get profile
    get_profile_parser = profile_subparsers.add_parser('get', help='Display details of a specific website profile.')
    get_profile_parser.add_argument('name', type=str, help='Name of the website profile to display.')

    # Delete profile
    delete_profile_parser = profile_subparsers.add_parser('delete', help='Delete a website profile.')
    delete_profile_parser.add_argument('name', type=str, help='Name of the website profile to delete.')

    # --- Upload command ---
    upload_parser = subparsers.add_parser('upload', help='Upload a file to a configured website.')
    upload_parser.add_argument('profile_name', type=str, help='Name of the website profile to use for upload.')
    upload_parser.add_argument('local_file_path', type=str, help='Path to the local file to upload.')
    upload_parser.add_argument('--remote-name', type=str,
                               help='Optional. Name to use for the file on the remote server.')

    args = parser.parse_args()

    # Fix: Instantiate ConfigManager without arguments based on the TypeError.
    # Assume ConfigManager has a method to load the config file after instantiation.
    config_manager = ConfigManager()
    try:
        config_manager.load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration from '{args.config}': {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == 'profile':
        if args.profile_command == 'add':
            try:
                credentials = Credentials(
                    type=args.cred_type,
                    username=args.cred_user,
                    password=args.cred_pass,
                    api_key_name=args.api_key_name,
                    api_key_value=args.api_key_value
                )
                profile = WebsiteProfile(
                    name=args.name,
                    url=args.url,
                    upload_method=args.method,
                    credentials=credentials,
                    remote_path=args.remote_path
                )
                config_manager.add_profile(profile)
                config_manager.save_config(args.config)
                print(f"Profile '{args.name}' added successfully.")
            except ValueError as e:
                print(f"Error adding profile: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred: {e}", file=sys.stderr)
                sys.exit(1)

        elif args.profile_command == 'list':
            profiles = config_manager.list_profiles()
            if not profiles:
                print("No website profiles configured.")
            else:
                print("Configured Website Profiles:")
                for name, profile in profiles.items():
                    print(f"  - {profile.name} (URL: {profile.url}, Method: {profile.upload_method})")
                    print(f"    Credentials: {profile.credentials.type}")
                    if profile.credentials.type == 'basic_auth':
                        print(f"    Username: {profile.credentials.username}")
                    elif profile.credentials.type == 'api_key':
                        print(f"    API Key Name: {profile.credentials.api_key_name}")
                    print(f"    Remote Path: {profile.remote_path}")

        elif args.profile_command == 'get':
            try:
                profile = config_manager.get_profile(args.name)
                print(f"Profile Details for '{profile.name}':")
                print(f"  URL: {profile.url}")
                print(f"  Upload Method: {profile.upload_method}")
                print(f"  Remote Path: {profile.remote_path}")
                print(f"  Credentials Type: {profile.credentials.type}")
                if profile.credentials.type == 'basic_auth':
                    print(f"  Username: {profile.credentials.username}")
                elif profile.credentials.type == 'api_key':
                    print(f"  API Key Name: {profile.credentials.api_key_name}")
                    print(f"  API Key Value: {'**********' if profile.credentials.api_key_value else 'None'}") # Mask sensitive info
                else:
                    print("  No specific credentials required.")
            except ValueError as e:
                print(f"Error getting profile: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred: {e}", file=sys.stderr)
                sys.exit(1)

        elif args.profile_command == 'delete':
            try:
                config_manager.delete_profile(args.name)
                config_manager.save_config(args.config)
                print(f"Profile '{args.name}' deleted successfully.")
            except ValueError as e:
                print(f"Error deleting profile: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred: {e}", file=sys.stderr)
                sys.exit(1)

    elif args.command == 'upload':
        try:
            profile = config_manager.get_profile(args.profile_name)
            uploader = Uploader(profile)
            success = uploader.upload_file(args.local_file_path, args.remote_name)
            if success:
                print(f"Upload of '{args.local_file_path}' successful.")
            else:
                print(f"Upload of '{args.local_file_path}' failed.", file=sys.stderr)
                sys.exit(1)
        except ValueError as e:
            print(f"Error during upload: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during upload: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
