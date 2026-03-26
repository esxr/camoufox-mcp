import json
from urllib.parse import urlparse

from . import mcp, manager


# ---------------------------------------------------------------------------
# Cookie tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_cookie_list(domain: str | None = None, path: str | None = None) -> str:
    """List all cookies, optionally filtered by domain and/or path."""
    try:
        await manager.ensure_browser()
        cookies = await manager.context.cookies()
        if domain is not None:
            cookies = [c for c in cookies if c.get("domain", "") == domain]
        if path is not None:
            cookies = [c for c in cookies if c.get("path", "") == path]
        return json.dumps(cookies, indent=2)
    except Exception as e:
        return f"Error listing cookies: {e}"


@mcp.tool()
async def browser_cookie_get(name: str) -> str:
    """Get a single cookie by name."""
    try:
        await manager.ensure_browser()
        cookies = await manager.context.cookies()
        for cookie in cookies:
            if cookie.get("name") == name:
                return json.dumps(cookie, indent=2)
        return "Cookie not found"
    except Exception as e:
        return f"Error getting cookie: {e}"


@mcp.tool()
async def browser_cookie_set(
    name: str,
    value: str,
    domain: str | None = None,
    path: str | None = None,
    expires: float | None = None,
    httpOnly: bool | None = None,
    secure: bool | None = None,
    sameSite: str | None = None,
) -> str:
    """Set a cookie on the current browser context."""
    try:
        await manager.ensure_browser()

        # Derive domain from current page URL if not provided
        if domain is None:
            page_url = manager.page.url
            parsed = urlparse(page_url)
            domain = parsed.hostname or ""

        cookie: dict = {"name": name, "value": value, "domain": domain}

        # Playwright requires a domain/path pair — default path to "/" if not given
        cookie["path"] = path if path is not None else "/"
        if expires is not None:
            cookie["expires"] = expires
        if httpOnly is not None:
            cookie["httpOnly"] = httpOnly
        if secure is not None:
            cookie["secure"] = secure
        if sameSite is not None:
            cookie["sameSite"] = sameSite

        await manager.context.add_cookies([cookie])
        return f"Cookie '{name}' set successfully on domain '{domain}'"
    except Exception as e:
        return f"Error setting cookie: {e}"


@mcp.tool()
async def browser_cookie_delete(name: str) -> str:
    """Delete a cookie by name."""
    try:
        await manager.ensure_browser()
        cookies = await manager.context.cookies()
        remaining = [c for c in cookies if c.get("name") != name]

        if len(remaining) == len(cookies):
            return f"Cookie '{name}' not found"

        await manager.context.clear_cookies()
        if remaining:
            await manager.context.add_cookies(remaining)

        return f"Cookie '{name}' deleted successfully"
    except Exception as e:
        return f"Error deleting cookie: {e}"


@mcp.tool()
async def browser_cookie_clear() -> str:
    """Clear all cookies from the current browser context."""
    try:
        await manager.ensure_browser()
        await manager.context.clear_cookies()
        return "All cookies cleared successfully"
    except Exception as e:
        return f"Error clearing cookies: {e}"


