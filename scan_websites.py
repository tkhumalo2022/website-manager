import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".vercel", ".netlify", "venv", ".venv", "env", ".idea", ".gradle"
}
WEBSITE_MARKERS = {
    "package.json", "index.html", "vite.config.js", "vite.config.ts",
    "next.config.js", "next.config.mjs", "vercel.json", "netlify.toml",
    "tailwind.config.js", "tailwind.config.ts", "astro.config.mjs"
}


def default_scan_paths() -> List[Path]:
    custom = os.getenv("WEBSITE_MANAGER_SCAN_PATHS", "").strip()
    if custom:
        return [Path(value).expanduser() for value in custom.split(os.pathsep) if value.strip()]
    home = Path.home()
    return [home / "Desktop", home / "Downloads", home / "OneDrive" / "Desktop"]


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect_stack(folder: Path) -> str:
    files = {p.name.lower() for p in folder.iterdir() if p.is_file()}
    dirs = {p.name.lower() for p in folder.iterdir() if p.is_dir()}
    package_text = safe_read(folder / "package.json").lower()

    if "next" in package_text or {"next.config.js", "next.config.mjs"} & files:
        return "Next.js"
    if "astro" in package_text or "astro.config.mjs" in files:
        return "Astro"
    if "vite" in package_text or {"vite.config.js", "vite.config.ts"} & files:
        return "Vite / React"
    if "react" in package_text:
        return "React"
    if "express" in package_text or {"server.js", "app.js"} & files:
        return "Node / Express"
    if "index.html" in files:
        return "Static HTML"
    if "src" in dirs and "public" in dirs:
        return "Frontend Web App"
    return "Unknown Web Project"


def has_api(folder: Path) -> bool:
    checks = [
        folder / "app" / "api", folder / "pages" / "api", folder / "api",
        folder / "routes", folder / "controllers", folder / "server.js", folder / "app.js"
    ]
    return any(path.exists() for path in checks)


def find_upload_endpoint(folder: Path) -> List[str]:
    patterns = ("upload", "signedurl", "signed_url", "create-upload")
    found: List[str] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [directory for directory in dirs if directory not in IGNORE_DIRS]
        root_path = Path(root)
        if len(root_path.relative_to(folder).parts) > 4:
            dirs[:] = []
            continue
        for filename in files:
            if not filename.endswith((".js", ".mjs", ".ts", ".jsx", ".tsx", ".py")):
                continue
            path = root_path / filename
            text = safe_read(path).lower()
            if any(pattern in text for pattern in patterns):
                found.append(str(path))
                if len(found) >= 8:
                    return found
    return found


def detect_deployment(folder: Path) -> str:
    deployments = []
    if (folder / "vercel.json").exists():
        deployments.append("Vercel")
    if (folder / "netlify.toml").exists():
        deployments.append("Netlify")
    if (folder / ".git").exists():
        deployments.append("Git")
    return ", ".join(deployments) if deployments else "Unknown"


def is_website(folder: Path) -> bool:
    try:
        names = {path.name for path in folder.iterdir()}
    except OSError:
        return False
    return bool(WEBSITE_MARKERS & names or ({"src", "public"} <= names) or "app" in names or "pages" in names)


def scan(paths: Optional[Iterable[Path]] = None, max_depth: int = 4):
    results = []
    seen = set()
    for base in paths or default_scan_paths():
        base_path = Path(base).expanduser().resolve()
        if not base_path.exists():
            continue
        for root, dirs, _ in os.walk(base_path):
            root_path = Path(root)
            dirs[:] = [directory for directory in dirs if directory not in IGNORE_DIRS]
            try:
                depth = len(root_path.relative_to(base_path).parts)
            except ValueError:
                depth = 0
            if depth > max_depth:
                dirs[:] = []
                continue
            key = str(root_path).casefold()
            if key in seen or not is_website(root_path):
                continue

            stack = detect_stack(root_path)
            api = has_api(root_path)
            upload_files = find_upload_endpoint(root_path)
            if api and upload_files:
                recommendation = "Existing API/upload code found; inspect before adding another endpoint."
            elif stack in {"Next.js", "Node / Express", "Astro"}:
                recommendation = "Add or connect a protected upload API if content uploads are required."
            else:
                recommendation = "Use a deployment workflow or pair this frontend with a backend."

            results.append({
                "website_name": root_path.name,
                "path": str(root_path),
                "stack": stack,
                "has_api": api,
                "upload_endpoint_files": upload_files,
                "deployment": detect_deployment(root_path),
                "recommended_integration": recommendation,
            })
            seen.add(key)
            dirs[:] = []
    return results


def write_reports(results, output_dir: Path = Path(".")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "websites_found.json"
    report_path = output_dir / "WEBSITE_SCAN_REPORT.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Website Scan Report", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", "",
        f"Total websites found: {len(results)}", "",
        "| Website | Stack | API | Deployment | Recommended integration |",
        "|---|---|---:|---|---|",
    ]
    for site in results:
        lines.append(
            f"| {site['website_name']} | {site['stack']} | {site['has_api']} | "
            f"{site['deployment']} | {site['recommended_integration']} |"
        )
        if site["upload_endpoint_files"]:
            lines.append("")
            lines.append(f"**{site['website_name']} upload-related files**")
            for item in site["upload_endpoint_files"]:
                lines.append(f"- `{item}`")
            lines.append("")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    found = scan()
    write_reports(found)
    print(f"Website scan complete. Found {len(found)} project(s).")
