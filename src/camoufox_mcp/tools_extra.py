"""DevTools, PDF, and testing/verification tools."""

import shutil
import tempfile

from . import mcp, manager


# ---------------------------------------------------------------------------
# DevTools: Tracing
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_start_tracing() -> str:
    """Start recording a Playwright trace (screenshots + snapshots)."""
    try:
        await manager.ensure_browser()
        await manager.context.tracing.start(screenshots=True, snapshots=True)
        manager._tracing = True
        return "Tracing started."
    except Exception as e:
        return f"Error starting tracing: {e}"


@mcp.tool()
async def browser_stop_tracing() -> str:
    """Stop recording and save the trace file. Returns the path to the trace."""
    try:
        await manager.ensure_browser()
        if not manager._tracing:
            return "Tracing is not currently active."
        trace_file = tempfile.mktemp(suffix=".zip", prefix="trace_")
        await manager.context.tracing.stop(path=trace_file)
        manager._tracing = False
        return f"Trace saved to: {trace_file}"
    except Exception as e:
        manager._tracing = False
        return f"Error stopping tracing: {e}"


# ---------------------------------------------------------------------------
# DevTools: Video
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_start_video(width: int | None = None, height: int | None = None) -> str:
    """Check video recording status. Video must be configured at browser launch time."""
    try:
        await manager.ensure_browser()
        page = manager.page
        if page.video:
            try:
                path = await page.video.path()
                return f"Video is being recorded at: {path}"
            except Exception:
                return "Video recording requires browser restart with video config. Set CAMOUFOX_VIDEO=true env var."
        return "Video recording requires browser restart with video config. Set CAMOUFOX_VIDEO=true env var."
    except Exception as e:
        return f"Error checking video status: {e}"


@mcp.tool()
async def browser_stop_video(filename: str | None = None) -> str:
    """Stop video recording and optionally copy to a specific filename."""
    try:
        await manager.ensure_browser()
        page = manager.page
        if not page.video:
            return "No video recording is active. Video must be configured at browser launch with CAMOUFOX_VIDEO=true."
        try:
            path = await page.video.path()
            if filename:
                shutil.copy2(str(path), filename)
                return f"Video saved to: {filename}"
            return f"Video available at: {path}"
        except Exception as e:
            return f"Error accessing video: {e}"
    except Exception as e:
        return f"Error stopping video: {e}"


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_pdf_save(filename: str | None = None) -> str:
    """Save the current page as a PDF. Note: may not be supported in Firefox/Camoufox."""
    try:
        await manager.ensure_browser()
        page = manager.page
        if filename:
            await page.pdf(path=filename)
            return f"PDF saved to: {filename}"
        else:
            pdf_path = tempfile.mktemp(suffix=".pdf", prefix="page_")
            await page.pdf(path=pdf_path)
            return f"PDF saved to: {pdf_path}"
    except Exception as e:
        msg = str(e)
        if "pdf" in msg.lower() or "not supported" in msg.lower() or "protocol error" in msg.lower():
            return f"PDF generation is not supported in this browser (Firefox/Camoufox). Error: {e}"
        return f"Error saving PDF: {e}"


# ---------------------------------------------------------------------------
# Testing / Verification tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def browser_generate_locator(element: str = "", ref: str = "") -> str:
    """Generate a human-readable Playwright locator string for the given element ref."""
    try:
        await manager.ensure_browser()
        if not ref:
            return "Error: ref parameter is required. Provide a snapshot ref like 'e3'."

        if ref not in manager._refs:
            return f"Unknown ref '{ref}'. Take a new snapshot first."

        info = manager._refs[ref]
        role = info.role.lower()
        name = info.name

        if name:
            locator_str = f'page.get_by_role("{role}", name="{name}")'
        else:
            locator_str = f'page.get_by_role("{role}")'

        if info.nth > 0:
            locator_str += f".nth({info.nth})"

        return f"Locator for [{ref}]: {locator_str}"
    except Exception as e:
        return f"Error generating locator: {e}"


