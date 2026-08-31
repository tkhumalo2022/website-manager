# Website Manager

A Python utility for discovering, scanning and managing local website projects.

## Why I built it

Working across multiple web projects creates a practical maintenance problem: projects end up spread across folders, configurations differ and it becomes difficult to get a quick view of what exists. Website Manager is an automation project aimed at making that workflow easier.

## Features

- Scans for website projects
- Produces structured website inventory data
- Generates a website scan report
- Centralises configuration
- Separates core logic and utility modules
- Supports packaging as a desktop executable

## Technology

- Python
- JSON configuration
- PyInstaller configuration
- Modular Python architecture

## Structure

```text
core/                 Core application logic
utils/                Shared utilities
main.py               Application entry point
scan_websites.py      Website discovery/scanning
config.py             Configuration handling
config.json           Runtime configuration
WebsiteManager.spec   Packaging configuration
```

## Output

The scanner can produce structured results such as `websites_found.json` and a readable `WEBSITE_SCAN_REPORT.md`, making it easier to inspect the projects discovered during a scan.

## What this project demonstrates

- Python scripting
- File-system automation
- Configuration management
- Modular application structure
- Turning a repetitive development task into a reusable tool

## Status

Utility / portfolio project. The repository is kept public because it represents automation work outside my main web-development stack.
