"""
Unit tests for campanion.py CLI.
Uses respx to mock httpx requests — no live API calls.
"""

import json
import os
import sys
from pathlib import Path

import pytest
import respx
from click.testing import CliRunner
from httpx import Response

# Set environment before import
os.environ["MERAKI_DASHBOARD_API_KEY"] = "test-api-key"
os.environ["MERAKI_ORG_ID"] = "123456"
os.environ["MERAKI_BASE_URL"] = "https://api.meraki.com/api/v1"

# Import the CLI
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import campanion

cli = campanion.cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()




# ============================================================================
# Generic API Tests
# ============================================================================


@respx.mock
def test_api_get(runner):
    """Test generic GET request."""
    mock_response = {"items": [{"id": "1", "name": "test"}]}
    respx.get("https://api.meraki.com/api/v1/organizations/123456/networks").mock(
        return_value=Response(200, json=mock_response)
    )

    result = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # Pagination adds total field
    assert data["items"] == mock_response["items"]
    assert data["total"] == 1


@respx.mock
def test_api_post(runner):
    """Test generic POST request."""
    mock_response = {"id": "789", "status": "created"}
    respx.post("https://api.meraki.com/api/v1/organizations/123456/nac/clients").mock(
        return_value=Response(201, json=mock_response)
    )

    body = json.dumps({"mac": "00:11:22:33:44:55"})
    result = runner.invoke(cli, ["api", "POST", "/organizations/{organizationId}/nac/clients", "--body", body])

    assert result.exit_code == 0
    assert json.loads(result.output) == mock_response


# ============================================================================
# Client Tests
# ============================================================================


@respx.mock
def test_clients_overview(runner):
    """Test clients-overview command."""
    mock_response = {"count": 25}
    respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/clients/overview").mock(
        return_value=Response(200, json=mock_response)
    )

    result = runner.invoke(cli, ["clients-overview"])

    assert result.exit_code == 0
    assert json.loads(result.output) == mock_response


