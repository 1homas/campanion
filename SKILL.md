---
name: campanion
description: Use the Cisco Access Manager (CAM) documentation and Meraki Dashboard APIs and the `/nac/` APIs specifically to analyze, correlate, configure, and troubleshoot users, devices, clients/endpoints, authentications/sessions or answer general feature availability, capability, configuration, and integration questions
argument-hint: "<QUERY> [--source <dir>] [--verbose] [--output <file>]"
version: 0.1.0
license: "[MIT](https://mit-license.org)"
---

# campanion

Cisco Access Manager (CAM) companion uses the Meraki Dashboard APIs for configuration, operations, analytics, and troubleshooting.

Use Cases:

- **Troubleshooting**: Query session history and details to diagnose authentication failures
- **Configuration**: Manage authorization policies, rules, certificates, and CRLs
- **Analytics**: Pull license usage, session data, and certificate overview
- **Compliance**: Review certificate authorities and CRL status
- **Correlation**: Use `api` command to query networks, devices, clients, and other Meraki Dashboard resources for context alongside NAC data

```bash
uv run --directory ~/AI/skills/campanion/scripts campanion.py <command> [options]
```

## Environment Variables

The script auto-loads `.env` from its own directory. No shell preamble needed.

Required in `~/AI/skills/campanion/.env`:

```bash
MERAKI_DASHBOARD_API_KEY=<api-key>
MERAKI_ORG_ID=<org-id>
MERAKI_BASE_URL=https://api.meraki.com/api/v1  # optional
MERAKI_CACHE_TTL=604800                         # optional, seconds
MERAKI_TIMEOUT=30                               # optional, HTTP timeout in seconds
```

## REST APIs

- Download the latest Meraki Dashboard OpenAPI specification from https://api.meraki.com/api/v1/organizations/$MERAKI_ORG_ID/openapiSpec?version=3
- The `/nac/` API endpoints are the most relevant
- Additional APIs may be used to correlate configs and events with other objects: networks, devices, clients, ssids, switch ports, users, etc.

## CLI Commands

### Sessions

```bash
# List session history (default 24h)
scripts/campanion.py sessions
scripts/campanion.py sessions --timespan 604800        # 7 days
scripts/campanion.py sessions --timespan 86400 --refresh  # bypass cache

# Count sessions by status
scripts/campanion.py count-sessions
scripts/campanion.py count-sessions --timespan 604800

# List failed sessions with failure details
scripts/campanion.py failed-sessions

# Get details for a specific session
scripts/campanion.py session-details <session-uuid>
```

### Authorization Policies & Rules

```bash
# List all policies
scripts/campanion.py policies

# List rules for a specific policy
scripts/campanion.py rules <policy-id>

# Create a rule
scripts/campanion.py create-rule <policy-id> --body '{"name":"...", "rank":1, "enabled":true, "authorizationProfile":{...}, "condition":{...}}'

# Update a rule
scripts/campanion.py update-rule <policy-id> <rule-id> --body '{"name":"...", "rank":2, ...}'

# Delete a rule
scripts/campanion.py delete-rule <policy-id> <rule-id>
```

### Certificates

```bash
# List certificates
scripts/campanion.py certificates
scripts/campanion.py certificates --status Enabled
scripts/campanion.py certificates --expiry --last-used

# Certificate overview (counts)
scripts/campanion.py certificates-overview

# Import a certificate
scripts/campanion.py import-certificate --contents "-----BEGIN CERTIFICATE-----..." --dry-run
scripts/campanion.py import-certificate --contents "..." --profile '{"enabled":true}'

# Update certificate config
scripts/campanion.py update-certificate <cert-id> --body '{"profile":{"enabled":true}}'
```

### CRLs

```bash
# List CRLs
scripts/campanion.py crls
scripts/campanion.py crls --sort-by createdAt --sort-order desc

# List CRL descriptors (metadata only)
scripts/campanion.py crl-descriptors

# Create CRL
scripts/campanion.py create-crl --ca-id <ca-id> --content "-----BEGIN X509 CRL-----..."
scripts/campanion.py create-crl --ca-id <ca-id> --content "..." --is-delta

# Delete CRL
scripts/campanion.py delete-crl <crl-id>
```

### Clients