# ---------------------------------------------------------------------------
# Storage state tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_storage_state(filename: str | None = None) -> str:
    """Export the full browser storage state (cookies + localStorage).

    If filename is provided, write the state to that file and return a
    confirmation.  Otherwise return the state as a JSON string.
    """
    try:
        await manager.ensure_browser()
        state = await manager.context.storage_state()
        if filename:
            with open(filename, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
            return f"Storage state saved to '{filename}'"
        return json.dumps(state, indent=2)
    except Exception as e:
        return f"Error exporting storage state: {e}"


@mcp.tool()
async def browser_set_storage_state(filename: str) -> str:
    """Restore browser storage state from a file produced by browser_storage_state.

    Restores cookies and localStorage entries for all origins present in the
    state file.
    """
    try:
        await manager.ensure_browser()

        with open(filename, "r", encoding="utf-8") as fh:
            state = json.load(fh)

        # Restore cookies
        await manager.context.clear_cookies()
        cookies = state.get("cookies", [])
        if cookies:
            await manager.context.add_cookies(cookies)

        # Restore localStorage for each origin
        origins = state.get("origins", [])
        for origin in origins:
            ls_entries = origin.get("localStorage", [])
            if not ls_entries:
                continue
            # Navigate to a page on the origin so we can set localStorage
            current_url = manager.page.url
            try:
                await manager.page.evaluate(
                    "([entries]) => { for (const [k, v] of entries) { window.localStorage.setItem(k, v); } }",
                    [[entry["name"], entry["value"]] for entry in ls_entries],
                )
            except Exception:
                # If evaluate fails (e.g. about:blank), skip silently
                pass

        return f"Storage state restored from '{filename}' ({len(cookies)} cookies, {len(origins)} origins)"
    except Exception as e:
        return f"Error restoring storage state: {e}"


# ---------------------------------------------------------------------------
# localStorage tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_localstorage_list() -> str:
    """List all localStorage entries on the current page."""
    try:
        await manager.ensure_browser()
        entries = await manager.page.evaluate("() => Object.entries(window.localStorage)")
        return json.dumps(dict(entries), indent=2)
    except Exception as e:
        return f"Error listing localStorage: {e}"


@mcp.tool()
async def browser_localstorage_get(key: str) -> str:
    """Get the value of a localStorage item by key."""
    try:
        await manager.ensure_browser()
        value = await manager.page.evaluate("([k]) => window.localStorage.getItem(k)", [key])
        if value is None:
            return "Key not found"
        return value
    except Exception as e:
        return f"Error getting localStorage item: {e}"


@mcp.tool()
async def browser_localstorage_set(key: str, value: str) -> str:
    """Set a localStorage item on the current page."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate(
            "([k, v]) => window.localStorage.setItem(k, v)", [key, value]
        )
        return f"localStorage['{key}'] set successfully"
    except Exception as e:
        return f"Error setting localStorage item: {e}"


@mcp.tool()
async def browser_localstorage_delete(key: str) -> str:
    """Remove a localStorage item by key."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate(
            "([k]) => window.localStorage.removeItem(k)", [key]
        )
        return f"localStorage['{key}'] deleted successfully"
    except Exception as e:
        return f"Error deleting localStorage item: {e}"


@mcp.tool()
async def browser_localstorage_clear() -> str:
    """Clear all localStorage entries on the current page."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate("() => window.localStorage.clear()")
        return "localStorage cleared successfully"
    except Exception as e:
        return f"Error clearing localStorage: {e}"


# ---------------------------------------------------------------------------
# sessionStorage tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_sessionstorage_list() -> str:
    """List all sessionStorage entries on the current page."""
    try:
        await manager.ensure_browser()
        entries = await manager.page.evaluate("() => Object.entries(window.sessionStorage)")
        return json.dumps(dict(entries), indent=2)
    except Exception as e:
        return f"Error listing sessionStorage: {e}"


@mcp.tool()
async def browser_sessionstorage_get(key: str) -> str:
    """Get the value of a sessionStorage item by key."""
    try:
        await manager.ensure_browser()
        value = await manager.page.evaluate(
            "([k]) => window.sessionStorage.getItem(k)", [key]
        )
        if value is None:
            return "Key not found"
        return value
    except Exception as e:
        return f"Error getting sessionStorage item: {e}"


@mcp.tool()
async def browser_sessionstorage_set(key: str, value: str) -> str:
    """Set a sessionStorage item on the current page."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate(
            "([k, v]) => window.sessionStorage.setItem(k, v)", [key, value]
        )
        return f"sessionStorage['{key}'] set successfully"
    except Exception as e:
        return f"Error setting sessionStorage item: {e}"


@mcp.tool()
async def browser_sessionstorage_delete(key: str) -> str:
    """Remove a sessionStorage item by key."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate(
            "([k]) => window.sessionStorage.removeItem(k)", [key]
        )
        return f"sessionStorage['{key}'] deleted successfully"
    except Exception as e:
        return f"Error deleting sessionStorage item: {e}"


@mcp.tool()
async def browser_sessionstorage_clear() -> str:
    """Clear all sessionStorage entries on the current page."""
    try:
        await manager.ensure_browser()
        await manager.page.evaluate("() => window.sessionStorage.clear()")
        return "sessionStorage cleared successfully"
    except Exception as e:
        return f"Error clearing sessionStorage: {e}"
