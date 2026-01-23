"""Tests for Store class."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from key_value.aio.stores.disk.store import DiskStore

from evolve_o_mart.store import Store


@pytest.fixture
def temp_store() -> Generator[Store, None, None]:
    """Create a store with a temporary data directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    test_store = Store(DiskStore(directory=temp_dir))

    yield test_store

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_initialize_store(temp_store: Store) -> None:
    """Test store initialization with seed products."""
    metadata, products = await temp_store.initialize()

    assert len(products) == 6  # 6 seed products
    assert products[0].name == "Steam Bowl"
    assert all(p.favorites == 0 for p in products)
    assert len(metadata.product_ids) == 6


@pytest.mark.asyncio
async def test_load_and_update_product(temp_store: Store) -> None:
    """Test loading and updating individual products."""
    _ = await temp_store.initialize()

    product = await temp_store.get_product("prod_001")
    assert product is not None
    assert product.favorites == 0

    product.favorites = 5
    await temp_store.update_product(product)

    product2 = await temp_store.get_product("prod_001")
    assert product2 is not None
    assert product2.favorites == 5


@pytest.mark.asyncio
async def test_get_metadata_and_products(temp_store: Store) -> None:
    """Test loading full store state."""
    _, products = await temp_store.get_metadata_and_products()

    products[0].favorites = 10
    await temp_store.update_product(products[0])

    _, products2 = await temp_store.get_metadata_and_products()
    assert products2[0].favorites == 10


@pytest.mark.asyncio
async def test_seed_products_content(temp_store: Store) -> None:
    """Test that seed products have expected content."""
    _, products = await temp_store.initialize()

    product_names = [p.name for p in products]
    assert "Steam Bowl" in product_names
    assert "The Uncertainty Lamp" in product_names
    assert "Regret Pencil" in product_names
    assert "Motivational Brick" in product_names
    assert "Procrastination Clock" in product_names
    assert "Existential Sponge" in product_names

    assert all(p.version == 1 for p in products)


@pytest.mark.asyncio
async def test_reset_store(temp_store: Store) -> None:
    """Test resetting store clears data."""
    _ = await temp_store.initialize()
    product = await temp_store.get_product("prod_001")
    assert product is not None
    product.favorites = 100
    await temp_store.update_product(product)

    _, products = await temp_store.reset()

    assert all(p.favorites == 0 for p in products)


@pytest.mark.asyncio
async def test_get_products_without_ids(temp_store: Store) -> None:
    """Test get_products without providing IDs."""
    _ = await temp_store.initialize()

    products = await temp_store.get_products()
    assert len(products) == 6


@pytest.mark.asyncio
async def test_favorite_product(temp_store: Store) -> None:
    """Test favorite_product increments favorites and reports ready_to_evolve."""
    from evolve_o_mart.store import FAVORITES_TO_EVOLVE

    _ = await temp_store.initialize()

    result = await temp_store.favorite_product("prod_001")
    assert result is not None
    assert result.success is True
    assert result.product is not None
    assert result.product.favorites == 1
    assert result.ready_to_evolve is False

    # Favorite until ready to evolve
    for _ in range(FAVORITES_TO_EVOLVE - 1):
        result = await temp_store.favorite_product("prod_001")

    assert result.product is not None
    assert result.product.favorites == FAVORITES_TO_EVOLVE
    assert result.ready_to_evolve is True


@pytest.mark.asyncio
async def test_favorite_product_not_found(temp_store: Store) -> None:
    """Test favorite_product with invalid product ID."""
    _ = await temp_store.initialize()

    result = await temp_store.favorite_product("invalid_id")
    assert result.success is False


@pytest.mark.asyncio
async def test_get_all_product_ids(temp_store: Store) -> None:
    """Test get_all_product_ids returns list of IDs."""
    _ = await temp_store.initialize()

    ids = await temp_store.get_all_product_ids()
    assert len(ids) == 6
    assert "prod_001" in ids


@pytest.mark.asyncio
async def test_get_state(temp_store: Store) -> None:
    """Test get_state returns full store state."""
    from evolve_o_mart.store import FAVORITES_TO_EVOLVE

    _ = await temp_store.initialize()

    state = await temp_store.get_state()
    assert state.favorites_to_evolve == FAVORITES_TO_EVOLVE
    assert len(state.products) == 6


@pytest.mark.asyncio
async def test_per_product_evolution_independence(temp_store: Store) -> None:
    """Test that favoriting one product doesn't affect others."""
    _ = await temp_store.initialize()

    # Favorite product 1 multiple times
    _ = await temp_store.favorite_product("prod_001")
    _ = await temp_store.favorite_product("prod_001")
    _ = await temp_store.favorite_product("prod_001")

    # Favorite product 2 once
    _ = await temp_store.favorite_product("prod_002")

    # Check they have independent counts
    prod1 = await temp_store.get_product("prod_001")
    prod2 = await temp_store.get_product("prod_002")

    assert prod1 is not None
    assert prod2 is not None
    assert prod1.favorites == 3
    assert prod2.favorites == 1
