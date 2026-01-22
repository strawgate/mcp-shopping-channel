"""Tests for Store class."""

import shutil
import tempfile
from pathlib import Path

import pytest
from key_value.aio.stores.disk.store import DiskStore

from evolve_o_mart.store import Store


@pytest.fixture
def temp_store() -> Store:
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

    assert metadata.generation == 1
    assert len(products) == 4
    assert products[0].name == "Steam Bowl"
    assert all(p.views == 0 for p in products)
    assert len(metadata.product_ids) == 4


@pytest.mark.asyncio
async def test_load_and_update_product(temp_store: Store) -> None:
    """Test loading and updating individual products."""
    await temp_store.initialize()

    product = await temp_store.get_product("prod_001")
    assert product is not None
    assert product.views == 0

    product.views = 5
    await temp_store.update_product(product)

    product2 = await temp_store.get_product("prod_001")
    assert product2 is not None
    assert product2.views == 5


@pytest.mark.asyncio
async def test_get_metadata_and_products(temp_store: Store) -> None:
    """Test loading full store state."""
    metadata, products = await temp_store.get_metadata_and_products()
    assert metadata.generation == 1

    metadata.generation = 2
    await temp_store.update_metadata(metadata)

    products[0].views = 10
    await temp_store.update_product(products[0])

    metadata2, products2 = await temp_store.get_metadata_and_products()
    assert metadata2.generation == 2
    assert products2[0].views == 10


@pytest.mark.asyncio
async def test_seed_products_content(temp_store: Store) -> None:
    """Test that seed products have expected content."""
    _, products = await temp_store.initialize()

    product_names = [p.name for p in products]
    assert "Steam Bowl" in product_names
    assert "The Uncertainty Lamp" in product_names
    assert "Regret Pencil" in product_names
    assert "Motivational Brick" in product_names

    assert all(p.version == 1 for p in products)


@pytest.mark.asyncio
async def test_reset_store(temp_store: Store) -> None:
    """Test resetting store clears data."""
    await temp_store.initialize()
    product = await temp_store.get_product("prod_001")
    assert product is not None
    product.views = 100
    await temp_store.update_product(product)

    metadata, products = await temp_store.reset()

    assert metadata.generation == 1
    assert all(p.views == 0 for p in products)


@pytest.mark.asyncio
async def test_get_products_without_ids(temp_store: Store) -> None:
    """Test get_products without providing IDs."""
    await temp_store.initialize()

    products = await temp_store.get_products()
    assert len(products) == 4


@pytest.mark.asyncio
async def test_mark_product_viewed(temp_store: Store) -> None:
    """Test mark_product_viewed increments views and tracks leader."""
    await temp_store.initialize()

    result = await temp_store.mark_product_viewed("prod_001")
    assert result is not None
    assert result.product.views == 1
    assert result.is_leader is True

    result2 = await temp_store.mark_product_viewed("prod_001")
    assert result2 is not None
    assert result2.product.views == 2

    result3 = await temp_store.mark_product_viewed("prod_002")
    assert result3 is not None
    assert result3.is_leader is False


@pytest.mark.asyncio
async def test_get_top_product(temp_store: Store) -> None:
    """Test get_top_product returns product with most views."""
    await temp_store.initialize()

    top = await temp_store.get_top_product()
    assert top is not None

    await temp_store.mark_product_viewed("prod_002")
    top = await temp_store.get_top_product()
    assert top is not None
    assert top.id == "prod_002"


@pytest.mark.asyncio
async def test_check_evolution_state(temp_store: Store) -> None:
    """Test check_evolution_state reports correct state."""
    from evolve_o_mart.store import VOTES_TO_EVOLVE

    await temp_store.initialize()

    state = await temp_store.check_evolution_state()
    assert state.winner is None
    assert state.can_evolve is False
    assert state.votes_until_evolution == VOTES_TO_EVOLVE

    await temp_store.mark_product_viewed("prod_001")
    state = await temp_store.check_evolution_state()
    assert state.winner is not None
    assert state.winner.id == "prod_001"
    assert state.votes_until_evolution == VOTES_TO_EVOLVE - 1
    assert state.can_evolve is False


@pytest.mark.asyncio
async def test_vote_countdown_to_evolution(temp_store: Store) -> None:
    """Test that voting counts toward evolution."""
    from evolve_o_mart.store import VOTES_TO_EVOLVE

    await temp_store.initialize()

    for _ in range(VOTES_TO_EVOLVE):
        await temp_store.mark_product_viewed("prod_001")

    state = await temp_store.check_evolution_state()
    assert state.can_evolve is True
    assert state.votes_until_evolution == 0
    assert state.winner is not None


@pytest.mark.asyncio
async def test_get_all_product_ids(temp_store: Store) -> None:
    """Test get_all_product_ids returns list of IDs."""
    await temp_store.initialize()

    ids = await temp_store.get_all_product_ids()
    assert len(ids) == 4
    assert "prod_001" in ids


@pytest.mark.asyncio
async def test_reset_product_views(temp_store: Store) -> None:
    """Test reset_product_views clears all view counts."""
    await temp_store.initialize()

    await temp_store.mark_product_viewed("prod_001")
    await temp_store.mark_product_viewed("prod_002")

    products = await temp_store.get_products()
    assert sum(p.views for p in products) > 0

    await temp_store.reset_product_views()

    products2 = await temp_store.get_products()
    assert all(p.views == 0 for p in products2)
