#!/usr/bin/env python3
"""Airux Tech — lokale APK builder (EAS --local)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Optional default Expo app folder (apps/mobile with eas.json). Override with AIRUX_APK_DEFAULT_PROJECT.
_DEFAULT_ENV = os.environ.get("AIRUX_APK_DEFAULT_PROJECT", "").strip()
DEFAULT_PROJECT = Path(_DEFAULT_ENV).expanduser() if _DEFAULT_ENV else Path()
BRAND_URL = os.environ.get("AIRUX_BRAND_URL", "https://the-airux-ecosystem.vercel.app/").strip()
BUILD_START_MARKER = "▸ Build gestart "
BUILD_LOG_ERROR_PATTERN = re.compile(
    r"\berror:|build failed|failure:|build mislukt|\bexception\b",
    re.I,
)
LOG_IGNORE_PATTERNS = (
    re.compile(r"checkkotlingradlepluginconfigurationerrors", re.I),
    re.compile(r"node-domexception", re.I),
)


class AiruxTheme:
    BG = "#141210"
    BG_SOFT = "#1c1916"
    PANEL = "#252019"
    PANEL_2 = "#2f2820"
    PANEL_LIGHT = "#3a3228"
    WOOD_EDGE = "#5c4a38"
    AMBER = "#e0ad56"
    AMBER_BRIGHT = "#f5cc7a"
    AMBER_DIM = "#3d3018"
    TEAL = "#5ecfb8"
    SKY = "#7eb8ff"
    CORAL = "#f09070"
    CREAM = "#faf6f0"
    MUTED = "#b8a894"
    SUCCESS = "#72e0a0"
    ERROR = "#ff8a8a"
    LOG_BG = "#1a1612"
    LOG_FG = "#efe6da"
    LOG_ACCENT = "#f5cc7a"
    FONT_UI = ("Ubuntu", "Cantarell", "Segoe UI", "Helvetica", "sans-serif")
    FONT_MONO = ("Ubuntu Mono", "DejaVu Sans Mono", "Consolas", "monospace")
    FONT_DISPLAY = ("Ubuntu", "Segoe UI", "Helvetica", "sans-serif")


def pick_font(families: tuple[str, ...], size: int, weight: str = "normal") -> tuple:
    available = tkfont.families()
    family = next((f for f in families if f in available), "TkDefaultFont")
    return (family, size, "bold") if weight == "bold" else (family, size)


class ShimmerHeader(tk.Canvas):
    def __init__(self, master: tk.Misc, height: int = 96, **kwargs) -> None:
        super().__init__(master, height=height, highlightthickness=0, bd=0, bg=AiruxTheme.BG, **kwargs)
        self._phase = 0
        self._running = True
        self.bind("<Configure>", lambda _e: self._paint_static())
        self.after(40, self._animate)

    def _paint_static(self) -> None:
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        self.delete("static")
        for i in range(20):
            t = i / 19
            r = int(24 + t * 30)
            g = int(20 + t * 22)
            b = int(16 + t * 14)
            y0, y1 = int(h * i / 20), int(h * (i + 1) / 20) + 1
            self.create_rectangle(0, y0, w, y1, fill=f"#{r:02x}{g:02x}{b:02x}", outline="", tags="static")
        self.create_rectangle(0, h - 3, w, h - 1, fill=AiruxTheme.WOOD_EDGE, outline="", tags="static")
        self.create_rectangle(0, h - 2, int(w * 0.62), h, fill=AiruxTheme.AMBER, outline="", tags="static")
        self.create_rectangle(int(w * 0.62), h - 2, w, h, fill=AiruxTheme.TEAL, outline="", tags="static")
        self.create_text(22, 30, anchor="w", text="AIRUX", fill=AiruxTheme.CREAM, font=pick_font(AiruxTheme.FONT_DISPLAY, 24, "bold"), tags="static")
        self.create_text(22, 56, anchor="w", text="Tech · APK Builder", fill=AiruxTheme.AMBER_BRIGHT, font=pick_font(AiruxTheme.FONT_DISPLAY, 12, "bold"), tags="static")
        self.create_text(22, 78, anchor="w", text="Lokaal · Expo-kwaliteit · Geen cloud-limiet", fill=AiruxTheme.MUTED, font=pick_font(AiruxTheme.FONT_UI, 9), tags="static")
        self.create_text(w - 16, h - 14, anchor="e", text="airux.tech", fill=AiruxTheme.SKY, font=pick_font(AiruxTheme.FONT_UI, 9), tags="static")

    def _animate(self) -> None:
        if not self._running:
            return
        self.delete("shimmer")
        w, h = max(self.winfo_width(), 1), max(self.winfo_height(), 1)
        x = (self._phase % (w + 120)) - 60
        for i in range(0, 60, 6):
            t = max(0, 1 - abs(i - 30) / 30)
            c = int(180 + t * 75)
            self.create_line(x + i, 6, x + i, h - 10, fill=f"#{c:02x}{int(c*0.82):02x}{int(c*0.45):02x}", width=2, tags="shimmer")
        self._phase += 12
        self.after(50, self._animate)

    def stop(self) -> None:
        self._running = False


class PreflightTile(tk.Canvas):
    COLORS = {
        "idle": ("#2a2824", AiruxTheme.MUTED, "—", AiruxTheme.WOOD_EDGE),
        "ok": ("#1a2e24", AiruxTheme.SUCCESS, "✓", AiruxTheme.TEAL),
        "fail": ("#351c1c", AiruxTheme.ERROR, "✕", AiruxTheme.CORAL),
        "busy": (AiruxTheme.AMBER_DIM, AiruxTheme.AMBER_BRIGHT, "…", AiruxTheme.AMBER),
    }

    def __init__(self, master, title: str, check_fn, accent: str, width=138, height=64, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, bg=AiruxTheme.BG_SOFT, cursor="hand2", **kwargs)
        self.title = title
        self.check_fn = check_fn
        self.accent = accent
        self.state = "idle"
        self._hover = False
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", lambda _e: self.run_check())
        self._draw()

    def _set_hover(self, v: bool) -> None:
        self._hover = v
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        bg, fg, icon, border = self.COLORS[self.state]
        if self._hover:
            border = self.accent
        self.create_rectangle(0, 0, 4, self.winfo_reqheight(), fill=self.accent, outline="")
        self.create_rectangle(4, 2, self.winfo_reqwidth() - 2, self.winfo_reqheight() - 2, fill=bg, outline=border, width=2)
        self.create_text(14, 16, anchor="w", text=self.title, fill=AiruxTheme.CREAM, font=pick_font(AiruxTheme.FONT_UI, 9, "bold"))
        self.create_text(14, 40, anchor="w", text="Klik om te testen", fill=AiruxTheme.MUTED, font=pick_font(AiruxTheme.FONT_UI, 8))
        self.create_text(self.winfo_reqwidth() - 16, 32, text=icon, fill=fg, font=pick_font(AiruxTheme.FONT_UI, 16, "bold"))

    def set_state(self, state: str) -> None:
        self.state = state
        self._draw()

    def run_check(self) -> None:
        self.set_state("busy")
        self.after(60, lambda: self.set_state("ok" if self.check_fn()[0] else "fail"))


class AccentPanel(tk.Frame):
    def __init__(self, master, title: str, subtitle: str = "", accent: str = AiruxTheme.AMBER, **kwargs):
        super().__init__(master, bg=AiruxTheme.BG, **kwargs)
        rim = tk.Frame(self, bg=AiruxTheme.WOOD_EDGE, padx=1, pady=1)
        rim.pack(fill="both", expand=True)
        row = tk.Frame(rim, bg=AiruxTheme.PANEL)
        row.pack(fill="both", expand=True)
        tk.Frame(row, bg=accent, width=4).pack(side="left", fill="y")
        inner = tk.Frame(row, bg=AiruxTheme.PANEL, padx=14, pady=10)
        inner.pack(side="left", fill="both", expand=True)
        head = tk.Frame(inner, bg=AiruxTheme.PANEL)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text=title, bg=AiruxTheme.PANEL, fg=AiruxTheme.CREAM, font=pick_font(AiruxTheme.FONT_UI, 11, "bold")).pack(side="left")
        if subtitle:
            tk.Label(head, text=subtitle, bg=AiruxTheme.PANEL, fg=accent, font=pick_font(AiruxTheme.FONT_UI, 9)).pack(side="right")
        self.body = tk.Frame(inner, bg=AiruxTheme.PANEL)
        self.body.pack(fill="both", expand=True)


class BuildButton(tk.Canvas):
    def __init__(self, master, command, width=200, height=50, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, bg=AiruxTheme.BG_SOFT, cursor="hand2", **kwargs)
        self._command = command
        self._hover = False
        self._disabled = False
        self._animating = False
        self.bind("<Enter>", lambda _e: self._hover_on())
        self.bind("<Leave>", lambda _e: self._hover_off())
        self.bind("<Button-1>", lambda _e: self._click())
        self._draw()
        self._start_idle_anim()

    def _hover_on(self) -> None:
        if not self._disabled:
            self._hover = True
            self._draw()

    def _hover_off(self) -> None:
        self._hover = False
        self._draw()

    def _click(self) -> None:
        if not self._disabled:
            self._command()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        fill = AiruxTheme.WOOD_EDGE if self._disabled else (AiruxTheme.AMBER_BRIGHT if self._hover else AiruxTheme.AMBER)
        self.create_rectangle(0, 3, w, h, fill=AiruxTheme.AMBER_DIM, outline="")
        self.create_rectangle(0, 0, w - 2, h - 3, fill=fill, outline=AiruxTheme.TEAL if self._hover and not self._disabled else AiruxTheme.WOOD_EDGE)
        label = "Bezig…" if self._disabled else "▶  Build APK"
        fg = AiruxTheme.BG if not self._disabled else AiruxTheme.MUTED
        self.create_text((w - 2) // 2, (h - 3) // 2, text=label, fill=fg, font=pick_font(AiruxTheme.FONT_UI, 12, "bold"))

    def _start_idle_anim(self) -> None:
        if self._animating:
            return
        self._animating = True
        self._idle_tick()

    def _idle_tick(self) -> None:
        if self._disabled:
            self._animating = False
            return
        self._draw()
        self.after(180, self._idle_tick)

    def set_disabled(self, disabled: bool) -> None:
        self._disabled = disabled
        self._draw()
        if not disabled:
            self._start_idle_anim()


class StatusChip(tk.Label):
    LABELS = {
        "idle": ("● Gereed", "#2a2824", AiruxTheme.MUTED),
        "building": ("● Bouwen…", AiruxTheme.AMBER_DIM, AiruxTheme.AMBER_BRIGHT),
        "success": ("● Geslaagd", "#1a2e24", AiruxTheme.SUCCESS),
        "error": ("● Mislukt", "#351c1c", AiruxTheme.ERROR),
    }

    def __init__(self, master, **kwargs):
        t, bg, fg = self.LABELS["idle"]
        super().__init__(master, text=t, bg=bg, fg=fg, font=pick_font(AiruxTheme.FONT_UI, 10, "bold"), padx=12, pady=6, **kwargs)

    def set_state(self, state: str) -> None:
        t, bg, fg = self.LABELS.get(state, self.LABELS["idle"])
        self.configure(text=t, bg=bg, fg=fg)


class ApkBuilderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Airux Tech · APK Builder")
        self.geometry("920x820")
        self.minsize(760, 680)
        self.configure(bg=AiruxTheme.BG)

        self.project_var = tk.StringVar(value=str(DEFAULT_PROJECT) if DEFAULT_PROJECT.is_dir() else "")
        self.output_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.building = False
        self.last_apk: Path | None = None
        self.last_log_file: Path | None = None
        self._build_output_path: Path | None = None
        self._build_slug = "app"
        self._build_stamp = ""
        self.header: ShimmerHeader | None = None

        self._build_ui()
        self._seed_log()
        self.after(500, self.run_all_checks)

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=AiruxTheme.BG, padx=18, pady=14)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        self.header = ShimmerHeader(outer, height=96)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        paned = ttk.Panedwindow(outer, orient="vertical")
        paned.grid(row=1, column=0, sticky="nsew")

        top = tk.Frame(paned, bg=AiruxTheme.BG_SOFT, padx=4, pady=4)
        log_host = tk.Frame(paned, bg=AiruxTheme.BG_SOFT, padx=4, pady=4)
        paned.add(top, weight=0)
        paned.add(log_host, weight=1)

        preflight = AccentPanel(top, "Systeemcheck", "klik tegel", AiruxTheme.TEAL)
        preflight.pack(fill="x", pady=(0, 8))
        tiles = tk.Frame(preflight.body, bg=AiruxTheme.PANEL)
        tiles.pack(fill="x")
        self.tile_node = PreflightTile(tiles, "Node.js", self.check_node, AiruxTheme.SKY)
        self.tile_node.pack(side="left", padx=(0, 8))
        self.tile_android = PreflightTile(tiles, "Android SDK", self.check_android, AiruxTheme.TEAL)
        self.tile_android.pack(side="left", padx=(0, 8))
        self.tile_eas = PreflightTile(tiles, "Expo / EAS", self.check_eas, AiruxTheme.AMBER)
        self.tile_eas.pack(side="left")
        self._ghost_btn(tiles, "Alles testen", self.run_all_checks).pack(side="right")

        paths = tk.Frame(top, bg=AiruxTheme.BG_SOFT)
        paths.pack(fill="x", pady=(0, 8))
        paths.columnconfigure(0, weight=1)
        paths.columnconfigure(1, weight=1)
        proj = AccentPanel(paths, "Projectmap", "apps/mobile", AiruxTheme.AMBER)
        proj.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        out = AccentPanel(paths, "APK opslaan in", "output", AiruxTheme.SKY)
        out.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._path_row(proj.body, self.project_var, self.pick_project)
        self._path_row(out.body, self.output_var, self.pick_output)

        actions = tk.Frame(top, bg=AiruxTheme.BG_SOFT)
        actions.pack(fill="x")
        self.build_btn = BuildButton(actions, self.start_build)
        self.build_btn.pack(side="left")
        meta = tk.Frame(actions, bg=AiruxTheme.BG_SOFT)
        meta.pack(side="left", padx=(16, 0))
        self.status_chip = StatusChip(meta)
        self.status_chip.pack(anchor="w")
        btns = tk.Frame(meta, bg=AiruxTheme.BG_SOFT)
        btns.pack(anchor="w", pady=(8, 0))
        self._ghost_btn(btns, "Log wissen", self.clear_log).pack(side="left", padx=(0, 6))
        self._ghost_btn(btns, "Log exporteren", self.export_log).pack(side="left", padx=(0, 6))
        self.open_btn = self._ghost_btn(btns, "Map openen", self.open_output_folder, state="disabled")
        self.open_btn.pack(side="left", padx=(0, 6))
        self._ghost_btn(btns, "Ecosysteem", self.open_brand).pack(side="left")

        log_panel = AccentPanel(log_host, "Build-log", "live output — sleep de scheidingslijn omhoog/omlaag", AiruxTheme.CORAL)
        log_panel.pack(fill="both", expand=True)
        log_panel.body.rowconfigure(1, weight=1)
        log_panel.body.columnconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Airux.Horizontal.TProgressbar",
            troughcolor=AiruxTheme.PANEL_2,
            background=AiruxTheme.TEAL,
            lightcolor=AiruxTheme.AMBER,
            darkcolor=AiruxTheme.TEAL,
            thickness=10,
            bordercolor=AiruxTheme.WOOD_EDGE,
        )
        self.progress = ttk.Progressbar(log_panel.body, mode="indeterminate", style="Airux.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        wrap = tk.Frame(log_panel.body, bg=AiruxTheme.LOG_BG, highlightbackground=AiruxTheme.TEAL, highlightthickness=1)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        mono = pick_font(AiruxTheme.FONT_MONO, 10)
        self.log = tk.Text(
            wrap,
            wrap="none",
            height=16,
            state="disabled",
            bg=AiruxTheme.LOG_BG,
            fg=AiruxTheme.LOG_FG,
            insertbackground=AiruxTheme.AMBER,
            relief="flat",
            padx=12,
            pady=10,
            font=mono,
            selectbackground=AiruxTheme.AMBER_DIM,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.tag_configure("accent", foreground=AiruxTheme.LOG_ACCENT)
        self.log.tag_configure("error", foreground=AiruxTheme.ERROR)
        self.log.tag_configure("success", foreground=AiruxTheme.SUCCESS)
        self.log.tag_configure("info", foreground=AiruxTheme.SKY)
        yscroll = ttk.Scrollbar(wrap, command=self.log.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(wrap, orient="horizontal", command=self.log.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.log.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        tk.Label(
            outer,
            text="Airux Tech · Deel APK via Drive — niet via WhatsApp.",
            bg=AiruxTheme.BG,
            fg=AiruxTheme.MUTED,
            font=pick_font(AiruxTheme.FONT_UI, 9),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.after(100, lambda: paned.sashpos(0, 340))

    def _seed_log(self) -> None:
        self.append_log("Welkom bij Airux Tech APK Builder\n", "accent")
        self.append_log("1. Controleer de systeemtegels (groen = ok)\n", "info")
        self.append_log("2. Kies projectmap en output\n", "info")
        self.append_log("3. Klik Build APK — logs verschijnen hier\n\n", "info")

    def _path_row(self, parent, variable, browse):
        row = tk.Frame(parent, bg=AiruxTheme.PANEL)
        row.pack(fill="x")
        entry = tk.Entry(
            row,
            textvariable=variable,
            bg=AiruxTheme.PANEL_LIGHT,
            fg=AiruxTheme.CREAM,
            insertbackground=AiruxTheme.AMBER,
            relief="flat",
            font=pick_font(AiruxTheme.FONT_UI, 10),
            highlightthickness=1,
            highlightbackground=AiruxTheme.WOOD_EDGE,
            highlightcolor=AiruxTheme.TEAL,
        )
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self._ghost_btn(row, "Bladeren…", browse).pack(side="right")

    def _ghost_btn(self, parent, text, command, state="normal"):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            state=state,
            bg=AiruxTheme.PANEL_2,
            fg=AiruxTheme.CREAM,
            activebackground=AiruxTheme.PANEL_LIGHT,
            activeforeground=AiruxTheme.AMBER_BRIGHT,
            relief="flat",
            font=pick_font(AiruxTheme.FONT_UI, 9, "bold"),
            padx=11,
            pady=5,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=AiruxTheme.WOOD_EDGE,
        )

        def enter(_e):
            if str(btn["state"]) != "disabled":
                btn.configure(bg=AiruxTheme.PANEL_LIGHT, fg=AiruxTheme.TEAL)

        def leave(_e):
            if str(btn["state"]) != "disabled":
                btn.configure(bg=AiruxTheme.PANEL_2, fg=AiruxTheme.CREAM)

        btn.bind("<Enter>", enter)
        btn.bind("<Leave>", leave)
        return btn

    def check_node(self) -> tuple[bool, str]:
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=5)
            subprocess.run(["npx", "--version"], capture_output=True, check=True, timeout=8)
            return True, "ok"
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False, "fail"

    def check_android(self) -> tuple[bool, str]:
        home = os.environ.get("ANDROID_HOME") or str(Path.home() / "Android" / "Sdk")
        return Path(home).is_dir(), home

    def check_eas(self) -> tuple[bool, str]:
        try:
            r = subprocess.run(["npx", "eas-cli", "whoami"], capture_output=True, text=True, timeout=25)
            return r.returncode == 0, r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False, "fail"

    def run_all_checks(self) -> None:
        for tile, fn in ((self.tile_node, self.check_node), (self.tile_android, self.check_android), (self.tile_eas, self.check_eas)):
            tile.set_state("busy")
            ok, _ = fn()
            tile.set_state("ok" if ok else "fail")

    def open_brand(self) -> None:
        try:
            subprocess.Popen(["xdg-open", BRAND_URL])
        except FileNotFoundError:
            messagebox.showinfo("Airux Tech", BRAND_URL)

    def pick_project(self) -> None:
        path = filedialog.askdirectory(title="Kies apps/mobile")
        if path:
            self.project_var.set(path)

    def pick_output(self) -> None:
        path = filedialog.askdirectory(title="APK opslaan in")
        if path:
            self.output_var.set(path)

    def open_output_folder(self) -> None:
        target = self.last_apk.parent if self.last_apk else Path(self.output_var.get()).expanduser()
        if not target.is_dir():
            messagebox.showerror("Airux Tech", "Outputmap niet gevonden.")
            return
        try:
            subprocess.Popen(["xdg-open", str(target)])
        except FileNotFoundError:
            messagebox.showinfo("Map", str(target))

    def clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def get_log_text(self) -> str:
        return self.log.get("1.0", "end-1c")

    def _format_log_for_export(self) -> str:
        header = (
            "Airux Tech APK Builder — build log\n"
            f"Geëxporteerd: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
            + ("=" * 60)
            + "\n\n"
        )
        return header + self.get_log_text()

    def export_log(self) -> None:
        content = self.get_log_text().strip()
        if not content:
            messagebox.showinfo("Airux Tech", "Er is nog geen log om te exporteren.")
            return
        initial_dir = self._build_output_path or Path(self.output_var.get()).expanduser()
        if not initial_dir.is_dir():
            initial_dir = Path.home() / "Desktop"
        stamp = self._build_stamp or datetime.now().strftime("%Y%m%d-%H%M")
        default_name = f"airux-tech-{self._build_slug}-{stamp}.log"
        path = filedialog.asksaveasfilename(
            title="Build-log exporteren",
            initialdir=str(initial_dir),
            initialfile=default_name,
            defaultextension=".log",
            filetypes=[("Logbestand", "*.log"), ("Tekstbestand", "*.txt"), ("Alle bestanden", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self._format_log_for_export(), encoding="utf-8")
            self.last_log_file = Path(path)
            self.append_log(f"\n▸ Log geëxporteerd:\n  {path}\n", "info")
            messagebox.showinfo("Airux Tech", f"Log opgeslagen:\n\n{path}")
        except OSError as exc:
            messagebox.showerror("Airux Tech", f"Log opslaan mislukt:\n\n{exc}")

    def auto_save_build_log(self, ok: bool) -> Path | None:
        if not self._build_output_path:
            return None
        content = self.get_log_text().strip()
        if not content:
            return None
        suffix = "success" if ok else "failed"
        dest = self._build_output_path / f"airux-tech-{self._build_slug}-{self._build_stamp}.{suffix}.log"
        try:
            dest.write_text(self._format_log_for_export(), encoding="utf-8")
            self.last_log_file = dest
            return dest
        except OSError:
            return None

    @staticmethod
    def _line_ignored_for_scan(line: str) -> bool:
        lowered = line.lower()
        return any(pattern.search(lowered) for pattern in LOG_IGNORE_PATTERNS)

    @staticmethod
    def classify_log_line(line: str) -> str | None:
        lowered = line.lower()
        if ApkBuilderApp._line_ignored_for_scan(line):
            return None
        if BUILD_LOG_ERROR_PATTERN.search(lowered):
            return "error"
        if re.search(r"\bwarning:|\[run_gradlew\] w:|npm warn\b|deprecated", lowered):
            return "warning"
        if "build successful" in lowered or "✔ apk klaar" in lowered:
            return "success"
        return None

    def scan_build_log_issues(self) -> tuple[int, int]:
        text = self.log.get("1.0", "end-1c")
        if BUILD_START_MARKER in text:
            text = text[text.rfind(BUILD_START_MARKER):]
        warnings = 0
        errors = 0
        for line in text.splitlines():
            if self._line_ignored_for_scan(line):
                continue
            lowered = line.lower()
            if BUILD_LOG_ERROR_PATTERN.search(lowered):
                errors += 1
            elif re.search(r"\bwarning:|\[run_gradlew\] w:|npm warn\b|deprecated", lowered):
                warnings += 1
        return warnings, errors

    def append_log(self, text: str, tag: str | None = None) -> None:
        self.log.configure(state="normal")
        if tag:
            self.log.insert("end", text, (tag,))
        else:
            self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_build(self) -> None:
        if self.building:
            return
        project = Path(self.project_var.get().strip()).expanduser()
        if not project.is_dir() or not (project / "eas.json").is_file():
            messagebox.showerror("Airux Tech", "Kies een geldige apps/mobile map met eas.json.")
            return
        output_dir = self.output_var.get().strip()
        if not output_dir:
            output_dir = filedialog.askdirectory(title="APK opslaan in", initialdir=str(Path.home() / "Desktop"))
            if not output_dir:
                return
            self.output_var.set(output_dir)
        output_path = Path(output_dir).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)

        self.building = True
        self.last_apk = None
        self.last_log_file = None
        self._build_output_path = output_path
        self._build_slug = read_app_slug(project) or "app"
        self._build_stamp = datetime.now().strftime("%Y%m%d-%H%M")
        self.build_btn.set_disabled(True)
        self.open_btn.configure(state="disabled")
        self.status_chip.set_state("building")
        self.progress.start(10)
        self.append_log(f"\n▸ Build gestart {datetime.now():%Y-%m-%d %H:%M:%S}\n", "accent")
        self.append_log(f"  Project: {project}\n  Output:  {output_path}\n\n", "info")
        threading.Thread(target=self.run_build, args=(project, output_path), daemon=True).start()

    def run_build(self, project: Path, output_path: Path) -> None:
        env = os.environ.copy()
        android_home = env.get("ANDROID_HOME") or str(Path.home() / "Android" / "Sdk")
        if Path(android_home).is_dir():
            env["ANDROID_HOME"] = android_home
            self.ui_log(f"ANDROID_HOME={android_home}\n")
        jdk = Path.home() / ".local" / "jdk-17"
        if not env.get("JAVA_HOME") and (jdk / "bin" / "java").is_file():
            env["JAVA_HOME"] = str(jdk)
            self.ui_log(f"JAVA_HOME={jdk}\n\n")
        try:
            proc = subprocess.Popen(
                ["npx", "eas-cli", "build", "-p", "android", "--profile", "preview", "--local"],
                cwd=str(project),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self.ui_finish(False, "npx niet gevonden — installeer Node.js.")
            return
        assert proc.stdout
        for line in proc.stdout:
            tag = self.classify_log_line(line)
            self.ui_log(line, tag)
        if proc.wait() != 0:
            self.ui_finish(False, "Build mislukt — zie log.")
            return
        apk = find_newest_apk(project)
        if not apk:
            self.ui_finish(False, "Geen APK gevonden.")
            return
        stamp = self._build_stamp
        slug = self._build_slug
        dest = output_path / f"airux-tech-{slug}-{stamp}.apk"
        if dest.exists():
            dest = output_path / f"airux-tech-{slug}-{stamp}-{apk.stat().st_mtime_ns}.apk"
        shutil.copy2(apk, dest)
        self.last_apk = dest
        self.ui_log(f"\n✔ APK klaar:\n  {dest}\n", "success")
        self.ui_finish(True, f"Build geslaagd\n\n{dest}")

    def ui_log(self, text: str, tag: str | None = None) -> None:
        self.after(0, lambda: self.append_log(text, tag))

    def ui_finish(self, ok: bool, message: str) -> None:
        def done() -> None:
            self.building = False
            self.progress.stop()
            self.build_btn.set_disabled(False)
            warnings, errors = self.scan_build_log_issues()
            clean = ok and warnings == 0 and errors == 0
            if not ok:
                self.status_chip.set_state("error")
            elif warnings > 0:
                self.status_chip.configure(text=f"● Geslaagd ({warnings} waarschuwingen)", bg="#3d3018", fg=AiruxTheme.AMBER_BRIGHT)
            else:
                self.status_chip.set_state("success")
            if ok:
                self.open_btn.configure(state="normal")
            log_file = self.auto_save_build_log(ok)
            if log_file:
                self.append_log(f"\n▸ Build-log opgeslagen:\n  {log_file}\n", "info")
                message = f"{message}\n\nLog:\n{log_file}"
            if ok and warnings > 0:
                message += f"\n\n⚠ {warnings} waarschuwing(en) in de log."
            (messagebox.showinfo if clean else (messagebox.showwarning if ok else messagebox.showerror))("Airux Tech", message)

        self.after(0, done)

    def destroy(self) -> None:
        if self.header:
            self.header.stop()
        super().destroy()


def read_app_slug(project: Path) -> str | None:
    app_json = project / "app.json"
    if not app_json.is_file():
        return None
    try:
        data = json.loads(app_json.read_text(encoding="utf-8"))
        slug = data.get("expo", data).get("slug") if isinstance(data, dict) else None
        return slug.strip().lower().replace(" ", "-") if isinstance(slug, str) and slug.strip() else None
    except (OSError, ValueError, AttributeError):
        return None


def find_newest_apk(project: Path) -> Path | None:
    ignore = {"node_modules", ".gradle", "intermediates"}
    files = [p for p in project.glob("**/*.apk") if p.is_file() and not any(x in ignore for x in p.parts)]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def main() -> None:
    ApkBuilderApp().mainloop()


if __name__ == "__main__":
    main()
