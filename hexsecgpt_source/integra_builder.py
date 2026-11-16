from pathlib import Path
import shutil

p = Path("hud_app.py")
s = p.read_text(encoding="utf-8")

if "from builder_engine import" in s:
    print("Builder già collegato: nessuna modifica.")
    raise SystemExit

backup = Path("hud_app.py.builder-backup")
shutil.copy2(p, backup)

s = s.replace(
    "import subprocess\n",
    "import subprocess\nimport re\n"
)

s = s.replace(
    "from HexSecGPT import Config, HexSecBrain\n",
    "from HexSecGPT import Config, HexSecBrain\n"
    "from builder_engine import create_script, list_scripts, "
    "validate_script, run_script\n"
)

get_marker = '''        if self.path in ("/", "/index.html"):
'''
get_code = '''        if self.path == "/api/builder/list":
            self.send_json({"scripts": list_scripts()})
            return

'''
if get_marker not in s:
    print("Punto GET non trovato. Backup conservato.")
    raise SystemExit
s = s.replace(get_marker, get_code + get_marker, 1)

post_marker = '''            if self.path == "/api/nmap":
'''
post_code = '''            if self.path == "/api/builder/create":
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
                    "```python ... ``` completo e commentato.\\n\\n"
                    "Nome progetto: " + name + "\\n"
                    "Richiesta: " + request
                )

                answer = "".join(brain.chat(prompt))
                match = re.search(
                    r"```(?:python|py)?\\s*\\n?(.*?)```",
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

'''
if post_marker not in s:
    print("Punto POST non trovato. Backup conservato.")
    raise SystemExit
s = s.replace(post_marker, post_code + post_marker, 1)

p.write_text(s, encoding="utf-8")
print("API BUILDER INTEGRATE.")
print("Backup:", backup)
