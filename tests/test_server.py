"""Tests for MCP server tools."""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from key_value.aio.stores.disk.store import DiskStore

from evolve_o_mart.store import Store

# Mock the GoogleGenaiSamplingHandler before importing server
sys.modules["evolve_o_mart.gemini.sampling"] = MagicMock()


@pytest.fixture
def temp_store():
    """Create a store with a temporary data directory."""
    temp_dir = Path(tempfile.mkdtemp())
    test_store = Store(DiskStore(directory=temp_dir))

    yield test_store

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_get_store_tool(temp_store: Store) -> None:
    """Test get_state returns expected structure."""
    result = await temp_store.get_state()

    assert len(result.products) == 6  # 6 seed products
    assert result.favorites_to_evolve > 0


@pytest.mark.asyncio
async def test_favorite_product_tool(temp_store: Store) -> None:
    """Test favorite_product increments favorites."""
    from evolve_o_mart.models import FavoriteResult

    result = await temp_store.favorite_product(product_id="prod_001")

    assert isinstance(result, FavoriteResult)
    assert result.success is True
    assert result.product is not None
    assert result.product.favorites == 1
    assert result.ready_to_evolve is False

    result2 = await temp_store.favorite_product(product_id="prod_001")
    assert result2.product is not None
    assert result2.product.favorites == 2


@pytest.mark.asyncio
async def test_favorite_product_not_found(temp_store: Store) -> None:
    """Test favorite_product with invalid product ID returns failure."""
    result = await temp_store.favorite_product(product_id="invalid_id")

    assert result.success is False


@pytest.mark.asyncio
async def test_reset_store_tool(temp_store: Store) -> None:
    """Test reset resets state."""
    _ = await temp_store.favorite_product(product_id="prod_001")
    _ = await temp_store.favorite_product(product_id="prod_001")

    store_result = await temp_store.get_state()
    prod = next(p for p in store_result.products if p.id == "prod_001")
    assert prod.favorites == 2

    result = await temp_store.tool_reset_store()

    assert result.success is True

    store2 = await temp_store.get_state()
    assert all(p.favorites == 0 for p in store2.products)


@pytest.mark.asyncio
async def test_favorite_product_ready_to_evolve(temp_store: Store) -> None:
    """Test that favorite_product reports ready_to_evolve when threshold reached."""
    from evolve_o_mart.store import FAVORITES_TO_EVOLVE

    # Favorite until one short of threshold
    for _ in range(FAVORITES_TO_EVOLVE - 1):
        result = await temp_store.favorite_product(product_id="prod_001")
        assert result.ready_to_evolve is False
        assert result.product is not None

    # Final favorite should trigger ready_to_evolve
    result = await temp_store.favorite_product(product_id="prod_001")
    assert result.ready_to_evolve is True
    assert result.product is not None
    assert result.product.favorites == FAVORITES_TO_EVOLVE
