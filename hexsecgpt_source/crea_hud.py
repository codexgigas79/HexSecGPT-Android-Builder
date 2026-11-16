from pathlib import Path

Path("static").mkdir(exist_ok=True)

server = r'''import os
import json
import ipaddress
import subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv
from HexSecGPT import Config, HexSecBrain

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
'''

html = r'''<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#030812">
<title>HexSecGPT | Cyber HUD</title>
<style>
:root{--cyan:#00eaff;--blue:#167bff;--bg:#030812;--panel:#071525;--muted:#7195a8}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(ellipse at 50% 20%,#09243b 0%,#030812 55%,#010409 100%);color:#d8faff;font-family:Arial,sans-serif;min-height:100vh}
header{padding:18px;text-align:center;border-bottom:1px solid #0b5368;letter-spacing:4px;color:var(--cyan);font-weight:bold;text-shadow:0 0 14px var(--cyan)}
.status{display:flex;justify-content:center;gap:18px;padding:12px;font-size:11px;color:#78b8ca;flex-wrap:wrap}
.dot{color:#00ffad;text-shadow:0 0 8px #00ffad}
main{max-width:850px;margin:auto;padding:10px}
.core-wrap{height:310px;display:flex;justify-content:center;align-items:center;position:relative}
canvas{width:min(300px,85vw);height:min(300px,85vw);max-width:300px;max-height:300px}
.core-label{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;pointer-events:none;color:#c9fbff;text-shadow:0 0 12px var(--cyan);letter-spacing:3px;font-size:13px}
.core-label small{display:block;font-size:9px;color:#56a9c3;margin-top:7px;letter-spacing:2px}
.panel{background:linear-gradient(145deg,#081a2bdf,#030b16ee);border:1px solid #08718b;border-radius:12px;padding:14px;margin:12px 0;box-shadow:0 0 18px #00cfff12,inset 0 0 20px #00aaff08}
h3{font-size:12px;letter-spacing:3px;color:var(--cyan);margin:0 0 12px}
#chat{height:230px;overflow-y:auto;font-size:14px;line-height:1.5;white-space:pre-wrap}
.msg{padding:9px;margin:7px 0;border-left:2px solid var(--blue);background:#071827}
.msg.user{border-color:var(--cyan);color:#d5fbff}
.controls{display:flex;gap:8px;margin-top:10px}
input{min-width:0;flex:1;background:#020a13;border:1px solid #14617a;border-radius:7px;color:white;padding:13px;font-size:14px;outline:none}
button{background:linear-gradient(135deg,#075b83,#07314f);border:1px solid var(--cyan);border-radius:7px;color:#e5fcff;padding:12px 15px;font-weight:bold}
button:disabled{opacity:.4}
.tools{display:grid;grid-template-columns:1fr 1fr;gap:9px}
#result{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.5;max-height:380px;overflow:auto;color:#bceaf2}
footer{text-align:center;color:#477b90;font-size:10px;letter-spacing:2px;padding:18px}
@media(max-width:430px){.core-wrap{height:275px}.tools{grid-template-columns:1fr}.controls button{padding:10px}}
</style>
</head>
<body>
<header>◈ HEXSECGPT ◈</header>
<div class="status">
<span><b class="dot">●</b> HUD ONLINE</span>
<span id="connection">● NEURAL LINK...</span>
<span>◈ DEFENSIVE SECURITY</span>
</div>
<main>
<div class="core-wrap">
<canvas id="core" width="600" height="600"></canvas>
<div class="core-label">HEXSEC<small id="mode">SYSTEM STANDBY</small></div>
</div>

<section class="panel">
<h3>◈ NEURAL INTERFACE</h3>
<div id="chat"><div class="msg">HexSecGPT pronto. Connessione locale inizializzata.</div></div>
<div class="controls">
<input id="message" placeholder="Inserisci un comando..." autocomplete="off">
<button id="send">INVIA</button>
</div>
</section>

<section class="panel">
<h3>◈ SECURITY OPERATIONS</h3>
<div class="tools">
<input id="target" placeholder="Indirizzo IP autorizzato">
<button id="scan">AVVIA NMAP</button>
</div>
<div class="controls">
<label style="font-size:11px;color:#8bb5c5"><input type="checkbox" id="authorized" style="width:auto"> Confermo di avere autorizzazione a eseguire la scansione</label>
</div>
<div id="result"></div>
</section>
</main>
<footer>HEXSECTEAM // LOCAL CYBER COMMAND CENTER</footer>
<script>
const canvas=document.getElementById('core'),ctx=canvas.getContext('2d');
let phase=0,activity='idle';
function draw(){
 const w=600,c=300;ctx.clearRect(0,0,w,w);phase+=activity==='busy'?.045:.012;
 const pulse=1+Math.sin(phase*2)*.035;
 const glow=ctx.createRadialGradient(c,c,25,c,c,190);
 glow.addColorStop(0,'#00eaff55');glow.addColorStop(.5,'#087bff20');glow.addColorStop(1,'#00102000');
 ctx.fillStyle=glow;ctx.fillRect(0,0,w,w);
 for(let ring=0;ring<5;ring++){
  ctx.save();ctx.translate(c,c);ctx.rotate(phase*(ring%2?-.35:.5)*(ring+1));
  ctx.beginPath();ctx.ellipse(0,0,95+ring*20,65+ring*17,0,0,Math.PI*2);
  ctx.strokeStyle=`rgba(${ring%2?0:20},${180+ring*10},255,${.65-ring*.08})`;
  ctx.lineWidth=ring===0?3:1.5;ctx.shadowBlur=18;ctx.shadowColor='#00dfff';ctx.stroke();
  for(let j=0;j<3+ring;j++){
   const a=j*Math.PI*2/(3+ring);
   ctx.beginPath();ctx.arc(Math.cos(a)*(95+ring*20),Math.sin(a)*(65+ring*17),ring===0?5:2.5,0,Math.PI*2);
   ctx.fillStyle='#9afaff';ctx.fill();
  }
  ctx.restore();
 }
 const core=ctx.createRadialGradient(c-22,c-25,5,c,c,75*pulse);
 core.addColorStop(0,'#ffffff');core.addColorStop(.18,'#8cffff');core.addColorStop(.48,'#00bfff');core.addColorStop(1,'#0645a8');
 ctx.beginPath();ctx.arc(c,c,68*pulse,0,Math.PI*2);ctx.fillStyle=core;ctx.shadowBlur=activity==='busy'?65:38;ctx.shadowColor='#00cfff';ctx.fill();ctx.shadowBlur=0;
 for(let i=0;i<35;i++){
  const a=i*2.399+phase*(activity==='busy'?2:.4),r=115+(i%7)*10;
  const x=c+Math.cos(a)*r,y=c+Math.sin(a)*r;
  ctx.fillStyle=`rgba(80,230,255,${.25+(i%5)*.14})`;ctx.fillRect(x,y,2.5,2.5);
 }
 ctx.restore?.();
 requestAnimationFrame(draw);
}
draw();
const mode=document.getElementById('mode'),chat=document.getElementById('chat');
function add(text,who){const d=document.createElement('div');d.className='msg '+who;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
async function post(url,data){
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const j=await r.json();if(!r.ok)throw Error(j.error||'Errore server');return j;
}
async function send(){
 const box=document.getElementById('message'),message=box.value.trim();if(!message)return;
 box.value='';add(message,'user');activity='busy';mode.textContent='PROCESSING NEURAL DATA';
 document.getElementById('send').disabled=true;
 try{const j=await post('/api/chat',{message});add(j.answer,'');}
 catch(e){add('Errore: '+e.message,'');}
 finally{activity='idle';mode.textContent='SYSTEM STANDBY';document.getElementById('send').disabled=false}
}
document.getElementById('send').onclick=send;
document.getElementById('message').addEventListener('keydown',e=>{if(e.key==='Enter')send()});
document.getElementById('scan').onclick=async()=>{
 const target=document.getElementById('target').value.trim();
 const authorized=document.getElementById('authorized').checked;
 if(!target||!authorized){alert('Inserire IP e confermare l’autorizzazione.');return}
 if(!confirm('Avviare Nmap su '+target+'?'))return;
 activity='busy';mode.textContent='SCANNING TARGET';
 const out=document.getElementById('result');out.textContent='Scansione e analisi AI in corso...';
 document.getElementById('scan').disabled=true;
 try{const j=await post('/api/nmap',{target,authorized:true});out.textContent='RAPPORTO NMAP\n\n'+j.report+'\n\nANALISI AI\n\n'+j.analysis;}
 catch(e){out.textContent='Errore: '+e.message}
 finally{activity='idle';mode.textContent='SYSTEM STANDBY';document.getElementById('scan').disabled=false}
};
fetch('/api/status').then(r=>r.json()).then(j=>{
 document.getElementById('connection').textContent='● AI LINK ACTIVE';
}).catch(()=>document.getElementById('connection').textContent='● AI LINK ERROR');
</script>
</body>
</html>'''

Path("hud_app.py").write_text(server, encoding="utf-8")
Path("static/index.html").write_text(html, encoding="utf-8")

print("Creati hud_app.py e static/index.html")
print("HexSecGPT.py e .HexSec non sono stati modificati.")
