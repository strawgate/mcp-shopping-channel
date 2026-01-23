"""Pydantic models for EVOLVE-O-MART."""

from pydantic import BaseModel


class Product(BaseModel):
    """A product in the store."""

    id: str
    name: str
    tagline: str
    description: str
    ascii_art: str
    version: int = 1
    favorites: int = 0
    parent_id: str | None = None
    created_at: str = ""


class StoreMetadata(BaseModel):
    """Store metadata (separate from products)."""

    product_ids: list[str]


class EvolutionResult(BaseModel):
    """Result from generating an evolution."""

    new_name: str
    new_tagline: str
    new_description: str
    evolution_note: str
    new_ascii_art: str


# ============ Tool Response Models ============


class StoreState(BaseModel):
    """Full store state returned by get_store."""

    favorites_to_evolve: int
    products: list[Product]


class FavoriteResult(BaseModel):
    """Result of favoriting a product."""

    success: bool = True
    product: Product | None = None
    message: str
    ready_to_evolve: bool = False


class EvolutionResponse(BaseModel):
    """Response from evolution tool."""

    success: bool
    message: str
    evolved_from: Product | None = None
    evolved_to: Product | None = None
    evolution_note: str | None = None


class ResetResult(BaseModel):
    """Result of store reset."""

    success: bool = True
    message: str
    products: list[str]
