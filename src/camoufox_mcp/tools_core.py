"""Core browser tools registered on the FastMCP server."""

import asyncio
import base64
import json
from typing import Optional

from mcp.server.fastmcp.utilities.types import Image as MCPImage

from . import manager, mcp


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_navigate(url: str) -> str:
    """Navigate to a URL."""
    await manager.ensure_browser()
    if "://" not in url:
        url = "https://" + url
    page = manager.page
    try:
        await page.goto(url, wait_until="domcontentloaded")
    except Exception as e:
        return f"Navigation error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_navigate_back() -> str:
    """Go back to the previous page."""
    await manager.ensure_browser()
    page = manager.page
    try:
        await page.go_back()
    except Exception as e:
        return f"Navigation error: {e}"
    return await manager.take_snapshot()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_snapshot() -> str:
    """Capture an accessibility snapshot of the current page."""
    await manager.ensure_browser()
    return await manager.take_snapshot()


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_click(
    element: str = "",
    ref: str = "",
    doubleClick: bool = False,
    button: str = "left",
    modifiers: list[str] | None = None,
) -> str:
    """Click an element on the page."""
    await manager.ensure_browser()
    if not ref:
        return "Error: ref is required for browser_click."
    try:
        locator = await manager.resolve_ref(ref)
        opts: dict = {"button": button}
        if modifiers:
            opts["modifiers"] = modifiers
        if doubleClick:
            await locator.dblclick(**opts)
        else:
            await locator.click(**opts)
    except Exception as e:
        return f"Click error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_drag(
    startElement: str = "",
    startRef: str = "",
    endElement: str = "",
    endRef: str = "",
) -> str:
    """Drag from one element to another."""
    await manager.ensure_browser()
    if not startRef or not endRef:
        return "Error: startRef and endRef are both required."
    try:
        start_locator = await manager.resolve_ref(startRef)
        end_locator = await manager.resolve_ref(endRef)
        start_box = await start_locator.bounding_box()
        end_box = await end_locator.bounding_box()
        if not start_box or not end_box:
            return "Error: could not get bounding boxes for the elements."
        start_x = start_box["x"] + start_box["width"] / 2
        start_y = start_box["y"] + start_box["height"] / 2
        end_x = end_box["x"] + end_box["width"] / 2
        end_y = end_box["y"] + end_box["height"] / 2
        page = manager.page
        await page.mouse.move(start_x, start_y)
        await page.mouse.down()
        await page.mouse.move(end_x, end_y)
        await page.mouse.up()
    except Exception as e:
        return f"Drag error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_hover(element: str = "", ref: str = "") -> str:
    """Hover over an element on the page."""
    await manager.ensure_browser()
    if not ref:
        return "Error: ref is required for browser_hover."
    try:
        locator = await manager.resolve_ref(ref)
        await locator.hover()
    except Exception as e:
        return f"Hover error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_select_option(
    element: str = "",
    ref: str = "",
    values: list[str] = [],
) -> str:
    """Select an option in a dropdown."""
    await manager.ensure_browser()
    if not ref:
        return "Error: ref is required for browser_select_option."
    try:
        locator = await manager.resolve_ref(ref)
        await locator.select_option(values)
    except Exception as e:
        return f"Select option error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_fill_form(fields: list[dict]) -> str:
    """Fill out a form with multiple fields at once.

    Each field dict has: name, type, ref, value.
    Supported types: textbox, checkbox, radio, combobox, slider.
    """
    await manager.ensure_browser()
    errors = []
    for field in fields:
        field_type = field.get("type", "textbox")
        field_ref = field.get("ref", "")
        field_value = field.get("value", "")
        field_name = field.get("name", "")
        if not field_ref:
            errors.append(f"Missing ref for field '{field_name}'.")
            continue
        try:
            locator = await manager.resolve_ref(field_ref)
            if field_type == "textbox":
                await locator.fill(field_value)
            elif field_type == "checkbox":
                await locator.set_checked(field_value.lower() == "true")
            elif field_type == "radio":
                await locator.check()
            elif field_type == "combobox":
                await locator.select_option(field_value)
            elif field_type == "slider":
                await locator.fill(field_value)
            else:
                errors.append(f"Unknown field type '{field_type}' for '{field_name}'.")
        except Exception as e:
            errors.append(f"Error filling '{field_name}': {e}")
    snapshot = await manager.take_snapshot()
    if errors:
        return "Errors:\n" + "\n".join(errors) + "\n\n" + snapshot
    return snapshot


