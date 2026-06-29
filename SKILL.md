---
name: campanion
description: Use the Cisco Access Manager (CAM) Meraki Dashboard APIs and the `/nac/` APIs specifically via CLI commands to analyze, correlate, configure, and troubleshoot users, devices, clients/endpoints, authentications/sessions or answer general feature availability, capability, configuration, and integration questions
argument-hint: "<QUERY> [--source <dir>] [--verbose] [--output <file>]"
version: 0.2.0
license: "[MIT](https://mit-license.org)"
---

# campanion

A Claude Code skill for Cisco Access Manager (CAM) operational management using the Meraki Dashboard APIs for configuration, operations, analytics, and troubleshooting.

## Skill Interface

Invoke via `/campanion` or let Claude Code automatically trigger when detecting CAM-related questions.

The skill automatically activates for questions about:

- Cisco Access Manager (CAM) features, configuration, troubleshooting
- Meraki NAC operations
- Authentication sessions or session history
- Authorization policies or rules
- Certificates, CRLs, or certificate authorities
- NAC clients, endpoints, or client groups
- NAC license usage

## Use Cases

- **Troubleshooting**: Query session history and details to diagnose authentication failures
- **Configuration**: Manage authorization policies, rules, certificates, and CRLs
- **Analytics**: Pull license usage, session data, and certificate overview
- **Compliance**: Review certificate authorities and CRL status
- **Correlation**: Use `api` command to query networks, devices, clients, and other Meraki Dashboard resources for context alongside NAC data

## CLI Interface

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
MERAKI_TIMEOUT=30                               # optional, HTTP timeout in seconds
```

## REST APIs

- Download the latest Meraki Dashboard OpenAPI specification from https://api.meraki.com/api/v1/organizations/$MERAKI_ORG_ID/openapiSpec?version=3
- The `/nac/` API endpoints are the most relevant
- Additional APIs may be used to correlate configs and events with other objects: networks, devices, clients, ssids, switch ports, users, etc.

## CLI Commands

### Sessions

```bash
# List session history (default 1 hour)
scripts/campanion.py sessions
scripts/campanion.py sessions --timespan 604800        # 7 days
scripts/campanion.py sessions --timespan 86400 --pretty  # formatted output
scripts/campanion.py sessions --limit 100              # limit to 100 results

# Count sessions by status
scripts/campanion.py count-sessions
scripts/campanion.py count-sessions --timespan 604800

# List failed sessions with failure details
scripts/campanion.py failed-sessions
scripts/campanion.py failed-sessions --timespan 86400 --pretty

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
scripts/campanion.py certificates --status valid
scripts/campanion.py certificates --expiry --last-used --pretty

# Certificate overview (counts)
scripts/campanion.py certificates-overview

# Import a certificate
scripts/campanion.py import-certificate --body '{"certificate":"-----BEGIN CERTIFICATE-----..."}'

# Update certificate config
scripts/campanion.py update-certificate <cert-id> --body '{"enabled":true}'
```

### CRLs

```bash
# List CRLs
scripts/campanion.py crls
scripts/campanion.py crls --sort-by caId --sort-order desc
scripts/campanion.py crls --ca-ids "ca1,ca2" --pretty

# List CRL descriptors (metadata only)
scripts/campanion.py crl-descriptors
scripts/campanion.py crl-descriptors --ca-ids "ca1,ca2"

# Create CRL
scripts/campanion.py create-crl --body '{"caId":"<ca-id>","crl":"-----BEGIN X509 CRL-----..."}'

# Delete CRL
scripts/campanion.py delete-crl <crl-id>
```

### Clients

```bash
# List all clients
scripts/campanion.py clients
scripts/campanion.py clients --search "laptop" --sort-key lastLogin
scripts/campanion.py clients --group-ids "g1,g2" --limit 50
scripts/campanion.py clients --ssid "Corporate" --pretty

# Get clients overview (counts)
scripts/campanion.py clients-overview

# Create a client
scripts/campanion.py create-client --body '{"mac":"AA:BB:CC:DD:EE:FF","description":"Printer"}'

