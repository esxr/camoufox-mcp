"""Camoufox MCP Server — stealth browser automation via MCP."""

import argparse
import os

from . import mcp, manager


def main():
    parser = argparse.ArgumentParser(description="Camoufox MCP Server — stealth browser automation via MCP")
    parser.add_argument("--record-video", action="store_true",
                        help="Enable video recording for all pages")
    parser.add_argument("--record-video-size", type=str, default=None,
                        help="Video size as WIDTHxHEIGHT (e.g. 1280x720). Defaults to viewport size.")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directory for output files (videos, traces). Defaults to ./camoufox-output")
    args = parser.parse_args()

    # Apply CLI args with env var fallbacks
    manager.record_video = args.record_video or os.environ.get("CAMOUFOX_RECORD_VIDEO", "").lower() == "true"
    manager.output_dir = args.output_dir or os.environ.get("CAMOUFOX_OUTPUT_DIR", "./.recordings")

    if args.record_video_size:
        w, h = args.record_video_size.split("x")
        manager.record_video_size = {"width": int(w), "height": int(h)}
    elif os.environ.get("CAMOUFOX_RECORD_VIDEO_SIZE"):
        w, h = os.environ["CAMOUFOX_RECORD_VIDEO_SIZE"].split("x")
        manager.record_video_size = {"width": int(w), "height": int(h)}

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
