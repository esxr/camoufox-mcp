# camoufox-mcp

[![GitHub stars](https://img.shields.io/github/stars/esxr/camoufox-mcp?style=social)](https://github.com/esxr/camoufox-mcp) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/) ![MCP Server](https://badge.mcpx.dev?type=server&features=tools 'MCP Server with Tools') ![Cloudflare Turnstile](https://img.shields.io/badge/Cloudflare_Turnstile-Passed-brightgreen?style=flat&logo=cloudflare)

Stealth browser MCP server with 58 tools for anti-detect web automation. Drop-in replacement for [@playwright/mcp](https://github.com/microsoft/playwright-mcp) — same interface, powered by [Camoufox](https://github.com/nickoala/camoufox) (anti-fingerprint Firefox).

## Quick Start

```bash
uvx camoufox-mcp-server
```

Or install from source:

```bash
git clone https://github.com/esxr/camoufox-mcp.git
cd camoufox-mcp
uv venv && uv pip install -e .
python -m camoufox fetch
```

## Usage with Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "camoufox": {
      "type": "stdio",
      "command": "uvx",
      "args": ["camoufox-mcp-server"],
      "env": {
        "CAMOUFOX_HEADLESS": "true",
        "CAMOUFOX_HUMANIZE": "true"
      }
    }
  }
}
```

## Why Camoufox over Playwright?

Regular Playwright browsers get flagged instantly by bot detection. Camoufox wraps the same Playwright API around an anti-detect Firefox that:

- Spoofs OS/browser fingerprints per-session (canvas, WebGL, audio)
- Humanizes mouse movements with natural curves
- Passes Cloudflare Turnstile automatically
- Supports authenticated proxies with GeoIP locale matching
- Loads Firefox addons (uBlock Origin, etc.)

| | Playwright MCP | Camoufox MCP |
|---|---|---|
| Browser | Chromium | Anti-detect Firefox |
| Fingerprinting | Detectable | Spoofed per-session |
| Turnstile/hCaptcha | Blocked | Passes |
| Mouse movements | Instant teleport | Human-like curves |
| Proxy support | Basic | Auth + GeoIP matching |
| Addons | No | Firefox extensions |
| Tool count | 22 (core) | 58 (full suite) |

## Tools (58)

### Core Navigation & Interaction (23)
- `browser_navigate` — Navigate to URL
- `browser_navigate_back` — Go back
- `browser_snapshot` — Accessibility tree with interactive element refs
- `browser_click` — Click element by ref
- `browser_type` — Type text into element
- `browser_fill_form` — Fill multiple form fields at once
- `browser_select_option` — Select dropdown option
- `browser_hover` — Hover over element
- `browser_drag` — Drag between elements
- `browser_press_key` — Press keyboard key
- `browser_take_screenshot` — Screenshot (full page, element, or viewport)
- `browser_evaluate` — Execute JavaScript
- `browser_run_code` — Run arbitrary JS in page context
- `browser_tabs` — List, create, close, switch tabs
- `browser_console_messages` — Read console output
- `browser_network_requests` — Inspect network traffic
- `browser_wait_for` — Wait for time/text/element
- `browser_file_upload` — Upload files
- `browser_handle_dialog` — Accept/dismiss dialogs
- `browser_resize` — Resize viewport
- `browser_close` — Close browser
- `browser_install` — Fetch camoufox binary

### Storage (17)
- `browser_cookie_list` — List all cookies
- `browser_cookie_get` — Get cookie by name
- `browser_cookie_set` — Set a cookie
- `browser_cookie_delete` — Delete cookie by name
- `browser_cookie_clear` — Clear all cookies
- `browser_localstorage_list` — List localStorage entries
- `browser_localstorage_get` — Get localStorage value
- `browser_localstorage_set` — Set localStorage value
- `browser_localstorage_delete` — Delete localStorage key
- `browser_localstorage_clear` — Clear all localStorage
- `browser_sessionstorage_list` — List sessionStorage entries
- `browser_sessionstorage_get` — Get sessionStorage value
- `browser_sessionstorage_set` — Set sessionStorage value
- `browser_sessionstorage_delete` — Delete sessionStorage key
- `browser_sessionstorage_clear` — Clear all sessionStorage
- `browser_storage_state` — Export cookies + localStorage to JSON
- `browser_set_storage_state` — Restore from saved state

### Network Interception (3)
- `browser_route` — Intercept/modify requests matching a pattern
- `browser_route_list` — List active route rules
- `browser_unroute` — Remove route rules

### Vision / Coordinate Mouse (6)
- `browser_mouse_move_xy` — Move cursor to coordinates
- `browser_mouse_click_xy` — Click at coordinates
- `browser_mouse_drag_xy` — Drag between coordinates
- `browser_mouse_down` — Press mouse button
- `browser_mouse_up` — Release mouse button
- `browser_mouse_wheel` — Scroll via mouse wheel

### DevTools & Testing (9)
- `browser_start_tracing` — Start Playwright tracing
- `browser_stop_tracing` — Stop tracing, save to file
- `browser_start_video` — Start video recording
- `browser_stop_video` — Stop video, save to file
- `browser_pdf_save` — Save page as PDF
- `browser_generate_locator` — Get Playwright locator string for a ref
- `browser_verify_text_visible` — Assert text is visible on page
- `browser_verify_element_visible` — Assert element is visible by role
- `browser_verify_value` — Assert element has expected value

## Configuration

All via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMOUFOX_HEADLESS` | `true` | Run headless |
| `CAMOUFOX_HUMANIZE` | `true` | Human-like mouse movements |
| `CAMOUFOX_PROXY` | — | Proxy URL: `http://user:pass@host:port` |
| `CAMOUFOX_GEOIP` | `false` | Auto-match locale/timezone to proxy IP |
| `CAMOUFOX_OS` | — | Spoof OS: `windows`, `macos`, `linux` |
| `CAMOUFOX_LOCALE` | — | Browser locale (e.g. `en-US`) |
| `CAMOUFOX_ADDONS` | — | Comma-separated Firefox addon paths |
| `CAMOUFOX_WIDTH` | `1280` | Viewport width |
| `CAMOUFOX_HEIGHT` | `720` | Viewport height |

## System Requirements

- **Python** 3.10+
- **uv** (recommended) or pip
- Camoufox browser binary (auto-fetched via `python -m camoufox fetch`)

## License

MIT
