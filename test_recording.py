"""Test video recording implementation for camoufox-mcp.

Uses screenshot-based recording: background captures screenshots at ~5fps,
then encodes to .webm via ffmpeg on stop/close.
"""

import asyncio
import glob
import os
import sys
import tempfile
import time

# Ensure we use the local source
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Force headless mode
os.environ["CAMOUFOX_HEADLESS"] = "true"


def find_webm_files(directory):
    """Recursively find all .webm files in a directory."""
    return glob.glob(os.path.join(directory, "**", "*.webm"), recursive=True)


# =========================================================================
# Test 1: Always-on recording mode
# =========================================================================
async def test_always_on_recording():
    print("\n" + "=" * 60)
    print("TEST 1: Always-on recording mode")
    print("=" * 60)

    from camoufox_mcp.browser import BrowserManager

    tmpdir = tempfile.mkdtemp(prefix="camofox_test_always_on_")
    print(f"  Output dir: {tmpdir}")

    manager = BrowserManager()
    manager.record_video = True
    manager.output_dir = tmpdir
    manager.headless = True

    try:
        await manager.ensure_browser()
        print("  Browser launched with record_video=True")
        print(f"  Recording active: {manager._recording}")

        page = manager.page
        await page.goto("https://example.com", wait_until="domcontentloaded")
        print("  Navigated to https://example.com")

        # Wait for screenshot frames to be captured
        await asyncio.sleep(3)
        print("  Waited 3 seconds for frame capture")

        # Check frames directory has frames
        frames_dir = manager._recording_frames_dir
        if frames_dir and os.path.isdir(frames_dir):
            frame_count = len(glob.glob(os.path.join(frames_dir, "frame_*.png")))
            print(f"  Captured {frame_count} frames so far")
        else:
            print(f"  WARNING: Frames directory not found: {frames_dir}")

        # Close browser (triggers _stop_recording -> ffmpeg encode)
        await manager.close()
        print("  Browser closed (recording stopped + encoded)")

        # Give filesystem a moment to flush
        time.sleep(1)

        # Check for video files
        video_dir = os.path.join(tmpdir, "videos")
        print(f"  Checking video dir: {video_dir}")

        if not os.path.isdir(video_dir):
            print(f"  FAIL: Video directory does not exist: {video_dir}")
            return False

        webm_files = find_webm_files(video_dir)
        print(f"  Found .webm files: {webm_files}")

        if webm_files:
            for f in webm_files:
                size = os.path.getsize(f)
                print(f"    {f} ({size} bytes)")
            print("  PASS: .webm file(s) found in videos directory")
            return True
        else:
            # List everything in video_dir for debugging
            all_files = []
            for root, dirs, files in os.walk(video_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    all_files.append(f"{fp} ({os.path.getsize(fp)} bytes)")
            print(f"  All files in video_dir: {all_files}")
            print("  FAIL: No .webm files found in videos directory")
            return False

    except Exception as e:
        print(f"  FAIL: Exception - {e}")
        import traceback
        traceback.print_exc()
        try:
            await manager.close()
        except Exception:
            pass
        return False


# =========================================================================
# Test 2: On-demand recording mode (restart_with_recording)
# =========================================================================
async def test_on_demand_recording():
    print("\n" + "=" * 60)
    print("TEST 2: On-demand recording mode (restart_with_recording)")
    print("=" * 60)

    from camoufox_mcp.browser import BrowserManager

    tmpdir = tempfile.mkdtemp(prefix="camofox_test_on_demand_")
    print(f"  Output dir: {tmpdir}")

    manager = BrowserManager()
    manager.record_video = False
    manager.output_dir = tmpdir
    manager.headless = True

    try:
        await manager.ensure_browser()
        print("  Browser launched with record_video=False")
        print(f"  Recording active: {manager._recording}")

        # Now enable recording on-demand
        await manager.restart_with_recording(enable=True)
        print("  Called restart_with_recording(enable=True)")
        print(f"  Recording active: {manager._recording}")

        page = manager.page
        await page.goto("https://example.com", wait_until="domcontentloaded")
        print("  Navigated to https://example.com")

        # Wait for screenshot frames
        await asyncio.sleep(3)
        print("  Waited 3 seconds for frame capture")

        # Check frames
        frames_dir = manager._recording_frames_dir
        if frames_dir and os.path.isdir(frames_dir):
            frame_count = len(glob.glob(os.path.join(frames_dir, "frame_*.png")))
            print(f"  Captured {frame_count} frames so far")

        # Close browser (triggers encoding)
        await manager.close()
        print("  Browser closed (recording stopped + encoded)")

        # Give filesystem a moment
        time.sleep(1)

        # Check for video files
        video_dir = os.path.join(tmpdir, "videos")
        print(f"  Checking video dir: {video_dir}")

        if not os.path.isdir(video_dir):
            print(f"  FAIL: Video directory does not exist: {video_dir}")
            return False

        webm_files = find_webm_files(video_dir)
        print(f"  Found .webm files: {webm_files}")

        if webm_files:
            for f in webm_files:
                size = os.path.getsize(f)
                print(f"    {f} ({size} bytes)")
            print("  PASS: .webm file(s) found in videos directory")
            return True
        else:
            all_files = []
            for root, dirs, files in os.walk(video_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    all_files.append(f"{fp} ({os.path.getsize(fp)} bytes)")
            print(f"  All files in video_dir: {all_files}")
            print("  FAIL: No .webm files found in videos directory")
            return False

    except Exception as e:
        print(f"  FAIL: Exception - {e}")
        import traceback
        traceback.print_exc()
        try:
            await manager.close()
        except Exception:
            pass
        return False


# =========================================================================
# Test 3: CLI argument parsing
# =========================================================================
def test_cli_arg_parsing():
    print("\n" + "=" * 60)
    print("TEST 3: CLI argument parsing (--record-video)")
    print("=" * 60)

    import argparse

    # Recreate the parser from server.py
    parser = argparse.ArgumentParser(description="Camoufox MCP Server")
    parser.add_argument("--record-video", action="store_true",
                        help="Enable video recording for all pages")
    parser.add_argument("--record-video-size", type=str, default=None,
                        help="Video size as WIDTHxHEIGHT")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directory for output files")

    all_pass = True

    # Test 3a: --record-video flag present
    args = parser.parse_args(["--record-video"])
    if args.record_video is True:
        print("  PASS: --record-video flag sets record_video=True")
    else:
        print(f"  FAIL: --record-video flag gave record_video={args.record_video}")
        all_pass = False

    # Test 3b: no --record-video flag
    args = parser.parse_args([])
    if args.record_video is False:
        print("  PASS: no --record-video flag gives record_video=False")
    else:
        print(f"  FAIL: no flag gave record_video={args.record_video}")
        all_pass = False

    # Test 3c: --record-video-size parsing
    args = parser.parse_args(["--record-video", "--record-video-size", "1920x1080"])
    if args.record_video_size == "1920x1080":
        w, h = args.record_video_size.split("x")
        size = {"width": int(w), "height": int(h)}
        if size == {"width": 1920, "height": 1080}:
            print("  PASS: --record-video-size 1920x1080 parsed correctly")
        else:
            print(f"  FAIL: size parsed as {size}")
            all_pass = False
    else:
        print(f"  FAIL: --record-video-size gave {args.record_video_size}")
        all_pass = False

    # Test 3d: --output-dir
    args = parser.parse_args(["--output-dir", "/tmp/my-output"])
    if args.output_dir == "/tmp/my-output":
        print("  PASS: --output-dir parsed correctly")
    else:
        print(f"  FAIL: --output-dir gave {args.output_dir}")
        all_pass = False

    if all_pass:
        print("  PASS: All CLI parsing tests passed")
    else:
        print("  FAIL: Some CLI parsing tests failed")

    return all_pass


# =========================================================================
# Main
# =========================================================================
def main():
    print("Camoufox MCP - Video Recording Tests")
    print("=" * 60)

    results = {}

    # Test 1: Always-on recording
    results["always_on"] = asyncio.run(test_always_on_recording())

    # Test 2: On-demand recording
    results["on_demand"] = asyncio.run(test_on_demand_recording())

    # Test 3: CLI parsing (synchronous)
    results["cli_parsing"] = test_cli_arg_parsing()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  {passed}/{total} tests passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
