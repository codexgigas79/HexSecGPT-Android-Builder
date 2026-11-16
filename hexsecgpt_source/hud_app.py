import os
import json
import ipaddress
import subprocess
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv
from HexSecGPT import Config, HexSecBrain
from builder_engine import create_script, list_scripts, validate_script, run_script

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / Config.ENV_FILE)

key = os.getenv(Config.API_KEY_NAME)
if not key:
    raise SystemExit("Chiave API assente. Configurala prima da HexSecGPT.py.")

brain = HexSecBrain(key, None)

class HUDHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json({
                "online": True,
                "model": brain.model,
                "system": "HexSecGPT Cyber HUD"
            })
            return

        if self.path == "/api/builder/list":
            self.send_json({"scripts": list_scripts()})
            return

        if self.path in ("/", "/index.html"):
            path = ROOT / "static" / "index.html"
            content = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_error(404)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 20000:
                self.send_json({"error": "Richiesta non valida."}, 400)
                return

            data = json.loads(self.rfile.read(size).decode("utf-8"))

            if self.path == "/api/chat":
                prompt = str(data.get("message", "")).strip()
                if not prompt or len(prompt) > 8000:
                    self.send_json({"error": "Messaggio vuoto o troppo lungo."}, 400)
                    return

                answer = "".join(brain.chat(prompt))
                self.send_json({"answer": answer})
                return

            if self.path == "/api/builder/create":
                name = str(data.get("name", "")).strip()
                request = str(data.get("request", "")).strip()

                if not request or len(request) > 4000:
                    self.send_json({"error": "Descrizione vuota o troppo lunga."}, 400)
                    return

                prompt = (
                    "Sei un programmatore Python. Genera uno script Python 3 "
                    "per automazioni locali legittime e non distruttive. "
                    "Non creare malware, furto di credenziali, persistenza, "
                    "evasione, attacchi o esfiltrazione. "
                    "Non installare pacchetti e non eseguire comandi di sistema "
                    "pericolosi. Rispondi esclusivamente con un blocco di codice "
                    "```python ... ``` completo e commentato.\n\n"
                    "Nome progetto: " + name + "\n"
                    "Richiesta: " + request
                )

                answer = "".join(brain.chat(prompt))
                match = re.search(
                    r"```(?:python|py)?\s*\n?(.*?)```",
                    answer, re.DOTALL | re.IGNORECASE
                )

                if not match:
                    self.send_json({
                        "error": "L'AI non ha restituito codice Python riconoscibile.",
                        "answer": answer[:4000]
                    }, 422)
                    return

                result = create_script(name, match.group(1).strip())
                self.send_json({
                    "result": result,
                    "preview": match.group(1).strip()[:5000]
                })
                return

            if self.path == "/api/builder/validate":
                name = str(data.get("name", "")).strip()
                result = validate_script(name)
                self.send_json(result)
                return

            if self.path == "/api/builder/run":
                name = str(data.get("name", "")).strip()

                if data.get("authorized") is not True:
                    self.send_json({"error": "Autorizzazione esplicita richiesta."}, 403)
                    return

                result = run_script(name, authorized=True)
                self.send_json(result)
                return

            if self.path == "/api/nmap":
                target = str(data.get("target", "")).strip()

                if data.get("authorized") is not True:
                    self.send_json({"error": "Confermare l'autorizzazione al test."}, 403)
                    return

                try:
                    ipaddress.ip_address(target)
                except ValueError:
                    self.send_json({"error": "Indirizzo IP non valido."}, 400)
                    return

                import shutil
                if not shutil.which("nmap"):
                    self.send_json({"error": "Nmap non installato."}, 500)
                    return

                result = subprocess.run(
                    ["nmap", "-sT", "-sV", "--top-ports", "100",
                     "--reason", target],
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                report = result.stdout or result.stderr
                if not report.strip():
                    self.send_json({"error": "Nessun risultato Nmap."}, 500)
                    return

                analysis_prompt = (
                    "Analizza questo rapporto Nmap per finalità difensive. "
                    "Distingui fatti e ipotesi, non inventare vulnerabilità "
                    "o CVE e adatta i suggerimenti al sistema effettivamente "
                    "descritto. Rispondi in italiano.\n\nRAPPORTO:\n"
                    + report[:10000]
                )
                analysis = "".join(brain.chat(analysis_prompt))
                self.send_json({"report": report, "analysis": analysis})
                return

            self.send_json({"error": "Endpoint sconosciuto."}, 404)

        except subprocess.TimeoutExpired:
            self.send_json({"error": "Tempo massimo Nmap superato."}, 504)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def log_message(self, format, *args):
        print("[HUD]", format % args)

if __name__ == "__main__":
    print("\nHEXSECGPT CYBER HUD")
    print("Interfaccia: http://127.0.0.1:8080")
    print("Server locale attivo. CTRL+C per arrestare.\n")
    ThreadingHTTPServer(("127.0.0.1", 8080), HUDHandler).serve_forever()
