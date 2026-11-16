import re
import shutil
from pathlib import Path

p = Path("HexSecGPT.py")
s = p.read_text(encoding="utf-8")

backup = Path("HexSecGPT_pre_nmap.py")
if not backup.exists():
    shutil.copy2(p, backup)

# Aggiunge shutil agli import
if not re.search(r'^import shutil$', s, re.M):
    s = s.replace("import subprocess", "import subprocess\nimport shutil", 1)

# Inserisce il metodo Nmap
if "def execute_nmap(self, target):" not in s:
    method = '''
    def execute_nmap(self, target):
        import ipaddress

        try:
            ipaddress.ip_address(target)
        except ValueError:
            self.ui.show_msg("Nmap", "Indirizzo IP non valido.", "red")
            return

        if not shutil.which("nmap"):
            self.ui.show_msg("Nmap", "Nmap non installato.", "red")
            return

        confirm = self.ui.get_input(
            f"Scansionare {target}? (s/n)"
        )

        if confirm.lower() not in ("s", "si", "sì"):
            self.ui.show_msg("Nmap", "Scansione annullata.", "yellow")
            return

        command = [
            "nmap", "-sT", "-sV",
            "--top-ports", "100",
            "--reason", target
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180
            )
            output = result.stdout or result.stderr
            self.ui.console.print(
                Panel(output or "Nessun risultato.",
                      title="Nmap Report",
                      border_style="cyan")
            )
        except subprocess.TimeoutExpired:
            self.ui.show_msg("Nmap", "Tempo massimo superato.", "red")
        except Exception as e:
            self.ui.show_msg("Nmap", str(e), "red")

'''
    marker = "    def run_chat(self):"
    if marker not in s:
        raise SystemExit("Metodo run_chat non trovato.")
    s = s.replace(marker, method + marker, 1)

# Inserisce il comando prima della chiamata al modello AI
marker = "                generator = self.brain.chat(prompt)"
if "if prompt.lower().startswith('/nmap'):" not in s:
    block = '''                if prompt.lower().startswith('/nmap'):
                    parts = prompt.split(maxsplit=1)
                    if len(parts) != 2:
                        self.ui.show_msg("Nmap", "Uso: /nmap INDIRIZZO_IP", "yellow")
                    else:
                        self.execute_nmap(parts[1])
                    continue

'''
    if marker not in s:
        raise SystemExit("Punto di inserimento non trovato.")
    s = s.replace(marker, block + marker, 1)

# Aggiorna il messaggio di aiuto
s = re.sub(
    r'(/new - Wipe Memory\\\\n)(/exit - Disconnect)',
    r'\1/nmap IP - Scansione autorizzata\\\\n\2',
    s,
    count=1
)

p.write_text(s, encoding="utf-8")
print("Integrazione Nmap applicata.")
print("Backup:", backup)