```bash
# List all clients
scripts/campanion.py clients
scripts/campanion.py clients --refresh

# Get clients overview (counts)
scripts/campanion.py clients-overview

# Create a client
scripts/campanion.py create-client --body '{"name":"...", "mac":"AA:BB:CC:DD:EE:FF", ...}'

# Update a client
scripts/campanion.py update-client <client-id> --body '{"name":"...", ...}'

# Bulk delete clients
scripts/campanion.py bulk-delete-clients --body '{"clientIds":["id1","id2"]}'

# Bulk edit clients
scripts/campanion.py bulk-edit-clients --body '{"items":[{"clientId":"...", "name":"..."}]}'

# Bulk upload clients (with groups and associations)
scripts/campanion.py bulk-upload-clients --body '{"items":[...]}'
```

### Client Groups

```bash
# List all client groups
scripts/campanion.py client-groups

# Create a client group
scripts/campanion.py create-client-group --body '{"name":"...", ...}'

# Update a client group (with bulk member operations)
scripts/campanion.py update-client-group <group-id> --body '{"name":"...", "members":{...}}'

# Delete a client group
scripts/campanion.py delete-client-group <group-id>
```

### Dictionaries

```bash
# List dictionaries
scripts/campanion.py dictionaries

# List attributes for a dictionary
scripts/campanion.py dictionary-attributes <dictionary-id>

# Search attribute values
scripts/campanion.py attribute-values <dictionary-id> <attribute-name> --search "query"
```

### License

```bash
# License usage (default: last 7 days)
scripts/campanion.py license-usage
scripts/campanion.py license-usage --days 30
scripts/campanion.py license-usage --start-date 2026-01-01 --end-date 2026-03-31
```

### Generic API (any Meraki Dashboard endpoint)

```bash
# List networks
scripts/campanion.py api GET /organizations/{organizationId}/networks

# List devices with pagination
scripts/campanion.py api GET /organizations/{organizationId}/devices --params '{"perPage":100}'

# Get a specific network
scripts/campanion.py api GET /networks/{networkId}

# List switches in the org
scripts/campanion.py api GET /organizations/{organizationId}/devices --params '{"productTypes[]":"switch"}'

# Get all ports on a switch
scripts/campanion.py api GET /devices/Q5VA-W6VM-BXLX/switch/ports

# Shut a switch port (disable)
scripts/campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled": false}'

# No-shut a switch port (enable)
scripts/campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled": true}'

# Any POST/PUT/DELETE
scripts/campanion.py api POST /organizations/{organizationId}/nac/clients --body '{"name":"test"}'
```

The `api` command auto-substitutes `{organizationId}` with `MERAKI_ORG_ID`. All other path parameters (e.g., `{networkId}`) must be supplied as literal values. GET responses are cached; write operations are not.

All scripts are run with `uv run --directory ~/AI/skills/campanion/scripts`.

### Global Options

```bash
# Compact JSON (no indent) — pipe-friendly
scripts/campanion.py --raw sessions
scripts/campanion.py --raw count-sessions | jq .total

# Bypass cache on any GET command
scripts/campanion.py sessions --refresh
scripts/campanion.py policies --refresh
```

## Caching

API responses are cached in `.cache/` for 7 days (configurable via `MERAKI_CACHE_TTL` env var, in seconds). Write operations (create/update/delete) automatically invalidate related cache entries.

## API Lessons Learned

### Response Structure

Session history returns nested structure, not flat array:

```json
{
  "items": [...],
  "meta": {
    "counts": {...},
    "failureReasons": [...],
    "authorization": { "ruleNames": [...] }
  }
}
```

### Session Object Fields

| Field                     | Description                          |
| ------------------------- | ------------------------------------ |
| `sessionId`               | UUID for session details lookup      |
| `ts`                      | ISO 8601 timestamp                   |
| `status`                  | "Success" or "Failed"                |
| `user.id`                 | Username or MAC (for MAB)            |
| `client.id`               | Client MAC address                   |
| `authentication.protocol` | MAB, EAP-TTLS, EAP-TLS, etc.         |
| `ssid.name`               | Wireless SSID                        |
| `details.ruleDetails`     | Matched authorization rule (success) |
| `details.failureInfo[]`   | Failure reason (failed)              |
| `details.failureAction[]` | Recommended remediation              |

### Auth Header

Use `X-Cisco-Meraki-API-Key`, not `Authorization: Bearer`.

### Common Failure Patterns

| Client Behavior                 | Likely Cause                           |
| ------------------------------- | -------------------------------------- |
| Repeated EAP failures, same MAC | Supplicant misconfiguration            |
| "Supplicant stopped responding" | Client rejected server cert or timeout |
| "Session timeout"               | Network connectivity or slow client    |

The script uses `load_dotenv(Path(__file__).parent.parent / ".env")` — it looks one level up from `scripts/` to find credentials regardless of working directory.
