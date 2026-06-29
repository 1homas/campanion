#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "python-dotenv",
#   "click",
#   "click-default-group",
# ]
# ///

"""
Cisco Access Manager (CAM) CLI for Meraki Dashboard REST APIs.
Provides operational management of NAC endpoints and generic API access.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import click
import httpx
from click_default_group import DefaultGroup
from dotenv import load_dotenv

# Load .env from project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Environment variables
API_KEY = os.getenv("MERAKI_DASHBOARD_API_KEY")
ORG_ID = os.getenv("MERAKI_ORG_ID")
BASE_URL = os.getenv("MERAKI_BASE_URL", "https://api.meraki.com/api/v1")
CACHE_TTL = int(os.getenv("MERAKI_CACHE_TTL", "604800"))  # 7 days
TIMEOUT = int(os.getenv("MERAKI_TIMEOUT", "30"))

# Cache directory
CACHE_DIR = PROJECT_ROOT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


class APIClient:
    """Meraki Dashboard API client with caching."""

    def __init__(self, api_key: str, org_id: str, base_url: str):
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=TIMEOUT)

    def _get_cache_key(self, method: str, path: str, params: Optional[dict]) -> str:
        """Generate cache key from request parameters."""
        key_data = f"{method}:{path}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[dict]:
        """Retrieve cached response if valid."""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        import time

        if time.time() - cache_file.stat().st_mtime > CACHE_TTL:
            cache_file.unlink()
            return None

        return json.loads(cache_file.read_text())

    def _cache_response(self, cache_key: str, data: dict) -> None:
        """Cache response data."""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        cache_file.write_text(json.dumps(data))

    def _invalidate_cache(self, path_prefix: str) -> None:
        """Invalidate cache entries matching path prefix."""
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        refresh: bool = False,
    ) -> dict:
        """Make API request with caching for GET requests."""
        # Substitute {organizationId} in path
        path = path.replace("{organizationId}", self.org_id)

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self.base_url}{path}"
        headers = {"X-Cisco-Meraki-API-Key": self.api_key}

        # Check cache for GET requests
        if method.upper() == "GET" and not refresh:
            cache_key = self._get_cache_key(method, path, params)
            cached = self._get_cached_response(cache_key)
            if cached is not None:
                return cached

        # Make request
        try:
            response = self.client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            click.echo(f"HTTP {e.response.status_code}: {e.response.text}", err=True)
            sys.exit(1)
        except httpx.RequestError as e:
            click.echo(f"Request error: {e}", err=True)
            sys.exit(1)

        data = response.json() if response.text else {}

        # Cache GET responses
        if method.upper() == "GET":
            cache_key = self._get_cache_key(method, path, params)
            self._cache_response(cache_key, data)

        # Invalidate cache for write operations
        if method.upper() in ("POST", "PUT", "DELETE"):
            self._invalidate_cache(path)

        return data


def get_client() -> APIClient:
    """Create API client with environment validation."""
    if not API_KEY:
        click.echo("Error: MERAKI_DASHBOARD_API_KEY not set", err=True)
        sys.exit(1)
    if not ORG_ID:
        click.echo("Error: MERAKI_ORG_ID not set", err=True)
        sys.exit(1)

    return APIClient(API_KEY, ORG_ID, BASE_URL)


def output_json(data: Any, raw: bool = False) -> None:
    """Output JSON data with optional formatting."""
    if raw:
        click.echo(json.dumps(data, separators=(",", ":")))
    else:
        click.echo(json.dumps(data, indent=2))


@click.group(cls=DefaultGroup, default="api", default_if_no_args=False)
@click.pass_context
def cli(ctx):
    """Cisco Access Manager (CAM) CLI for Meraki Dashboard APIs."""
    ctx.ensure_object(dict)


# ============================================================================
# Generic API Command
# ============================================================================


@cli.command()
@click.argument("method", type=click.Choice(["GET", "POST", "PUT", "DELETE"], case_sensitive=False))
@click.argument("path")
@click.option("--params", help="Query parameters as JSON")
@click.option("--body", help="Request body as JSON")
@click.option("--refresh", is_flag=True, help="Bypass cache for GET requests")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def api(method: str, path: str, params: Optional[str], body: Optional[str], refresh: bool, raw: bool):
    """Make a generic API call to any Meraki Dashboard endpoint."""
    client = get_client()

    params_dict = json.loads(params) if params else None
    body_dict = json.loads(body) if body else None

    result = client.request(method, path, params=params_dict, body=body_dict, refresh=refresh)
    output_json(result, raw)


# ============================================================================
# Sessions
# ============================================================================


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", help="Pagination token for next page")
@click.option("--ending-before", help="Pagination token for previous page")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def sessions(t0: Optional[str], timespan: Optional[int], per_page: Optional[int],
             starting_after: Optional[str], ending_before: Optional[str],
             refresh: bool, raw: bool):
    """List NAC session history."""
    client = get_client()

    params = {}
    if t0:
        params["t0"] = t0
    if timespan:
        params["timespan"] = timespan
    if per_page:
        params["perPage"] = per_page
    if starting_after:
        params["startingAfter"] = starting_after
    if ending_before:
        params["endingBefore"] = ending_before

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/history",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.argument("session_id")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def session_details(session_id: str, refresh: bool, raw: bool):
    """Get NAC session details."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/{session_id}/details", refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def count_sessions(t0: Optional[str], timespan: Optional[int], refresh: bool, raw: bool):
    """Count sessions by status."""
    client = get_client()

    params = {}
    if t0:
        params["t0"] = t0
    if timespan:
        params["timespan"] = timespan

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/history",
                           params=params if params else None, refresh=refresh)

    # Aggregate by status
    counts = {}
    for session in result.get("items", []):
        status = session.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    output_json(counts, raw)


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def failed_sessions(t0: Optional[str], timespan: Optional[int], refresh: bool, raw: bool):
    """List failed sessions with reasons."""
    client = get_client()

    params = {}
    if t0:
        params["t0"] = t0
    if timespan:
        params["timespan"] = timespan

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/history",
                           params=params if params else None, refresh=refresh)

    # Filter failed sessions
    failed = [s for s in result.get("items", []) if s.get("status") == "failed"]

    output_json({"total": len(failed), "sessions": failed}, raw)


