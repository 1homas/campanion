# CAMpanion

Cisco Access Manager (CAM) companion CLI for operational management via Meraki Dashboard REST APIs.

## Features

- **NAC Operations**: Manage sessions, policies, certificates, clients, and groups
- **Meraki Dashboard Correlation**: Query networks, devices, switch ports via generic API command
- **Smart Caching**: 7-day cache for GET requests with auto-invalidation on writes
- **Zero Setup**: Uses uv inline metadata — no venv or `pip install` needed

## Quick Start

1. **Set up credentials**:

```bash
cp .env.example .env
# Edit .env with your API key and org ID
```

2. **Run commands**:

```bash
# List NAC sessions
uv run --directory ~/AI/skills/campanion/scripts campanion.py sessions

# Get client counts
uv run --directory ~/AI/skills/campanion/scripts campanion.py clients-overview

# Generic API — query any Meraki endpoint
uv run --directory ~/AI/skills/campanion/scripts campanion.py api GET /organizations/{organizationId}/networks
```

## Available Commands

### Sessions

- `sessions` — List session history
- `session-details <id>` — Get session details
- `count-sessions` — Count sessions by status
- `failed-sessions` — List failed sessions with reasons

### Authorization

- `policies` — List authorization policies
- `rules <policy-id>` — List rules for a policy
- `create-rule <policy-id> --body <json>` — Create rule
- `update-rule <policy-id> <rule-id> --body <json>` — Update rule
- `delete-rule <policy-id> <rule-id>` — Delete rule

### Certificates

- `certificates` — List certificates
- `certificates-overview` — Certificate counts
- `import-certificate --body <json>` — Import certificate
- `update-certificate <id> --body <json>` — Update certificate config
- `crls` — List CRLs
- `crl-descriptors` — CRL metadata
- `create-crl --body <json>` — Create CRL
- `delete-crl <id>` — Delete CRL

### Clients

- `clients` — List NAC clients
- `clients-overview` — Client counts
- `create-client --body <json>` — Create client
- `update-client <id> --body <json>` — Update client
- `bulk-delete-clients --body <json>` — Bulk delete
- `bulk-edit-clients --body <json>` — Bulk edit
- `bulk-upload-clients --body <json>` — Bulk upload

### Client Groups

- `client-groups` — List groups
- `create-client-group --body <json>` — Create group
- `update-client-group <id> --body <json>` — Update group
- `delete-client-group <id>` — Delete group

### Dictionaries

- `dictionaries` — List dictionaries
- `dictionary-attributes <id>` — List attributes
- `attribute-values <dict-id> <attr-name>` — Search attribute values

### License

- `license-usage` — License usage stats

### Generic API

- `api <method> <path> [--params <json>] [--body <json>]` — Call any Meraki Dashboard endpoint

## Global Options

- `--refresh` — Bypass cache on GET requests
- `--raw` — Compact JSON output (no indentation)

## Testing

```bash
uv run --directory ~/AI/skills/campanion/scripts --with pytest --with respx --with click --with click-default-group --with python-dotenv pytest ~/AI/skills/campanion/tests/ -v
```

## Architecture

- **Single-file CLI** with uv inline metadata (no `pyproject.toml`)
- **Smart caching** in `.cache/` with SHA-256 keys and configurable TTL
- **Auto path substitution** — `{organizationId}` replaced automatically
- **Test-driven** — 30+ tests with `respx` mocking (no live API calls)

## Requirements

- Python 3.11+
- uv (for dependency management)

## Environment Variables

| Variable                   | Required | Default                         | Description            |
| -------------------------- | -------- | ------------------------------- | ---------------------- |
| `MERAKI_DASHBOARD_API_KEY` | Yes      | —                               | API key                |
| `MERAKI_ORG_ID`            | Yes      | —                               | Organization ID        |
| `MERAKI_BASE_URL`          | No       | `https://api.meraki.com/api/v1` | Base API URL           |
| `MERAKI_CACHE_TTL`         | No       | `604800`                        | Cache TTL (seconds)    |
| `MERAKI_TIMEOUT`           | No       | `30`                            | HTTP timeout (seconds) |

## Use Cases

- **Troubleshooting**: Query session history and details to diagnose authentication failures
- **Configuration**: Manage authorization policies, rules, certificates, and CRLs
- **Analytics**: Pull license usage, session data, and certificate overview
- **Compliance**: Review certificate authorities and CRL status
- **Correlation**: Use `api` command to query networks, devices, clients for context alongside NAC data
