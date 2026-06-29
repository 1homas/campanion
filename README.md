# CAMpanion

A Claude Code skill providing operational management of Cisco Access Manager (CAM) via Meraki Dashboard REST APIs. Using CLI commands is more efficient than an MCP server when performing REST API operations.

## Features

- **Claude Code Skill**: Invocable via `/campanion` to analyze, correlate, configure, and troubleshoot CAM deployments
- **NAC Operations**: Manage sessions, policies, certificates, clients, and groups
- **Meraki Dashboard Correlation**: Query networks, devices, switch ports via generic API command
- **Smart Caching**: 7-day cache for GET requests with auto-invalidation on writes
- **Zero Setup**: Uses uv inline metadata — no venv or `pip install` needed

## Quick Start

### As a Skill

```bash
/campanion
```

The skill triggers automatically when Claude Code detects questions about CAM, Meraki NAC, authentication sessions, authorization policies, certificates, clients/endpoints, or license usage.

### As a CLI

1. **Set up credentials**:

```bash
cp .env.example .env
# Edit .env with your API key and org ID
```

2. **Run commands**:

```bash
# Make script executable (one time)
chmod +x ~/AI/skills/campanion/scripts/campanion.py

# List NAC sessions (direct execution)
~/AI/skills/campanion/scripts/campanion.py sessions

# List sessions from last 24 hours
~/AI/skills/campanion/scripts/campanion.py sessions --timespan 86400

# Get client counts
~/AI/skills/campanion/scripts/campanion.py clients-overview

# Search for clients
~/AI/skills/campanion/scripts/campanion.py clients --search "laptop" --sort-key lastLogin

# Generic API — query any Meraki endpoint
~/AI/skills/campanion/scripts/campanion.py api GET /organizations/{organizationId}/networks
```

Alternatively, use `uv run` if you prefer not to make the script executable:

```bash
uv run --directory ~/AI/skills/campanion/scripts campanion.py sessions --timespan 86400
```

## Available Commands

All GET commands support REST API query parameters. Use `<command> --help` for full options.

### Sessions

- `sessions` — List session history
  - Options: `--t0`, `--timespan`, `--per-page`, `--starting-after`, `--ending-before`
- `session-details <id>` — Get session details
- `count-sessions` — Count sessions by status
  - Options: `--t0`, `--timespan`
- `failed-sessions` — List failed sessions with reasons
  - Options: `--t0`, `--timespan`

### Authorization

- `policies` — List authorization policies
  - Options: `--policy-ids`
- `rules <policy-id>` — List rules for a policy
- `create-rule <policy-id> --body <json>` — Create rule
- `update-rule <policy-id> <rule-id> --body <json>` — Update rule
- `delete-rule <policy-id> <rule-id>` — Delete rule

### Certificates

- `certificates` — List certificates
  - Options: `--status`, `--expiry`, `--last-used`
- `certificates-overview` — Certificate counts
- `import-certificate --body <json>` — Import certificate
- `update-certificate <id> --body <json>` — Update certificate config
- `crls` — List CRLs
  - Options: `--per-page`, `--sort-by`, `--sort-order`, `--crl-ids`, `--ca-ids`
- `crl-descriptors` — CRL metadata
  - Options: `--per-page`, `--sort-by`, `--sort-order`, `--ca-ids`
- `create-crl --body <json>` — Create CRL
- `delete-crl <id>` — Delete CRL

### Clients

- `clients` — List NAC clients
  - Options: `--search`, `--sort-order`, `--sort-key`, `--per-page`, `--client-ids`, `--group-ids`, `--ssid`, `--classification`
- `clients-overview` — Client counts
- `create-client --body <json>` — Create client
- `update-client <id> --body <json>` — Update client
- `bulk-delete-clients --body <json>` — Bulk delete
- `bulk-edit-clients --body <json>` — Bulk edit
- `bulk-upload-clients --body <json>` — Bulk upload

### Client Groups

- `client-groups` — List groups
  - Options: `--search`, `--sort-order`, `--sort-key`, `--per-page`, `--group-ids`
- `create-client-group --body <json>` — Create group
- `update-client-group <id> --body <json>` — Update group
- `delete-client-group <id>` — Delete group

### Dictionaries

- `dictionaries` — List dictionaries
- `dictionary-attributes <id>` — List attributes
  - Options: `--network-ids`
- `attribute-values <dict-id> <attr-name>` — Search attribute values
  - Options: `--search`, `--network-ids`

### License

- `license-usage` — License usage stats
  - Options: `--start-date`, `--end-date`, `--network-ids`

### Generic API

- `api <method> <path> [--params <json>] [--body <json>]` — Call any Meraki Dashboard endpoint

## Global Options

Common options available across GET commands:

- `--refresh` — Bypass cache on GET requests
- `--raw` — Compact JSON output (no indentation)
- `--per-page <n>` — Results per page (range varies by endpoint)
- `--starting-after <token>` — Pagination token for next page
- `--ending-before <token>` — Pagination token for previous page
- `--sort-order <asc|desc>` — Sort direction
- `--sort-key <field>` — Field to sort by (endpoint-specific)
- `--search <query>` — Fuzzy search (clients, groups, attributes)

Time range options (sessions commands):

- `--t0 <timestamp>` — Start time (ISO8601 or Unix timestamp)
- `--timespan <seconds>` — Duration in seconds (max 2678400 = 31 days)

Use `<command> --help` to see all available options for a specific command.

## Testing

```bash
uv run --directory ~/AI/skills/campanion/scripts --with pytest --with respx --with click --with click-default-group --with python-dotenv pytest ~/AI/skills/campanion/tests/ -v
```

## Architecture

- **Single-file CLI** with `#!/usr/bin/env -S uv run` shebang and inline PEP 723 metadata (no `pyproject.toml`)
- **Direct execution** — runs as a standalone script without `uv run` prefix
- **Smart caching** in `.cache/` with SHA-256 keys and configurable TTL
- **Auto path substitution** — `{organizationId}` replaced automatically
- **Full REST API support** — all GET commands expose their query parameters
- **Test-driven** — comprehensive test suite with `respx` mocking (no live API calls)

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
