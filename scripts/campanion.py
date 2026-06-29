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
TIMEOUT = int(os.getenv("MERAKI_TIMEOUT", "30"))


class APIClient:
    """Meraki Dashboard API client."""

    def __init__(self, api_key: str, org_id: str, base_url: str):
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=TIMEOUT)


    def _make_single_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> dict:
        """Make a single API request without pagination."""
        url = f"{self.base_url}{path}"
        headers = {"X-Cisco-Meraki-API-Key": self.api_key}

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
        return data

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Make API request."""
        # Substitute {organizationId} in path
        path = path.replace("{organizationId}", self.org_id)

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        # Handle pagination for GET requests (always enabled)
        if method.upper() == "GET":
            return self._paginated_request(path, params, limit)

        # For non-GET requests, make single request
        return self._make_single_request(method, path, params, body)

    def _apply_limit(self, data: dict, limit: int) -> dict:
        """Apply limit to response data."""
        if isinstance(data, list):
            return data[:limit]
        elif isinstance(data, dict) and "items" in data:
            return {"items": data["items"][:limit], "total": len(data["items"][:limit])}
        return data

    def _paginated_request(self, path: str, params: Optional[dict], limit: Optional[int] = None) -> dict:
        """Fetch all pages for a paginated GET request using integer-based startingAfter."""
        all_items = []
        current_params = params.copy() if params else {}

        # Set max page size if not specified
        if "perPage" not in current_params:
            current_params["perPage"] = 1000

        # Remove endingBefore if present (incompatible with pagination)
        if "endingBefore" in current_params:
            del current_params["endingBefore"]

        page_index = 0

        while True:
            # Set startingAfter to current index if not first page
            if page_index > 0:
                current_params["startingAfter"] = str(page_index)

            data = self._make_single_request("GET", path, current_params, None)

            # Handle different response formats
            if isinstance(data, list):
                all_items.extend(data)
                page_index += len(data)

                # Check if limit reached
                if limit is not None and len(all_items) >= limit:
                    all_items = all_items[:limit]
                    break

                # If we got fewer items than perPage, we're done
                if len(data) < current_params.get("perPage", 1000):
                    break
                if not data:
                    break
            elif isinstance(data, dict) and "items" in data:
                items = data.get("items", [])
                all_items.extend(items)
                page_index += len(items)

                # Check if limit reached
                if limit is not None and len(all_items) >= limit:
                    all_items = all_items[:limit]
                    break

                # If we got fewer items than perPage, we're done
                if len(items) < current_params.get("perPage", 1000):
                    break
                if not items:
                    break
            else:
                # Non-paginated response
                return data

        # Return in same format as API
        if isinstance(data, dict) and "items" in data:
            return {"items": all_items, "total": len(all_items)}
        return all_items


def get_client() -> APIClient:
    """Create API client with environment validation."""
    if not API_KEY:
        click.echo("Error: MERAKI_DASHBOARD_API_KEY not set", err=True)
        sys.exit(1)
    if not ORG_ID:
        click.echo("Error: MERAKI_ORG_ID not set", err=True)
        sys.exit(1)

    return APIClient(API_KEY, ORG_ID, BASE_URL)


def output_json(data: Any, pretty: bool = False) -> None:
    """Output JSON data with optional formatting."""
    if pretty:
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(json.dumps(data, separators=(",", ":")))


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
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def api(method: str, path: str, params: Optional[str], body: Optional[str], limit: Optional[int], pretty: bool):
    """Make a generic API call to any Meraki Dashboard endpoint."""
    client = get_client()

    params_dict = json.loads(params) if params else None
    body_dict = json.loads(body) if body else None

    result = client.request(method, path, params=params_dict, body=body_dict, limit=limit)
    output_json(result, pretty)


# ============================================================================
# Sessions
# ============================================================================


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", type=int, help="Start index for pagination (integer, 0-based)")
@click.option("--ending-before", type=int, help="End index for pagination (integer, 0-based)")
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def sessions(t0: Optional[str], timespan: Optional[int], per_page: Optional[int],
             starting_after: Optional[int], ending_before: Optional[int],
             limit: Optional[int], pretty: bool):
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
                           params=params if params else None, limit=limit)
    output_json(result, pretty)


@cli.command()
@click.argument("session_id")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def session_details(session_id: str, pretty: bool):
    """Get NAC session details."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/{session_id}/details")
    output_json(result, pretty)


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def count_sessions(t0: Optional[str], timespan: Optional[int], pretty: bool):
    """Count sessions by status."""
    client = get_client()

    params = {}
    if t0:
        params["t0"] = t0
    if timespan:
        params["timespan"] = timespan

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/history",
                           params=params if params else None)

    # Aggregate by status
    counts = {}
    for session in result.get("items", []):
        status = session.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

    output_json(counts, pretty)


