import os
import json
from pathlib import Path
from datetime import datetime


def default_scan_paths():
    """Return portable default locations without hard-coding a developer machine."""
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "Downloads",
        home / "OneDrive" / "Desktop",
        home / "Desktop" / "JarvisProjects",
    ]

    custom_paths = os.environ.get("WEBSITE_MANAGER_SCAN_PATHS", "").strip()
    if custom_paths:
        return [Path(value).expanduser() for value in custom_paths.split(os.pathsep) if value.strip()]

    return candidates


SCAN_PATHS = default_scan_paths()

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".vercel", ".netlify", "venv", ".venv", "env"
}

WEBSITE_MARKERS = {
    "package.json", "index.html", "vite.config.js", "vite.config.ts",
    "next.config.js", "next.config.mjs", "vercel.json", "netlify.toml",
    "tailwind.config.js", "tailwind.config.ts"
}

API_MARKERS = [
    "app/api",
    "pages/api",
    "server.js",
    "app.js",
    "routes",
    "controllers"
]


def safe_read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def detect_stack(folder):
    files = {p.name.lower() for p in folder.iterdir() if p.is_file()}
    dirs = {p.name.lower() for p in folder.iterdir() if p.is_dir()}

    package_json = folder / "package.json"
    package_text = safe_read(package_json).lower() if package_json.exists() else ""

    if "next" in package_text or "next.config.js" in files or "next.config.mjs" in files:
        return "Next.js"
    if "vite" in package_text or "vite.config.js" in files or "vite.config.ts" in files:
        return "Vite / React"
    if "react" in package_text:
        return "React"
    if "express" in package_text or "server.js" in files or "app.js" in files:
        return "Node / Express"
    if "index.html" in files:
        return "Static HTML"
    if "streamlit" in package_text:
        return "Python / Streamlit"
    if "src" in dirs and "public" in dirs:
        return "Frontend Web App"
    return "Unknown Web Project"


def has_api(folder):
    checks = [
        folder / "app" / "api",
        folder / "pages" / "api",
        folder / "routes",
        folder / "controllers",
        folder / "server.js",
        folder / "app.js"
    ]
    return any(p.exists() for p in checks)


def find_upload_endpoint(folder):
    patterns = ["upload", "/api/upload", "app.post", "router.post"]
    found = []

    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        depth = len(Path(root).relative_to(folder).parts)
        if depth > 4:
            dirs[:] = []
            continue

        for file in files:
            if file.endswith((".js", ".ts", ".jsx", ".tsx", ".py", ".json")):
                path = Path(root) / file
                text = safe_read(path).lower()
                for pattern in patterns:
                    if pattern in text:
                        found.append(str(path))
                        break

    return found[:5]


def detect_deployment(folder):
    deployments = []
    if (folder / "vercel.json").exists():
        deployments.append("Vercel")
    if (folder / "netlify.toml").exists():
        deployments.append("Netlify")
    if (folder / ".git").exists():
        deployments.append("Git")
    if (folder / "package.json").exists():
        text = safe_read(folder / "package.json").lower()
        if "vercel" in text:
            deployments.append("Vercel clue")
        if "netlify" in text:
            deployments.append("Netlify clue")
    return ", ".join(deployments) if deployments else "Unknown"


def is_website(folder):
    try:
        names = {p.name for p in folder.iterdir()}
    except Exception:
        return False

    if WEBSITE_MARKERS.intersection(names):
        return True

    if "src" in names and "public" in names:
        return True

    if "app" in names or "pages" in names:
        return True

    return False


def scan():
    results = []
    seen = set()

    for base in SCAN_PATHS:
        base_path = Path(base)
        if not base_path.exists():
            continue

        for root, dirs, files in os.walk(base_path):
            root_path = Path(root)

            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            try:
                rel_depth = len(root_path.relative_to(base_path).parts)
            except Exception:
                rel_depth = 0

            if rel_depth > 4:
                dirs[:] = []
                continue

            if str(root_path).lower() in seen:
                continue

            if is_website(root_path):
                stack = detect_stack(root_path)
                api = has_api(root_path)
                upload_files = find_upload_endpoint(root_path)
                deployment = detect_deployment(root_path)

                if api and upload_files:
                    recommended = "Existing API likely available. Inspect endpoint files."
                elif stack in ["Next.js", "Node / Express"]:
                    recommended = "Add protected /api/upload endpoint."
                elif stack in ["Vite / React", "React", "Static HTML", "Frontend Web App"]:
                    recommended = "Use GitHub/Vercel content update workflow or add backend."
                else:
                    recommended = "Manual review needed."

                results.append({
                    "website_name": root_path.name,
                    "path": str(root_path),
                    "stack": stack,
                    "has_api": api,
                    "upload_endpoint_files": upload_files,
                    "deployment": deployment,
                    "recommended_integration": recommended
                })

                seen.add(str(root_path).lower())
                dirs[:] = []

    return results


def write_reports(results):
    with open("websites_found.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    lines = []
    lines.append("# Website Scan Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"Total websites found: {len(results)}")
    lines.append("")
    lines.append("| Website Name | Path | Stack | Has API? | Upload Files Found | Deployment | Recommended Integration |")
    lines.append("|---|---|---|---|---|---|---|")

    for site in results:
        upload_files = "<br>".join(site["upload_endpoint_files"]) if site["upload_endpoint_files"] else "None"
        lines.append(
            f"| {site['website_name']} | {site['path']} | {site['stack']} | {site['has_api']} | {upload_files} | {site['deployment']} | {site['recommended_integration']} |"
        )

    with open("WEBSITE_SCAN_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    found = scan()
    write_reports(found)

    print("")
    print("Website scan complete.")
    print(f"Websites found: {len(found)}")
    print("Created:")
    print("- WEBSITE_SCAN_REPORT.md")
    print("- websites_found.json")
    print("")
    print("Open the report with:")
    print("notepad WEBSITE_SCAN_REPORT.md")
