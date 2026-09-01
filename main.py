import argparse
import os
import sys
from pathlib import Path

from config import ConfigManager, Credentials, WebsiteProfile
from core.uploader import Uploader
from scan_websites import default_scan_paths, scan, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="website-manager",
        description="Discover local website projects and manage safe upload profiles.",
    )
    parser.add_argument("--config", default="config.json", help="Path to local JSON configuration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Discover website projects")
    scan_parser.add_argument("--path", action="append", dest="paths", help="Scan root; repeat for multiple roots")
    scan_parser.add_argument("--max-depth", type=int, default=4)
    scan_parser.add_argument("--output-dir", default=".")

    doctor_parser = subparsers.add_parser("doctor", help="Validate local configuration and required environment variables")
    doctor_parser.add_argument("--show-paths", action="store_true")

    profile_parser = subparsers.add_parser("profile", help="Manage upload profiles")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

    add = profile_sub.add_parser("add", help="Add a profile")
    add.add_argument("name")
    add.add_argument("--url", required=True)
    add.add_argument("--method", choices=["http_multipart", "tkws_signed"], default="http_multipart")
    add.add_argument("--remote-path", default="/")
    add.add_argument("--cred-type", choices=["none", "basic_auth", "api_key"], default="none")
    add.add_argument("--cred-user")
    add.add_argument("--password-env")
    add.add_argument("--api-key-name")
    add.add_argument("--api-key-env")
    add.add_argument("--customer-id-env")
    add.add_argument("--supabase-anon-key-env")
    add.add_argument("--replace", action="store_true")

    profile_sub.add_parser("list", help="List profiles")
    get = profile_sub.add_parser("get", help="Show a profile without exposing secret values")
    get.add_argument("name")
    delete = profile_sub.add_parser("delete", help="Delete a profile")
    delete.add_argument("name")

    upload = subparsers.add_parser("upload", help="Upload a file using a profile")
    upload.add_argument("profile_name")
    upload.add_argument("local_file_path")
    upload.add_argument("--remote-name")
    upload.add_argument("--dry-run", action="store_true")
    return parser


def load_manager(path: str) -> ConfigManager:
    manager = ConfigManager()
    manager.load_config(path)
    return manager


def command_scan(args) -> int:
    paths = [Path(value).expanduser() for value in args.paths] if args.paths else None
    results = scan(paths=paths, max_depth=args.max_depth)
    write_reports(results, Path(args.output_dir))
    print(f"Found {len(results)} website project(s).")
    print(f"Report: {Path(args.output_dir) / 'WEBSITE_SCAN_REPORT.md'}")
    return 0


def command_doctor(args, manager: ConfigManager, config_path: str) -> int:
    problems = []
    print(f"Config: {Path(config_path).resolve()} {'(present)' if Path(config_path).exists() else '(not created yet)'}")
    profiles = manager.list_profiles()
    print(f"Profiles: {len(profiles)}")

    for profile in profiles.values():
        creds = profile.credentials
        if creds.type == "basic_auth" and creds.password_env and not os.getenv(creds.password_env):
            problems.append(f"{profile.name}: missing environment variable {creds.password_env}")
        if creds.type == "api_key" and creds.api_key_env and not os.getenv(creds.api_key_env):
            problems.append(f"{profile.name}: missing environment variable {creds.api_key_env}")
        if profile.upload_method == "tkws_signed":
            for variable in (profile.customer_id_env, profile.supabase_anon_key_env):
                if not variable:
                    problems.append(f"{profile.name}: tkws_signed requires customer/supabase env variable names")
                elif not os.getenv(variable):
                    problems.append(f"{profile.name}: missing environment variable {variable}")

    if args.show_paths:
        print("Default scan roots:")
        for path in default_scan_paths():
            print(f"- {path} {'OK' if path.exists() else 'missing'}")

    if problems:
        print("Doctor found issues:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Doctor checks passed.")
    return 0


def command_profile(args, manager: ConfigManager, config_path: str) -> int:
    if args.profile_command == "add":
        credentials = Credentials(
            type=args.cred_type,
            username=args.cred_user,
            password_env=args.password_env,
            api_key_name=args.api_key_name,
            api_key_env=args.api_key_env,
        )
        profile = WebsiteProfile(
            name=args.name,
            url=args.url,
            upload_method=args.method,
            credentials=credentials,
            remote_path=args.remote_path,
            customer_id_env=args.customer_id_env,
            supabase_anon_key_env=args.supabase_anon_key_env,
        )
        manager.add_profile(profile, replace=args.replace)
        manager.save_config(config_path)
        print(f"Saved profile '{profile.name}'.")
        return 0

    if args.profile_command == "list":
        profiles = manager.list_profiles()
        if not profiles:
            print("No profiles configured.")
            return 0
        for profile in profiles.values():
            print(f"{profile.name}: {profile.upload_method} -> {profile.url}{profile.remote_path}")
        return 0

    if args.profile_command == "get":
        profile = manager.get_profile(args.name)
        print(f"Name: {profile.name}")
        print(f"URL: {profile.url}")
        print(f"Method: {profile.upload_method}")
        print(f"Remote path: {profile.remote_path}")
        print(f"Credentials: {profile.credentials.type}")
        if profile.credentials.password_env:
            print(f"Password env: {profile.credentials.password_env}")
        if profile.credentials.api_key_env:
            print(f"API key env: {profile.credentials.api_key_env}")
        if profile.customer_id_env:
            print(f"Customer ID env: {profile.customer_id_env}")
        if profile.supabase_anon_key_env:
            print(f"Supabase anon-key env: {profile.supabase_anon_key_env}")
        return 0

    if args.profile_command == "delete":
        manager.delete_profile(args.name)
        manager.save_config(config_path)
        print(f"Deleted profile '{args.name}'.")
        return 0

    return 2


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        return command_scan(args)

    try:
        manager = load_manager(args.config)
        if args.command == "doctor":
            return command_doctor(args, manager, args.config)
        if args.command == "profile":
            return command_profile(args, manager, args.config)
        if args.command == "upload":
            profile = manager.get_profile(args.profile_name)
            success = Uploader(profile).upload_file(
                args.local_file_path,
                args.remote_name,
                dry_run=args.dry_run,
            )
            return 0 if success else 1
    except (KeyError, ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