@cli.command()
@click.option("--t0", help="Beginning of timespan (ISO8601 format or Unix timestamp). Max lookback: 31 days")
@click.option("--timespan", type=int, help="Timespan in seconds (max 2678400 = 31 days). Default: 3600 (1 hour)")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def failed_sessions(t0: Optional[str], timespan: Optional[int], pretty: bool):
    """List failed sessions with reasons."""
    client = get_client()

    params = {}
    if t0:
        params["t0"] = t0
    if timespan:
        params["timespan"] = timespan

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/sessions/history",
                           params=params if params else None)

    # Filter failed sessions
    failed = [s for s in result.get("items", []) if s.get("status") == "failed"]

    output_json({"total": len(failed), "sessions": failed}, raw)


# ============================================================================
# Authorization Policies
# ============================================================================


@cli.command()
@click.option("--policy-ids", help="Comma-separated list of policy IDs to retrieve")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def policies(policy_ids: Optional[str], pretty: bool):
    """List authorization policies."""
    client = get_client()

    params = {}
    if policy_ids:
        params["policyIds"] = policy_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/authorization/policies",
                           params=params if params else None)
    output_json(result, pretty)


@cli.command()
@click.argument("policy_id")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def rules(policy_id: str, pretty: bool):
    """List rules for an authorization policy."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/authorization/policies")

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
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def create_rule(policy_id: str, body: str, pretty: bool):
    """Create authorization rule."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("policy_id")
@click.argument("rule_id")
@click.option("--body", required=True, help="Rule body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def update_rule(policy_id: str, rule_id: str, body: str, pretty: bool):
    """Update authorization rule."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules/{rule_id}", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("policy_id")
@click.argument("rule_id")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def delete_rule(policy_id: str, rule_id: str, pretty: bool):
    """Delete authorization rule."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/authorization/policies/{policy_id}/rules/{rule_id}")
    output_json(result, pretty)


# ============================================================================
# Certificates
# ============================================================================


@cli.command()
@click.option("--status", type=click.Choice(["valid", "expiring", "expired"]), help="Filter by certificate status")
@click.option("--expiry", is_flag=True, help="Filter certificates expiring within one month")
@click.option("--last-used", is_flag=True, help="Filter certificates not used in over one month")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def certificates(status: Optional[str], expiry: bool, last_used: bool, pretty: bool):
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
                           params=params if params else None)
    output_json(result, pretty)


@cli.command()
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def certificates_overview(pretty: bool):
    """Get certificate counts."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/certificates/overview")
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Certificate body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def import_certificate(body: str, pretty: bool):
    """Import certificate."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/certificates/import", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("certificate_id")
@click.option("--body", required=True, help="Certificate config as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def update_certificate(certificate_id: str, body: str, pretty: bool):
    """Update certificate configuration."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/certificates/{certificate_id}", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.option("--per-page", type=int, help="Entries per page (3-20). Default: 20")
@click.option("--starting-after", type=int, help="Start index for pagination (integer, 0-based)")
@click.option("--ending-before", type=int, help="End index for pagination (integer, 0-based)")
@click.option("--sort-by", type=click.Choice(["caId"]), help="Field to sort by. Default: caId")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort order. Default: asc")
@click.option("--crl-ids", help="Comma-separated list of CRL IDs to filter")
@click.option("--ca-ids", help="Comma-separated list of CA IDs to filter")
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def crls(per_page: Optional[int], starting_after: Optional[int], ending_before: Optional[int],
         sort_by: Optional[str], sort_order: Optional[str], crl_ids: Optional[str], ca_ids: Optional[str],
         limit: Optional[int], pretty: bool):
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
                           params=params if params else None, limit=limit)
    output_json(result, pretty)


@cli.command()
@click.option("--per-page", type=int, help="Entries per page (3-100). Default: 100")
@click.option("--starting-after", type=int, help="Start index for pagination (integer, 0-based)")
@click.option("--ending-before", type=int, help="End index for pagination (integer, 0-based)")
@click.option("--sort-by", type=click.Choice(["caId"]), help="Field to sort by. Default: caId")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort order. Default: asc")
@click.option("--ca-ids", help="Comma-separated list of CA IDs to filter")
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def crl_descriptors(per_page: Optional[int], starting_after: Optional[int], ending_before: Optional[int],
                    sort_by: Optional[str], sort_order: Optional[str], ca_ids: Optional[str],
                    limit: Optional[int], pretty: bool):
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
                           params=params if params else None, limit=limit)
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="CRL body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def create_crl(body: str, pretty: bool):
    """Create CRL."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("crl_id")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def delete_crl(crl_id: str, pretty: bool):
    """Delete CRL."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/certificates/authorities/crls/{crl_id}")
    output_json(result, pretty)


# ============================================================================
# Clients
# ============================================================================


@cli.command()
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort direction")
@click.option("--sort-key", help="Field to sort by (e.g., mac, description, lastLogin)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", type=int, help="Start index for pagination (integer, 0-based)")
@click.option("--ending-before", type=int, help="End index for pagination (integer, 0-based)")
@click.option("--search", help="Fuzzy search on clients")
@click.option("--client-ids", help="Comma-separated list of client IDs")
@click.option("--group-ids", help="Comma-separated list of group IDs")
@click.option("--last-network-name", help="Comma-separated list of network names")
@click.option("--ssid", help="Comma-separated list of SSIDs")
@click.option("--classification", help="Classification filters as JSON")
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def clients(sort_order: Optional[str], sort_key: Optional[str], per_page: Optional[int],
            starting_after: Optional[int], ending_before: Optional[int], search: Optional[str],
            client_ids: Optional[str], group_ids: Optional[str], last_network_name: Optional[str],
            ssid: Optional[str], classification: Optional[str], limit: Optional[int], pretty: bool):
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
                           params=params if params else None, limit=limit)
    output_json(result, pretty)


@cli.command()
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def clients_overview(pretty: bool):
    """Get client counts."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/clients/overview")
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Client body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def create_client(body: str, pretty: bool):
    """Create NAC client."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("client_id")
@click.option("--body", required=True, help="Client config as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def update_client(client_id: str, body: str, pretty: bool):
    """Update NAC client."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/clients/{client_id}", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Client IDs as JSON array")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def bulk_delete_clients(body: str, pretty: bool):
    """Bulk delete NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkDelete", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Bulk edit body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def bulk_edit_clients(body: str, pretty: bool):
    """Bulk edit NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkEdit", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Bulk upload body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def bulk_upload_clients(body: str, pretty: bool):
    """Bulk upload NAC clients."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/bulkUpload", body=body_dict)
    output_json(result, pretty)


# ============================================================================
# Client Groups
# ============================================================================


@cli.command()
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), help="Sort direction")
@click.option("--sort-key", help="Field to sort by (e.g., name, description)")
@click.option("--per-page", type=int, help="Entries per page (3-1000). Default: 1000")
@click.option("--starting-after", type=int, help="Start index for pagination (integer, 0-based)")
@click.option("--ending-before", type=int, help="End index for pagination (integer, 0-based)")
@click.option("--search", help="Fuzzy search on client groups")
@click.option("--group-ids", help="Comma-separated list of group IDs")
@click.option("--limit", type=int, help="Maximum number of items to return")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def client_groups(sort_order: Optional[str], sort_key: Optional[str], per_page: Optional[int],
                  starting_after: Optional[int], ending_before: Optional[int], search: Optional[str],
                  group_ids: Optional[str], limit: Optional[int], pretty: bool):
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
                           params=params if params else None, limit=limit)
    output_json(result, pretty)


@cli.command()
@click.option("--body", required=True, help="Group body as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def create_client_group(body: str, pretty: bool):
    """Create client group."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("POST", f"/organizations/{ORG_ID}/nac/clients/groups", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("group_id")
