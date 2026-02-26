#!/usr/bin/env python3
"""
DiskForge — Conversor Universal de Discos Virtuais
Compatível com Windows | Python 3.8+
qemu-img.exe embutido em tools/qemu/.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import os
import sys
import queue
import time
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# ─── Constantes ─────────────────────────────────────────────────────

SCRIPT_DIR = Path(os.path.abspath(sys.argv[0])).parent
TOOLS_DIR  = SCRIPT_DIR / "tools" / "qemu"
QEMU_EXE   = TOOLS_DIR / "qemu-img.exe"

# ─── Formatos suportados ─────────────────────────────────────────────

FORMATS = {
    "raw":       {"label": "RAW / IMG",     "ext": ".img",   "star": False,
                  "desc": "Imagem setor a setor, universal e bootável"},
    "qcow2":     {"label": "QCOW2",         "ext": ".qcow2", "star": True,
                  "desc": "Formato nativo QEMU — snapshots e compressão"},
    "vmdk":      {"label": "VMDK",          "ext": ".vmdk",  "star": False,
                  "desc": "VMware / VirtualBox / QEMU"},
    "vdi":       {"label": "VDI",           "ext": ".vdi",   "star": False,
                  "desc": "VirtualBox Disk Image"},
    "vhdx":      {"label": "VHDX",          "ext": ".vhdx",  "star": False,
                  "desc": "Hyper-V (geração 2)"},
    "vpc":       {"label": "VHD / VPC",     "ext": ".vhd",   "star": False,
                  "desc": "Hyper-V legado / Virtual PC"},
    "qcow":      {"label": "QCOW",          "ext": ".qcow",  "star": False,
                  "desc": "QEMU Copy-On-Write v1 (legado)"},
    "qed":       {"label": "QED",           "ext": ".qed",   "star": False,
                  "desc": "QEMU Enhanced Disk (legado)"},
    "parallels": {"label": "Parallels HDD", "ext": ".hdd",   "star": False,
                  "desc": "Parallels Desktop para Mac"},
}

# ─── Paleta ─────────────────────────────────────────────────────────

C = {
    "bg":       "#0d0f18",
    "surface":  "#13162a",
    "surface2": "#1c2035",
    "border":   "#252a45",
    "accent":   "#4d7cfe",
    "success":  "#27c87a",
    "warning":  "#f5a623",
    "error":    "#f0445a",
    "text":     "#dde3f5",
    "text2":    "#8892b0",
    "text3":    "#4a5278",
    "gold":     "#f5c842",
}

FF_MONO  = ("Courier New", 9)
FF_SMALL = ("Segoe UI",    8)
FF_LABEL = ("Segoe UI",    9)
FF_TITLE = ("Segoe UI",   15, "bold")

# ─── Utilitários ────────────────────────────────────────────────────

def human_size(path) -> str:
    try:
        b = os.path.getsize(str(path))
        for u in ("B","KB","MB","GB","TB"):
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"
    except: return "—"

def human_time(seconds: float) -> str:
    if seconds < 0 or seconds > 86400*7: return "—"
    from datetime import timedelta
    td = timedelta(seconds=int(seconds))
    h, rem = divmod(td.seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:   return f"{h}h {m:02d}m {s:02d}s"
    if m:   return f"{m}m {s:02d}s"
    return f"{s}s"

def qemu_path() -> str:
    if QEMU_EXE.exists():
        return str(QEMU_EXE)
    if shutil.which("qemu-img"):
        return "qemu-img"
    return None

# ─── Conversor universal ─────────────────────────────────────────────

def run_qemu(args: list, log_q: queue.Queue, prog_cb, eta_cb) -> int:
    exe = qemu_path()
    if not exe:
        log_q.put(("error", "qemu-img não encontrado em tools/qemu/."))
        return -1

    cmd = [exe] + args
    log_q.put(("info", f"$ {' '.join(cmd)}"))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        start_t = time.time()

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            m = re.search(r"\((\d+(?:\.\d+)?)/100%\)", line)
            if m:
                pct = float(m.group(1))
                elapsed = time.time() - start_t
                if pct > 0:
                    remain = (elapsed / (pct / 100)) - elapsed
                    prog_cb(pct)
                    eta_cb(remain, pct)
            log_q.put(("log", line))

        proc.wait()
        rc = proc.returncode
        if rc == -1073741515:
            log_q.put(("error", "0xC0000135: DLL ausente — verifique a pasta tools/qemu/."))
        return rc

    except FileNotFoundError:
        log_q.put(("error", "qemu-img.exe não encontrado."))
        return -1
    except Exception as e:
        log_q.put(("error", str(e)))
        return -1


def conv_universal(src, dst, fmt_in, fmt_out, log_q, prog_cb, step_cb, eta_cb):
    step_cb(0)
    if not os.path.exists(src):
        log_q.put(("error", "Arquivo de origem não encontrado.")); return False
    log_q.put(("ok", f"Origem: {src}  ({human_size(src)})"))
    log_q.put(("info", f"Conversão: {fmt_in.upper()} → {fmt_out.upper()}"))
    prog_cb(2)

    step_cb(1)
    rc = run_qemu(["convert", "-p", "-f", fmt_in, "-O", fmt_out, src, dst],
                  log_q, prog_cb, eta_cb)
    if rc != 0:
        log_q.put(("error", f"Conversão falhou (código {rc})")); return False

    step_cb(2)
    log_q.put(("ok", f"Arquivo gerado: {dst}  ({human_size(dst)})"))
    prog_cb(100)
    return True


# ─── Widget: FormatPicker ────────────────────────────────────────────

class FormatPicker(tk.Frame):
    """Seletor de formato com dropdown customizado."""

    def __init__(self, parent, label_text, initial="qcow2", on_change=None, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._value     = initial
        self._on_change = on_change
        self._popup     = None

        tk.Label(self, text=label_text, font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["bg"]).pack(anchor="w", pady=(0,4))

        self._card = tk.Frame(self, bg=C["surface2"],
                              highlightthickness=1,
                              highlightbackground=C["border"],
                              cursor="hand2")
        self._card.pack(fill="x")

        inner = tk.Frame(self._card, bg=C["surface2"])
        inner.pack(fill="x", padx=10, pady=9)

        self._ext_lbl  = tk.Label(inner, text="", font=("Courier New",9,"bold"),
                                   fg=C["accent"], bg=C["surface2"], width=7, anchor="w")
        self._ext_lbl.pack(side="left")

        self._name_lbl = tk.Label(inner, text="", font=("Segoe UI",10,"bold"),
                                   fg=C["text"], bg=C["surface2"])
        self._name_lbl.pack(side="left")

        self._star_lbl = tk.Label(inner, text="", font=("Segoe UI",9),
                                   fg=C["gold"], bg=C["surface2"])
        self._star_lbl.pack(side="left", padx=(3,0))

        self._desc_lbl = tk.Label(inner, text="", font=FF_SMALL,
                                   fg=C["text3"], bg=C["surface2"])
        self._desc_lbl.pack(side="left", padx=(8,0))

        tk.Label(inner, text="▾", font=("Segoe UI",12),
                 fg=C["text3"], bg=C["surface2"]).pack(side="right")

        for w in self._card.winfo_children() + [self._card]:
            pass
        self._bind_all_children(self._card, self._toggle)

        self._refresh()

    def _bind_all_children(self, widget, fn):
        widget.bind("<Button-1>", fn)
        widget.bind("<Enter>", lambda _: self._card.config(
            highlightbackground=C["accent"]))
        widget.bind("<Leave>", lambda _: self._popup or self._card.config(
            highlightbackground=C["border"]))
        for child in widget.winfo_children():
            self._bind_all_children(child, fn)

    def _refresh(self):
        fmt = FORMATS[self._value]
        self._ext_lbl.config(text=fmt["ext"])
        self._name_lbl.config(text=fmt["label"])
        self._star_lbl.config(text="★" if fmt["star"] else "")
        self._desc_lbl.config(text=fmt["desc"])

    def get(self): return self._value
    def set(self, v):
        self._value = v; self._refresh()

    def _toggle(self, _=None):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy(); self._popup = None; return
        self._open_popup()

    def _open_popup(self):
        self.update_idletasks()
        x = self._card.winfo_rootx()
        y = self._card.winfo_rooty() + self._card.winfo_height() + 2
        w = self._card.winfo_width()
        row_h = 34

        pop = tk.Toplevel(self)
        pop.wm_overrideredirect(True)
        pop.geometry(f"{w}x{len(FORMATS)*row_h+2}+{x}+{y}")
        pop.configure(bg=C["border"])
        pop.lift()
        self._popup = pop

        wrap = tk.Frame(pop, bg=C["surface2"])
        wrap.pack(fill="both", expand=True, padx=1, pady=1)

        for key, info in FORMATS.items():
            self._make_opt(wrap, key, info, row_h, pop)

        pop.bind("<FocusOut>", lambda _: self._close_popup())
        pop.focus_set()

    def _make_opt(self, parent, key, info, row_h, pop):
        sel = key == self._value
        bg0 = C["surface"] if sel else C["surface2"]

        row = tk.Frame(parent, bg=bg0, cursor="hand2", height=row_h)
        row.pack(fill="x"); row.pack_propagate(False)

        inn = tk.Frame(row, bg=bg0)
        inn.pack(fill="both", expand=True, padx=10)

        e = tk.Label(inn, text=info["ext"], font=("Courier New",8,"bold"),
                     fg=C["accent"], bg=bg0, width=7, anchor="w")
        e.pack(side="left")
        n = tk.Label(inn, text=info["label"], font=FF_LABEL,
                     fg=C["text"] if sel else C["text2"], bg=bg0)
        n.pack(side="left")
        if info["star"]:
            tk.Label(inn, text=" ★", font=("Segoe UI",8),
                     fg=C["gold"], bg=bg0).pack(side="left")
        d = tk.Label(inn, text=info["desc"], font=FF_SMALL,
                     fg=C["text3"], bg=bg0)
        d.pack(side="right")

        all_w = [row, inn, e, n, d]

        def pick(k=key, p=pop):
            self._value = k; self._refresh()
            p.destroy(); self._popup = None
            self._card.config(highlightbackground=C["border"])
            if self._on_change: self._on_change(k)

        def hov_on(_, ws=all_w):
            for w in ws: w.config(bg=C["border"])
        def hov_off(_, ws=all_w, bg=bg0):
            for w in ws: w.config(bg=bg)

        for w in all_w:
            w.bind("<Button-1>", lambda _, f=pick: f())
            w.bind("<Enter>", hov_on)
            w.bind("<Leave>", hov_off)

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None


# ─── Widget: ProgressBar ────────────────────────────────────────────

class ProgressBar(tk.Canvas):
    def __init__(self, parent, height=7, **kw):
        super().__init__(parent, height=height, bg=C["border"],
                         highlightthickness=0, **kw)
        self._pct = 0; self._anim = 0; self._h = height
        self.bind("<Configure>", lambda _: self._redraw())
        self._bar  = self.create_rectangle(0,0,0,height, fill=C["accent"], outline="")
        self._glow = self.create_oval(0,-4,0,height+4, fill=C["accent"],
                                      outline="", stipple="gray50")
        self._tick()

    def _redraw(self):
        w = self.winfo_width()
        fw = int(w * self._pct / 100)
        self.coords(self._bar, 0, 0, fw, self._h)
        self.coords(self._glow, fw-24, -2, fw+4, self._h+2)

    def set(self, pct):
        self._pct = max(0.0, min(100.0, pct)); self._redraw()

    def _tick(self):
        self._anim = (self._anim+1) % 20
        a = abs(self._anim-10)/10
        c = self._lerp(C["accent"], "#ffffff", a*0.3)
        self.itemconfig(self._glow, fill=c)
        self.after(60, self._tick)

    @staticmethod
    def _lerp(c1, c2, t):
        r1,g1,b1=int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
        r2,g2,b2=int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


# ─── Widget: StepList ───────────────────────────────────────────────

class StepList(tk.Frame):
    def __init__(self, parent, steps, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._rows = []
        for s in steps:
            row = tk.Frame(self, bg=C["bg"]); row.pack(anchor="w", pady=2)
            dot = tk.Label(row, text="○", font=("Segoe UI",10),
                           fg=C["text3"], bg=C["bg"], width=2)
            dot.pack(side="left")
            lbl = tk.Label(row, text=s, font=FF_LABEL, fg=C["text3"], bg=C["bg"])
            lbl.pack(side="left", padx=4)
            self._rows.append((dot, lbl))

    def activate(self, idx):
        for i,(d,l) in enumerate(self._rows):
            if i<idx:   d.config(text="●",fg=C["success"]); l.config(fg=C["text2"])
            elif i==idx:d.config(text="◉",fg=C["accent"]);  l.config(fg=C["text"])
            else:       d.config(text="○",fg=C["text3"]);   l.config(fg=C["text3"])

    def complete(self):
        for d,l in self._rows:
            d.config(text="●",fg=C["success"]); l.config(fg=C["success"])

    def reset(self):
        for d,l in self._rows:
            d.config(text="○",fg=C["text3"]); l.config(fg=C["text3"])


# ─── Widget: FileRow ────────────────────────────────────────────────

class FileRow(tk.Frame):
    def __init__(self, parent, label, var, browse_cmd, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        tk.Label(self, text=label.upper(), font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["bg"]).pack(anchor="w", pady=(0,4))

        box = tk.Frame(self, bg=C["surface2"],
                       highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="x")

        self._entry = tk.Entry(box, textvariable=var, font=FF_LABEL,
                               bg=C["surface2"], fg=C["text"], relief="flat",
                               insertbackground=C["accent"], bd=7)
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<FocusIn>",
            lambda _: box.config(highlightbackground=C["accent"]))
        self._entry.bind("<FocusOut>",
            lambda _: box.config(highlightbackground=C["border"]))

        btn = tk.Label(box, text="  Procurar  ", font=FF_SMALL,
                       fg=C["accent"], bg=C["surface2"], cursor="hand2")
        btn.pack(side="right", padx=4)
        btn.bind("<Button-1>", lambda _: browse_cmd())
        btn.bind("<Enter>", lambda _: btn.config(fg=C["text"]))
        btn.bind("<Leave>", lambda _: btn.config(fg=C["accent"]))

        self._info = tk.Label(self, text="", font=FF_SMALL, fg=C["text3"], bg=C["bg"])
        self._info.pack(anchor="w", pady=(3,0))

    def set_info(self, text, color=None):
        self._info.config(text=text, fg=color or C["text3"])


# ─── App principal ───────────────────────────────────────────────────

CONV_STEPS = ["Validar origem", "Converter", "Verificar saída"]

class DiskForge(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DiskForge")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(860, 680)

        self._src_var = tk.StringVar()
        self._dst_var = tk.StringVar()
        self._running = False
        self._log_q   = queue.Queue()
        self._steps_widget: StepList = None

        self._src_var.trace_add("write", self._on_src_change)
        self._build()
        self._center()
        self._check_deps_async()
        self._poll()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = 980, 760
        self.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}")

    # ─── Build ───────────────────────────────────────────────────────

    def _build(self):
        # ── Sidebar ──────────────────────────────────────────────────
        sb = tk.Frame(self, bg=C["surface"], width=215)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)

        # Logo
        lf = tk.Frame(sb, bg=C["surface"])
        lf.pack(fill="x", padx=14, pady=(20,0))
        tk.Label(lf, text="◈", font=("Segoe UI",22), fg=C["accent"],
                 bg=C["surface"]).pack(side="left")
        nf = tk.Frame(lf, bg=C["surface"]); nf.pack(side="left", padx=8)
        tk.Label(nf, text="DiskForge", font=("Segoe UI",12,"bold"),
                 fg=C["text"], bg=C["surface"]).pack(anchor="w")
        tk.Label(nf, text="v1.1.0  •  Conversor Universal", font=("Segoe UI",7),
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w")

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", padx=12, pady=12)

        # Status qemu
        tk.Label(sb, text="FERRAMENTAS", font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=14, pady=(0,5))
        dep = tk.Frame(sb, bg=C["surface"]); dep.pack(fill="x", padx=14)
        self._qemu_dot = tk.Label(dep, text="○", font=("Segoe UI",10),
                                   fg=C["text3"], bg=C["surface"])
        self._qemu_dot.pack(side="left")
        tk.Label(dep, text="qemu-img", font=FF_SMALL,
                 fg=C["text2"], bg=C["surface"]).pack(side="left", padx=6)

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", padx=12, pady=12)

        # Lista de formatos
        tk.Label(sb, text="FORMATOS SUPORTADOS", font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=14, pady=(0,6))
        for key, info in FORMATS.items():
            row = tk.Frame(sb, bg=C["surface"]); row.pack(fill="x", padx=14, pady=1)
            tk.Label(row, text=info["ext"], font=("Courier New",8),
                     fg=C["accent"], bg=C["surface"], width=7, anchor="w").pack(side="left")
            lbl = info["label"] + (" ★" if info["star"] else "")
            tk.Label(row, text=lbl, font=("Segoe UI",8),
                     fg=C["gold"] if info["star"] else C["text2"],
                     bg=C["surface"]).pack(side="left")

        # ── Main area ─────────────────────────────────────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)

        # Bottom bar — empacotado antes do conteúdo para garantir visibilidade
        bot = tk.Frame(main, bg=C["surface"])
        bot.pack(fill="x", side="bottom")
        bi = tk.Frame(bot, bg=C["surface"]); bi.pack(fill="x", padx=24, pady=10)
        self._status_lbl = tk.Label(bi, text="Pronto.", font=FF_LABEL,
                                    fg=C["text2"], bg=C["surface"])
        self._status_lbl.pack(side="left")
        self._go_btn = tk.Button(bi, text="▶  Iniciar Conversão",
                                 font=("Segoe UI",10,"bold"),
                                 bg=C["accent"], fg=C["text"], relief="flat",
                                 bd=0, padx=18, pady=8, cursor="hand2",
                                 activebackground="#3a6be0",
                                 activeforeground=C["text"],
                                 command=self._start_conversion)
        self._go_btn.pack(side="right")

        # Área de conteúdo scrollável
        body = tk.Frame(main, bg=C["bg"])
        body.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(body, bg=C["bg"])
        hdr.pack(fill="x", padx=24, pady=(18,0))
        tk.Label(hdr, text="Conversor Universal de Discos", font=FF_TITLE,
                 fg=C["text"], bg=C["bg"]).pack(anchor="w")
        tk.Label(hdr, text="Converta entre qualquer combinação: RAW, QCOW2, VMDK, VDI, VHDX, VHD e mais.",
                 font=FF_LABEL, fg=C["text2"], bg=C["bg"],
                 wraplength=600, justify="left").pack(anchor="w", pady=(3,0))

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", padx=24, pady=(12,10))

        # ── Seletores de formato ──────────────────────────────────────
        fmt_row = tk.Frame(body, bg=C["bg"])
        fmt_row.pack(fill="x", padx=24, pady=(0,10))

        self._fmt_in = FormatPicker(fmt_row, "FORMATO DE ENTRADA",
                                    initial="vmdk", on_change=self._on_fmt_change)
        self._fmt_in.pack(side="left", fill="x", expand=True)

        arrow = tk.Frame(fmt_row, bg=C["bg"], width=46)
        arrow.pack(side="left"); arrow.pack_propagate(False)
        tk.Label(arrow, text="→", font=("Segoe UI",18),
                 fg=C["accent"], bg=C["bg"]).place(relx=0.5, rely=0.5, anchor="center")

        self._fmt_out = FormatPicker(fmt_row, "FORMATO DE SAÍDA",
                                     initial="qcow2", on_change=self._on_fmt_change)
        self._fmt_out.pack(side="left", fill="x", expand=True)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", padx=24, pady=(4,10))

        # ── Arquivos + Etapas ─────────────────────────────────────────
        files = tk.Frame(body, bg=C["bg"]); files.pack(fill="x", padx=24)

        left = tk.Frame(files, bg=C["bg"]); left.pack(side="left", fill="x", expand=True)

        right = tk.Frame(files, bg=C["bg"], width=175)
        right.pack(side="right", fill="y", padx=(14,0)); right.pack_propagate(False)
        tk.Label(right, text="ETAPAS", font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["bg"]).pack(anchor="w", pady=(2,5))
        self._steps_widget = StepList(right, CONV_STEPS)
        self._steps_widget.pack(anchor="w")

        self._src_row = FileRow(left, "Arquivo de Origem",
                                self._src_var, self._browse_src)
        self._src_row.pack(fill="x", pady=(0,8))

        self._dst_row = FileRow(left, "Arquivo de Destino",
                                self._dst_var, self._browse_dst)
        self._dst_row.pack(fill="x")

        # ── Progresso ────────────────────────────────────────────────
        prog = tk.Frame(body, bg=C["bg"]); prog.pack(fill="x", padx=24, pady=(12,0))

        stats = tk.Frame(prog, bg=C["bg"]); stats.pack(fill="x", pady=(0,4))
        self._pct_lbl = tk.Label(stats, text="", font=("Segoe UI",10,"bold"),
                                  fg=C["accent"], bg=C["bg"]); self._pct_lbl.pack(side="left")
        self._eta_lbl = tk.Label(stats, text="", font=FF_SMALL,
                                  fg=C["text3"], bg=C["bg"]); self._eta_lbl.pack(side="right")
        self._spd_lbl = tk.Label(stats, text="", font=FF_SMALL,
                                  fg=C["text3"], bg=C["bg"]); self._spd_lbl.pack(side="right", padx=14)

        self._progress = ProgressBar(prog, height=7)
        self._progress.pack(fill="x")

        # ── Log ──────────────────────────────────────────────────────
        log_wrap = tk.Frame(body, bg=C["surface2"])
        log_wrap.pack(fill="both", expand=True, padx=24, pady=(10,0))

        lh = tk.Frame(log_wrap, bg=C["surface2"]); lh.pack(fill="x", padx=10, pady=(6,2))
        tk.Label(lh, text="SAÍDA", font=("Segoe UI",7,"bold"),
                 fg=C["text3"], bg=C["surface2"]).pack(side="left")
        clr = tk.Label(lh, text="limpar", font=FF_SMALL, fg=C["text3"],
                       bg=C["surface2"], cursor="hand2"); clr.pack(side="right")
        clr.bind("<Button-1>", lambda _: self._log_txt.delete("1.0","end"))

        self._log_txt = tk.Text(log_wrap, bg=C["surface2"], fg=C["text2"],
                                font=FF_MONO, relief="flat", wrap="word",
                                selectbackground=C["accent"],
                                highlightthickness=0, bd=0, height=7)
        sb2 = ttk.Scrollbar(log_wrap, command=self._log_txt.yview)
        self._log_txt.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y", pady=4, padx=(0,3))
        self._log_txt.pack(side="left", fill="both", expand=True, padx=(10,0), pady=(0,6))

        for tag, fg in [("info",C["text2"]),("ok",C["success"]),
                        ("error",C["error"]),("warn",C["warning"]),("log",C["text3"])]:
            self._log_txt.tag_config(tag, foreground=fg)

    # ─── Eventos ─────────────────────────────────────────────────────

    def _on_fmt_change(self, _=None): self._auto_dst()

    def _on_src_change(self, *_):
        p = self._src_var.get()
        self._src_row.set_info(f"Tamanho: {human_size(p)}" if os.path.exists(p) else "")
        self._auto_dst()

    def _auto_dst(self):
        src = self._src_var.get()
        if not src: return
        ext = FORMATS[self._fmt_out.get()]["ext"]
        self._dst_var.set(str(Path(src).parent / f"{Path(src).stem}_converted{ext}"))

    def _browse_src(self):
        fmt = FORMATS[self._fmt_in.get()]
        p = filedialog.askopenfilename(
            title=f"Selecionar {fmt['label']}",
            filetypes=[(f"{fmt['label']} (*{fmt['ext']})", f"*{fmt['ext']}"),
                       ("Todos", "*.*")])
        if p: self._src_var.set(p)

    def _browse_dst(self):
        fmt = FORMATS[self._fmt_out.get()]
        p = filedialog.asksaveasfilename(
            title="Salvar como",
            defaultextension=fmt["ext"],
            filetypes=[(f"{fmt['label']} (*{fmt['ext']})", f"*{fmt['ext']}")])
        if p: self._dst_var.set(p)

    # ─── Deps ────────────────────────────────────────────────────────

    def _check_deps_async(self):
        def _chk():
            ok = bool(qemu_path())
            self.after(0, lambda: self._qemu_dot.config(
                text="●" if ok else "✕",
                fg=C["success"] if ok else C["error"]))
            if not ok:
                self.after(0, lambda: messagebox.showwarning(
                    "qemu-img não encontrado",
                    f"Não foi possível encontrar tools/qemu/qemu-img.exe.\n\n"
                    f"Certifique-se de que a pasta tools/qemu/ está junto ao script:\n"
                    f"{SCRIPT_DIR}"))
        threading.Thread(target=_chk, daemon=True).start()

    # ─── Conversão ───────────────────────────────────────────────────

    def _start_conversion(self):
        if self._running: return
        src, dst       = self._src_var.get().strip(), self._dst_var.get().strip()
        fmt_in, fmt_out = self._fmt_in.get(), self._fmt_out.get()

        if not qemu_path():
            messagebox.showwarning("qemu-img não encontrado",
                "Certifique-se de que a pasta tools/qemu/ está junto ao script.")
            return
        if fmt_in == fmt_out:
            messagebox.showwarning("Formatos iguais",
                "O formato de entrada e saída são iguais. Escolha formatos diferentes.")
            return
        if not src or not dst:
            messagebox.showwarning("Campos obrigatórios",
                "Preencha os caminhos de origem e destino antes de iniciar.")
            return
        if not os.path.exists(src):
            messagebox.showerror("Arquivo não encontrado",
                f"O arquivo de origem não existe:\n{src}")
            return

        self._running = True
        self._go_btn.config(state="disabled", text="Convertendo…")
        self._status_lbl.config(text="Processando…", fg=C["warning"])
        self._progress.set(0)
        self._pct_lbl.config(text="0%")
        self._eta_lbl.config(text=""); self._spd_lbl.config(text="")
        self._steps_widget.reset()
        self._log_txt.delete("1.0","end")
        self._log_append("info",
            f"Iniciando: {FORMATS[fmt_in]['label']} → {FORMATS[fmt_out]['label']}")

        t0 = [time.time()]

        def prog_cb(pct):
            pct = max(0.0, min(100.0, pct))
            self.after(0, lambda: self._progress.set(pct))
            self.after(0, lambda: self._pct_lbl.config(text=f"{pct:.1f}%"))

        def eta_cb(remain, pct):
            elapsed = time.time() - t0[0]
            if pct > 1: remain = max(0, elapsed/(pct/100) - elapsed)
            self.after(0, lambda: self._eta_lbl.config(text=f"ETA: {human_time(remain)}"))
            self.after(0, lambda: self._spd_lbl.config(text=f"Decorrido: {human_time(elapsed)}"))

        def step_cb(idx):
            self.after(0, lambda: self._steps_widget.activate(idx))

        def worker():
            ok = conv_universal(src, dst, fmt_in, fmt_out,
                                self._log_q, prog_cb, step_cb, eta_cb)
            self._log_q.put(("__done__", ok))

        threading.Thread(target=worker, daemon=True).start()

    # ─── Poll ────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                kind, msg = self._log_q.get_nowait()
                if kind == "__done__":
                    self._running = False
                    self._go_btn.config(state="normal", text="▶  Iniciar Conversão")
                    if msg:
                        self._status_lbl.config(text="Concluído!", fg=C["success"])
                        self._steps_widget.complete()
                        messagebox.showinfo("Conversão concluída! ✓",
                            f"Arquivo gerado com sucesso:\n\n{self._dst_var.get()}")
                    else:
                        self._status_lbl.config(text="Falha. Veja o log.", fg=C["error"])
                else:
                    self._log_append(kind, msg)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _log_append(self, kind: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = {"info":"ℹ","ok":"✓","error":"✗","warn":"⚠","log":"·"}.get(kind,"·")
        self._log_txt.insert("end", f"[{ts}] {prefix} {msg}\n", kind)
        self._log_txt.see("end")


# ─── Entry ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass

    app = DiskForge()
    app.mainloop()