# ============================================================================
# Authorization Policies
# ============================================================================


@cli.command()
@click.option("--policy-ids", help="Comma-separated list of policy IDs to retrieve")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def policies(policy_ids: Optional[str], refresh: bool, raw: bool):
    """List authorization policies."""
    client = get_client()

    params = {}
    if policy_ids:
        params["policyIds"] = policy_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/authorization/policies",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.argument("policy_id")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def rules(policy_id: str, refresh: bool, raw: bool):
    """List rules for an authorization policy."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/authorization/policies", refresh=refresh)

    # Filter to specific policy
    for policy in result.get("items", []):
        if policy.get("id") == policy_id:
            output_json(policy.get("rules", []), raw)
            return

    click.echo(f"Policy {policy_id} not found", err=True)
    sys.exit(1)


@cli.command()
@click.argument("policy_id")
@click.option("--body", required=True, help="Rule body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def create_rule(policy_id: str, body: str, raw: bool):
    """Create authorization rule."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("policy_id")
@click.argument("rule_id")
@click.option("--body", required=True, help="Rule body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def update_rule(policy_id: str, rule_id: str, body: str, raw: bool):
    """Update authorization rule."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules/{rule_id}", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("policy_id")
@click.argument("rule_id")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def delete_rule(policy_id: str, rule_id: str, raw: bool):
    """Delete authorization rule."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules/{rule_id}")
    output_json(result, raw)


# ============================================================================
# Certificates
# ============================================================================


@cli.command()
@click.option("--status", type=click.Choice(["valid", "expiring", "expired"]), help="Filter by certificate status")
@click.option("--expiry", is_flag=True, help="Filter certificates expiring within one month")
@click.option("--last-used", is_flag=True, help="Filter certificates not used in over one month")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def certificates(status: Optional[str], expiry: bool, last_used: bool, refresh: bool, raw: bool):
    """List certificates."""
    client = get_client()

    params = {}
    if status:
        params["status"] = status
    if expiry:
        params["expiry"] = True
    if last_used:
        params["lastUsed"] = True

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/certificates",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def certificates_overview(refresh: bool, raw: bool):
    """Get certificate counts."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/certificates/overview", refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Certificate body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def import_certificate(body: str, raw: bool):
    """Import certificate."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/certificates/import", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("certificate_id")
