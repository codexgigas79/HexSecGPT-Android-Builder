import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "workspace"
MAX_CODE_SIZE = 50000
MAX_OUTPUT_SIZE = 12000
MAX_RUNTIME = 30

WORKSPACE.mkdir(exist_ok=True)

def safe_name(name):
    name = str(name).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        raise ValueError("Nome non valido. Usare lettere, numeri, _ o -.")
    return name

def script_path(name):
    name = str(name).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}\.(py|sh)", name):
        raise ValueError("Sono ammessi solo file .py e .sh con nome semplice.")
    path = (WORKSPACE / name).resolve()
    if path.parent != WORKSPACE.resolve():
        raise ValueError("Percorso non consentito.")
    return path

def create_script(name, code):
    name = safe_name(name)
    code = str(code)
    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        raise ValueError("Script troppo grande.")
    if not code.strip():
        raise ValueError("Il codice è vuoto.")

    path = script_path(name + ".py")
    if path.exists():
        raise FileExistsError("Il file esiste già. Non verrà sovrascritto.")

    path.write_text(code, encoding="utf-8")
    return {"created": True, "file": path.name}

def list_scripts():
    return [
        {"name": p.name, "size": p.stat().st_size}
        for p in sorted(WORKSPACE.iterdir())
        if p.is_file() and p.suffix in (".py", ".sh")
    ]

def validate_script(name):
    path = script_path(name)
    if not path.is_file():
        raise FileNotFoundError("Script non trovato.")

    if path.suffix == ".py":
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True, text=True, timeout=10
        )
    else:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True, text=True, timeout=10
        )

    return {
        "valid": result.returncode == 0,
        "output": (result.stderr or result.stdout)[:MAX_OUTPUT_SIZE]
    }

def run_script(name, authorized=False):
    if authorized is not True:
        raise PermissionError("Autorizzazione esplicita richiesta.")

    path = script_path(name)
    if not path.is_file():
        raise FileNotFoundError("Script non trovato.")

    check = validate_script(name)
    if not check["valid"]:
        raise ValueError("Script non valido: " + check["output"])

    if path.suffix == ".py":
        command = [sys.executable, str(path)]
    else:
        command = ["bash", str(path)]

    result = subprocess.run(
        command,
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=MAX_RUNTIME
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-MAX_OUTPUT_SIZE:],
        "stderr": result.stderr[-MAX_OUTPUT_SIZE:]
    }
