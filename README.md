# EVOLVE-O-MART™

> Products That Grow With You

A demo showcasing [FastMCP](https://gofastmcp.com) - products compete for favorites, and the winner evolves into something more absurd using AI.

**[Try the live demo →](https://strawgate.github.io/mcp-shopping-channel/)**

## How It Works

1. Four products compete for your favorites
2. Click "FAVORITE" to vote for a product  
3. After 20 total favorites, click "EVOLVE NOW"
4. The winning product evolves via Google Gemini AI
5. Repeat!

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
| `CORS_ORIGINS` | Allowed CORS origins (default: `*`). |
| `VOTES_TO_EVOLVE` | Favorites needed to evolve (default: `20`) |

## License

MIT
