# Website Manager

A Python utility for discovering local website projects and managing upload profiles from one command-line workflow.

## Why I built it

Working across several web projects creates a simple maintenance problem: projects end up spread across different folders and it becomes difficult to see what exists, which stack each project uses and whether an upload/API path is already available.

Website Manager automates that first inspection step and keeps reusable upload profiles in one place.

## Features

- Scans common project folders automatically
- Detects common web stacks from project files
- Checks for API and upload-related code
- Produces JSON inventory data and a readable Markdown report
- Manages website upload profiles from the command line
- Keeps local configuration separate from the public repository
- Supports packaging as a desktop executable

## Technology

- Python
- JSON configuration
- `pathlib` and file-system automation
- PyInstaller configuration

## Project structure

```text
core/                           Core upload logic
utils/                          Shared utilities
examples/                       Sanitized example scan output
main.py                         CLI entry point
scan_websites.py                Website discovery and reporting
config.py                       Configuration model and persistence
config.example.json             Safe configuration template
WebsiteManager.spec             Packaging configuration
```

## Setup

The application works without a local config file by loading its built-in demonstration profiles. For persistent local profiles, copy the example first:

```bash
cp config.example.json config.json
```

`config.json` is intentionally ignored by Git because it can contain local paths and credentials.

## Scanning projects

Run:

```bash
python scan_websites.py
```

By default the scanner checks common locations under the current user's home directory, including Desktop, Downloads and OneDrive Desktop when present.

To provide custom scan roots, set `WEBSITE_MANAGER_SCAN_PATHS` using the operating system path separator between locations.

The scan generates:

```text
websites_found.json
WEBSITE_SCAN_REPORT.md
```

Both files are intentionally ignored by Git because real reports contain absolute local file paths. Sanitized examples are available in `examples/`.

## CLI examples

List configured profiles:

```bash
python main.py profile list
```

Add a profile:

```bash
python main.py profile add my-site --url https://example.com/api/upload --method http_post
```

Upload a file using a configured profile:

```bash
python main.py upload my-site ./content/example.txt
```

## What this project demonstrates

- Python scripting and CLI design
- File-system automation
- Configuration management
- Basic stack detection
- Modular application structure
- Handling local machine data more safely in a public repository
- Turning a repetitive development task into a reusable utility

## Status

Utility and portfolio project.
