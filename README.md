# EVOLVE-O-MART™

> Products That Grow With You

A demo showcasing [FastMCP](https://gofastmcp.com) - products evolve into something more absurd using AI after you favorite them enough times.

**[Try the live demo →](https://strawgate.github.io/mcp-shopping-channel/)**

## How It Works

1. Six products compete for your favorites
2. Click "FAVORITE" to support a product  
3. After 5 favorites, a product automatically evolves via Google Gemini AI
4. Each product evolves independently!

## Quick Start

```bash
# Set your Google API key
export GOOGLE_API_KEY=your-api-key

# Run the server
uv run evolve-o-mart serve --http

# Open index.html in your browser
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google Gemini API key (required for evolution) |
| `CORS_ORIGINS` | Allowed CORS origins (default: `*`) |
| `FAVORITES_TO_EVOLVE` | Favorites needed per product (default: `5`) |

## License

MIT