@click.option("--body", required=True, help="Certificate config as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def update_certificate(certificate_id: str, body: str, raw: bool):
    """Update certificate configuration."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/certificates/{certificate_id}", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.option("--per-page", type=int, help="Entries per page (3-20). Default: 20")
@click.option("--starting-after", help="Pagination token for next page")
@click.option("--ending-before", help="Pagination token for previous page")
@click.option("--sort-by", type=click.Choice(["caId"]), help="Field to sort by. Default: caId")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort order. Default: asc")
@click.option("--crl-ids", help="Comma-separated list of CRL IDs to filter")
@click.option("--ca-ids", help="Comma-separated list of CA IDs to filter")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def crls(per_page: Optional[int], starting_after: Optional[str], ending_before: Optional[str],
         sort_by: Optional[str], sort_order: Optional[str], crl_ids: Optional[str], ca_ids: Optional[str],
         refresh: bool, raw: bool):
    """List CRLs."""
    client = get_client()

    params = {}
    if per_page:
        params["perPage"] = per_page
    if starting_after:
        params["startingAfter"] = starting_after
    if ending_before:
        params["endingBefore"] = ending_before
    if sort_by:
        params["sortBy"] = sort_by
    if sort_order:
        params["sortOrder"] = sort_order
    if crl_ids:
        params["crlIds"] = crl_ids.split(",")
    if ca_ids:
        params["caIds"] = ca_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--per-page", type=int, help="Entries per page (3-100). Default: 100")
@click.option("--starting-after", help="Pagination token for next page")
@click.option("--ending-before", help="Pagination token for previous page")
@click.option("--sort-by", type=click.Choice(["caId"]), help="Field to sort by. Default: caId")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort order. Default: asc")
@click.option("--ca-ids", help="Comma-separated list of CA IDs to filter")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def crl_descriptors(per_page: Optional[int], starting_after: Optional[str], ending_before: Optional[str],
                    sort_by: Optional[str], sort_order: Optional[str], ca_ids: Optional[str],
                    refresh: bool, raw: bool):
    """Get CRL metadata."""
    client = get_client()

    params = {}
    if per_page:
        params["perPage"] = per_page
    if starting_after:
        params["startingAfter"] = starting_after
    if ending_before:
        params["endingBefore"] = ending_before
    if sort_by:
        params["sortBy"] = sort_by
    if sort_order:
        params["sortOrder"] = sort_order
    if ca_ids:
        params["caIds"] = ca_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls/descriptors",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="CRL body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def create_crl(body: str, raw: bool):
    """Create CRL."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("crl_id")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def delete_crl(crl_id: str, raw: bool):
    """Delete CRL."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls/{crl_id}")
    output_json(result, raw)


# ============================================================================
# Clients
# ============================================================================


@cli.command()
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort direction")
@click.option("--sort-key", help="Field to sort by (e.g., mac, description, lastLogin)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", help="Pagination token for next page")
@click.option("--ending-before", help="Pagination token for previous page")
@click.option("--search", help="Fuzzy search on clients")
@click.option("--client-ids", help="Comma-separated list of client IDs")
@click.option("--group-ids", help="Comma-separated list of group IDs")
@click.option("--last-network-name", help="Comma-separated list of network names")
@click.option("--ssid", help="Comma-separated list of SSIDs")
@click.option("--classification", help="Classification filters as JSON")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def clients(sort_order: Optional[str], sort_key: Optional[str], per_page: Optional[int],
            starting_after: Optional[str], ending_before: Optional[str], search: Optional[str],
            client_ids: Optional[str], group_ids: Optional[str], last_network_name: Optional[str],
            ssid: Optional[str], classification: Optional[str], refresh: bool, raw: bool):
    """List NAC clients."""
    client = get_client()

    params = {}
    if sort_order:
        params["sortOrder"] = sort_order
    if sort_key:
        params["sortKey"] = sort_key
    if per_page:
        params["perPage"] = per_page
    if starting_after:
        params["startingAfter"] = starting_after
    if ending_before:
        params["endingBefore"] = ending_before
    if search:
        params["search"] = search
    if client_ids:
        params["clientIds"] = client_ids.split(",")
    if group_ids:
        params["groupIds"] = group_ids.split(",")
    if last_network_name:
        params["lastNetworkName"] = last_network_name.split(",")
    if ssid:
        params["ssid"] = ssid.split(",")
    if classification:
        params["classification"] = json.loads(classification)

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/clients",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def clients_overview(refresh: bool, raw: bool):
    """Get client counts."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/clients/overview", refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Client body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def create_client(body: str, raw: bool):
    """Create NAC client."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("client_id")
@click.option("--body", required=True, help="Client config as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def update_client(client_id: str, body: str, raw: bool):
    """Update NAC client."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/clients/{client_id}", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Client IDs as JSON array")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def bulk_delete_clients(body: str, raw: bool):
    """Bulk delete NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkDelete", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Bulk edit body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def bulk_edit_clients(body: str, raw: bool):
    """Bulk edit NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkEdit", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Bulk upload body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def bulk_upload_clients(body: str, raw: bool):
    """Bulk upload NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkUpload", body=body_dict)
    output_json(result, raw)


# ============================================================================
# Client Groups
# ============================================================================


@cli.command()
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort direction")
@click.option("--sort-key", help="Field to sort by (e.g., name, description)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", help="Pagination token for next page")
@click.option("--ending-before", help="Pagination token for previous page")
@click.option("--search", help="Fuzzy search on client groups")
@click.option("--group-ids", help="Comma-separated list of group IDs")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def client_groups(sort_order: Optional[str], sort_key: Optional[str], per_page: Optional[int],
                  starting_after: Optional[str], ending_before: Optional[str], search: Optional[str],
                  group_ids: Optional[str], refresh: bool, raw: bool):
    """List client groups."""
    client = get_client()

    params = {}
    if sort_order:
        params["sortOrder"] = sort_order
    if sort_key:
        params["sortKey"] = sort_key
    if per_page:
        params["perPage"] = per_page
    if starting_after:
        params["startingAfter"] = starting_after
    if ending_before:
        params["endingBefore"] = ending_before
    if search:
        params["search"] = search
    if group_ids:
        params["groupIds"] = group_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/clients/groups",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.option("--body", required=True, help="Group body as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def create_client_group(body: str, raw: bool):
    """Create client group."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/groups", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("group_id")
@click.option("--body", required=True, help="Group config as JSON")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def update_client_group(group_id: str, body: str, raw: bool):
    """Update client group."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/clients/groups/{group_id}", body=body_dict)
    output_json(result, raw)


@cli.command()
@click.argument("group_id")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def delete_client_group(group_id: str, raw: bool):
    """Delete client group."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/clients/groups/{group_id}")
    output_json(result, raw)


