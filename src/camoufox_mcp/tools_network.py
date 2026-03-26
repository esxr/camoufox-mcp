"""Network routing tools for intercepting and modifying requests."""

from .browser import RouteInfo
from . import mcp, manager


@mcp.tool()
async def browser_route(
    pattern: str,
    status: int | None = None,
    body: str | None = None,
    contentType: str | None = None,
    headers: list[str] | None = None,
    removeHeaders: str | None = None,
) -> str:
    """Intercept requests matching a URL pattern and fulfill or modify them.

    - pattern: glob or regex to match request URLs
    - status/body/contentType: fulfill the request with a synthetic response
    - headers: list of "Name: Value" strings to add to the response
    - removeHeaders: comma-separated header names to strip from the response
    """
    try:
        await manager.ensure_browser()
        page = manager.page

        fulfilling = status is not None or body is not None or contentType is not None
        modifying_headers = headers is not None or removeHeaders is not None

        async def handler(route):
            if fulfilling:
                fulfill_kwargs = {}
                if status is not None:
                    fulfill_kwargs["status"] = status
                if body is not None:
                    fulfill_kwargs["body"] = body
                if contentType is not None:
                    fulfill_kwargs["content_type"] = contentType
                if headers is not None:
                    response_headers = {}
                    for h in headers:
                        if ": " in h:
                            k, v = h.split(": ", 1)
                            response_headers[k] = v
                    if response_headers:
                        fulfill_kwargs["headers"] = response_headers
                await route.fulfill(**fulfill_kwargs)
            elif modifying_headers:
                response = await route.fetch()
                resp_headers = dict(response.headers)

                # Add headers
                if headers is not None:
                    for h in headers:
                        if ": " in h:
                            k, v = h.split(": ", 1)
                            resp_headers[k] = v

                # Remove headers
                if removeHeaders is not None:
                    for name in removeHeaders.split(","):
                        name = name.strip()
                        # Case-insensitive removal
                        keys_to_remove = [k for k in resp_headers if k.lower() == name.lower()]
                        for k in keys_to_remove:
                            del resp_headers[k]

                await route.fulfill(
                    status=response.status,
                    headers=resp_headers,
                    body=await response.body(),
                )
            else:
                await route.continue_()

        await page.route(pattern, handler)
        manager._routes.append(RouteInfo(pattern=pattern, handler=handler))

        parts = [f"Route registered for pattern '{pattern}'"]
        if fulfilling:
            parts.append(f"(fulfill: status={status}, body={'<set>' if body else 'none'}, contentType={contentType})")
        if modifying_headers:
            if headers:
                parts.append(f"(add headers: {len(headers)})")
            if removeHeaders:
                parts.append(f"(remove headers: {removeHeaders})")
        return " ".join(parts)
    except Exception as e:
        return f"Error creating route: {e}"


@mcp.tool()
async def browser_route_list() -> str:
    """List all active route patterns."""
    try:
        await manager.ensure_browser()
        if not manager._routes:
            return "No active routes."
        lines = [f"Active routes ({len(manager._routes)}):"]
        for i, route_info in enumerate(manager._routes):
            lines.append(f"  {i + 1}. {route_info.pattern}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing routes: {e}"


@mcp.tool()
async def browser_unroute(pattern: str | None = None) -> str:
    """Remove route handlers. If pattern is given, remove that specific route. Otherwise remove all routes."""
    try:
        await manager.ensure_browser()
        page = manager.page

        if pattern is not None:
            matching = [r for r in manager._routes if r.pattern == pattern]
            if not matching:
                return f"No route found for pattern '{pattern}'"
            for route_info in matching:
                await page.unroute(pattern, route_info.handler)
            manager._routes = [r for r in manager._routes if r.pattern != pattern]
            return f"Route for pattern '{pattern}' removed."
        else:
            for route_info in manager._routes:
                await page.unroute(route_info.pattern, route_info.handler)
            count = len(manager._routes)
            manager._routes.clear()
            return f"All routes removed ({count} total)."
    except Exception as e:
        return f"Error removing route: {e}"
