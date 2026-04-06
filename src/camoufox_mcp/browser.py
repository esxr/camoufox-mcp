"""Browser lifecycle management using Camoufox."""

import asyncio
import base64
import glob
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Dialog, FileChooser, Locator, Page


INTERACTIVE_ROLES = frozenset({
    "button", "link", "textbox", "checkbox", "radio", "combobox",
    "menuitem", "tab", "slider", "spinbutton", "switch", "searchbox",
    "option", "menuitemcheckbox", "menuitemradio", "treeitem",
    "cell", "gridcell", "row", "columnheader", "rowheader",
})

STRUCTURAL_ROLES = frozenset({
    "WebArea", "document", "main", "navigation", "banner", "contentinfo",
    "complementary", "form", "region", "article", "section", "group",
    "list", "listitem", "table", "tbody", "thead", "tfoot",
    "heading", "paragraph", "blockquote", "figure", "img", "separator",
    "toolbar", "menu", "menubar", "tablist", "tabpanel", "dialog",
    "alertdialog", "alert", "status", "log", "marquee", "timer",
    "tree", "treegrid", "grid", "progressbar", "meter",
})


@dataclass
class RefInfo:
    role: str
    name: str
    nth: int = 0  # nth occurrence of this (role, name) pair


@dataclass
class TabInfo:
    page: Page
    console_messages: list = field(default_factory=list)
    network_requests: list = field(default_factory=list)


@dataclass
class RouteInfo:
    pattern: str
    handler: Any = None


