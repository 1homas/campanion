# Campanion Specification

## Purpose

A Claude Code skill for operational management of Cisco Access Manager (CAM) via the Meraki Dashboard REST APIs. Provides both an agent-invocable skill interface and a standalone CLI for read/write access to NAC-specific endpoints (sessions, policies, certificates, clients, dictionaries, licensing) and correlation via the generic Meraki Dashboard API (networks, devices, switch ports).

## Scope

### In Scope

- **NAC Operations** (read + write): authorization policies/rules, certificates, CRLs, clients, client groups, dictionaries, license usage, session history/details
- **Meraki Dashboard Correlation** (read + write via `api` command): networks, devices, switch ports, clients — any endpoint in the OpenAPI spec
- **Documentation Queries**: answer CAM product questions using bundled `assets/` documentation

### Out of Scope

- Creating or modifying Meraki organizations or networks
- Meraki wireless, appliance, or camera configuration
- Multi-org operations (single org per `.env`)
- User authentication or SSO configuration (CAM handles this server-side)

## Architecture

```
campanion/
├── SKILL.md                # Skill frontmatter + agent instructions
├── scripts/
│   └── campanion.py        # Main CLI (Click, httpx, uv inline deps)
├── tests/
│   └── test_campanion.py   # Unit tests (pytest, respx mocks)
├── assets/                 # CAM/Meraki product documentation (markdown)
├── references/
│   ├── specs.md            # This specification
│   └── meraki_openapi_v3.json  # Meraki Dashboard OpenAPI 3.0 spec
├── .cache/                 # API response cache (gitignored)
├── .env                    # Credentials (gitignored)
├── CLAUDE.md               # Claude Code project instructions
└── README.md               # Human-readable project documentation
```

### Skill vs CLI

- **Skill** (`SKILL.md`): Agent-invocable via `/campanion` — automatically triggers on CAM-related queries
- **CLI** (`campanion.py`): Direct command-line tool for scripting and manual operations

## CLI Design

### Invocation

The CLI can be executed directly (recommended) or via `uv run`:

```bash
# Direct execution (executable script)
~/AI/skills/campanion/scripts/campanion.py <command> [options]

# Or via uv run
uv run --directory ~/AI/skills/campanion/scripts campanion.py <command> [options]
```

The script uses `#!/usr/bin/env -S uv run` shebang with inline PEP 723 metadata — no virtual environment or `pip install` required.

### Commands

All GET commands support their respective REST API query parameters for filtering, pagination, sorting, and time ranges.

| Command                 | Verb   | Endpoint                                          | Description                  | Key Query Parameters                                               |
| ----------------------- | ------ | ------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------ |
| `sessions`              | GET    | `/nac/sessions/history`                           | List session history         | `--t0`, `--timespan`, `--per-page`, `--starting-after`             |
| `session-details`       | GET    | `/nac/sessions/{id}/details`                      | Session detail               | —                                                                  |
| `count-sessions`        | GET    | `/nac/sessions/history` (aggregated)              | Count by status              | `--t0`, `--timespan`                                               |
| `failed-sessions`       | GET    | `/nac/sessions/history` (filtered)                | Failed sessions with reasons | `--t0`, `--timespan`                                               |
| `policies`              | GET    | `/nac/authorization/policies`                     | List auth policies           | `--policy-ids`                                                     |
| `rules`                 | GET    | `/nac/authorization/policies` (filtered)          | List rules for a policy      | —                                                                  |
| `create-rule`           | POST   | `/nac/authorization/policies/{id}/rules`          | Create auth rule             | —                                                                  |
| `update-rule`           | PUT    | `/nac/authorization/policies/{id}/rules/{id}`     | Update auth rule             | —                                                                  |
| `delete-rule`           | DELETE | `/nac/authorization/policies/{id}/rules/{id}`     | Delete auth rule             | —                                                                  |
| `certificates`          | GET    | `/nac/certificates`                               | List certificates            | `--status`, `--expiry`, `--last-used`                              |
| `certificates-overview` | GET    | `/nac/certificates/overview`                      | Certificate counts           | —                                                                  |
| `import-certificate`    | POST   | `/nac/certificates/import`                        | Import certificate           | —                                                                  |
| `update-certificate`    | PUT    | `/nac/certificates/{id}`                          | Update certificate config    | —                                                                  |
| `crls`                  | GET    | `/nac/certificates/authorities/crls`              | List CRLs                    | `--per-page`, `--sort-by`, `--sort-order`, `--crl-ids`, `--ca-ids` |
| `crl-descriptors`       | GET    | `/nac/certificates/authorities/crls/descriptors`  | CRL metadata                 | `--per-page`, `--sort-by`, `--sort-order`, `--ca-ids`              |
| `create-crl`            | POST   | `/nac/certificates/authorities/crls`              | Create CRL                   | —                                                                  |
| `delete-crl`            | DELETE | `/nac/certificates/authorities/crls/{id}`         | Delete CRL                   | —                                                                  |
| `clients`               | GET    | `/nac/clients`                                    | List NAC clients             | `--search`, `--sort-key`, `--client-ids`, `--group-ids`, `--ssid`  |
| `clients-overview`      | GET    | `/nac/clients/overview`                           | Client counts                | —                                                                  |
| `create-client`         | POST   | `/nac/clients`                                    | Create client                | —                                                                  |
| `update-client`         | PUT    | `/nac/clients/{id}`                               | Update client                | —                                                                  |
| `bulk-delete-clients`   | POST   | `/nac/clients/bulkDelete`                         | Bulk delete                  | —                                                                  |
| `bulk-edit-clients`     | POST   | `/nac/clients/bulkEdit`                           | Bulk edit                    | —                                                                  |
| `bulk-upload-clients`   | POST   | `/nac/clients/bulkUpload`                         | Bulk upload                  | —                                                                  |
| `client-groups`         | GET    | `/nac/clients/groups`                             | List client groups           | `--search`, `--sort-key`, `--group-ids`, `--per-page`              |
| `create-client-group`   | POST   | `/nac/clients/groups`                             | Create group                 | —                                                                  |
| `update-client-group`   | PUT    | `/nac/clients/groups/{id}`                        | Update group                 | —                                                                  |
| `delete-client-group`   | DELETE | `/nac/clients/groups/{id}`                        | Delete group                 | —                                                                  |
| `dictionaries`          | GET    | `/nac/dictionaries`                               | List dictionaries            | —                                                                  |
| `dictionary-attributes` | GET    | `/nac/dictionaries/{id}/attributes`               | List attributes              | `--network-ids`                                                    |
| `attribute-values`      | GET    | `/nac/dictionaries/{id}/attributes/{name}/values` | Search attribute values      | `--search`, `--network-ids`                                        |
| `license-usage`         | GET    | `/nac/license/usage`                              | License usage stats          | `--start-date`, `--end-date`, `--network-ids`                      |
| `api`                   | ANY    | Any Meraki Dashboard path                         | Generic API call             | `--params`, `--body`                                               |

