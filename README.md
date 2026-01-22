# EVOLVE-O-MART™

> Products That Grow With You

A demo MCP-powered web application where products compete for views. The most-viewed product evolves into a new, more absurd version each generation.

## The Concept

Four products compete for attention. Users click to view products, and views are recorded via MCP tool calls. The winning product evolves:

- **Steam Bowl v1** → **Steam Bowl v2 (NOW WITH POTATOES)** → **Steam Bowl v3 (NOW WITH BLUETOOTH)**

The other three products stay exactly the same, waiting for their chance to win.

## Quick Start (Local Testing)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter the project
cd mcp-shopping-channel

# Install dependencies and run the HTTP server
uv run evolve-o-mart serve --http

# Open in another terminal or your browser:
open index.html
# Or serve the HTML with: python -m http.server 3000
```

The server runs at `http://127.0.0.1:8000/mcp` and the frontend points there by default.

## CLI Commands

```bash
# Start MCP server (stdio mode for MCP clients)
uv run evolve-o-mart serve

# Start HTTP server (for web frontend)
uv run evolve-o-mart serve --http --port 8000

# Check store status
uv run evolve-o-mart status

# Trigger evolution manually (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
uv run evolve-o-mart evolve

# Preview evolution without applying
uv run evolve-o-mart evolve --dry-run

# Force evolution (bypass debounce)
uv run evolve-o-mart evolve --force

# Reset store to initial state
uv run evolve-o-mart reset

# Run tests
uv run pytest -v
```

## Architecture

```
┌─────────────────────────────────┐
│  Static Frontend                │
│  (Alpine.js + HTML)             │
│  Hosted: GitHub Pages/Vercel    │
└──────────────┬──────────────────┘
               │ JSON-RPC 2.0 over HTTPS
               │ POST /mcp
               ▼
┌─────────────────────────────────┐
│  FastMCP Server                 │
│  • get_store - list products    │
│  • view_product - record view   │
│  • evolve - debounced mutation  │
│  Hosted: FastMCP Cloud / Local  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  py-key-value-aio + JSON File   │
│  In-memory + disk persistence   │
└─────────────────────────────────┘
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `get_store_state` | Get all products, current generation, and leader |
| `view_product(product_id)` | Record a favorite, returns updated product |
| `evolve(dry_run?)` | Evolve the most-favorited product |
| `reset_store` | Reset to initial seed products |

### Evolution via FastMCP Sampling

The `evolve` tool uses FastMCP's sampling API with the `AnthropicSamplingHandler` as a fallback. When the MCP client doesn't support sampling, the server falls back to calling Claude directly via the handler:

```python
from fastmcp.client.sampling.handlers.anthropic import AnthropicSamplingHandler

anthropic_handler = AnthropicSamplingHandler(
    default_model="claude-sonnet-4-20250514",
)

mcp = FastMCP(
    name="EvolvingStore",
    sampling_handler=anthropic_handler,
    sampling_handler_behavior="fallback",
)
```

Inside tools, use `ctx.sample()` for structured LLM responses:

```python
result = await ctx.sample(
    messages=prompt,
    result_type=EvolutionResult,  # Pydantic model
    max_tokens=1024,
)
```

### Debouncing

The `evolve` tool is debounced to prevent rapid repeated evolutions. By default, it won't run if called within 5 minutes of the last evolution. Configure via:

```bash
export EVOLVE_DEBOUNCE_SECONDS=300  # 5 minutes (default)
```

The CLI `--force` flag bypasses this for manual triggers.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required for evolve) | Claude API key for generating evolutions |
| `DATA_FILE` | `store_state.json` | Path to state persistence file |
| `EVOLVE_DEBOUNCE_SECONDS` | `300` | Minimum seconds between evolutions |

## Project Structure

```
mcp-shopping-channel/
├── src/
│   └── evolve_o_mart/
│       ├── __init__.py        # Package exports
│       ├── server.py          # FastMCP server + CLI
│       ├── models.py          # Pydantic models
│       ├── storage.py         # py-key-value-aio storage layer
│       └── seeds.py           # Seed product data
├── tests/
│   ├── test_models.py         # Model tests
│   ├── test_storage.py        # Storage layer tests
│   └── test_server.py         # MCP tool tests
├── index.html                 # Alpine.js frontend
├── pyproject.toml             # UV/Python project config
├── store_state.json           # State persistence (auto-created)
└── README.md                  # This file
```

## Deployment

### Option A: FastMCP Cloud (Recommended)

1. Push this repo to GitHub
2. Connect to [FastMCP Cloud](https://fastmcp.app)
3. Deploy the package
4. Update `MCP_ENDPOINT` in `index.html` to your cloud URL

### Option B: Self-Hosted

```bash
# Install dependencies
uv sync

# Run HTTP server for web frontend
uv run evolve-o-mart serve --http --host 0.0.0.0 --port 8000

# Or run stdio server for MCP clients
uv run evolve-o-mart serve
```

### Deploy Frontend

1. Update `MCP_ENDPOINT` in `index.html` to your server URL
2. Deploy to any static host:

```bash
# GitHub Pages
git subtree push --prefix . origin gh-pages

# Vercel
vercel

# Netlify
netlify deploy --prod

# Or just open index.html locally for testing
```

## Customization

### Change Seed Products

Edit `src/evolve_o_mart/seeds.py`:

```python
SEED_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Your Product",
        "tagline": "Your tagline",
        "description": "Description here",
        "ascii_art": "...",
        "version": 1,
    },
    # ... more products
]
```

Then reset the store: `uv run evolve-o-mart reset`

### Styling

The frontend uses CSS variables for easy theming:

```css
:root {
    --tv-red: #ff3c3c;
    --tv-yellow: #ffd93d;
    --tv-blue: #4dabf7;
    --tv-green: #51cf66;
    --bg-dark: #0a0a12;
    /* ... */
}
```

## How It Works

1. **Page Load**: Frontend calls `get_store` to fetch all products
2. **User Clicks "VIEW NOW"**: Frontend calls `view_product(id)` 
3. **Views Accumulate**: The product with most views gets a green "ON SALE" banner
4. **Evolution**: Call `evolve` tool (manually, via cron, or from an AI agent):
   - Finds the winner (most views)
   - Uses FastMCP sampling with Claude to generate an evolved version
   - Replaces winner with evolved product
   - Resets all view counts to 0
5. **Repeat**: New generation begins, products compete again

## Scheduled Evolution

For automated evolution, set up a cron job:

```bash
# Every hour
0 * * * * cd /path/to/mcp-shopping-channel && ANTHROPIC_API_KEY=sk-ant-... uv run evolve-o-mart evolve >> /var/log/evolve.log 2>&1
```

## License

MIT - Do whatever you want with it!
