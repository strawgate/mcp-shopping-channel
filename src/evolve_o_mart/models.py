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
    views: int = 0
    parent_id: str | None = None
    created_at: str = ""


class StoreMetadata(BaseModel):
    """Store metadata (separate from products)."""

    generation: int
    generation_started_at: str
    last_winner_id: str | None = None
    votes_this_generation: int = 0
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

    generation: int
    generation_started_at: str
    last_winner_id: str | None
    current_leader_id: str | None
    votes_this_generation: int
    votes_until_evolution: int
    votes_to_evolve: int
    products: list[Product]


class ViewResult(BaseModel):
    """Result of viewing/favoriting a product."""

    success: bool = True
    product: Product
    is_leader: bool
    message: str


class EvolutionResponse(BaseModel):
    """Response from evolution tool."""

    success: bool
    message: str
    generation: int | None = None
    evolved_from: Product | None = None
    evolved_to: Product | None = None
    evolution_note: str | None = None
    dry_run: bool = False
    would_evolve: Product | None = None
    not_ready: bool = False
    votes_until_evolution: int | None = None
    votes_to_evolve: int | None = None


class ResetResult(BaseModel):
    """Result of store reset."""

    success: bool = True
    message: str
    generation: int
    products: list[str]
