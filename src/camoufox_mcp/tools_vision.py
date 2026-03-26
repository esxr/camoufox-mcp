"""Coordinate-based mouse tools for vision/screenshot-based interaction."""

from . import mcp, manager


@mcp.tool()
async def browser_mouse_move_xy(x: int, y: int) -> str:
    """Move the mouse cursor to the given (x, y) coordinates."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.move(x, y)
        return f"Mouse moved to ({x}, {y})."
    except Exception as e:
        return f"Error moving mouse: {e}"


@mcp.tool()
async def browser_mouse_click_xy(x: int, y: int) -> str:
    """Click at the given (x, y) coordinates and return a page snapshot."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.click(x, y)
        return await manager.take_snapshot()
    except Exception as e:
        return f"Error clicking at ({x}, {y}): {e}"


@mcp.tool()
async def browser_mouse_drag_xy(startX: int, startY: int, endX: int, endY: int) -> str:
    """Drag from (startX, startY) to (endX, endY) and return a page snapshot."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.move(startX, startY)
        await page.mouse.down()
        await page.mouse.move(endX, endY)
        await page.mouse.up()
        return await manager.take_snapshot()
    except Exception as e:
        return f"Error dragging from ({startX}, {startY}) to ({endX}, {endY}): {e}"


@mcp.tool()
async def browser_mouse_down(button: str = "left") -> str:
    """Press and hold a mouse button (left, right, or middle)."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.down(button=button)
        return f"Mouse button '{button}' pressed down."
    except Exception as e:
        return f"Error pressing mouse down: {e}"


@mcp.tool()
async def browser_mouse_up(button: str = "left") -> str:
    """Release a mouse button (left, right, or middle)."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.up(button=button)
        return f"Mouse button '{button}' released."
    except Exception as e:
        return f"Error releasing mouse: {e}"


@mcp.tool()
async def browser_mouse_wheel(deltaX: int = 0, deltaY: int = 0) -> str:
    """Scroll the mouse wheel by the given delta amounts."""
    try:
        await manager.ensure_browser()
        page = manager.page
        await page.mouse.wheel(delta_x=deltaX, delta_y=deltaY)
        return f"Mouse wheel scrolled (deltaX={deltaX}, deltaY={deltaY})."
    except Exception as e:
        return f"Error scrolling mouse wheel: {e}"
