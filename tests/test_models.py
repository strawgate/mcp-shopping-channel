"""Tests for models."""

from evolve_o_mart.models import EvolutionResult, Product, StoreMetadata


def test_product_model() -> None:
    """Test Product model creation."""
    product = Product(
        id="prod_001",
        name="Test Product",
        tagline="Test tagline",
        description="Test description",
        ascii_art="[art]",
        version=1,
        favorites=0,
        created_at="2024-01-01T00:00:00Z",
    )
    assert product.id == "prod_001"
    assert product.name == "Test Product"
    assert product.favorites == 0
    assert product.parent_id is None


def test_product_with_parent() -> None:
    """Test Product model with parent."""
    product = Product(
        id="prod_002",
        name="Evolved Product",
        tagline="Evolved tagline",
        description="Evolved description",
        ascii_art="[evolved art]",
        version=2,
        favorites=5,
        parent_id="prod_001",
        created_at="2024-01-02T00:00:00Z",
    )
    assert product.parent_id == "prod_001"
    assert product.version == 2


def test_store_metadata_model() -> None:
    """Test StoreMetadata model creation."""
    metadata = StoreMetadata(
        product_ids=["prod_001", "prod_002"],
    )
    assert len(metadata.product_ids) == 2


def test_evolution_result_model() -> None:
    """Test EvolutionResult model creation."""
    result = EvolutionResult(
        new_name="Steam Bowl v2",
        new_tagline="Now with bluetooth!",
        new_description="The Steam Bowl you love, now connected.",
        evolution_note="NOW WITH BLUETOOTH",
        new_ascii_art="[new art]",
    )
    assert result.new_name == "Steam Bowl v2"
    assert "BLUETOOTH" in result.evolution_note
