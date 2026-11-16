from pathlib import Path

p = Path("HexSecGPT.py")
s = p.read_text()

old = "                self.brain.client.models.list()"

new = '''                request = urllib.request.Request(
                    self.brain.base_url + "/models",
                    headers={
                        "Authorization": f"Bearer {self.brain.api_key}"
                    },
                    method="GET"
                )
                with urllib.request.urlopen(request, timeout=30) as response:
                    if response.status != 200:
                        raise RuntimeError("OpenRouter connection failed")'''

if s.count(old) != 1:
    raise SystemExit("Controllo connessione non trovato. Nessuna modifica.")

s = s.replace(old, new, 1)
p.write_text(s)

print("Verifica OpenRouter aggiornata.")