@click.option("--body", required=True, help="Group config as JSON")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def update_client_group(group_id: str, body: str, pretty: bool):
    """Update client group."""
    client = get_client()
    body_dict = json.loads(body)
    result = client.request("PUT", f"/organizations/{ORG_ID}/nac/clients/groups/{group_id}", body=body_dict)
    output_json(result, pretty)


@cli.command()
@click.argument("group_id")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def delete_client_group(group_id: str, pretty: bool):
    """Delete client group."""
    client = get_client()
    result = client.request("DELETE", f"/organizations/{ORG_ID}/nac/clients/groups/{group_id}")
    output_json(result, pretty)


# ============================================================================
# Dictionaries
# ============================================================================


@cli.command()
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def dictionaries(pretty: bool):
    """List dictionaries."""
    client = get_client()
    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries")
    output_json(result, pretty)


@cli.command()
@click.argument("dictionary_id")
@click.option("--network-ids", help="Comma-separated list of network IDs to filter enum values")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def dictionary_attributes(dictionary_id: str, network_ids: Optional[str], pretty: bool):
    """List dictionary attributes."""
    client = get_client()

    params = {}
    if network_ids:
        params["networkIds"] = network_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries/{dictionary_id}/attributes",
                           params=params if params else None)
    output_json(result, pretty)


@cli.command()
@click.argument("dictionary_id")
@click.argument("attribute_name")
@click.option("--search", help="Search string for contains-match filtering")
@click.option("--network-ids", help="Comma-separated list of network IDs to filter values")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def attribute_values(dictionary_id: str, attribute_name: str, search: Optional[str],
                    network_ids: Optional[str], pretty: bool):
    """Search attribute values."""
    client = get_client()

    params = {}
    if search:
        params["search"] = search
    if network_ids:
        params["networkIds"] = network_ids.split(",")

    result = client.request("GET", f"/organizations/{ORG_ID}/nac/dictionaries/{dictionary_id}/attributes/{attribute_name}/values",
                           params=params if params else None)
    output_json(result, pretty)


# ============================================================================
# License
# ============================================================================


@cli.command()
@click.option("--start-date", help="Start date for usage data (UTC, YYYY-MM-DD format)")
@click.option("--end-date", help="End date for usage data (UTC, YYYY-MM-DD format)")
@click.option("--network-ids", help="Comma-separated list of network IDs")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON with 2-space indents")
def license_usage(start_date: Optional[str], end_date: Optional[str], network_ids: Optional[str],
                  pretty: bool):
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
                           params=params if params else None)
    output_json(result, pretty)


if __name__ == "__main__":
    cli()
