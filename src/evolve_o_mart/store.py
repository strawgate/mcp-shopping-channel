"""Store for EVOLVE-O-MART using py-key-value-aio."""

import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from logging import Logger

from fastmcp import Context, FastMCP
from fastmcp.resources import Resource
from fastmcp.tools import Tool
from fastmcp.utilities.logging import get_logger
from key_value.aio.adapters.pydantic import PydanticAdapter
from key_value.aio.protocols.key_value import AsyncKeyValue

from evolve_o_mart.models import (
    EvolutionResponse,
    EvolutionResult,
    Product,
    ResetResult,
    StoreMetadata,
    StoreState,
    ViewResult,
)
from evolve_o_mart.seeds import SEED_PRODUCTS

METADATA_KEY = "metadata"
PRODUCT_COLLECTION = "products"
METADATA_COLLECTION = "metadata"
VOTES_TO_EVOLVE = int(os.environ.get("VOTES_TO_EVOLVE", "5"))

logger: Logger = get_logger(name="evolve-o-mart")


def _generate_product_id() -> str:
    """Generate a unique product ID."""
    return f"prod_{secrets.token_hex(8)}"


@dataclass
class EvolutionState:
    """State needed for evolution."""

    metadata: StoreMetadata
    products: list[Product]
    winner: Product | None
    can_evolve: bool
    votes_until_evolution: int


