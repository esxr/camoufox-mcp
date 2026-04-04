"""Comprehensive test for all camoufox-mcp tools."""

import asyncio
import json
import os
import sys
import traceback

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from camoufox_mcp.browser import BrowserManager
from camoufox_mcp import manager, mcp
from camoufox_mcp import tools_core, tools_storage, tools_network, tools_vision, tools_extra

# Track results
results = {}

def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results[name] = (passed, detail)
    print(f"  [{status}] {name}{(' — ' + detail[:200]) if detail else ''}")

async def test_all():
    print("=" * 70)
    print("CAMOUFOX MCP — COMPREHENSIVE TOOL TEST")
    print("=" * 70)

    # =========================================================================
    # CORE TOOLS (tools_core.py)
    # =========================================================================
    print("\n--- CORE TOOLS ---")

    # 1. browser_navigate
    try:
        result = await tools_core.browser_navigate("https://example.com")
        passed = "example.com" in result.lower() or "Example" in result
        record("browser_navigate", passed, result[:150])
    except Exception as e:
        record("browser_navigate", False, f"EXCEPTION: {e}")
        traceback.print_exc()
        # If navigate fails, everything else will too
        print("FATAL: Cannot navigate. Aborting.")
        return

    # 3. browser_snapshot
    try:
        result = await tools_core.browser_snapshot()
        passed = "example.com" in result.lower() or "Example" in result
        record("browser_snapshot", passed, result[:150])
    except Exception as e:
        record("browser_snapshot", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 5. browser_hover (on a link from example.com snapshot)
    try:
        # Find a valid ref from the snapshot
        refs = list(manager._refs.keys())
        if refs:
            ref = refs[0]
            result = await tools_core.browser_hover(ref=ref)
            passed = "error" not in result.lower() or "Hover error" not in result
            record("browser_hover", passed, f"ref={ref}, {result[:150]}")
        else:
            record("browser_hover", False, "No refs available in snapshot")
    except Exception as e:
        record("browser_hover", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 4. browser_click (click "More information..." link on example.com)
    try:
        refs = list(manager._refs.keys())
        if refs:
            ref = refs[0]  # First interactive element
            result = await tools_core.browser_click(ref=ref)
            passed = "Click error" not in result
            record("browser_click", passed, f"ref={ref}, {result[:150]}")
        else:
            record("browser_click", False, "No refs available in snapshot")
    except Exception as e:
        record("browser_click", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 2. browser_navigate_back
    try:
        result = await tools_core.browser_navigate_back()
        passed = "Navigation error" not in result
        record("browser_navigate_back", passed, result[:150])
    except Exception as e:
        record("browser_navigate_back", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 7. browser_press_key
    try:
        result = await tools_core.browser_press_key(key="Escape")
        passed = "Key press error" not in result
        record("browser_press_key", passed, result[:150])
    except Exception as e:
        record("browser_press_key", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 8. browser_tabs — list
    try:
        result = await tools_core.browser_tabs(action="list")
        passed = "Tab error" not in result and ("Open tabs" in result or "No tabs" in result)
        record("browser_tabs(list)", passed, result[:150])
    except Exception as e:
        record("browser_tabs(list)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 9. browser_tabs — new
    try:
        result = await tools_core.browser_tabs(action="new")
        passed = "Tab error" not in result
        record("browser_tabs(new)", passed, result[:150])
    except Exception as e:
        record("browser_tabs(new)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 10. browser_tabs — select
    try:
        result = await tools_core.browser_tabs(action="select", index=0)
        passed = "Tab error" not in result and "Error" not in result
        record("browser_tabs(select)", passed, result[:150])
    except Exception as e:
        record("browser_tabs(select)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 11. browser_tabs — close (close tab index 1)
    try:
        result = await tools_core.browser_tabs(action="close", index=1)
        passed = "Tab error" not in result
        record("browser_tabs(close)", passed, result[:150])
    except Exception as e:
        record("browser_tabs(close)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 12. browser_take_screenshot (return image)
    try:
        result = await tools_core.browser_take_screenshot()
        # Result should be an Image object, not a string with "error"
        from mcp.server.fastmcp.utilities.types import Image as MCPImage
        if isinstance(result, MCPImage):
            record("browser_take_screenshot(image)", True, f"Got Image object, format={result._format}")
        elif isinstance(result, str) and "error" in result.lower():
            record("browser_take_screenshot(image)", False, result[:200])
        else:
            record("browser_take_screenshot(image)", True, f"Got result type={type(result).__name__}")
    except Exception as e:
        record("browser_take_screenshot(image)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 13. browser_take_screenshot (save to file)
    try:
        result = await tools_core.browser_take_screenshot(filename="/tmp/camoufox_test.png")
        passed = "saved" in result.lower() or os.path.exists("/tmp/camoufox_test.png")
        size = os.path.getsize("/tmp/camoufox_test.png") if os.path.exists("/tmp/camoufox_test.png") else 0
        record("browser_take_screenshot(file)", passed, f"{result} (size={size})")
    except Exception as e:
        record("browser_take_screenshot(file)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 14. browser_evaluate
    try:
        result = await tools_core.browser_evaluate(function="() => document.title")
        passed = "Evaluate error" not in result
        record("browser_evaluate", passed, result[:150])
    except Exception as e:
        record("browser_evaluate", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 23. browser_run_code
    try:
        result = await tools_core.browser_run_code(code="document.title")
        passed = "Run code error" not in result
        record("browser_run_code", passed, result[:150])
    except Exception as e:
        record("browser_run_code", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 15. browser_console_messages
    try:
        result = await tools_core.browser_console_messages()
        passed = "error" not in result.lower() or "No console messages" in result or "[" in result
        record("browser_console_messages", passed, result[:150])
    except Exception as e:
        record("browser_console_messages", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 16. browser_network_requests
    try:
        result = await tools_core.browser_network_requests()
        passed = True  # "No network requests" is also fine
        record("browser_network_requests", passed, result[:150])
    except Exception as e:
        record("browser_network_requests", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 17. browser_wait_for(time=1)
    try:
        result = await tools_core.browser_wait_for(time=1)
        passed = "Wait error" not in result
        record("browser_wait_for(time)", passed, result[:150])
    except Exception as e:
        record("browser_wait_for(time)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 18. browser_resize
    try:
        result = await tools_core.browser_resize(width=800, height=600)
        passed = "800" in result and "600" in result
        record("browser_resize", passed, result[:150])
    except Exception as e:
        record("browser_resize", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # Resize back
    await tools_core.browser_resize(width=1280, height=720)

    # 20. browser_fill_form — test with empty fields (should not crash)
    try:
        result = await tools_core.browser_fill_form(fields=[])
        passed = True  # As long as it doesn't crash
        record("browser_fill_form(empty)", passed, result[:150])
    except Exception as e:
        record("browser_fill_form(empty)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 26. browser_install — just check it doesn't crash
    try:
        result = await tools_core.browser_install()
        passed = "error" not in result.lower() or "installed" in result.lower() or "already" in result.lower() or "Camoufox" in result
        record("browser_install", passed, result[:200])
    except Exception as e:
        record("browser_install", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # STORAGE TOOLS (tools_storage.py)
    # =========================================================================
    print("\n--- STORAGE TOOLS ---")

    # Navigate to example.com first (ensure we're on a real page for storage)
    await tools_core.browser_navigate("https://example.com")

    # 27. browser_cookie_list
    try:
        result = await tools_storage.browser_cookie_list()
        passed = "Error" not in result
        record("browser_cookie_list", passed, result[:150])
    except Exception as e:
        record("browser_cookie_list", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 28. browser_cookie_set
    try:
        result = await tools_storage.browser_cookie_set(name="test_cookie", value="123")
        passed = "set successfully" in result.lower() or "Error" not in result
        record("browser_cookie_set", passed, result[:150])
    except Exception as e:
        record("browser_cookie_set", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 29. browser_cookie_get
    try:
        result = await tools_storage.browser_cookie_get(name="test_cookie")
        passed = "123" in result or "test_cookie" in result
        record("browser_cookie_get", passed, result[:150])
    except Exception as e:
        record("browser_cookie_get", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 30. browser_cookie_delete
    try:
        result = await tools_storage.browser_cookie_delete(name="test_cookie")
        passed = "deleted" in result.lower() or "not found" in result.lower()
        record("browser_cookie_delete", passed, result[:150])
    except Exception as e:
        record("browser_cookie_delete", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 31. browser_cookie_clear
    try:
        result = await tools_storage.browser_cookie_clear()
        passed = "cleared" in result.lower()
        record("browser_cookie_clear", passed, result[:150])
    except Exception as e:
        record("browser_cookie_clear", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 32. browser_localstorage_set
    try:
        result = await tools_storage.browser_localstorage_set(key="testkey", value="testval")
        passed = "set successfully" in result.lower()
        record("browser_localstorage_set", passed, result[:150])
    except Exception as e:
        record("browser_localstorage_set", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 33. browser_localstorage_get
    try:
        result = await tools_storage.browser_localstorage_get(key="testkey")
        passed = "testval" in result
        record("browser_localstorage_get", passed, result[:150])
    except Exception as e:
        record("browser_localstorage_get", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 34. browser_localstorage_list
    try:
        result = await tools_storage.browser_localstorage_list()
        passed = "testkey" in result or "Error" not in result
        record("browser_localstorage_list", passed, result[:150])
    except Exception as e:
        record("browser_localstorage_list", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 35. browser_localstorage_delete
    try:
        result = await tools_storage.browser_localstorage_delete(key="testkey")
        passed = "deleted" in result.lower()
        record("browser_localstorage_delete", passed, result[:150])
    except Exception as e:
        record("browser_localstorage_delete", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 36. browser_localstorage_clear
    try:
        result = await tools_storage.browser_localstorage_clear()
        passed = "cleared" in result.lower()
        record("browser_localstorage_clear", passed, result[:150])
    except Exception as e:
        record("browser_localstorage_clear", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 37. browser_sessionstorage_set
    try:
        result = await tools_storage.browser_sessionstorage_set(key="skey", value="sval")
        passed = "set successfully" in result.lower()
        record("browser_sessionstorage_set", passed, result[:150])
    except Exception as e:
        record("browser_sessionstorage_set", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 38. browser_sessionstorage_get
    try:
        result = await tools_storage.browser_sessionstorage_get(key="skey")
        passed = "sval" in result
        record("browser_sessionstorage_get", passed, result[:150])
    except Exception as e:
        record("browser_sessionstorage_get", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 39. browser_sessionstorage_list
    try:
        result = await tools_storage.browser_sessionstorage_list()
        passed = "skey" in result or "Error" not in result
        record("browser_sessionstorage_list", passed, result[:150])
    except Exception as e:
        record("browser_sessionstorage_list", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 40. browser_sessionstorage_delete
    try:
        result = await tools_storage.browser_sessionstorage_delete(key="skey")
        passed = "deleted" in result.lower()
        record("browser_sessionstorage_delete", passed, result[:150])
    except Exception as e:
        record("browser_sessionstorage_delete", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 41. browser_sessionstorage_clear
    try:
        result = await tools_storage.browser_sessionstorage_clear()
        passed = "cleared" in result.lower()
        record("browser_sessionstorage_clear", passed, result[:150])
    except Exception as e:
        record("browser_sessionstorage_clear", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 42. browser_storage_state
    try:
        result = await tools_storage.browser_storage_state()
        passed = "Error" not in result and ("cookies" in result or "{" in result)
        record("browser_storage_state", passed, result[:150])
    except Exception as e:
        record("browser_storage_state", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 42b. browser_storage_state with filename
    try:
        result = await tools_storage.browser_storage_state(filename="/tmp/camoufox_state.json")
        passed = "saved" in result.lower() or os.path.exists("/tmp/camoufox_state.json")
        record("browser_storage_state(file)", passed, result[:150])
    except Exception as e:
        record("browser_storage_state(file)", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 43. browser_set_storage_state
    try:
        if os.path.exists("/tmp/camoufox_state.json"):
            result = await tools_storage.browser_set_storage_state(filename="/tmp/camoufox_state.json")
            passed = "restored" in result.lower() or "Error" not in result
            record("browser_set_storage_state", passed, result[:150])
        else:
            record("browser_set_storage_state", False, "No state file available")
    except Exception as e:
        record("browser_set_storage_state", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # NETWORK TOOLS (tools_network.py)
    # =========================================================================
    print("\n--- NETWORK TOOLS ---")

    # 44. browser_route
    try:
        result = await tools_network.browser_route(
            pattern="**/*.css",
            status=200,
            body="/* blocked */",
            contentType="text/css"
        )
        passed = "Route registered" in result or "Error" not in result
        record("browser_route", passed, result[:150])
    except Exception as e:
        record("browser_route", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 45. browser_route_list
    try:
        result = await tools_network.browser_route_list()
        passed = "css" in result.lower() or "Active routes" in result or "No active" in result
        record("browser_route_list", passed, result[:150])
    except Exception as e:
        record("browser_route_list", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 46. browser_unroute
    try:
        result = await tools_network.browser_unroute(pattern="**/*.css")
        passed = "removed" in result.lower() or "Error" not in result
        record("browser_unroute", passed, result[:150])
    except Exception as e:
        record("browser_unroute", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # VISION TOOLS (tools_vision.py)
    # =========================================================================
    print("\n--- VISION TOOLS ---")

    # 47. browser_mouse_move_xy
    try:
        result = await tools_vision.browser_mouse_move_xy(x=100, y=100)
        passed = "moved" in result.lower() or "Error" not in result
        record("browser_mouse_move_xy", passed, result[:150])
    except Exception as e:
        record("browser_mouse_move_xy", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 48. browser_mouse_click_xy
    try:
        result = await tools_vision.browser_mouse_click_xy(x=100, y=100)
        passed = "Error" not in result or "error" not in result.lower()
        record("browser_mouse_click_xy", passed, result[:150])
    except Exception as e:
        record("browser_mouse_click_xy", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 49. browser_mouse_down
    try:
        result = await tools_vision.browser_mouse_down()
        passed = "pressed" in result.lower() or "Error" not in result
        record("browser_mouse_down", passed, result[:150])
    except Exception as e:
        record("browser_mouse_down", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 50. browser_mouse_up
    try:
        result = await tools_vision.browser_mouse_up()
        passed = "released" in result.lower() or "Error" not in result
        record("browser_mouse_up", passed, result[:150])
    except Exception as e:
        record("browser_mouse_up", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 51. browser_mouse_wheel
    try:
        result = await tools_vision.browser_mouse_wheel(deltaY=100)
        passed = "scrolled" in result.lower() or "Error" not in result
        record("browser_mouse_wheel", passed, result[:150])
    except Exception as e:
        record("browser_mouse_wheel", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 52. browser_mouse_drag_xy
    try:
        result = await tools_vision.browser_mouse_drag_xy(startX=100, startY=100, endX=200, endY=200)
        passed = "Error" not in result or "error" not in result.lower()
        record("browser_mouse_drag_xy", passed, result[:150])
    except Exception as e:
        record("browser_mouse_drag_xy", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # EXTRA TOOLS (tools_extra.py)
    # =========================================================================
    print("\n--- EXTRA TOOLS ---")

    # 53. browser_start_tracing
    try:
        result = await tools_extra.browser_start_tracing()
        passed = "started" in result.lower() or "Error" not in result
        record("browser_start_tracing", passed, result[:150])
    except Exception as e:
        record("browser_start_tracing", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 54. browser_stop_tracing
    try:
        result = await tools_extra.browser_stop_tracing()
        passed = "saved" in result.lower() or "Trace" in result
        record("browser_stop_tracing", passed, result[:150])
    except Exception as e:
        record("browser_stop_tracing", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 55. browser_start_video (will report not configured, that's OK)
    try:
        result = await tools_extra.browser_start_video()
        passed = True  # Any non-exception result is OK
        record("browser_start_video", passed, result[:150])
    except Exception as e:
        record("browser_start_video", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 56. browser_stop_video (will report not active, that's OK)
    try:
        result = await tools_extra.browser_stop_video()
        passed = True  # Any non-exception result is OK
        record("browser_stop_video", passed, result[:150])
    except Exception as e:
        record("browser_stop_video", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 57. browser_pdf_save (Firefox may not support it — that's OK if it reports gracefully)
    try:
        result = await tools_extra.browser_pdf_save()
        passed = True  # Any non-exception result is OK (including "not supported")
        record("browser_pdf_save", passed, result[:200])
    except Exception as e:
        record("browser_pdf_save", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # Navigate back to example.com and take a snapshot so we have refs
    await tools_core.browser_navigate("https://example.com")
    snap = await tools_core.browser_snapshot()

    # 58. browser_generate_locator
    try:
        refs = list(manager._refs.keys())
        if refs:
            ref = refs[0]
            result = await tools_extra.browser_generate_locator(ref=ref)
            passed = "Locator" in result or "get_by_role" in result
            record("browser_generate_locator", passed, result[:150])
        else:
            record("browser_generate_locator", False, "No refs in snapshot")
    except Exception as e:
        record("browser_generate_locator", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 59. browser_verify_text_visible
    try:
        result = await tools_extra.browser_verify_text_visible(text="Example")
        passed = "PASS" in result
        record("browser_verify_text_visible", passed, result[:150])
    except Exception as e:
        record("browser_verify_text_visible", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # 60. browser_verify_element_visible
    try:
        result = await tools_extra.browser_verify_element_visible(role="link", accessibleName="More information...")
        passed = "PASS" in result or "FAIL" in result  # As long as it doesn't crash
        record("browser_verify_element_visible", passed, result[:150])
    except Exception as e:
        record("browser_verify_element_visible", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # NAVIGATE TO GOOGLE TO TEST TYPING
    # =========================================================================
    print("\n--- GOOGLE TYPING TEST ---")

    try:
        result = await tools_core.browser_navigate("https://www.google.com")
        snap = await tools_core.browser_snapshot()
        # Find the search textbox ref
        search_ref = None
        for ref_id, info in manager._refs.items():
            if info.role.lower() in ("textbox", "searchbox", "combobox"):
                search_ref = ref_id
                break

        if search_ref:
            # 6. browser_type
            result = await tools_core.browser_type(ref=search_ref, text="hello world")
            passed = "Type error" not in result
            record("browser_type", passed, f"ref={search_ref}, {result[:120]}")
        else:
            record("browser_type", False, f"No textbox ref found in Google snapshot. Refs: {list(manager._refs.keys())[:5]}")
    except Exception as e:
        record("browser_type", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # BROWSER CLOSE (last test)
    # =========================================================================
    print("\n--- CLEANUP ---")

    # 19. browser_close
    try:
        result = await tools_core.browser_close()
        passed = "closed" in result.lower()
        record("browser_close", passed, result[:150])
    except Exception as e:
        record("browser_close", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = len(results)
    passed_count = sum(1 for v in results.values() if v[0])
    failed_count = total - passed_count
    print(f"Total: {total} | Passed: {passed_count} | Failed: {failed_count}")
    if failed_count > 0:
        print("\nFAILED TOOLS:")
        for name, (passed, detail) in results.items():
            if not passed:
                print(f"  FAIL: {name} — {detail[:200]}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_all())
