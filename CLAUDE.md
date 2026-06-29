# CLAUDE.md

## Overview

This is a Claude Code skill providing operational management of Cisco Access Manager (CAM) via Meraki Dashboard REST APIs.

## Specification

See `references/specs.md` for the full project specification including architecture, scope, and design decisions.

## API Reference

- **OpenAPI**: `references/meraki_openapi_v3.json` (OpenAPI 3.0)
- **Base URL**: `https://api.meraki.com/api/v1`
- **Auth**: `X-Cisco-Meraki-API-Key: {MERAKI_DASHBOARD_API_KEY}` header or Bearer token

### API Endpoints

| Category      | Endpoints                                                                                          | Methods     |
| ------------- | -------------------------------------------------------------------------------------------------- | ----------- |
| Authorization | `/organizations/{orgId}/nac/authorization/policies`                                                | GET         |
|               | `/organizations/{orgId}/nac/authorization/policies/{policyId}/rules`                               | POST        |
|               | `/organizations/{orgId}/nac/authorization/policies/{policyId}/rules/{ruleId}`                      | PUT, DELETE |
| Certificates  | `/organizations/{orgId}/nac/certificates`                                                          | GET         |
|               | `/organizations/{orgId}/nac/certificates/{certificateId}`                                          | PUT         |
|               | `/organizations/{orgId}/nac/certificates/import`                                                   | POST        |
|               | `/organizations/{orgId}/nac/certificates/overview`                                                 | GET         |
|               | `/organizations/{orgId}/nac/certificates/authorities/crls`                                         | GET, POST   |
|               | `/organizations/{orgId}/nac/certificates/authorities/crls/descriptors`                             | GET         |
|               | `/organizations/{orgId}/nac/certificates/authorities/crls/{crlId}`                                 | DELETE      |
| Clients       | `/organizations/{orgId}/nac/clients`                                                               | GET, POST   |
|               | `/organizations/{orgId}/nac/clients/{clientId}`                                                    | PUT         |
|               | `/organizations/{orgId}/nac/clients/bulkDelete`                                                    | POST        |
|               | `/organizations/{orgId}/nac/clients/bulkEdit`                                                      | POST        |
|               | `/organizations/{orgId}/nac/clients/bulkUpload`                                                    | POST        |
|               | `/organizations/{orgId}/nac/clients/overview`                                                      | GET         |
| Groups        | `/organizations/{orgId}/nac/clients/groups`                                                        | GET, POST   |
|               | `/organizations/{orgId}/nac/clients/groups/{groupId}`                                              | PUT, DELETE |
| Dictionaries  | `/organizations/{orgId}/nac/dictionaries`                                                          | GET         |
|               | `/organizations/{orgId}/nac/dictionaries/{dictionaryId}/attributes`                                | GET         |
|               | `/organizations/{orgId}/nac/dictionaries/{dictionaryId}/attributes/{attributeName}/values`         | GET         |
| License       | `/organizations/{orgId}/nac/license/usage`                                                         | GET         |
| Sessions      | `/organizations/{orgId}/nac/sessions/history`                                                      | GET         |
|               | `/organizations/{orgId}/nac/sessions/{sessionId}/details`                                          | GET         |

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