class Store:
    """Key-value store for products and metadata."""

    def __init__(self, key_value: AsyncKeyValue) -> None:
        """Initialize store with given key-value backend."""
        self._key_value: AsyncKeyValue = key_value
        self._products: PydanticAdapter[Product] = PydanticAdapter[Product](
            key_value=self._key_value, pydantic_model=Product, default_collection=PRODUCT_COLLECTION
        )
        self._metadata_store: PydanticAdapter[StoreMetadata] = PydanticAdapter[StoreMetadata](
            key_value=self._key_value, pydantic_model=StoreMetadata, default_collection=METADATA_COLLECTION
        )
        self._initialized: bool = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        metadata = await self._metadata_store.get(key=METADATA_KEY)
        if metadata is None:
            _ = await self.initialize()

        self._initialized = True

    async def initialize(self) -> tuple[StoreMetadata, list[Product]]:
        """Create initial store state with seed products."""
        now = datetime.now(UTC).isoformat()

        products: list[Product] = []
        product_ids: list[str] = []

        logger.info("Initializing store with seed products")

        for seed in SEED_PRODUCTS:
            product = seed.model_copy(update={"created_at": now, "views": 0})
            products.append(product)
            product_ids.append(product.id)
            await self.update_product(product)

        metadata: StoreMetadata = StoreMetadata(
            generation=1,
            generation_started_at=now,
            last_winner_id=None,
            votes_this_generation=0,
            product_ids=product_ids,
        )
        _ = await self.update_metadata(metadata)

        return metadata, products

    # ============ Core Operations ============

    async def get_metadata_and_products(self) -> tuple[StoreMetadata, list[Product]]:
        """Load full store state, initializing if needed."""
        await self._ensure_initialized()
        metadata: StoreMetadata = await self.get_metadata()
        products: list[Product] = await self.get_products(metadata.product_ids)
        return metadata, products

    async def get_metadata(self) -> StoreMetadata:
        """Get store metadata."""
        await self._ensure_initialized()
        metadata = await self._metadata_store.get(key=METADATA_KEY)

        if metadata is None:
            msg = "Store not initialized. This should never happen."
            raise RuntimeError(msg)

        return metadata

    async def update_metadata(self, metadata: StoreMetadata) -> None:
        """Save store metadata."""
        await self._metadata_store.put(key=METADATA_KEY, value=metadata)

    async def get_product(self, product_id: str) -> Product | None:
        """Get a product by ID."""
        await self._ensure_initialized()
        return await self._products.get(key=product_id)

    async def update_product(self, product: Product) -> None:
        """Save a product."""
        await self._products.put(key=product.id, value=product)

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product."""
        return await self._products.delete(key=product_id)

    async def get_products(self, product_ids: list[str] | None = None) -> list[Product]:
        """Get all products. If no IDs provided, loads from metadata."""
        if product_ids is None:
            product_ids = await self.get_all_product_ids()

        products: list[Product] = []
        for product_id in product_ids:
            product = await self.get_product(product_id)
            if product is not None:
                products.append(product)
        return products

    async def get_top_product(self) -> Product | None:
        """Get the product with most views."""
        products: list[Product] = await self.get_products()
        if not products:
            return None
        return max(products, key=lambda p: p.views)

    async def get_all_product_ids(self) -> list[str]:
        """Get all product IDs."""
        metadata: StoreMetadata = await self.get_metadata()
        return metadata.product_ids

    # ============ Business Operations ============

    async def get_state(self) -> StoreState:
        """Get the current store state with all products."""
        metadata, products = await self.get_metadata_and_products()
        leader = max(products, key=lambda p: p.views) if products else None
        votes_until = max(0, VOTES_TO_EVOLVE - metadata.votes_this_generation)

        return StoreState(
            generation=metadata.generation,
            generation_started_at=metadata.generation_started_at,
            last_winner_id=metadata.last_winner_id,
            current_leader_id=leader.id if leader else None,
            votes_this_generation=metadata.votes_this_generation,
            votes_until_evolution=votes_until,
            votes_to_evolve=VOTES_TO_EVOLVE,
            products=products,
        )

    async def mark_product_viewed(self, product_id: str) -> ViewResult | None:
        """Increment views for a product and return result."""
        logger.info(f"Marking product {product_id} viewed")

        product: Product | None = await self.get_product(product_id)
        if product is None:
            return None

        product.views += 1
        await self.update_product(product)

        metadata = await self.get_metadata()
        metadata.votes_this_generation += 1
        await self.update_metadata(metadata)

        leader: Product | None = await self.get_top_product()
        is_leader = leader is not None and leader.id == product_id

        return ViewResult(
            product=product,
            is_leader=is_leader,
            message=f"Favorited {product.name} (v{product.version}) - {product.views} total favorites",
        )

    async def check_evolution_state(self) -> EvolutionState:
        """Check if evolution is possible and return current state."""
        metadata, products = await self.get_metadata_and_products()

        winner = max(products, key=lambda p: p.views)
        if winner.views == 0:
            return EvolutionState(metadata, products, None, False, VOTES_TO_EVOLVE)

        votes_until = max(0, VOTES_TO_EVOLVE - metadata.votes_this_generation)
        can_evolve = votes_until == 0

        return EvolutionState(metadata, products, winner, can_evolve, votes_until)

    async def evolve(self, ctx: Context, dry_run: bool = False) -> EvolutionResponse:
        """Evolve the most-favorited product into a new version."""
        logger.info("Evolving the most-favorited product")

        state = await self.check_evolution_state()

        if state.winner is None:
            return EvolutionResponse(success=False, message="No products have been favorited yet")

        if not dry_run and not state.can_evolve:
            return EvolutionResponse(
                success=False,
                message=f"Need {state.votes_until_evolution} more favorites to trigger evolution.",
                not_ready=True,
                votes_until_evolution=state.votes_until_evolution,
                votes_to_evolve=VOTES_TO_EVOLVE,
            )

        if dry_run:
            return EvolutionResponse(
                success=True,
                message=f"Would evolve {state.winner.name} (v{state.winner.version}) with {state.winner.views} favorites",
                dry_run=True,
                would_evolve=state.winner,
            )

        try:
            evolution = await self._generate_evolution(ctx, state.winner)
        except Exception as e:
            return EvolutionResponse(success=False, message=str(e))

        evolved = await self.apply_evolution(state.winner, evolution)
        metadata = await self.get_metadata()

        return EvolutionResponse(
            success=True,
            message=f"{state.winner.name} evolved into {evolved.name}!",
            generation=metadata.generation,
            evolved_from=state.winner,
            evolved_to=evolved,
            evolution_note=evolution.evolution_note,
        )

    async def _generate_evolution(self, ctx: Context, winner: Product) -> EvolutionResult:
        """Use LLM via FastMCP sampling to generate an evolved version."""
        prompt = f"""You are evolving a product for a comedic shopping channel called EVOLVE-O-MART.