@respx.mock
def test_client_groups(runner):
    """Test client-groups command."""
    mock_response = {
        "meta": {"totalCount": 2},
        "items": [
            {"id": "g1", "name": "Printers"},
            {"id": "g2", "name": "Phones"}
        ]
    }
    respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/clients/groups").mock(
        return_value=Response(200, json=mock_response)
    )

    result = runner.invoke(cli, ["client-groups"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # Pagination transforms response format
    assert data["total"] == 2
    assert len(data["items"]) == 2




# ============================================================================
# Error Handling Tests
# ============================================================================


@respx.mock
def test_api_error_handling(runner):
    """Test HTTP error handling."""
    respx.get("https://api.meraki.com/api/v1/organizations/123456/invalid").mock(
        return_value=Response(404, json={"error": "Not found"})
    )

    result = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/invalid"])

    assert result.exit_code == 1
    assert "404" in result.output


def test_missing_api_key(runner, monkeypatch):
    """Test error when API key is missing."""
    monkeypatch.delenv("MERAKI_DASHBOARD_API_KEY", raising=False)
    # Force reimport to pick up env change
    import importlib
    importlib.reload(campanion)

    result = runner.invoke(campanion.cli, ["clients-overview"])

    assert result.exit_code == 1


# ============================================================================
# Output Format Tests
# ============================================================================


@respx.mock
def test_raw_output_flag(runner):
    """Test default output is compact JSON and --pretty produces formatted JSON."""
    mock_response = {"items": [{"id": "1", "name": "test"}]}
    respx.get("https://api.meraki.com/api/v1/organizations/123456/networks").mock(
        return_value=Response(200, json=mock_response)
    )

    # Test default compact output
    result = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks"])
    assert result.exit_code == 0
    # Compact JSON has no spaces after separators (includes total from pagination)
    assert '{"items":[{"id":"1","name":"test"}],"total":1}' == result.output.replace("\n", "")

    # Test --pretty flag produces formatted output
    result = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks", "--pretty"])
    assert result.exit_code == 0
    # Pretty-printed JSON has newlines and indentation
    assert "\n" in result.output
    assert "  " in result.output  # Check for 2-space indents


# ============================================================================
# Pagination Tests
# ============================================================================


@respx.mock
def test_pagination_sessions(runner):
    """Test pagination automatically fetches all pages for sessions."""
    # First page response (full page of 3 items to keep test small)
    page1 = {
        "items": [{"sessionId": f"s{i}", "status": "success"} for i in range(3)]
    }
    # Second page response (partial page)
    page2 = {
        "items": [{"sessionId": f"s{i}", "status": "success"} for i in range(3, 5)]
    }

    # Mock responses based on parameters
    def mock_handler(request):
        params = dict(request.url.params)
        if "startingAfter" not in params:
            # First request (index 0)
            return Response(200, json=page1)
        elif params.get("startingAfter") == "3":
            # Second request (index 3)
            return Response(200, json=page2)
        return Response(404, json={"error": "Unexpected request"})

    respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/sessions/history").mock(
        side_effect=mock_handler
    )

    result = runner.invoke(cli, ["sessions", "--per-page", "3"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 5
    assert len(data["items"]) == 5


@respx.mock
def test_pagination_clients(runner):
    """Test pagination automatically fetches all pages for clients."""
    # First page (full - 3 items)
    page1 = {
        "items": [{"id": f"c{i}", "mac": f"00:00:00:00:00:{i:02x}"} for i in range(3)]
    }
    # Second page (partial - only 2 items, less than perPage)
    page2 = {
        "items": [{"id": f"c{i}", "mac": f"00:00:00:00:00:{i:02x}"} for i in range(3, 5)]
    }

    def mock_handler(request):
        params = dict(request.url.params)
        if "startingAfter" not in params:
            return Response(200, json=page1)
        elif params.get("startingAfter") == "3":
            return Response(200, json=page2)
        return Response(404, json={"error": f"Unexpected params: {params}"})

    respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/clients").mock(
        side_effect=mock_handler
    )

    result = runner.invoke(cli, ["clients", "--per-page", "3"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 5
    assert len(data["items"]) == 5


@respx.mock
def test_pagination_stops_on_partial_page(runner):
    """Test pagination stops when receiving fewer items than perPage."""
    # Single partial page (2 items when perPage is 3)
    page1 = {
        "items": [{"id": f"c{i}", "mac": f"00:00:00:00:00:{i:02x}"} for i in range(2)]
    }

    route = respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/clients").mock(
        return_value=Response(200, json=page1)
    )

    result = runner.invoke(cli, ["clients", "--per-page", "3"])

    assert result.exit_code == 0
    assert route.call_count == 1  # Only one request made
    data = json.loads(result.output)
    assert len(data["items"]) == 2
    assert data["total"] == 2


@respx.mock
def test_limit_option(runner):
    """Test --limit option caps result count."""
    # First page with 3 items
    page1 = {
        "items": [{"id": f"c{i}", "mac": f"00:00:00:00:00:{i:02x}"} for i in range(3)]
    }
    # Second page with 2 items
    page2 = {
        "items": [{"id": f"c{i}", "mac": f"00:00:00:00:00:{i:02x}"} for i in range(3, 5)]
    }

    def mock_handler(request):
        params = dict(request.url.params)
        if "startingAfter" not in params:
            return Response(200, json=page1)
        elif params.get("startingAfter") == "3":
            return Response(200, json=page2)
        return Response(404, json={"error": f"Unexpected params: {params}"})

    route = respx.get("https://api.meraki.com/api/v1/organizations/123456/nac/clients").mock(
        side_effect=mock_handler
    )

    result = runner.invoke(cli, ["clients", "--per-page", "3", "--limit", "4"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # Should stop after getting 4 items (doesn't need full second page)
    assert len(data["items"]) == 4
    assert data["total"] == 4
    assert route.call_count == 2  # Two pages fetched to reach limit