# ---------------------------------------------------------------------------
# Typing / Keyboard
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_type(
    element: str = "",
    ref: str = "",
    text: str = "",
    submit: bool = False,
    slowly: bool = False,
) -> str:
    """Type text into an input field."""
    await manager.ensure_browser()
    if not ref:
        return "Error: ref is required for browser_type."
    try:
        locator = await manager.resolve_ref(ref)
        if slowly:
            await locator.press_sequentially(text, delay=100)
        else:
            await locator.fill(text)
        if submit:
            await locator.press("Enter")
    except Exception as e:
        return f"Type error: {e}"
    return await manager.take_snapshot()


@mcp.tool()
async def browser_press_key(key: str) -> str:
    """Press a keyboard key or key combination."""
    await manager.ensure_browser()
    page = manager.page
    try:
        await page.keyboard.press(key)
    except Exception as e:
        return f"Key press error: {e}"
    return await manager.take_snapshot()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_tabs(
    action: str = "list",
    index: int | None = None,
) -> str:
    """Manage browser tabs (list, new, close, select)."""
    await manager.ensure_browser()
    try:
        if action == "list":
            tabs = manager.list_tabs()
            lines = []
            for t in tabs:
                page_obj = manager._tabs[t["index"]].page
                try:
                    title = await page_obj.title()
                except Exception:
                    title = ""
                active_marker = " (active)" if t["active"] else ""
                lines.append(f"[{t['index']}]{active_marker} {title} — {t['url']}")
            return "Open tabs:\n" + "\n".join(lines) if lines else "No tabs open."
        elif action == "new":
            idx = await manager.new_tab()
            return await manager.take_snapshot()
        elif action == "close":
            await manager.close_tab(index)
            tabs = manager.list_tabs()
            if not tabs:
                return "All tabs closed."
            return await manager.take_snapshot()
        elif action == "select":
            if index is None:
                return "Error: index is required for select action."
            manager.select_tab(index)
            return await manager.take_snapshot()
        else:
            return f"Unknown tab action: {action}"
    except Exception as e:
        return f"Tab error: {e}"


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_take_screenshot(
    type: str = "png",
    filename: str | None = None,
    element: str | None = None,
    ref: str | None = None,
    fullPage: bool = False,
):
    """Take a screenshot of the current page or a specific element."""
    await manager.ensure_browser()
    page = manager.page
    screenshot_type = "jpeg" if type.lower() in ("jpg", "jpeg") else "png"
    try:
        if ref:
            locator = await manager.resolve_ref(ref)
            screenshot_bytes = await locator.screenshot(type=screenshot_type)
        elif fullPage:
            screenshot_bytes = await page.screenshot(full_page=True, type=screenshot_type)
        else:
            screenshot_bytes = await page.screenshot(type=screenshot_type)

        if filename:
            with open(filename, "wb") as f:
                f.write(screenshot_bytes)
            return f"Screenshot saved to {filename}"

        return MCPImage(data=screenshot_bytes, format=screenshot_type)
    except Exception as e:
        return f"Screenshot error: {e}"


# ---------------------------------------------------------------------------
# JavaScript evaluation
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_evaluate(
    function: str,
    element: str | None = None,
    ref: str | None = None,
) -> str:
    """Execute JavaScript in the browser console."""
    await manager.ensure_browser()
    try:
        if ref:
            locator = await manager.resolve_ref(ref)
            result = await locator.evaluate(function)
        else:
            page = manager.page
            result = await page.evaluate(function)
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        return f"Evaluate error: {e}"


@mcp.tool()
async def browser_run_code(code: str) -> str:
    """Execute JavaScript code in the browser."""
    await manager.ensure_browser()
    page = manager.page
    try:
        result = await page.evaluate(code)
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        return f"Run code error: {e}"