The winning product from last generation is:
- Name: {winner.name}
- Version: {winner.version}
- Tagline: {winner.tagline}
- Description: {winner.description}

Generate an EVOLVED version that adds one absurd new feature.
The product should get progressively more ridiculous with each evolution.
You can subtract features (to prevent bloat) but you must provide an absurd reason for the removal.

Make it funny but not crude. Appropriate for a family-friendly audience. Parody "as seen on TV" products. Not too corny."""

        result = await ctx.sample(
            messages=prompt,
            result_type=EvolutionResult,
            max_tokens=10240,
        )
        return result.result

    async def apply_evolution(self, winner: Product, evolution: EvolutionResult) -> Product:
        """Apply evolution results: create new product, reset views, update metadata."""
        metadata = await self.get_metadata()

        now = datetime.now(UTC).isoformat()
        evolved = Product(
            id=_generate_product_id(),
            name=evolution.new_name,
            tagline=evolution.new_tagline,
            description=evolution.new_description,
            ascii_art=evolution.new_ascii_art,
            version=winner.version + 1,
            views=0,
            parent_id=winner.id,
            created_at=now,
        )

        await self.update_product(evolved)

        new_product_ids = [evolved.id if pid == winner.id else pid for pid in metadata.product_ids]

        for pid in metadata.product_ids:
            if pid != winner.id:
                prod = await self.get_product(pid)
                if prod is not None:
                    prod.views = 0
                    await self.update_product(prod)

        metadata.product_ids = new_product_ids
        metadata.generation += 1
        metadata.generation_started_at = now
        metadata.last_winner_id = winner.id
        metadata.votes_this_generation = 0
        await self.update_metadata(metadata)

        return evolved

    # ============ Lifecycle ============

    async def reset_product_views(self) -> None:
        """Reset views for all products."""
        for product_id in await self.get_all_product_ids():
            product = await self.get_product(product_id)
            if product is not None:
                product.views = 0
                await self.update_product(product)

    async def reset(self) -> tuple[StoreMetadata, list[Product]]:
        """Reset store to initial state."""
        metadata = await self.get_metadata()
        for product_id in metadata.product_ids:
            _ = await self.delete_product(product_id)
        self._initialized = False
        return await self.initialize()

    # ============ MCP Tool Methods (only for those needing transformation) ============

    async def tool_reset_store(self) -> ResetResult:
        """Reset the store to initial state."""
        metadata, products = await self.reset()
        return ResetResult(
            message="Store reset to initial state",
            generation=metadata.generation,
            products=[p.name for p in products],
        )

    # ============ MCP Registration ============

    def add_tools_to_server(self, server: FastMCP) -> None:
        """Register store operations as MCP tools."""
        _ = server.add_tool(Tool.from_function(fn=self.get_state, name="get_store_state"))
        _ = server.add_tool(Tool.from_function(fn=self.mark_product_viewed, name="view_product"))
        _ = server.add_tool(Tool.from_function(fn=self.evolve, name="evolve"))
        _ = server.add_tool(Tool.from_function(fn=self.tool_reset_store, name="reset_store"))

    def add_resources_to_server(self, server: FastMCP) -> None:
        """Register store data as MCP resources."""

        async def get_state_json() -> str:
            """Get store state as JSON."""
            state = await self.get_state()
            return state.model_dump_json()

        async def get_products_json() -> str:
            """Get all products as JSON."""
            products = await self.get_products()
            import json

            return json.dumps([p.model_dump() for p in products])

        async def get_leader_json() -> str:
            """Get leader product as JSON."""
            leader = await self.get_top_product()
            if leader is None:
                return "null"
            return leader.model_dump_json()

        _ = server.add_resource(Resource.from_function(fn=get_state_json, uri="store://state"))
        _ = server.add_resource(Resource.from_function(fn=get_products_json, uri="store://products"))
        _ = server.add_resource(Resource.from_function(fn=get_leader_json, uri="store://leader"))
