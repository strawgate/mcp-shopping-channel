"""Tests for MCP server tools."""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP
from key_value.aio.stores.disk.store import DiskStore

from evolve_o_mart.store import Store

# Mock the GoogleGenaiSamplingHandler before importing server
sys.modules["evolve_o_mart.gemini.sampling"] = MagicMock()


@pytest.fixture
def temp_store_with_mcp():
    """Create a store with a temporary data directory and MCP server."""
    temp_dir = Path(tempfile.mkdtemp())
    test_store = Store(DiskStore(directory=temp_dir))

    # Create a test MCP server and register the store
    test_mcp = FastMCP(name="TestStore")
    test_store.add_tools_to_server(test_mcp)
    test_store.add_resources_to_server(test_mcp)

    yield test_store, test_mcp

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_get_store_tool(temp_store_with_mcp) -> None:  # noqa: ANN001
    """Test get_store_state tool returns expected structure."""
    store, mcp = temp_store_with_mcp

    tool = mcp._tool_manager._tools["get_store_state"]
    result = await tool.fn()

    assert result.generation == 1
    assert len(result.products) == 4
    assert result.current_leader_id is not None


@pytest.mark.asyncio
async def test_view_product_tool(temp_store_with_mcp) -> None:  # noqa: ANN001
    """Test view_product tool increments views."""
    from evolve_o_mart.models import ViewResult

    store, mcp = temp_store_with_mcp

    view_tool = mcp._tool_manager._tools["view_product"]
    get_tool = mcp._tool_manager._tools["get_store_state"]

    result = await view_tool.fn(product_id="prod_001")

    assert isinstance(result, ViewResult)
    assert result.success is True
    assert result.product.views == 1
    assert result.is_leader is True

    result2 = await view_tool.fn(product_id="prod_001")
    assert result2.product.views == 2

    store_result = await get_tool.fn()
    assert store_result.current_leader_id == "prod_001"


@pytest.mark.asyncio
async def test_view_product_not_found(temp_store_with_mcp) -> None:  # noqa: ANN001
    """Test view_product tool with invalid product ID returns None."""
    _, mcp = temp_store_with_mcp

    tool = mcp._tool_manager._tools["view_product"]
    result = await tool.fn(product_id="invalid_id")

    # mark_product_viewed returns None for not found
    assert result is None


@pytest.mark.asyncio
async def test_reset_store_tool(temp_store_with_mcp) -> None:  # noqa: ANN001
    """Test reset_store tool resets state."""
    _, mcp = temp_store_with_mcp

    view_tool = mcp._tool_manager._tools["view_product"]
    get_tool = mcp._tool_manager._tools["get_store_state"]
    reset_tool = mcp._tool_manager._tools["reset_store"]

    await view_tool.fn(product_id="prod_001")
    await view_tool.fn(product_id="prod_001")

    store_result = await get_tool.fn()
    prod = next(p for p in store_result.products if p.id == "prod_001")
    assert prod.views == 2

    result = await reset_tool.fn()

    assert result.success is True
    assert result.generation == 1

    store2 = await get_tool.fn()
    assert all(p.views == 0 for p in store2.products)
