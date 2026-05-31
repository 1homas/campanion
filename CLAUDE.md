# CLAUDE.md

## Specification

See `references/campanion.md` for the full project specification including architecture, scope, and design decisions.

## API Reference

- **OpenAPI**: `references/meraki_openapi_v3.json` (OpenAPI 3.0)
- **Base URL**: `https://api.meraki.com/api/v1`
- **Auth**: `X-Cisco-Meraki-API-Key: {MERAKI_DASHBOARD_API_KEY}` header or Bearer token

### API Endpoints

| Category      | Endpoints                                                           | Methods     |
| ------------- | ------------------------------------------------------------------- | ----------- |
| Authorization | `/organizations/{orgId}/nac/authorization/policies`                 | GET         |
|               | `.../policies/{policyId}/rules`                                     | POST        |
|               | `.../policies/{policyId}/rules/{ruleId}`                            | PUT, DELETE |
| Certificates  | `/organizations/{orgId}/nac/certificates`                           | GET         |
|               | `.../certificates/{certificateId}`                                  | PUT         |
|               | `.../certificates/import`                                           | POST        |
|               | `.../certificates/overview`                                         | GET         |
|               | `.../certificates/authorities/crls`                                 | GET, POST   |
|               | `.../certificates/authorities/crls/descriptors`                     | GET         |
|               | `.../certificates/authorities/crls/{crlId}`                         | DELETE      |
| Clients       | `/organizations/{orgId}/nac/clients`                                | GET, POST   |
|               | `.../clients/{clientId}`                                            | PUT         |
|               | `.../clients/bulkDelete`                                            | POST        |
|               | `.../clients/bulkEdit`                                              | POST        |
|               | `.../clients/bulkUpload`                                            | POST        |
|               | `.../clients/overview`                                              | GET         |
| Groups        | `/organizations/{orgId}/nac/clients/groups`                         | GET, POST   |
|               | `.../clients/groups/{groupId}`                                      | PUT, DELETE |
| Dictionaries  | `/organizations/{orgId}/nac/dictionaries`                           | GET         |
|               | `.../dictionaries/{dictionaryId}/attributes`                        | GET         |
|               | `.../dictionaries/{dictionaryId}/attributes/{attributeName}/values` | GET         |
| License       | `/organizations/{orgId}/nac/license/usage`                          | GET         |
| Sessions      | `/organizations/{orgId}/nac/sessions/history`                       | GET         |
|               | `.../sessions/{sessionId}/details`                                  | GET         |

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
