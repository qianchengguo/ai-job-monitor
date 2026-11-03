"""UI-only preview. Simulated Chrome APIs, NOT an installed-extension acceptance test."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHIM="""
const prefix='ai-job-monitor-preview-only';
let state=JSON.parse(localStorage.getItem(prefix)||'{}');
window.chrome={storage:{local:{async get(keys){return Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,state[k]]));},async set(v){Object.assign(state,v);localStorage.setItem(prefix,JSON.stringify(state));}}},
runtime:{async sendMessage(){const r=await fetch('/data/feed.json',{cache:'no-store'});const f=await r.json();await chrome.storage.local.set({jobFeed:f,lastSyncedAt:new Date().toISOString()});return {ok:true};}},
permissions:{async request(){return false;}},tabs:{create({url}){window.open(url);}}};
const p=document.createElement('p');p.textContent='开发预览：Chrome API为模拟，本页不证明扩展已安装或系统通知已验证。';p.style.color='#a34c00';document.body.prepend(p);
await import('/extension/app.js?v=2');
"""
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  if self.path in ['/','/preview']:
   raw=(ROOT/'extension/index.html').read_text().replace('href="style.css"','href="/extension/style.css"').replace('src="app.js"','src="/preview-shim.js"').encode()
  elif self.path=='/preview-shim.js':raw=SHIM.encode()
  else:return super().do_GET()
  self.send_response(200);self.send_header('Content-Type','text/javascript' if self.path.endswith('.js') else 'text/html; charset=utf-8');self.end_headers();self.wfile.write(raw)
if __name__=='__main__':
 print('Preview (simulated Chrome API): http://127.0.0.1:18743',flush=True)
 ThreadingHTTPServer(('127.0.0.1',18743),partial(Handler,directory=str(ROOT))).serve_forever()
