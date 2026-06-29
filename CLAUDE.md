# CLAUDE.md

## Overview

This is a Claude Code skill providing operational management of Cisco Access Manager (CAM) via Meraki Dashboard REST APIs.

## Specification

See `references/specs.md` for the full project specification including architecture, scope, and design decisions.

## API Reference

- **OpenAPI**: `references/meraki_openapi_v3.json` (OpenAPI 3.0)
- **Base URL**: `https://api.meraki.com/api/v1/organizations/{orgId}`
- **Auth**: `X-Cisco-Meraki-API-Key: {MERAKI_DASHBOARD_API_KEY}` header or Bearer token

### API Endpoints

| Category      | Endpoints                                                            | Methods     |
| ------------- | -------------------------------------------------------------------- | ----------- |
| Authorization | `/nac/authorization/policies`                                        | GET         |
|               | `/nac/authorization/policies/{policyId}/rules`                       | POST        |
|               | `/nac/authorization/policies/{policyId}/rules/{ruleId}`              | PUT, DELETE |
| Certificates  | `/nac/certificates`                                                  | GET         |
|               | `/nac/certificates/{certificateId}`                                  | PUT         |
|               | `/nac/certificates/import`                                           | POST        |
|               | `/nac/certificates/overview`                                         | GET         |
|               | `/nac/certificates/authorities/crls`                                 | GET, POST   |
|               | `/nac/certificates/authorities/crls/descriptors`                     | GET         |
|               | `/nac/certificates/authorities/crls/{crlId}`                         | DELETE      |
| Clients       | `/nac/clients`                                                       | GET, POST   |
|               | `/nac/clients/{clientId}`                                            | PUT         |
|               | `/nac/clients/bulkDelete`                                            | POST        |
|               | `/nac/clients/bulkEdit`                                              | POST        |
|               | `/nac/clients/bulkUpload`                                            | POST        |
|               | `/nac/clients/overview`                                              | GET         |
| Groups        | `/nac/clients/groups`                                                | GET, POST   |
|               | `/nac/clients/groups/{groupId}`                                      | PUT, DELETE |
| Dictionaries  | `/nac/dictionaries`                                                  | GET         |
|               | `/nac/dictionaries/{dictionaryId}/attributes`                        | GET         |
|               | `/nac/dictionaries/{dictionaryId}/attributes/{attributeName}/values` | GET         |
| License       | `/nac/license/usage`                                                 | GET         |
| Sessions      | `/nac/sessions/history`                                              | GET         |
|               | `/nac/sessions/{sessionId}/details`                                  | GET         |

## Setup

### Install uv

This project uses `uv` for Python package management. Install it if not already available:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew (macOS)
brew install uv

# Or via pip
pip install uv
```

Verify installation:

```bash
uv --version
```

## Running Scripts

Never generate custom/inline Python scripts for API queries.
Always use the `scripts/campanion.py` CLI or create new subcommands and options for the `/nac/` APIs.

### Examples

```bash
# Run main script (auto-loads .env from project root)
uv run --directory ~/AI/skills/campanion/scripts campanion.py <command> [options]

# Generic API — call any Meraki Dashboard endpoint
uv run --directory ~/AI/skills/campanion/scripts campanion.py api GET /organizations/{organizationId}/networks
uv run --directory ~/AI/skills/campanion/scripts campanion.py api GET /organizations/{organizationId}/devices --params '{"perPage":100}'

# List switch ports
uv run --directory ~/AI/skills/campanion/scripts campanion.py api GET /devices/Q5VA-W6VM-BXLX/switch/ports

# Shut a switch port
uv run --directory ~/AI/skills/campanion/scripts campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled": false}'

# No-shut a switch port
uv run --directory ~/AI/skills/campanion/scripts campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled": true}'
```

## Key Files

- `scripts/campanion.py` — Main API client (uv inline metadata, no venv needed)
- `.env` — Credentials (gitignored)
- `tests/*.py` — Unit tests
- `references/openapiSpec.json`
- `references/spec.md`

## Packages

Use Python packages:

- httpx
- pyyaml
- asyncio

## Testing

- Use Red/Green Test-Driven Development to ensure quality with every change
- Tests use `respx` to mock HTTP responses — no live API calls needed
- Run tests:

```bash
uv run --directory ~/AI/skills/campanion/scripts --with pytest --with respx --with click --with click-default-group --with python-dotenv pytest ~/AI/skills/campanion/tests/ -v
```
