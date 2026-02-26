#!/usr/bin/env python3
"""
DiskForge — Conversor de Discos Virtuais
Compatível com Windows | Python 3.8+
Baixa o qemu-img.exe automaticamente se necessário.
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
import urllib.request
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# ─── Constantes ─────────────────────────────────────────────────────

APP_DIR   = Path(os.path.expanduser("~")) / ".diskforge"
TOOLS_DIR = APP_DIR / "tools"
QEMU_EXE  = TOOLS_DIR / "qemu-img.exe"

# Repositório que extrai qemu-img.exe + DLLs do instalador oficial (Stefan Weil)
# A URL real do ZIP é descoberta via GitHub API em tempo de execução
QEMU_GITHUB_API = "https://api.github.com/repos/fdcastel/qemu-img-windows-x64/releases/latest"
QEMU_ZIP_NAME   = "qemu-img-portable.zip"

# ─── Paleta ─────────────────────────────────────────────────────────

C = {
    "bg":       "#0d0f18",
    "surface":  "#13162a",
    "surface2": "#1c2035",
    "border":   "#252a45",
    "accent":   "#4d7cfe",
    "accent2":  "#7b5ea7",
    "success":  "#27c87a",
    "warning":  "#f5a623",
    "error":    "#f0445a",
    "text":     "#dde3f5",
    "text2":    "#8892b0",
    "text3":    "#4a5278",
}

FF_MONO  = ("Courier New", 9)
FF_UI    = ("Segoe UI",    10)
FF_SMALL = ("Segoe UI",    8)
FF_LABEL = ("Segoe UI",    9)
FF_TITLE = ("Segoe UI",   17, "bold")

# ─── Modos ──────────────────────────────────────────────────────────

MODES = {
    "vmdk_to_img": {
        "label": "VMDK → Imagem Inicializável",
        "icon":  "◈",
        "desc":  "Converte disco VMDK em imagem .img bootável preservando todos os dados e partições.",
        "steps": ["Validar origem", "Converter VMDK → RAW", "Verificar saída"],
        "ext_in":  (".vmdk", "Disco VMDK (*.vmdk)"),
        "ext_out": (".img",  "Imagem RAW (*.img)"),
    },
    "vdi_to_vmdk": {
        "label": "VDI → VMDK",
        "icon":  "⬡",
        "desc":  "Converte disco VDI (VirtualBox) para formato VMDK compatível com VMware e QEMU.",
        "steps": ["Validar origem", "Converter VDI → VMDK", "Verificar saída"],
        "ext_in":  (".vdi",  "Disco VDI (*.vdi)"),
        "ext_out": (".vmdk", "Disco VMDK (*.vmdk)"),
    },
    "vdi_to_img": {
        "label": "VDI → Imagem Inicializável",
        "icon":  "⬢",
        "desc":  "Converte VDI em imagem bootável via pipeline interno: VDI → VMDK → IMG.",
        "steps": ["Validar origem", "VDI → VMDK (temp)", "VMDK → Imagem RAW", "Finalizar"],
        "ext_in":  (".vdi", "Disco VDI (*.vdi)"),
        "ext_out": (".img", "Imagem RAW (*.img)"),
    },
}

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
    td = timedelta(seconds=int(seconds))
    h, rem = divmod(td.seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:   return f"{h}h {m:02d}m {s:02d}s"
    if m:   return f"{m}m {s:02d}s"
    return f"{s}s"

def qemu_path() -> str:
    # Prioriza qemu-img no PATH do sistema, depois o local
    if shutil.which("qemu-img"):
        return "qemu-img"
    if QEMU_EXE.exists():
        return str(QEMU_EXE)
    return None

def ensure_tools_dir():
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Download do qemu-img ────────────────────────────────────────────

def _get_download_url(log_cb) -> str | None:
    """
    Descobre a URL do ZIP via GitHub API.
    Retorna a URL do asset .zip da release mais recente do fdcastel/qemu-img-windows-x64.
    """
    import json
    log_cb("info", "Consultando GitHub API para URL de download…")
    try:
        req = urllib.request.Request(
            QEMU_GITHUB_API,
            headers={"User-Agent": "DiskForge/1.0", "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "")
            if name.endswith(".zip") and "x64" in name.lower():
                url = asset["browser_download_url"]
                log_cb("ok", f"Encontrado: {name}")
                log_cb("info", f"URL: {url}")
                return url

        # Se não achou asset .zip, tenta o zipball da release
        zipball = data.get("zipball_url")
        if zipball:
            log_cb("warn", "Asset .zip não encontrado, usando zipball da release.")
            return zipball

        log_cb("error", "Nenhum asset .zip encontrado na release.")
        return None

    except Exception as e:
        log_cb("error", f"Falha ao consultar GitHub API: {e}")
        return None


def _do_download(url: str, dest: Path, log_cb, progress_cb) -> bool:
    """Faz o download com progresso."""
    downloaded = [0]
    total      = [0]
    start_t    = [time.time()]

    def reporthook(count, block_size, total_size):
        downloaded[0] = min(count * block_size, total_size if total_size > 0 else count * block_size)
        total[0]      = total_size if total_size > 0 else 1
        pct     = min(99, downloaded[0] / total[0] * 100)
        elapsed = time.time() - start_t[0]
        speed   = downloaded[0] / elapsed if elapsed > 0 else 0
        remain  = (total[0] - downloaded[0]) / speed if speed > 0 else 0
        progress_cb(pct, speed, remain)
        if count % 50 == 0:
            log_cb("log", f"  {pct:.0f}%  {downloaded[0]//1024} KB / {total[0]//1024} KB"
                          f"  [{speed/1024:.0f} KB/s  ETA {human_time(remain)}]")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DiskForge/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            total_size = int(resp.headers.get("Content-Length", 0))
            block = 65536
            count = 0
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                count += 1
                reporthook(count, block, total_size)
        return True
    except Exception as e:
        log_cb("error", f"Erro no download: {e}")
        return False


def _extract_zip(zip_path: Path, log_cb) -> bool:
    """Extrai o ZIP achatando pastas, colocando tudo em TOOLS_DIR."""
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            members = [m for m in z.namelist() if not m.endswith("/")]
            log_cb("info", f"Extraindo {len(members)} arquivo(s)…")
            for name in members:
                filename = Path(name).name
                if not filename:
                    continue
                data = z.read(name)
                dest = TOOLS_DIR / filename
                with open(dest, "wb") as f:
                    f.write(data)
                log_cb("log", f"  {filename}  ({len(data)//1024} KB)")
        return True
    except Exception as e:
        log_cb("error", f"Erro ao extrair ZIP: {e}")
        return False


def download_qemu(progress_cb, log_cb):
    """
    Baixa o qemu-img.exe + todas as DLLs para Windows.
    Usa o repositório fdcastel/qemu-img-windows-x64 (build do Stefan Weil, portátil).
    A URL é descoberta em tempo real via GitHub API.
    """
    ensure_tools_dir()

    # Limpa instalação anterior quebrada
    for old in TOOLS_DIR.glob("*"):
        try: old.unlink()
        except: pass

    log_cb("info", "=== Instalando qemu-img para Windows ===")
    log_cb("info", f"Pasta de destino: {TOOLS_DIR}")

    # 1. Descobre URL via GitHub API
    url = _get_download_url(log_cb)
    if not url:
        log_cb("error", "Não foi possível obter a URL de download.")
        log_cb("warn",  "Instale manualmente o QEMU de https://www.qemu.org/download/#windows")
        log_cb("warn",  "Depois adicione a pasta do QEMU ao PATH do Windows.")
        return False

    # 2. Faz o download
    zip_path = TOOLS_DIR / QEMU_ZIP_NAME
    log_cb("info", "Baixando pacote…")
    ok = _do_download(url, zip_path, log_cb, progress_cb)
    if not ok:
        return False
    progress_cb(70, 0, 0)

    # 3. Extrai
    log_cb("info", "Extraindo arquivos…")
    ok = _extract_zip(zip_path, log_cb)
    zip_path.unlink(missing_ok=True)
    if not ok:
        return False
    progress_cb(90, 0, 0)

    # 4. Verifica se qemu-img.exe está presente
    if not QEMU_EXE.exists():
        # Procura em subpastas
        found_list = list(TOOLS_DIR.rglob("qemu-img.exe"))
        if found_list:
            src_dir = found_list[0].parent
            log_cb("info", f"qemu-img encontrado em: {src_dir} — copiando para {TOOLS_DIR}")
            for f in src_dir.iterdir():
                shutil.copy2(f, TOOLS_DIR / f.name)
        else:
            log_cb("error", "qemu-img.exe não encontrado no pacote.")
            log_cb("warn",  "Instale manualmente: https://www.qemu.org/download/#windows")
            return False

    # 5. Testa execução
    log_cb("info", "Testando qemu-img…")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            [str(QEMU_EXE), "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=flags
        )
        if result.returncode == 0:
            ver = result.stdout.strip().splitlines()[0]
            log_cb("ok", f"✓ {ver}")
            log_cb("ok", "qemu-img instalado e funcionando!")
            progress_cb(100, 0, 0)
            return True
        else:
            code = result.returncode & 0xFFFFFFFF
            log_cb("error", f"qemu-img falhou (código 0x{code:08X})")
            if code == 0xC0000135:
                log_cb("warn", "0xC0000135 = DLL ausente mesmo após extração.")
                log_cb("warn", "Solução alternativa: instale o QEMU completo de")
                log_cb("warn", "https://www.qemu.org/download/#windows e adicione ao PATH.")
            return False
    except Exception as e:
        log_cb("error", f"Não foi possível executar qemu-img: {e}")
        return False

# ─── Conversores ────────────────────────────────────────────────────

def run_qemu(args: list, log_q: queue.Queue, prog_cb, eta_cb) -> int:
    exe = qemu_path()
    if not exe:
        log_q.put(("error", "qemu-img não encontrado. Use o botão 'Instalar qemu-img'."))
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

        start_t  = time.time()
        last_pct = [0.0]

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue

            # qemu-img mostra: (XX.XX/100%)
            m = re.search(r"\((\d+(?:\.\d+)?)/100%\)", line)
            if m:
                pct = float(m.group(1))
                last_pct[0] = pct
                elapsed = time.time() - start_t
                if pct > 0:
                    total_est = elapsed / (pct / 100)
                    remain    = total_est - elapsed
                    speed_str = f"{pct:.1f}%"
                    prog_cb(pct)
                    eta_cb(remain, pct)
                log_q.put(("log", line))
            else:
                log_q.put(("log", line))

        proc.wait()
        rc = proc.returncode
        if rc == -1073741515:  # 0xC0000135 - DLL não encontrada
            log_q.put(("error", "Erro 0xC0000135: DLL ausente. O qemu-img.exe não consegue encontrar suas DLLs."))
            log_q.put(("warn",  "Solução: Delete a pasta %USERPROFILE%\\.diskforge\\tools e clique em 'Instalar qemu-img' novamente."))
            log_q.put(("warn",  "Alternativa: Instale o QEMU completo de https://www.qemu.org/download/#windows"))
        return rc

    except FileNotFoundError:
        log_q.put(("error", "qemu-img.exe não encontrado no caminho especificado."))
        return -1
    except Exception as e:
        log_q.put(("error", str(e)))
        return -1


def conv_vmdk_to_img(src, dst, log_q, prog_cb, step_cb, eta_cb):
    step_cb(0)
    if not os.path.exists(src):
        log_q.put(("error", "Arquivo de origem não encontrado.")); return False
    log_q.put(("ok", f"Origem: {src} ({human_size(src)})"))
    prog_cb(2)

    step_cb(1)
    log_q.put(("info", "Convertendo VMDK → RAW (imagem inicializável)…"))
    rc = run_qemu(["convert", "-p", "-f", "vmdk", "-O", "raw", src, dst],
                  log_q, prog_cb, eta_cb)
    if rc != 0:
        log_q.put(("error", f"Conversão falhou (código {rc})")); return False

    step_cb(2)
    log_q.put(("ok", f"Imagem gerada: {dst} ({human_size(dst)})"))
    prog_cb(100)
    return True


def conv_vdi_to_vmdk(src, dst, log_q, prog_cb, step_cb, eta_cb):
    step_cb(0)
    if not os.path.exists(src):
        log_q.put(("error", "Arquivo de origem não encontrado.")); return False
    log_q.put(("ok", f"Origem: {src} ({human_size(src)})"))
    prog_cb(2)

    step_cb(1)
    log_q.put(("info", "Convertendo VDI → VMDK…"))
    rc = run_qemu(["convert", "-p", "-f", "vdi", "-O", "vmdk", src, dst],
                  log_q, prog_cb, eta_cb)
    if rc != 0:
        log_q.put(("error", f"Conversão falhou (código {rc})")); return False

    step_cb(2)
    log_q.put(("ok", f"VMDK gerado: {dst} ({human_size(dst)})"))
    prog_cb(100)
    return True


def conv_vdi_to_img(src, dst, log_q, prog_cb, step_cb, eta_cb):
    step_cb(0)
    if not os.path.exists(src):
        log_q.put(("error", "Arquivo de origem não encontrado.")); return False
    log_q.put(("ok", f"Origem: {src} ({human_size(src)})"))
    prog_cb(2)

    tmp = Path(dst).with_suffix("").with_name(Path(dst).stem + "_tmp_diskforge.vmdk")

    step_cb(1)
    log_q.put(("info", "Etapa 1/2 — VDI → VMDK intermediário…"))
    rc = run_qemu(["convert", "-p", "-f", "vdi", "-O", "vmdk", src, str(tmp)],
                  log_q,
                  lambda p: prog_cb(p * 0.48),
                  lambda r, p: eta_cb(r * 2, p / 2))
    if rc != 0:
        log_q.put(("error", f"Etapa 1 falhou (código {rc})")); return False
    prog_cb(50)

    step_cb(2)
    log_q.put(("info", "Etapa 2/2 — VMDK → Imagem RAW…"))
    rc = run_qemu(["convert", "-p", "-f", "vmdk", "-O", "raw", str(tmp), dst],
                  log_q,
                  lambda p: prog_cb(50 + p * 0.48),
                  lambda r, p: eta_cb(r, 50 + p / 2))
    try:
        tmp.unlink()
        log_q.put(("info", "Arquivo intermediário removido."))
    except: pass

    if rc != 0:
        log_q.put(("error", f"Etapa 2 falhou (código {rc})")); return False

    step_cb(3)
    log_q.put(("ok", f"Imagem gerada: {dst} ({human_size(dst)})"))
    prog_cb(100)
    return True


CONVERTERS = {
    "vmdk_to_img": conv_vmdk_to_img,
    "vdi_to_vmdk": conv_vdi_to_vmdk,
    "vdi_to_img":  conv_vdi_to_img,
}

# ─── Widgets ────────────────────────────────────────────────────────

class NavButton(tk.Frame):
    def __init__(self, parent, key, icon, label, on_click, **kw):
        super().__init__(parent, bg=C["surface"], cursor="hand2", **kw)
        self.key = key
        self._on_click = on_click
        self._active = False

        self._indicator = tk.Frame(self, bg=C["surface"], width=3)
        self._indicator.pack(side="left", fill="y")

        inner = tk.Frame(self, bg=C["surface"])
        inner.pack(side="left", fill="x", expand=True, padx=(8,12), pady=8)

        self._icon_lbl = tk.Label(inner, text=icon, font=("Segoe UI",12),
                                  fg=C["text3"], bg=C["surface"])
        self._icon_lbl.pack(side="left")

        self._text_lbl = tk.Label(inner, text=label, font=FF_LABEL,
                                  fg=C["text2"], bg=C["surface"], anchor="w")
        self._text_lbl.pack(side="left", padx=8, fill="x", expand=True)

        for w in [self, inner, self._icon_lbl, self._text_lbl]:
            w.bind("<Button-1>", lambda _: self._on_click(self.key))
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)

    def set_active(self, active: bool):
        self._active = active
        bg   = C["surface2"] if active else C["surface"]
        fg_i = C["accent"]   if active else C["text3"]
        fg_t = C["text"]     if active else C["text2"]
        ind  = C["accent"]   if active else C["surface"]
        self.config(bg=bg)
        self._indicator.config(bg=ind)
        self._icon_lbl.config(fg=fg_i, bg=bg)
        self._text_lbl.config(fg=fg_t, bg=bg)
        for w in self.winfo_children():
            if isinstance(w, tk.Frame) and w != self._indicator:
                w.config(bg=bg)

    def _hover_on(self, _):
        if not self._active:
            self.config(bg=C["surface2"])
            for w in self.winfo_children():
                w.config(bg=C["surface2"])
    def _hover_off(self, _):
        if not self._active:
            self.config(bg=C["surface"])
            for w in self.winfo_children():
                w.config(bg=C["surface"])


class ProgressBar(tk.Canvas):
    def __init__(self, parent, height=8, **kw):
        super().__init__(parent, height=height, bg=C["border"],
                         highlightthickness=0, **kw)
        self._pct   = 0
        self._anim  = 0
        self._h     = height
        self.bind("<Configure>", self._on_resize)
        self._bar = self.create_rectangle(0, 0, 0, height,
                                          fill=C["accent"], outline="")
        self._glow = self.create_oval(0, -4, 0, height+4,
                                      fill=C["accent"], outline="",
                                      stipple="gray50")
        self._animate()

    def _on_resize(self, e):
        self._redraw()

    def _redraw(self):
        w = self.winfo_width()
        fill_w = int(w * self._pct / 100)
        self.coords(self._bar, 0, 0, fill_w, self._h)
        gw = 24
        self.coords(self._glow, fill_w - gw, -2, fill_w + 4, self._h + 2)

    def set(self, pct: float):
        self._pct = max(0.0, min(100.0, pct))
        self._redraw()

    def _animate(self):
        # Pulsa o brilho da ponta
        self._anim = (self._anim + 1) % 20
        alpha = abs(self._anim - 10) / 10
        color = self._lerp_color(C["accent"], "#ffffff", alpha * 0.3)
        self.itemconfig(self._glow, fill=color)
        self.after(60, self._animate)

    @staticmethod
    def _lerp_color(c1, c2, t):
        r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        r = int(r1 + (r2-r1)*t); g = int(g1 + (g2-g1)*t); b = int(b1 + (b2-b1)*t)
        return f"#{r:02x}{g:02x}{b:02x}"


class StepList(tk.Frame):
    def __init__(self, parent, steps, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._rows = []
        for s in steps:
            row = tk.Frame(self, bg=C["bg"])
            row.pack(anchor="w", pady=3)
            dot = tk.Label(row, text="○", font=("Segoe UI",11),
                           fg=C["text3"], bg=C["bg"], width=2)
            dot.pack(side="left")
            lbl = tk.Label(row, text=s, font=FF_LABEL,
                           fg=C["text3"], bg=C["bg"])
            lbl.pack(side="left", padx=4)
            self._rows.append((dot, lbl))

    def activate(self, idx):
        for i, (dot, lbl) in enumerate(self._rows):
            if i < idx:
                dot.config(text="●", fg=C["success"]); lbl.config(fg=C["text2"])
            elif i == idx:
                dot.config(text="◉", fg=C["accent"]);  lbl.config(fg=C["text"])
            else:
                dot.config(text="○", fg=C["text3"]);   lbl.config(fg=C["text3"])

    def complete(self):
        for dot, lbl in self._rows:
            dot.config(text="●", fg=C["success"]); lbl.config(fg=C["success"])

    def reset(self):
        for dot, lbl in self._rows:
            dot.config(text="○", fg=C["text3"]); lbl.config(fg=C["text3"])


class FileRow(tk.Frame):
    def __init__(self, parent, label, var, browse_cmd, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        tk.Label(self, text=label.upper(), font=("Segoe UI",8,"bold"),
                 fg=C["text3"], bg=C["bg"]).pack(anchor="w", pady=(0,4))

        box = tk.Frame(self, bg=C["surface2"],
                       highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="x")

        self._entry = tk.Entry(box, textvariable=var, font=FF_LABEL,
                               bg=C["surface2"], fg=C["text"], relief="flat",
                               insertbackground=C["accent"], bd=8)
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<FocusIn>",  lambda _: box.config(highlightbackground=C["accent"]))
        self._entry.bind("<FocusOut>", lambda _: box.config(highlightbackground=C["border"]))

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

class DiskForge(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DiskForge")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(820, 620)

        self._mode    = "vmdk_to_img"
        self._src_var = tk.StringVar()
        self._dst_var = tk.StringVar()
        self._running = False
        self._log_q   = queue.Queue()
        self._nav_btns: dict[str, NavButton] = {}
        self._steps_widget: StepList = None

        self._src_var.trace_add("write", self._on_src_change)

        self._build()
        self._center()
        self._select_mode("vmdk_to_img")
        self._check_deps_async()
        self._poll()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 900, 700
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ─── Build ───────────────────────────────────────────────────────

    def _build(self):
        # ── Sidebar ──────────────────────────────────────────────────
        self._sidebar = tk.Frame(self, bg=C["surface"], width=230)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo
        lf = tk.Frame(self._sidebar, bg=C["surface"])
        lf.pack(fill="x", padx=18, pady=(26,0))
        tk.Label(lf, text="◈", font=("Segoe UI",26), fg=C["accent"],
                 bg=C["surface"]).pack(side="left")
        nf = tk.Frame(lf, bg=C["surface"])
        nf.pack(side="left", padx=10)
        tk.Label(nf, text="DiskForge", font=("Segoe UI",14,"bold"),
                 fg=C["text"], bg=C["surface"]).pack(anchor="w")
        tk.Label(nf, text="v1.0  •  Conversor de Discos", font=FF_SMALL,
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w")

        self._sep(self._sidebar)

        tk.Label(self._sidebar, text="OPERAÇÕES", font=("Segoe UI",8,"bold"),
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=18, pady=(0,6))

        for key, info in MODES.items():
            btn = NavButton(self._sidebar, key, info["icon"], info["label"],
                            self._select_mode)
            btn.pack(fill="x", padx=6, pady=1)
            self._nav_btns[key] = btn

        self._sep(self._sidebar)

        # Dependências
        tk.Label(self._sidebar, text="FERRAMENTAS", font=("Segoe UI",8,"bold"),
                 fg=C["text3"], bg=C["surface"]).pack(anchor="w", padx=18, pady=(0,6))

        self._dep_frame = tk.Frame(self._sidebar, bg=C["surface"])
        self._dep_frame.pack(fill="x", padx=18)
        self._qemu_dot  = self._dep_row("qemu-img")

        install_row = tk.Frame(self._sidebar, bg=C["surface"])
        install_row.pack(fill="x", padx=14, pady=(8,0))
        self._install_btn = tk.Label(install_row, text="⬇  Instalar qemu-img",
                                     font=FF_SMALL, fg=C["accent"],
                                     bg=C["surface"], cursor="hand2", padx=4)
        self._install_btn.pack(anchor="w")
        self._install_btn.bind("<Button-1>", lambda _: self._install_qemu())

        # Versão
        tk.Label(self._sidebar, text="CentOS 7 / VMDK / VDI",
                 font=FF_SMALL, fg=C["text3"], bg=C["surface"]).pack(
                 side="bottom", pady=12)

        # ── Main ─────────────────────────────────────────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True)

        # Header
        hdr = tk.Frame(main, bg=C["bg"])
        hdr.pack(fill="x", padx=30, pady=(26,0))
        self._title_lbl = tk.Label(hdr, text="", font=FF_TITLE,
                                   fg=C["text"], bg=C["bg"])
        self._title_lbl.pack(anchor="w")
        self._desc_lbl  = tk.Label(hdr, text="", font=FF_LABEL,
                                   fg=C["text2"], bg=C["bg"],
                                   wraplength=540, justify="left")
        self._desc_lbl.pack(anchor="w", pady=(4,0))

        tk.Frame(main, bg=C["border"], height=1).pack(fill="x", padx=30, pady=14)

        # Content
        content = tk.Frame(main, bg=C["bg"])
        content.pack(fill="x", padx=30)

        left  = tk.Frame(content, bg=C["bg"])
        left.pack(side="left", fill="x", expand=True)

        right = tk.Frame(content, bg=C["bg"], width=190)
        right.pack(side="right", fill="y", padx=(20,0))
        right.pack_propagate(False)
        tk.Label(right, text="ETAPAS", font=("Segoe UI",8,"bold"),
                 fg=C["text3"], bg=C["bg"]).pack(anchor="w", pady=(0,8))
        self._steps_container = right

        # Arquivos
        self._src_row = FileRow(left, "Arquivo de Origem",
                                self._src_var, self._browse_src)
        self._src_row.pack(fill="x", pady=(0,12))

        self._dst_row = FileRow(left, "Arquivo de Destino",
                                self._dst_var, self._browse_dst)
        self._dst_row.pack(fill="x")

        # ── Progresso ────────────────────────────────────────────────
        prog_area = tk.Frame(main, bg=C["bg"])
        prog_area.pack(fill="x", padx=30, pady=(18,0))

        # Stats row
        stats = tk.Frame(prog_area, bg=C["bg"])
        stats.pack(fill="x", pady=(0,6))

        self._pct_lbl  = tk.Label(stats, text="",    font=("Segoe UI",11,"bold"),
                                  fg=C["accent"], bg=C["bg"])
        self._pct_lbl.pack(side="left")

        self._eta_lbl  = tk.Label(stats, text="",    font=FF_SMALL,
                                  fg=C["text3"], bg=C["bg"])
        self._eta_lbl.pack(side="right")

        self._spd_lbl  = tk.Label(stats, text="",    font=FF_SMALL,
                                  fg=C["text3"], bg=C["bg"])
        self._spd_lbl.pack(side="right", padx=16)

        self._progress = ProgressBar(prog_area, height=8)
        self._progress.pack(fill="x")

        # ── Log ──────────────────────────────────────────────────────
        log_wrap = tk.Frame(main, bg=C["surface2"])
        log_wrap.pack(fill="both", expand=True, padx=30, pady=(14,0))

        log_hdr = tk.Frame(log_wrap, bg=C["surface2"])
        log_hdr.pack(fill="x", padx=10, pady=(8,2))
        tk.Label(log_hdr, text="SAÍDA", font=("Segoe UI",8,"bold"),
                 fg=C["text3"], bg=C["surface2"]).pack(side="left")
        _clear_btn = tk.Label(log_hdr, text="limpar", font=FF_SMALL, fg=C["text3"],
                              bg=C["surface2"], cursor="hand2")
        _clear_btn.pack(side="right")
        _clear_btn.bind("<Button-1>", lambda _: self._log_txt.delete("1.0","end"))

        self._log_txt = tk.Text(log_wrap, bg=C["surface2"], fg=C["text2"],
                                font=FF_MONO, relief="flat", wrap="word",
                                selectbackground=C["accent"],
                                highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(log_wrap, command=self._log_txt.yview)
        self._log_txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=4, padx=(0,4))
        self._log_txt.pack(side="left", fill="both", expand=True,
                           padx=(10,0), pady=(0,8))

        for tag, fg in [("info",C["text2"]),("ok",C["success"]),
                        ("error",C["error"]),("warn",C["warning"]),
                        ("log",C["text3"])]:
            self._log_txt.tag_config(tag, foreground=fg)

        # ── Bottom bar ───────────────────────────────────────────────
        bot = tk.Frame(main, bg=C["surface"])
        bot.pack(fill="x", side="bottom")
        inner = tk.Frame(bot, bg=C["surface"])
        inner.pack(fill="x", padx=30, pady=12)

        self._status_lbl = tk.Label(inner, text="Pronto.", font=FF_LABEL,
                                    fg=C["text2"], bg=C["surface"])
        self._status_lbl.pack(side="left")

        self._go_btn = tk.Button(inner, text="▶  Iniciar Conversão",
                                 font=("Segoe UI",10,"bold"),
                                 bg=C["accent"], fg=C["text"],
                                 relief="flat", bd=0, padx=18, pady=8,
                                 cursor="hand2", activebackground="#3a6be0",
                                 activeforeground=C["text"],
                                 command=self._start_conversion)
        self._go_btn.pack(side="right")

    def _sep(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=14, pady=16)

    def _dep_row(self, name):
        row = tk.Frame(self._dep_frame, bg=C["surface"])
        row.pack(fill="x", pady=2)
        dot = tk.Label(row, text="○", font=("Segoe UI",10),
                       fg=C["text3"], bg=C["surface"])
        dot.pack(side="left")
        tk.Label(row, text=name, font=FF_SMALL, fg=C["text2"],
                 bg=C["surface"]).pack(side="left", padx=6)
        return dot

    # ─── Modo ────────────────────────────────────────────────────────

    def _select_mode(self, key: str):
        self._mode = key
        info = MODES[key]

        for k, btn in self._nav_btns.items():
            btn.set_active(k == key)

        self._title_lbl.config(text=info["label"])
        self._desc_lbl.config(text=info["desc"])

        # Rebuilds steps
        if self._steps_widget:
            self._steps_widget.destroy()
        self._steps_widget = StepList(self._steps_container, info["steps"])
        self._steps_widget.pack(anchor="w")

        self._auto_dst()

    def _on_src_change(self, *_):
        p = self._src_var.get()
        if os.path.exists(p):
            self._src_row.set_info(f"Tamanho: {human_size(p)}", C["text3"])
        else:
            self._src_row.set_info("")
        self._auto_dst()

    def _auto_dst(self):
        src = self._src_var.get()
        if not src: return
        info = MODES[self._mode]
        stem   = Path(src).stem
        folder = Path(src).parent
        ext    = info["ext_out"][0]
        self._dst_var.set(str(folder / f"{stem}_converted{ext}"))

    def _browse_src(self):
        ext, label = MODES[self._mode]["ext_in"]
        p = filedialog.askopenfilename(
            title=f"Selecionar {label}",
            filetypes=[(label, f"*{ext}"), ("Todos", "*.*")])
        if p: self._src_var.set(p)

    def _browse_dst(self):
        ext, label = MODES[self._mode]["ext_out"]
        p = filedialog.asksaveasfilename(
            title="Salvar como",
            defaultextension=ext,
            filetypes=[(label, f"*{ext}")])
        if p: self._dst_var.set(p)

    # ─── Deps ────────────────────────────────────────────────────────

    def _check_deps_async(self):
        def _check():
            ok = bool(qemu_path())
            self.after(0, lambda: self._set_dep(self._qemu_dot, ok))
            self.after(0, lambda: self._install_btn.config(
                fg=C["text3"] if ok else C["accent"],
                cursor="arrow" if ok else "hand2"))
        threading.Thread(target=_check, daemon=True).start()

    def _set_dep(self, dot, ok):
        dot.config(text="●" if ok else "✕",
                   fg=C["success"] if ok else C["error"])

    def _install_qemu(self):
        if qemu_path():
            messagebox.showinfo("Já instalado",
                                f"qemu-img já está disponível:\n{qemu_path()}")
            return
        if self._running:
            return
        self._running = True
        self._go_btn.config(state="disabled")
        self._status_lbl.config(text="Baixando qemu-img…", fg=C["warning"])
        self._progress.set(0)
        self._log_txt.delete("1.0", "end")

        def _dl_progress(pct, speed, remain):
            self.after(0, lambda: self._progress.set(pct))
            self.after(0, lambda: self._pct_lbl.config(text=f"{pct:.0f}%"))
            self.after(0, lambda: self._eta_lbl.config(
                text=f"ETA {human_time(remain)}"))
            self.after(0, lambda: self._spd_lbl.config(
                text=f"{speed/1024:.0f} KB/s"))

        def _worker():
            ok = download_qemu(
                _dl_progress,
                lambda kind, msg: self._log_q.put((kind, msg))
            )
            self._log_q.put(("__install_done__", ok))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Conversão ───────────────────────────────────────────────────

    def _start_conversion(self):
        if self._running: return
        src = self._src_var.get().strip()
        dst = self._dst_var.get().strip()

        if not qemu_path():
            messagebox.showwarning("qemu-img não encontrado",
                "Clique em 'Instalar qemu-img' na barra lateral antes de converter.")
            return
        if not src or not dst:
            messagebox.showwarning("Campos obrigatórios",
                "Preencha origem e destino antes de iniciar.")
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
        self._eta_lbl.config(text="")
        self._spd_lbl.config(text="")
        self._steps_widget.reset()
        self._log_txt.delete("1.0","end")
        self._log_append("info",
            f"[{datetime.now():%H:%M:%S}] Iniciando: {MODES[self._mode]['label']}\n")

        start_ref = [time.time()]
        last_pct  = [0.0]

        def prog_cb(pct):
            pct = max(0.0, min(100.0, pct))
            last_pct[0] = pct
            self.after(0, lambda: self._progress.set(pct))
            self.after(0, lambda: self._pct_lbl.config(text=f"{pct:.1f}%"))

        def eta_cb(remain, pct):
            elapsed = time.time() - start_ref[0]
            if pct > 1:
                total_est = elapsed / (pct / 100)
                remain    = max(0, total_est - elapsed)
            self.after(0, lambda: self._eta_lbl.config(
                text=f"ETA: {human_time(remain)}"))
            self.after(0, lambda: self._spd_lbl.config(
                text=f"Decorrido: {human_time(elapsed)}"))

        def step_cb(idx):
            self.after(0, lambda: self._steps_widget.activate(idx))

        def worker():
            fn = CONVERTERS[self._mode]
            ok = fn(src, dst, self._log_q, prog_cb, step_cb, eta_cb)
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

                elif kind == "__install_done__":
                    self._running = False
                    self._go_btn.config(state="normal")
                    self._check_deps_async()
                    if msg:
                        self._status_lbl.config(text="qemu-img instalado!", fg=C["success"])
                        messagebox.showinfo("Instalado!", "qemu-img instalado com sucesso.")
                    else:
                        self._status_lbl.config(text="Falha no download.", fg=C["error"])
                        messagebox.showerror("Erro", "Não foi possível baixar o qemu-img.\nVerifique sua conexão e tente novamente.")
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
        windll.shcore.SetProcessDpiAwareness(1)  # HiDPI no Windows
    except: pass

    app = DiskForge()
    app.mainloop()
