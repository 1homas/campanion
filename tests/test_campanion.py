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


@pytest.fixture(autouse=True)
def mock_cache(tmp_path, monkeypatch):
    """Use temp cache directory."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    monkeypatch.setattr(campanion, "CACHE_DIR", cache_dir)


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
    assert json.loads(result.output) == mock_response


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
    assert data["meta"]["totalCount"] == 2


# ============================================================================
# Cache Tests
# ============================================================================


@respx.mock
def test_cache_get_request(runner):
    """Test that GET requests are cached."""
    mock_response = {"items": [{"id": "1"}]}
    route = respx.get("https://api.meraki.com/api/v1/organizations/123456/networks").mock(
        return_value=Response(200, json=mock_response)
    )

    # First request
    result1 = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks"])
    assert result1.exit_code == 0
    assert route.call_count == 1

    # Second request (should use cache)
    result2 = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks"])
    assert result2.exit_code == 0
    assert route.call_count == 1  # No additional API call


@respx.mock
def test_cache_refresh_flag(runner):
    """Test --refresh flag bypasses cache."""
    mock_response = {"items": [{"id": "1"}]}
    route = respx.get("https://api.meraki.com/api/v1/organizations/123456/networks").mock(
        return_value=Response(200, json=mock_response)
    )

    # First request
    result1 = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks"])
    assert result1.exit_code == 0
    assert route.call_count == 1

    # Second request with --refresh
    result2 = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks", "--refresh"])
    assert result2.exit_code == 0
    assert route.call_count == 2  # Cache bypassed


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
    """Test --raw flag produces compact JSON."""
    mock_response = {"items": [{"id": "1", "name": "test"}]}
    respx.get("https://api.meraki.com/api/v1/organizations/123456/networks").mock(
        return_value=Response(200, json=mock_response)
    )

    result = runner.invoke(cli, ["api", "GET", "/organizations/{organizationId}/networks", "--raw"])

    assert result.exit_code == 0
    # Compact JSON has no spaces after separators
    assert '{"items":[{"id":"1","name":"test"}]}' in result.output.replace("\n", "")