# ============================================================================
# Dictionaries
# ============================================================================


@cli.command()
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def dictionaries(refresh: bool, raw: bool):
    """List dictionaries."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries", refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.argument("dictionary_id")
@click.option("--network-ids", help="Comma-separated list of network IDs to filter enum values")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def dictionary_attributes(dictionary_id: str, network_ids: Optional[str], refresh: bool, raw: bool):
    """List dictionary attributes."""
    client = get_client()

    params = {}
    if network_ids:
        params["networkIds"] = network_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries/{dictionary_id}/attributes",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


@cli.command()
@click.argument("dictionary_id")
@click.argument("attribute_name")
@click.option("--search", help="Search string for contains-match filtering")
@click.option("--network-ids", help="Comma-separated list of network IDs to filter values")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def attribute_values(dictionary_id: str, attribute_name: str, search: Optional[str],
                    network_ids: Optional[str], refresh: bool, raw: bool):
    """Search attribute values."""
    client = get_client()

    params = {}
    if search:
        params["search"] = search
    if network_ids:
        params["networkIds"] = network_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries/{dictionary_id}/attributes/{attribute_name}/values",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


# ============================================================================
# License
# ============================================================================


@cli.command()
@click.option("--start-date", help="Start date for usage data (UTC, YYYY-MM-DD format)")
@click.option("--end-date", help="End date for usage data (UTC, YYYY-MM-DD format)")
@click.option("--network-ids", help="Comma-separated list of network IDs")
@click.option("--refresh", is_flag=True, help="Bypass cache")
@click.option("--raw", is_flag=True, help="Compact JSON output")
def license_usage(start_date: Optional[str], end_date: Optional[str], network_ids: Optional[str],
                  refresh: bool, raw: bool):
    """Get license usage stats."""
    client = get_client()

    params = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    if network_ids:
        params["networkIds"] = network_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/license/usage",
                           params=params if params else None, refresh=refresh)
    output_json(result, raw)


if __name__ == "__main__":
    cli()
