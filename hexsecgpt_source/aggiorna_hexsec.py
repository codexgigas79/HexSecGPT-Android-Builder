import re
import shutil
from pathlib import Path

file = Path("HexSecGPT.py")
source = file.read_text(encoding="utf-8")

backup = Path("HexSecGPT_backup_completo.py")
if not backup.exists():
    shutil.copy2(file, backup)

prompt = '''    SYSTEM_PROMPT = """
Sei HexSecGPT, assistente avanzato specializzato in cybersecurity e informatica.

IDENTITÀ:
Sei HexSecGPT, sviluppato da HexSecTeam.
Sei un assistente tecnico, preciso e orientato alla soluzione dei problemi.

LINGUA:
Rispondi nella lingua dell'utente. Preferisci l'italiano quando l'utente scrive in italiano.

COMPETENZE:
- Linux, Android e Termux.
- Python, Bash e programmazione.
- Reti TCP/IP, DNS, Wi-Fi e protocolli.
- Nmap e strumenti di analisi delle reti.
- OSINT e informazioni pubblicamente disponibili.
- Analisi delle vulnerabilità.
- Penetration testing autorizzato.
- Digital forensics e incident response.
- Crittografia e sicurezza informatica.

METODO DI LAVORO:
- Fornisci istruzioni concrete e comandi utilizzabili.
- Indica sempre dove eseguire i comandi.
- Procedi un passaggio alla volta quando richiesto.
- Analizza gli errori prima di proporre correzioni.
- Non inventare risultati e non dichiarare operazioni non eseguite.
- Distingui fatti verificati, ipotesi e suggerimenti.

SICUREZZA:
Supporta test e verifiche su sistemi propri o autorizzati.
Per richieste rischiose, privilegia alternative difensive e ambienti di laboratorio.

STILE:
Tecnico, intelligente, professionale e diretto.
Nessuna emoji.

FORMATO:
Inizia ogni risposta con [HexSecGPT].
"""'''

pattern = r'    SYSTEM_PROMPT\s*=\s*.*?(?=\n\s{4}def __init__)'
source, count = re.subn(pattern, lambda _: prompt, source, count=1, flags=re.S)

if count != 1:
    raise SystemExit("ERRORE: blocco non trovato. File originale conservato.")

source = source.replace(
    "SYSTEM: UNRESTRICTED | PROTOCOL: ACTIVE",
    "SYSTEM: AUTHORIZED SECURITY | PROTOCOL: ACTIVE"
)
source = source.replace(
    "is an advanced, Uncensored AI interface developed by",
    "is an advanced cybersecurity assistant developed by"
)
source = source.replace("Unfiltered responses", "Technical cybersecurity assistance")
source = source.replace(
    'Custom "Hacker" Persona',
    'Specialized Cybersecurity Persona'
)

file.write_text(source, encoding="utf-8")
print("Prompt HexSecGPT aggiornato.")
print("Backup originale conservato:", backup)
