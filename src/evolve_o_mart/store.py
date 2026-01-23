"""Store for EVOLVE-O-MART using py-key-value-aio."""

import json
import os
import secrets
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
    FavoriteResult,
    Product,
    ResetResult,
    StoreMetadata,
    StoreState,
)
from evolve_o_mart.seeds import SEED_PRODUCTS

METADATA_KEY = "metadata"
PRODUCT_COLLECTION = "products"
METADATA_COLLECTION = "metadata"
FAVORITES_TO_EVOLVE = int(os.environ.get("FAVORITES_TO_EVOLVE", "5"))
MAX_EVOLUTION_TOKENS = 10240

logger: Logger = get_logger(name="evolve-o-mart")


def _generate_product_id() -> str:
    """Generate a unique product ID."""
    return f"prod_{secrets.token_hex(8)}"


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
            product = seed.model_copy(update={"created_at": now, "favorites": 0})
            products.append(product)
            product_ids.append(product.id)
            await self.update_product(product)

        metadata: StoreMetadata = StoreMetadata(product_ids=product_ids)
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

    async def get_all_product_ids(self) -> list[str]:
        """Get all product IDs."""
        metadata: StoreMetadata = await self.get_metadata()
        return metadata.product_ids

    # ============ Business Operations ============

    async def get_state(self) -> StoreState:
        """Get the current store state with all products."""
        _, products = await self.get_metadata_and_products()

        return StoreState(
            favorites_to_evolve=FAVORITES_TO_EVOLVE,
            products=products,
        )

    async def favorite_product(self, product_id: str) -> FavoriteResult:
        """Add a favorite to a product and return result."""
        logger.info(f"Favoriting product {product_id}")

        product: Product | None = await self.get_product(product_id)
        if product is None:
            return FavoriteResult(
                success=False,
                product=None,
                message=f"Product {product_id} not found",
                ready_to_evolve=False,
            )

        product.favorites += 1
        await self.update_product(product)

        ready_to_evolve = product.favorites >= FAVORITES_TO_EVOLVE

        return FavoriteResult(
            product=product,
            message=f"Favorited {product.name} (v{product.version}) - {product.favorites}/{FAVORITES_TO_EVOLVE}",
            ready_to_evolve=ready_to_evolve,
        )

    async def evolve(self, ctx: Context, product_id: str) -> EvolutionResponse:
        """Evolve a specific product into a new version.

        Args:
            ctx: FastMCP context (injected automatically).
            product_id: ID of the product to evolve.
        """
        logger.info(f"Evolving product {product_id}")

        product = await self.get_product(product_id)
        if product is None:
            return EvolutionResponse(success=False, message=f"Product {product_id} not found")

        if product.favorites < FAVORITES_TO_EVOLVE:
            return EvolutionResponse(
                success=False,
                message=f"{product.name} needs {FAVORITES_TO_EVOLVE - product.favorites} more favorites to evolve",
            )

        try:
            evolution = await self._generate_evolution(ctx, product)
        except Exception as e:
            return EvolutionResponse(success=False, message=str(e))

        evolved = await self.apply_evolution(product, evolution)

        return EvolutionResponse(
            success=True,
            message=f"{product.name} evolved into {evolved.name}!",
            evolved_from=product,
            evolved_to=evolved,
            evolution_note=evolution.evolution_note,
        )

    async def _generate_evolution(self, ctx: Context, product: Product) -> EvolutionResult:
        """Use LLM via FastMCP sampling to generate an evolved version."""
        prompt = f"""You are evolving a product for a comedic shopping channel called EVOLVE-O-MART.

The product to evolve is:
- Name: {product.name}
- Version: {product.version}
- Tagline: {product.tagline}
- Description: {product.description}

Generate an EVOLVED version that adds one absurd new feature.
The product should get progressively more ridiculous with each evolution.
You can subtract features (to prevent bloat) but you must provide an absurd reason for the removal.

Make it funny but not crude. Appropriate for a family-friendly audience. Parody "as seen on TV" products. Not too corny."""

        result = await ctx.sample(
            messages=prompt,
            result_type=EvolutionResult,
            max_tokens=MAX_EVOLUTION_TOKENS,
        )
        return result.result

    async def apply_evolution(self, product: Product, evolution: EvolutionResult) -> Product:
        """Apply evolution results: create new product version, reset its favorites."""
        metadata = await self.get_metadata()

        now = datetime.now(UTC).isoformat()
        evolved = Product(
            id=_generate_product_id(),
            name=evolution.new_name,
            tagline=evolution.new_tagline,
            description=evolution.new_description,
            ascii_art=evolution.new_ascii_art,
            version=product.version + 1,
            favorites=0,
            parent_id=product.id,
            created_at=now,
        )

        await self.update_product(evolved)

        # Replace old product with evolved in the list (keep others unchanged)
        metadata.product_ids = [evolved.id if pid == product.id else pid for pid in metadata.product_ids]
        await self.update_metadata(metadata)

        return evolved

    # ============ Lifecycle ============

    async def reset(self) -> tuple[StoreMetadata, list[Product]]:
        """Reset store to initial state."""
        metadata = await self.get_metadata()
        for product_id in metadata.product_ids:
            _ = await self.delete_product(product_id)
        self._initialized = False
        return await self.initialize()

    # ============ MCP Tool Methods ============

    async def tool_reset_store(self) -> ResetResult:
        """Reset the store to initial state."""
        _, products = await self.reset()
        return ResetResult(
            message="Store reset to initial state",
            products=[p.name for p in products],
        )

    # ============ MCP Registration ============

    def add_tools_to_server(self, server: FastMCP) -> None:
        """Register store operations as MCP tools."""
        _ = server.add_tool(Tool.from_function(fn=self.get_state, name="get_store_state"))
        _ = server.add_tool(Tool.from_function(fn=self.favorite_product, name="favorite_product"))
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
            return json.dumps([p.model_dump() for p in products])

        _ = server.add_resource(Resource.from_function(fn=get_state_json, uri="store://state"))
        _ = server.add_resource(Resource.from_function(fn=get_products_json, uri="store://products"))