### Global Options

Most GET commands support:

| Flag               | Description                                                |
| ------------------ | ---------------------------------------------------------- |
| `--refresh`        | Bypass cache for GET requests                              |
| `--raw`            | Compact JSON output (no indentation)                       |
| `--per-page`       | Results per page (varies by endpoint: 3-1000)              |
| `--starting-after` | Pagination token for next page                             |
| `--ending-before`  | Pagination token for previous page                         |
| `--sort-order`     | Sort direction (`asc` or `desc`)                           |
| `--sort-key`       | Field to sort by (varies by endpoint)                      |
| `--search`         | Fuzzy search string (clients, groups, attribute values)    |
| `--t0`             | Start time (ISO8601 or Unix timestamp, sessions only)      |
| `--timespan`       | Duration in seconds (max 2678400 = 31 days, sessions only) |

Refer to `<command> --help` for endpoint-specific options.

### Caching

- GET responses cached in `.cache/` with SHA-256 keyed filenames
- Default TTL: 7 days (`MERAKI_CACHE_TTL` env var, in seconds)
- `--refresh` flag bypasses cache on any GET command
- Write operations (POST/PUT/DELETE) auto-invalidate related cache entries

## Environment Variables

| Variable                   | Required | Default                         | Description            |
| -------------------------- | -------- | ------------------------------- | ---------------------- |
| `MERAKI_DASHBOARD_API_KEY` | Yes      | —                               | API key                |
| `MERAKI_ORG_ID`            | Yes      | —                               | Organization ID        |
| `MERAKI_BASE_URL`          | No       | `https://api.meraki.com/api/v1` | Base API URL           |
| `MERAKI_CACHE_TTL`         | No       | `604800`                        | Cache TTL (seconds)    |
| `MERAKI_TIMEOUT`           | No       | `30`                            | HTTP timeout (seconds) |

## Dependencies

Runtime (declared as uv inline metadata):

- `httpx` — HTTP client
- `python-dotenv` — `.env` loading
- `click` — CLI framework (campanion.py)
- `click-default-group` — default command group

Testing:

- `pytest` — test runner
- `respx` — httpx mock transport

## Testing Strategy

- Red/Green TDD for all CLI commands
- `respx` mocks httpx at the transport level — no live API calls
- Temp directory for cache isolation per test
- All 30+ tests validate: exit codes, JSON output structure, cache behavior, error handling

## Constraints

- Single-file scripts with uv inline metadata (no `pyproject.toml`, no venv)
- Python 3.11+ required
- Auth via `X-Cisco-Meraki-API-Key` header (not Bearer token)
- `{organizationId}` auto-substituted in the `api` command; all other path params must be literal

## Skill Trigger

The skill automatically activates when Claude Code detects questions or tasks related to:

- Cisco Access Manager (CAM) features, configuration, or troubleshooting
- Meraki NAC operations
- Authentication sessions or session history
- Authorization policies or policy rules
- Certificates, CRLs, or certificate authorities
- NAC clients, endpoints, or client groups
- NAC license usage or licensing
- Correlating NAC data with Meraki Dashboard (networks, devices, switch ports)

## Use Cases

- **Troubleshooting**: Query session history and details to diagnose authentication failures
- **Configuration**: Manage authorization policies, rules, certificates, and CRLs
- **Analytics**: Pull license usage, session data, and certificate overview
- **Compliance**: Review certificate authorities and CRL status

## Output Formats

### Authorization Policy Display

When displaying authorization policies in table format, use this column order:

| Rank | Rule Name | Conditions | Authorization |
| ---- | --------- | ---------- | ------------- |

- **Rank**: Rule priority (0-based, lower executes first)
- **Rule Name**: Descriptive name for the rule
- **Conditions**: Compact summary of matching criteria (auth method, device type, groups, certificates, etc.)
- **Authorization**: Result (PERMIT/DENY) + SGT + additional attributes (iPSK, Voice Domain, etc.)

## Versioning

Follows [Semantic Versioning](https://semver.org/). Current version: `0.2.0` (declared in `SKILL.md` frontmatter).
