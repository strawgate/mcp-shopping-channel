# Developing EVOLVE-O-MART

## Architecture

```
+---------------------------------------+
|             FRONTEND                  |
|   Alpine.js + GitHub Pages            |
|   MCP Client (JSON-RPC over HTTP)     |
+---------------------------------------+
                    |
               MCP Protocol
                    |
                    v
+---------------------------------------+
|           FastMCP Server              |
|   Tools: get_store, view, evolve      |
|   Resources: store://state            |
+-------------------+-------------------+
|  Storage          |  AI               |
|  py-key-value     |  Google Gemini    |
|  (Disk/ES)        |  (Sampling API)   |
+-------------------+-------------------+
```

## Project Structure

```
mcp-shopping-channel/
├── src/evolve_o_mart/
│   ├── server.py          # FastMCP server + CLI
│   ├── store.py           # Store class with MCP tools/resources
│   ├── models.py          # Pydantic models
│   ├── seeds.py           # Seed product data
│   ├── gemini/            # Google Gemini sampling handler
│   └── storage/           # Storage backends
├── tests/
├── index.html             # Alpine.js frontend
└── pyproject.toml
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `get_store_state` | Get all products and store state |
| `view_product(product_id)` | Record a favorite |
| `evolve(dry_run?)` | Evolve the winning product |
| `reset_store` | Reset to initial state |

## MCP Resources

| Resource | Purpose |
|----------|---------|
| `store://state` | Current store state |
| `store://products` | All products |
| `store://leader` | Current leader |

## Running Tests

```bash
uv run pytest -v
```

## CLI

```bash
# stdio mode (for MCP clients)
uv run evolve-o-mart serve

# HTTP mode (for web frontend)
uv run evolve-o-mart serve --http --port 8000
```

## Deployment

**Frontend:** GitHub Pages via `.github/workflows/deploy-pages.yml`

**Backend:** Prefect Horizon or self-hosted

The frontend endpoint can be configured via URL parameter:
```
?endpoint=https://your-backend/mcp
```

## Customizing Seed Products

Edit `src/evolve_o_mart/seeds.py`:

```python
SEED_PRODUCTS = [
    Product(
        id="prod_001",
        name="Your Product",
        tagline="Your tagline",
        description="Description",
        ascii_art="...",
    ),
]
```
