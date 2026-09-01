# Website Manager

Website Manager is a small Python operations utility for developers who keep several web projects on one machine. It discovers local sites, identifies their likely stack/API surface, generates an inventory report, and keeps reusable upload profiles in one CLI.

## What v1 does

- Scan Desktop, Downloads, OneDrive Desktop, or custom roots for website projects.
- Detect common stacks including Next.js, Vite/React, React, Astro, Express and static HTML.
- Flag API/upload-related code and produce JSON + Markdown reports.
- Maintain local upload profiles without requiring secrets in the repository.
- Upload to a normal multipart HTTP endpoint.
- Upload through the TK Web Studio signed-upload flow.
- Run a local `doctor` check before uploads.
- Support dry-run validation before any network request.

## Install

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` for local profiles. `config.json`, generated scan reports and local credentials are intentionally ignored by Git.

## Scan websites

```bash
python main.py scan
python main.py scan --path "C:\\Projects" --path "D:\\Client Sites"
```

Generated files:

- `websites_found.json`
- `WEBSITE_SCAN_REPORT.md`

## Manage profiles

```bash
python main.py profile list
python main.py profile add my-site \
  --url https://example.com \
  --method http_multipart \
  --remote-path /api/upload \
  --cred-type api_key \
  --api-key-name X-API-KEY \
  --api-key-env MY_SITE_API_KEY
```

Secret values should live in environment variables. The config stores only the environment-variable names.

### TK Web Studio signed uploads

```bash
python main.py profile add tk-web-studio \
  --url https://tkwebstudio.company \
  --method tkws_signed \
  --remote-path /api/create-upload-url \
  --customer-id-env TKWS_CUSTOMER_ID \
  --supabase-anon-key-env SUPABASE_ANON_KEY
```

Then set those environment variables locally before uploading.

## Validate before uploading

```bash
python main.py doctor --show-paths
python main.py upload tk-web-studio ./content/logo.png --dry-run
python main.py upload tk-web-studio ./content/logo.png
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Safety model

- Real config files and scan output stay local.
- Profile listing never prints secret values.
- New profiles use environment-variable references for passwords/API keys.
- `--dry-run` validates routing and file metadata without making a network request.
- The TK Web Studio path requires explicit customer ID and Supabase anon-key environment variables.

## Project status

**v1 implementation** — usable CLI utility with scanning, profile management, upload routing, dry-run checks and unit tests.