# ---------------------------------------------------------------------------
# Console / Network
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_console_messages(level: str | None = None) -> str:
    """Retrieve console messages from the current page."""
    await manager.ensure_browser()
    tab = manager.current_tab
    if not tab:
        return "No active tab."
    messages = tab.console_messages
    if level:
        level_lower = level.lower()
        if level_lower == "error":
            messages = [m for m in messages if m["type"] == "error"]
        elif level_lower == "warning":
            messages = [m for m in messages if m["type"] == "warning"]
        elif level_lower == "info":
            messages = [m for m in messages if m["type"] in ("info", "log", "debug")]
        elif level_lower == "debug":
            messages = [m for m in messages if m["type"] == "debug"]
        else:
            messages = [m for m in messages if m["type"] == level_lower]
    if not messages:
        return "No console messages."
    lines = []
    for m in messages:
        lines.append(f"[{m['type']}] {m['text']}")
    return "\n".join(lines)


@mcp.tool()
async def browser_network_requests(includeStatic: bool = False) -> str:
    """Retrieve network requests from the current page."""
    await manager.ensure_browser()
    tab = manager.current_tab
    if not tab:
        return "No active tab."
    requests = tab.network_requests
    if not includeStatic:
        static_types = {"image", "stylesheet", "font", "media"}
        requests = [r for r in requests if r.get("resource_type") not in static_types]
    if not requests:
        return "No network requests."
    lines = []
    for r in requests:
        status = r.get("status") or "pending"
        lines.append(f"[{r['method']}] {status} {r['url']} ({r.get('resource_type', '')})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wait
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_wait_for(
    time: float | None = None,
    text: str | None = None,
    textGone: str | None = None,
) -> str:
    """Wait for a specified time, text to appear, or text to disappear."""
    if time is None and text is None and textGone is None:
        return "Error: at least one of time, text, or textGone is required."
    await manager.ensure_browser()
    page = manager.page
    try:
        if time is not None:
            await asyncio.sleep(min(time, 30))
        if text is not None:
            await page.wait_for_selector(f"text={text}", timeout=30000)
        if textGone is not None:
            await page.wait_for_selector(
                f"text={textGone}", state="hidden", timeout=30000
            )
    except Exception as e:
        return f"Wait error: {e}"
    return await manager.take_snapshot()


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_file_upload(paths: list[str] | None = None) -> str:
    """Upload files via a file chooser dialog."""
    await manager.ensure_browser()
    file_chooser = manager._file_chooser
    if not file_chooser:
        return "Error: no file chooser dialog is active. Trigger a file input first."
    try:
        if paths:
            await file_chooser.set_files(paths)
        else:
            await file_chooser.set_files([])
        manager._file_chooser = None
    except Exception as e:
        manager._file_chooser = None
        return f"File upload error: {e}"
    return await manager.take_snapshot()


# ---------------------------------------------------------------------------
# Dialog handling
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_handle_dialog(
    accept: bool,
    promptText: str | None = None,
) -> str:
    """Handle a browser dialog (alert, confirm, prompt)."""
    dialog = manager._dialog
    if not dialog:
        return "Error: no dialog is currently active."
    dialog_type = dialog.type
    dialog_message = dialog.message
    try:
        if accept:
            if promptText is not None and dialog_type == "prompt":
                await dialog.accept(promptText)
            else:
                await dialog.accept()
        else:
            await dialog.dismiss()
        manager._dialog = None
    except Exception as e:
        manager._dialog = None
        return f"Dialog error: {e}"
    action = "accepted" if accept else "dismissed"
    return f"Dialog ({dialog_type}) \"{dialog_message}\" was {action}."


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@mcp.tool()
async def browser_close() -> str:
    """Close the browser."""
    await manager.close()
    return "Browser closed."


@mcp.tool()
async def browser_resize(width: int, height: int) -> str:
    """Resize the browser viewport."""
    await manager.ensure_browser()
    await manager.resize(width, height)
    return f"Browser resized to {width}x{height}."


@mcp.tool()
async def browser_install() -> str:
    """Install or update the Camoufox browser binary."""
    try:
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "camoufox", "fetch",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")
        if process.returncode == 0:
            return f"Camoufox installed successfully.\n{output}"
        else:
            return f"Camoufox install failed (exit code {process.returncode}).\n{output}"
    except Exception as e:
        return f"Install error: {e}"