# Update a client
scripts/campanion.py update-client <client-id> --body '{"description":"Updated name"}'

# Bulk delete clients
scripts/campanion.py bulk-delete-clients --body '{"clientIds":["id1","id2"]}'

# Bulk edit clients
scripts/campanion.py bulk-edit-clients --body '{"items":[{"clientId":"...","description":"..."}]}'

# Bulk upload clients
scripts/campanion.py bulk-upload-clients --body '{"items":[{"mac":"...","description":"..."}]}'
```

### Client Groups

```bash
# List all client groups
scripts/campanion.py client-groups
scripts/campanion.py client-groups --search "printer" --sort-key name
scripts/campanion.py client-groups --group-ids "g1,g2" --pretty

# Create a client group
scripts/campanion.py create-client-group --body '{"name":"Printers","description":"All printers"}'

# Update a client group
scripts/campanion.py update-client-group <group-id> --body '{"description":"Updated description"}'

# Delete a client group
scripts/campanion.py delete-client-group <group-id>
```

### Dictionaries

```bash
# List dictionaries
scripts/campanion.py dictionaries
scripts/campanion.py dictionaries --pretty

# List attributes for a dictionary
scripts/campanion.py dictionary-attributes <dictionary-id>
scripts/campanion.py dictionary-attributes <dictionary-id> --network-ids "net1,net2"

# Search attribute values
scripts/campanion.py attribute-values <dictionary-id> <attribute-name> --search "query"
scripts/campanion.py attribute-values <dictionary-id> <attribute-name> --network-ids "net1,net2" --pretty
```

### License

```bash
# License usage
scripts/campanion.py license-usage
scripts/campanion.py license-usage --start-date 2026-01-01 --end-date 2026-03-31
scripts/campanion.py license-usage --network-ids "net1,net2" --pretty
```

### Generic API (any Meraki Dashboard endpoint)

```bash
# List networks
scripts/campanion.py api GET /organizations/{organizationId}/networks
scripts/campanion.py api GET /organizations/{organizationId}/networks --pretty

# List devices with parameters
scripts/campanion.py api GET /organizations/{organizationId}/devices --params '{"perPage":100}'
scripts/campanion.py api GET /organizations/{organizationId}/devices --params '{"productTypes":["switch"]}' --limit 50

# Get a specific network
scripts/campanion.py api GET /networks/{networkId}

# Get all ports on a switch
scripts/campanion.py api GET /devices/Q5VA-W6VM-BXLX/switch/ports --pretty

# Shut a switch port (disable)
scripts/campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled":false}'

# No-shut a switch port (enable)
scripts/campanion.py api PUT /devices/Q5VA-W6VM-BXLX/switch/ports/5 --body '{"enabled":true}'

# Any POST/PUT/DELETE
scripts/campanion.py api POST /organizations/{organizationId}/nac/clients --body '{"mac":"AA:BB:CC:DD:EE:FF"}'
```

The `api` command auto-substitutes `{organizationId}` with `MERAKI_ORG_ID`. All other path parameters (e.g., `{networkId}`) must be supplied as literal values.

All scripts are run with `uv run --directory ~/AI/skills/campanion/scripts`.

### Global Options

All GET commands support these options:

- `--pretty` — Pretty-print JSON with 2-space indents (default is compact JSON for piping)
- `--limit <n>` — Maximum number of items to return (caps pagination)
- `--per-page <n>` — Results per page (varies by endpoint, default typically 1000)
- `--starting-after <index>` — Pagination start index (integer, 0-based)
- `--ending-before <index>` — Pagination end index (integer, 0-based)

**Automatic pagination**: All GET requests fetch all pages by default. Use `--limit` to cap results.

```bash
# Compact JSON (default) — pipe-friendly
scripts/campanion.py sessions | jq '.items | length'
scripts/campanion.py count-sessions | jq .

# Pretty-printed JSON for human readability
scripts/campanion.py sessions --pretty
scripts/campanion.py clients --limit 100 --pretty
```

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