class BrowserManager:
    def __init__(self):
        # Config from env vars with defaults
        self.headless = os.environ.get("CAMOUFOX_HEADLESS", "true").lower() == "true"
        self.humanize = os.environ.get("CAMOUFOX_HUMANIZE", "true").lower() == "true"
        self.geoip = os.environ.get("CAMOUFOX_GEOIP", "false").lower() == "true"
        self.os_spoof = os.environ.get("CAMOUFOX_OS", None)  # "windows", "macos", "linux"
        self.locale = os.environ.get("CAMOUFOX_LOCALE", None)
        self.viewport_width = int(os.environ.get("CAMOUFOX_WIDTH", "1280"))
        self.viewport_height = int(os.environ.get("CAMOUFOX_HEIGHT", "720"))

        # Proxy: CAMOUFOX_PROXY=http://user:pass@host:port
        proxy_str = os.environ.get("CAMOUFOX_PROXY", None)
        self.proxy = self._parse_proxy(proxy_str) if proxy_str else None

        # Addons: comma-separated paths
        addons_str = os.environ.get("CAMOUFOX_ADDONS", "")
        self.addons = [a.strip() for a in addons_str.split(",") if a.strip()] if addons_str else []

        # State
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._tabs: List[TabInfo] = []
        self._current_tab_index: int = 0
        self._refs: Dict[str, RefInfo] = {}
        self._ref_counters: Dict[tuple, int] = {}  # (role, name) -> count seen so far
        self._dialog: Optional[Dialog] = None
        self._file_chooser: Optional[FileChooser] = None
        self._routes: List[RouteInfo] = []
        self._tracing = False
        self.record_video = False
        self.record_video_size = None  # {"width": int, "height": int} or None
        self.output_dir = "./.recordings"
        # Screenshot-based video recording state
        self._recording = False
        self._recording_task: Optional[asyncio.Task] = None
        self._recording_frames_dir: Optional[str] = None
        self._recording_video_path: Optional[str] = None
        self._recording_fps = 5  # frames per second for screenshot capture

    @staticmethod
    def _parse_proxy(proxy_str: str) -> dict:
        """Parse proxy string like http://user:pass@host:port."""
        from urllib.parse import urlparse
        p = urlparse(proxy_str)
        result = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            result["username"] = p.username
        if p.password:
            result["password"] = p.password
        return result

    @staticmethod
    def _strip_viewport_from_launch_opts(opts: Dict[str, Any]) -> None:
        """Remove viewport-locking keys from Camoufox config env vars.

        Camoufox injects fixed window.innerWidth/innerHeight values via its
        fingerprint system, which locks the rendering viewport regardless of
        Playwright's no_viewport setting. Stripping these keys lets the browser
        use the actual window dimensions for rendering.
        """
        env = opts.get("env", {})
        # Reassemble the config JSON from CAMOU_CONFIG_* chunks
        chunks = []
        idx = 1
        while f"CAMOU_CONFIG_{idx}" in env:
            chunks.append(env[f"CAMOU_CONFIG_{idx}"])
            idx += 1
        if not chunks:
            return
        config = json.loads("".join(chunks))
        # Remove viewport-locking properties
        for key in (
            "window.innerWidth",
            "window.innerHeight",
            "window.outerWidth",
            "window.outerHeight",
        ):
            config.pop(key, None)
        # Re-serialize and re-chunk
        new_json = json.dumps(config)
        chunk_size = 32767  # macOS/Linux
        # Clear old chunks
        for j in range(1, idx):
            del env[f"CAMOU_CONFIG_{j}"]
        # Write new chunks
        for j, start in enumerate(range(0, len(new_json), chunk_size), 1):
            env[f"CAMOU_CONFIG_{j}"] = new_json[start : start + chunk_size]

    async def ensure_browser(self) -> None:
        """Lazily launch the browser on first use."""
        if self._context is not None:
            return

        from playwright.async_api import async_playwright
        from camoufox.async_api import AsyncNewBrowser

        # Start playwright
        self._playwright = await async_playwright().start()

        # Build launch kwargs for camoufox
        kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "humanize": self.humanize,
        }
        if self.proxy:
            kwargs["proxy"] = self.proxy
        if self.addons:
            kwargs["addons"] = self.addons
        if self.geoip:
            kwargs["geoip"] = True
        if self.os_spoof:
            kwargs["os"] = self.os_spoof
        if self.locale:
            kwargs["locale"] = self.locale

        if not self.headless:
            # In headed mode, generate launch options and strip viewport-locking
            # properties so the browser viewport follows the actual window size.
            from camoufox.utils import launch_options as cf_launch_options
            from functools import partial

            opts = await asyncio.get_event_loop().run_in_executor(
                None, partial(cf_launch_options, **kwargs)
            )
            self._strip_viewport_from_launch_opts(opts)
            self._browser = await AsyncNewBrowser(
                self._playwright, from_options=opts
            )
        else:
            self._browser = await AsyncNewBrowser(self._playwright, **kwargs)

        # Build context kwargs — NOTE: record_video_dir is Chromium-only,
        # so we use screenshot-based recording via _start_recording() instead.
        context_kwargs: Dict[str, Any] = {}
        if self.headless:
            context_kwargs["viewport"] = {"width": self.viewport_width, "height": self.viewport_height}
        else:
            context_kwargs["no_viewport"] = True

        self._context = await self._browser.new_context(**context_kwargs)

        page = await self._context.new_page()

        tab = TabInfo(page=page)
        self._setup_page_listeners(tab)
        self._tabs.append(tab)

        # Start screenshot-based video recording if enabled
        if self.record_video:
            await self._start_recording()

    def _setup_page_listeners(self, tab: TabInfo) -> None:
        page = tab.page

        def on_console(msg):
            tab.console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": str(msg.location) if msg.location else None,
            })

        def on_request(req):
            tab.network_requests.append({
                "method": req.method,
                "url": req.url,
                "resource_type": req.resource_type,
                "status": None,
                "response_headers": None,
            })

        def on_response(resp):
            for entry in reversed(tab.network_requests):
                if entry["url"] == resp.url and entry["status"] is None:
                    entry["status"] = resp.status
                    entry["response_headers"] = dict(resp.headers) if resp.headers else None
                    break

        def on_dialog(dialog):
            self._dialog = dialog

        def on_filechooser(fc):
            self._file_chooser = fc

        page.on("console", on_console)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("dialog", on_dialog)
        page.on("filechooser", on_filechooser)

    # ── Tab management ──────────────────────────────────────────────

    @property
    def current_tab(self) -> Optional[TabInfo]:
        if not self._tabs:
            return None
        if self._current_tab_index >= len(self._tabs):
            self._current_tab_index = len(self._tabs) - 1
        return self._tabs[self._current_tab_index]

    @property
    def page(self) -> Optional[Page]:
        tab = self.current_tab
        return tab.page if tab else None

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context

    async def new_tab(self, url: Optional[str] = None) -> int:
        await self.ensure_browser()
        page = await self._context.new_page()
        if self.headless:
            await page.set_viewport_size(
                {"width": self.viewport_width, "height": self.viewport_height}
            )
        tab = TabInfo(page=page)
        self._setup_page_listeners(tab)
        self._tabs.append(tab)
        self._current_tab_index = len(self._tabs) - 1
        if url:
            await page.goto(url)
        return self._current_tab_index

    async def close_tab(self, index: Optional[int] = None) -> None:
        idx = index if index is not None else self._current_tab_index
        if 0 <= idx < len(self._tabs):
            await self._tabs[idx].page.close()
            self._tabs.pop(idx)
            if self._current_tab_index >= len(self._tabs):
                self._current_tab_index = max(0, len(self._tabs) - 1)

    def select_tab(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._current_tab_index = index

    def list_tabs(self) -> List[dict]:
        result = []
        for i, tab in enumerate(self._tabs):
            result.append({
                "index": i,
                "url": tab.page.url,
                "title": "",  # title requires await, handled in tool
                "active": i == self._current_tab_index,
            })
        return result

    # ── Snapshot system ─────────────────────────────────────────────

    async def take_snapshot(self) -> str:
        """Capture accessibility tree via aria_snapshot and assign refs to interactive elements."""
        page = self.page
        if not page:
            return "No page open."

        try:
            raw = await page.locator("body").aria_snapshot()
        except Exception as e:
            return f"Failed to capture snapshot: {e}"

        if not raw or not raw.strip():
            return f"Page URL: {page.url}\n(empty accessibility tree)"

        self._refs.clear()
        self._ref_counters.clear()
        output_lines = []

        for line in raw.splitlines():
            tagged = self._tag_interactive_line(line)
            output_lines.append(tagged)

        header = f"Page URL: {page.url}\n"
        return header + "\n".join(output_lines)

    # Roles that get a ref tag for interaction
    _INTERACTIVE_PREFIXES = (
        "button", "link", "textbox", "checkbox", "radio", "combobox",
        "menuitem", "tab ", "slider", "spinbutton", "switch", "searchbox",
        "option", "menuitemcheckbox", "menuitemradio", "treeitem",
    )

    def _tag_interactive_line(self, line: str) -> str:
        """If line represents an interactive element, assign a ref and tag it."""
        stripped = line.lstrip("- ")
        lower = stripped.lower()

        for prefix in self._INTERACTIVE_PREFIXES:
            if lower.startswith(prefix):
                # Parse role and name from aria_snapshot format:
                # e.g. 'link "Learn more"' or 'button "Submit"' or 'textbox "Email"'
                role, name = self._parse_role_name(stripped)
                key = (role.lower(), name)
                nth = self._ref_counters.get(key, 0)
                self._ref_counters[key] = nth + 1

                ref_id = f"e{len(self._refs)}"
                self._refs[ref_id] = RefInfo(role=role, name=name, nth=nth)

                # Insert ref tag preserving indentation
                indent = line[: len(line) - len(line.lstrip())]
                dash = "- " if line.lstrip().startswith("-") else ""
                return f"{indent}{dash}[{ref_id}] {stripped}"
                break

        return line

    @staticmethod
    def _parse_role_name(text: str) -> tuple:
        """Parse 'role "name"' or 'role' from aria_snapshot line."""
        # Handle formats like: link "Learn more":   or  button "Submit"  or  textbox "Email" [value=...]
        import re
        match = re.match(r'^(\w+)\s+"([^"]*)"', text)
        if match:
            return match.group(1), match.group(2)
        # Role only (no name)
        match = re.match(r'^(\w+)', text)
        if match:
            return match.group(1), ""
        return text.strip(), ""

    async def resolve_ref(self, ref: str) -> Locator:
        """Resolve a snapshot ref (e.g. 'e3') to a Playwright Locator."""
        if ref not in self._refs:
            raise ValueError(
                f"Unknown ref '{ref}'. Take a new snapshot with browser_snapshot first."
            )

        info = self._refs[ref]
        page = self.page
        if not page:
            raise RuntimeError("No page open.")

        role_name = info.role.lower()
        if info.name:
            locator = page.get_by_role(role_name, name=info.name)
        else:
            locator = page.get_by_role(role_name)

        # Handle nth occurrence for disambiguation
        if info.nth > 0:
            locator = locator.nth(info.nth)
        else:
            count = await locator.count()
            if count == 0:
                raise ValueError(
                    f"Element ref '{ref}' ({info.role} \"{info.name}\") not found on page. "
                    "Take a new snapshot — the page may have changed."
                )

        return locator

    # ── Screenshot-based video recording ─────────────────────────

    async def _start_recording(self) -> None:
        """Start a background task that periodically captures screenshots."""
        if self._recording:
            return
        # Create frames directory inside output_dir/videos/
        video_dir = os.path.join(self.output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        self._recording_frames_dir = tempfile.mkdtemp(prefix="frames_", dir=video_dir)
        video_name = f"video_{uuid.uuid4().hex[:8]}.mp4"
        self._recording_video_path = os.path.join(video_dir, video_name)
        self._recording = True
        self._recording_task = asyncio.create_task(self._capture_loop())

    async def _capture_loop(self) -> None:
        """Background loop: take a screenshot every 1/fps seconds."""
        frame_num = 0
        interval = 1.0 / self._recording_fps
        while self._recording:
            page = self.page
            if page:
                try:
                    frame_path = os.path.join(
                        self._recording_frames_dir, f"frame_{frame_num:06d}.png"
                    )
                    await page.screenshot(path=frame_path, type="png")
                    frame_num += 1
                except Exception:
                    pass  # page may be navigating / closed
            await asyncio.sleep(interval)

    async def _stop_recording(self) -> Optional[str]:
        """Stop the capture loop and encode frames to .webm with ffmpeg."""
        if not self._recording:
            return None
        self._recording = False
        if self._recording_task:
            try:
                self._recording_task.cancel()
                try:
                    await self._recording_task
                except (asyncio.CancelledError, Exception):
                    pass
            except Exception:
                pass
            self._recording_task = None

        video_path = self._recording_video_path
        frames_dir = self._recording_frames_dir

        if not frames_dir or not os.path.isdir(frames_dir):
            return None

        # Check we have frames
        frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.png")))
        if not frame_files:
            shutil.rmtree(frames_dir, ignore_errors=True)
            return None

        # Encode with ffmpeg: input pattern -> webm (VP8)
        try:
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(self._recording_fps),
                "-i", os.path.join(frames_dir, "frame_%06d.png"),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                video_path,
            ]
            proc = subprocess.run(
                cmd, capture_output=True, timeout=60
            )
            # Clean up frames
            shutil.rmtree(frames_dir, ignore_errors=True)
            self._recording_frames_dir = None

            if proc.returncode == 0 and os.path.isfile(video_path):
                return video_path
            else:
                return None
        except Exception:
            shutil.rmtree(frames_dir, ignore_errors=True)
            self._recording_frames_dir = None
            return None

    @property
    def recording_video_path(self) -> Optional[str]:
        """Return the path where the current recording will be saved."""
        return self._recording_video_path

    async def restart_with_recording(self, enable: bool, video_size: dict | None = None) -> None:
        """Restart browser context with or without video recording."""
        current_url = self.page.url if self.page else None
        await self.close()
        self.record_video = enable
        if video_size:
            self.record_video_size = video_size
        await self.ensure_browser()
        if current_url and current_url not in ("about:blank", ""):
            try:
                await self.page.goto(current_url, wait_until="domcontentloaded")
            except Exception:
                pass

    # ── Cleanup ─────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close browser and clean up."""
        self._tracing = False
        # Stop screenshot-based video recording (encodes to .webm)
        await self._stop_recording()
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._tabs.clear()
        self._refs.clear()
        self._ref_counters.clear()
        self._routes.clear()
        self._context = None
        self._browser = None
        self._playwright = None
        self._dialog = None
        self._file_chooser = None

    async def resize(self, width: int, height: int) -> None:
        self.viewport_width = width
        self.viewport_height = height
        page = self.page
        if page:
            await page.set_viewport_size({"width": width, "height": height})