@mcp.tool()
async def browser_verify_element_visible(role: str, accessibleName: str) -> str:
    """Verify that an element with the given role and accessible name is visible on the page."""
    try:
        await manager.ensure_browser()
        page = manager.page
        locator = page.get_by_role(role, name=accessibleName)
        visible = await locator.is_visible()
        if visible:
            return f'PASS: element visible — get_by_role("{role}", name="{accessibleName}")'
        else:
            return f'FAIL: element not visible — get_by_role("{role}", name="{accessibleName}")'
    except Exception as e:
        return f'FAIL: error checking visibility — get_by_role("{role}", name="{accessibleName}"): {e}'


@mcp.tool()
async def browser_verify_text_visible(text: str) -> str:
    """Verify that the given text is visible on the page."""
    try:
        await manager.ensure_browser()
        page = manager.page
        locator = page.get_by_text(text)
        count = await locator.count()
        if count == 0:
            return f'FAIL: text not found on page — "{text}"'
        visible = await locator.first.is_visible()
        if visible:
            return f'PASS: text visible — "{text}"'
        else:
            return f'FAIL: text found but not visible — "{text}"'
    except Exception as e:
        return f'FAIL: error checking text visibility — "{text}": {e}'


@mcp.tool()
async def browser_verify_list_visible(element: str = "", ref: str = "", items: list[str] | None = None) -> str:
    """Verify that a list container contains all expected item texts.

    - ref: snapshot ref for the list container element
    - items: list of expected item texts
    """
    try:
        await manager.ensure_browser()
        if items is None:
            items = []

        if not ref:
            return "Error: ref parameter is required. Provide a snapshot ref for the list container."

        container = await manager.resolve_ref(ref)

        results = []
        all_pass = True
        for item_text in items:
            item_locator = container.get_by_text(item_text)
            count = await item_locator.count()
            if count > 0:
                visible = await item_locator.first.is_visible()
                if visible:
                    results.append(f'  PASS: "{item_text}"')
                else:
                    results.append(f'  FAIL: "{item_text}" found but not visible')
                    all_pass = False
            else:
                results.append(f'  FAIL: "{item_text}" not found in container')
                all_pass = False

        status = "PASS" if all_pass else "FAIL"
        header = f"{status}: list verification [{ref}] ({len(items)} items)"
        return header + "\n" + "\n".join(results) if results else header
    except Exception as e:
        return f"FAIL: error verifying list: {e}"


@mcp.tool()
async def browser_verify_value(
    type: str,
    element: str = "",
    ref: str = "",
    value: str = "",
) -> str:
    """Verify that an element's current value matches the expected value.

    - type: one of "textbox", "checkbox", "radio", "combobox", "slider"
    - ref: snapshot ref for the element
    - value: expected value (for checkbox/radio use "true"/"false")
    """
    try:
        await manager.ensure_browser()
        if not ref:
            return "Error: ref parameter is required. Provide a snapshot ref."

        locator = await manager.resolve_ref(ref)

        if type == "textbox":
            actual = await locator.input_value()
            if actual == value:
                return f'PASS: textbox [{ref}] value is "{actual}"'
            return f'FAIL: textbox [{ref}] expected "{value}", got "{actual}"'

        elif type in ("checkbox", "radio"):
            checked = await locator.is_checked()
            actual_str = str(checked).lower()
            expected_str = value.lower()
            if actual_str == expected_str:
                return f"PASS: {type} [{ref}] checked={actual_str}"
            return f"FAIL: {type} [{ref}] expected checked={expected_str}, got checked={actual_str}"

        elif type == "combobox":
            actual = await locator.evaluate(
                """el => {
                    if (el.tagName === 'SELECT') {
                        const opt = el.options[el.selectedIndex];
                        return opt ? opt.textContent.trim() : '';
                    }
                    return el.value || el.textContent || '';
                }"""
            )
            if str(actual) == value:
                return f'PASS: combobox [{ref}] selected value is "{actual}"'
            return f'FAIL: combobox [{ref}] expected "{value}", got "{actual}"'

        elif type == "slider":
            actual = await locator.input_value()
            if actual == value:
                return f'PASS: slider [{ref}] value is "{actual}"'
            return f'FAIL: slider [{ref}] expected "{value}", got "{actual}"'

        else:
            return f"Error: unknown type '{type}'. Use one of: textbox, checkbox, radio, combobox, slider"

    except Exception as e:
        return f"FAIL: error verifying value for [{ref}]: {e}"
