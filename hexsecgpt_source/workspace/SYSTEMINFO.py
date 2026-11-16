#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEMINFO
==========
Programma di sola lettura che mostra informazioni sul dispositivo Android
e sull'ambiente Termux.

Caratteristiche di sicurezza:
- Nessuna modifica a file o directory.
- Nessuna esecuzione di comandi di sistema esterni (no subprocess/os.system).
- Nessuna installazione di pacchetti.
- Tutte le letture sono protette da try/except per evitare crash.

Autore: HexSecTeam
Licenza: uso locale legittimo e non distruttivo.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from datetime import datetime
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Utility di formattazione
# ---------------------------------------------------------------------------

def format_bytes(num_bytes: int) -> str:
    """Converte un numero di byte in una stringa leggibile (B, KB, MB, GB, TB)."""
    try:
        value = float(num_bytes)
    except (TypeError, ValueError):
        return "n/d"

    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024.0 or unit == "PB":
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def section(title: str) -> None:
    """Stampa un'intestazione di sezione omogenea."""
    print()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)


def kv(label: str, value: Optional[str]) -> None:
    """Stampa una coppia chiave/valore allineata, gestendo valori mancanti."""
    shown = value if value not in (None, "") else "n/d"
    print(f"{label:<28}: {shown}")


# ---------------------------------------------------------------------------
# Lettura sicura delle proprietà Android (sola lettura)
# ---------------------------------------------------------------------------

def read_android_properties(path: str = "/system/build.prop") -> Dict[str, str]:
    """
    Legge in modo sicuro il file build.prop di Android e restituisce un dizionario
    delle proprietà. Non modifica nulla: apre il file solo in modalità lettura.
    In caso di file assente o permessi insufficienti restituisce un dizionario vuoto.
    """
    props: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                # Salta righe vuote e commenti
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                props[key.strip()] = val.strip()
    except (FileNotFoundError, PermissionError, OSError):
        # Ambiente non Android o file non accessibile: nessun problema.
        return {}
    return props


def is_android() -> bool:
    """Rileva in modo euristico se siamo su Android/Termux."""
    if os.path.exists("/system/build.prop"):
        return True
    if "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ:
        return True
    # Termux imposta tipicamente PREFIX e TERMUX_VERSION
    if "TERMUX_VERSION" in os.environ or "com.termux" in os.environ.get("PREFIX", ""):
        return True
    return "android" in platform.platform().lower()


# ---------------------------------------------------------------------------
# Raccolta informazioni
# ---------------------------------------------------------------------------

def show_python_info() -> None:
    """Mostra la versione di Python e dettagli di implementazione."""
    section("PYTHON")
    kv("Versione Python", platform.python_version())
    kv("Implementazione", platform.python_implementation())
    kv("Compilatore", platform.python_compiler())
    kv("Eseguibile", sys.executable)


def show_os_info() -> None:
    """Mostra informazioni sul sistema operativo e sull'architettura."""
    section("SISTEMA OPERATIVO")
    kv("Sistema", platform.system())
    kv("Nome nodo", platform.node())
    kv("Release", platform.release())
    kv("Versione", platform.version())
    kv("Architettura", platform.machine())
    kv("Piattaforma", platform.platform())

    # Dettagli aggiuntivi da os.uname() se disponibile (solo lettura).
    try:
        uname = os.uname()
        kv("Kernel", f"{uname.sysname} {uname.release}")
        kv("Architettura kernel", uname.machine)
    except (AttributeError, OSError):
        pass


def show_android_info() -> None:
    """Mostra informazioni specifiche del dispositivo Android, se disponibili."""
    section("DISPOSITIVO ANDROID")

    if not is_android():
        kv("Rilevamento", "Ambiente Android non rilevato")
        return

    kv("Rilevamento", "Ambiente Android/Termux rilevato")

    props = read_android_properties()
    if not props:
        kv("build.prop", "non leggibile o non presente")
        return

    # Proprietà di interesse: modello, produttore, versione Android, SDK.
    kv("Produttore", props.get("ro.product.manufacturer"))
    kv("Modello", props.get("ro.product.model"))
    kv("Dispositivo", props.get("ro.product.device"))
    kv("Versione Android", props.get("ro.build.version.release"))
    kv("API level (SDK)", props.get("ro.build.version.sdk"))
    kv("Build ID", props.get("ro.build.id"))
    kv("Tipo build", props.get("ro.build.type"))
    kv("Tag build", props.get("ro.build.tags"))


def show_termux_info() -> None:
    """Mostra informazioni sull'ambiente Termux, se presente."""
    section("TERMUX")

    prefix = os.environ.get("PREFIX")
    termux_version = os.environ.get("TERMUX_VERSION")
    home = os.environ.get("HOME")

    if not prefix and not termux_version:
        kv("Rilevamento", "Ambiente Termux non rilevato")
        return

    kv("Rilevamento", "Ambiente Termux rilevato")
    kv("TERMUX_VERSION", termux_version)
    kv("PREFIX", prefix)
    kv("HOME", home)
    kv("Shell", os.environ.get("SHELL"))


def show_paths_and_disk() -> None:
    """Mostra directory corrente e spazio libero disponibile."""
    section("PERCORSI E SPAZIO SU DISCO")

    cwd = os.getcwd()
    kv("Directory corrente", cwd)

    # Spazio disco della directory corrente.
    try:
        usage = shutil.disk_usage(cwd)
        kv("Spazio totale (cwd)", format_bytes(usage.total))
        kv("Spazio usato (cwd)", format_bytes(usage.used))
        kv("Spazio libero (cwd)", format_bytes(usage.free))
    except OSError as exc:
        kv("Spazio disco (cwd)", f"non disponibile ({exc.__class__.__name__})")

    # Spazio disco della home, se diversa dalla cwd.
    home = os.environ.get("HOME")
    if home and os.path.isdir(home) and os.path.abspath(home) != os.path.abspath(cwd):
        try:
            home_usage = shutil.disk_usage(home)
            kv("Spazio libero (HOME)", format_bytes(home_usage.free))
        except OSError:
            kv("Spazio libero (HOME)", "non disponibile")


def show_datetime_info() -> None:
    """Mostra data e ora correnti in formato locale e ISO 8601."""
    section("DATA E ORA")
    now = datetime.now()
    kv("Data e ora locale", now.strftime("%Y-%m-%d %H:%M:%S"))
    kv("Formato ISO 8601", now.isoformat(timespec="seconds"))
    kv("Fuso orario locale", now.astimezone().tzname())
    kv("Timestamp epoch", str(int(now.timestamp())))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Punto di ingresso: raccoglie e stampa tutte le informazioni."""
    print("SYSTEMINFO - Report locale (sola lettura)")
    print(f"Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    show_python_info()
    show_os_info()
    show_android_info()
    show_termux_info()
    show_paths_and_disk()
    show_datetime_info()

    print()
    print("=" * 60)
    print(" Fine del report. Nessun file è stato modificato.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Uscita pulita su Ctrl+C
        print("\nInterrotto dall'utente.")
        sys.exit(130)
