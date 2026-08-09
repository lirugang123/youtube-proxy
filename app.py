# Combined proxy server: YouTube + Web proxy + HTTP CONNECT
import socket, threading, os, json, re, base64, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import yt_dlp

# ── Helpers ──────────────────────────────────────────────
def b64enc(url): return base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')
def b64dec(s):
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s).decode()

def rewrite_html(html, base_url):
    p = urlparse(base_url)
    domain = f"{p.scheme}://{p.netloc}"
    # Rewrite absolute URLs
    for attr in ['href', 'src', 'action']:
        html = re.sub(rf'({attr}\s*=\s*["\'])(https?://[^"\']*?)(["\'])',
            lambda m, a=attr: f'{m.group(1)}/proxy/{b64enc(m.group(2))}{m.group(3)}', html)
        html = re.sub(rf'({attr}\s*=\s*["\'])(/[^"\']*?)(["\'])',
            lambda m: f'{m.group(1)}/proxy/{b64enc(domain + m.group(2))}{m.group(3)}', html)
    # Rewrite inline CSS url()
    html = re.sub(r'url\(\s*["\']?(https?://[^"\')\s]+)',
        lambda m: f'url("/proxy/{b64enc(m.group(1))}")', html)
    # Rewrite <base href>
    html = re.sub(r'(<base\s+[^>]*href\s*=\s*["\'])(https?://[^"\']*?)(["\'])',
        lambda m: f'{m.group(1)}/proxy/{b64enc(m.group(2))}{m.group(3)}', html)
    # JS fetch/xhr redirect
    html = html.replace('fetch(', 'fetch(window.location.pathname.startsWith("/proxy/")?"":"")')
    return html

def fetch_url(url, timeout=60):
    req = socket.create_connection(('0.0.0.0', 0)) if False else None
    import urllib.request
    r = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    })
    return urllib.request.urlopen(r, timeout=timeout)

# ── YouTube Search ──────────────────────────────────────
def youtube_search(q, n=10):
    try:
        with yt_dlp.YoutubeDL({'extractor': f'ytsearch{n}', 'quiet': True, 'no_warnings': True, 'socket_timeout': 15}) as ydl:
            info = ydl.extract_info(f"ytsearch{n}:{q}", download=False)
            if not info or not info.get('entries'): return {'error': '无结果'}
            return [{'id': e.get('id'), 'title': e.get('title',''), 'duration': e.get('duration',0),
                     'thumbnail': e.get('thumbnail',''), 'channel': e.get('channel',''),
                     'view_count': e.get('view_count',0)} for e in info['entries']]
    except Exception as e: return {'error': str(e)}

_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YouTube Proxy</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0f0f0f;color:#fff}
.c{max-width:1200px;margin:0 auto;padding:20px}h1{font-size:1.4rem;margin-bottom:12px;color:#ff0033}
.s{display:flex;margin-bottom:20px;gap:8px}.s input{flex:1;padding:12px;border-radius:8px;border:none;background:#1a1a1a;color:#fff;font-size:16px}
.s button{padding:12px 24px;background:#ff0033;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:16px}
.r{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.v{background:#1a1a1a;border-radius:8px;overflow:hidden;cursor:pointer;transition:transform .15s}.v:hover{transform:scale(1.02)}
.t{width:100%;aspect-ratio:16/9;object-fit:cover;background:#000}.i{padding:10px}
.tt{font-size:13px;font-weight:600;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:5px}
.m{font-size:11px;color:#aaa}.o{display:none;position:fixed;inset:0;background:#000;z-index:999;flex-direction:column}
.o.a{display:flex}.ph{padding:10px 16px;background:#1a1a1a;display:flex;align-items:center;gap:10px}
.cb{background:none;border:none;color:#fff;font-size:18px;cursor:pointer}.pt{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:600px}
.pc{flex:1;display:flex;align-items:center;justify-content:center}video{width:100%;max-height:100%;aspect-ratio:16/9}
.l{display:none;text-align:center;padding:30px;color:#aaa}.l.a{display:block}.e{color:#ff4444;text-align:center;padding:20px}
.f{text-align:center;padding:25px;color:#555;font-size:11px;margin-top:15px}</style></head>
<body><div class="c"><h1>&#9654; YouTube</h1><div class="s"><input id="qi" placeholder="搜索..." onkeydown="if(event.key==='Enter')sr()"><button onclick="sr()">搜索</button></div>
<div class="l" id="l">搜索中...</div><div class="r" id="r"></div>
<div style="margin-top:20px;padding:16px;background:#1a1a1a;border-radius:8px"><h3 style="font-size:13px;color:#aaa;margin-bottom:8px">🌐 访问任意网站</h3><div style="display:flex;gap:8px"><input id="ui" placeholder="输入网址，如 www.google.com" style="flex:1;padding:10px;border-radius:6px;border:none;background:#0f0f0f;color:#fff;font-size:14px"><button onclick="go()" style="padding:10px 20px;background:#444;color:#fff;border:none;border-radius:6px;cursor:pointer">打开</button></div><div style="margin-top:8px;font-size:11px;color:#666">通过境外服务器中转，HTML 链接自动可点击</div><script>function go(){var u=document.getElementById('ui').value.trim();if(!u)return;var t=u;if(!t.startsWith('http'))t='https://'+t;window.location.href='/proxy/'+t}</script></div>
<div class="f">YouTube Proxy via yt-dlp</div></div>
<div class="o" id="o"><div class="ph"><button class="cb" onclick="cl()">✕</button><span class="pt" id="pt"></span></div><div class="pc"><video id="vp" controls autoplay></video></div></div>
<script>async function sr(){const q=document.getElementById('qi').value.trim();if(!q)return;
document.getElementById('l').classList.add('a');document.getElementById('r').innerHTML='';
try{const d=await(await fetch('/search?q='+encodeURIComponent(q))).json();
document.getElementById('l').classList.remove('a');
if(d.error){document.getElementById('r').innerHTML='<div class="e">'+d.error+'</div>';return;}
d.forEach(v=>{const dur=v.duration?Math.floor(v.duration/60)+':'+('0'+Math.floor(v.duration%60)).slice(-2):'';
const c=document.createElement('div');c.className='v';c.onclick=()=>pl(v.id,v.title);
c.innerHTML=`<img class="t" src="${v.thumbnail}" loading="lazy"><div class="i"><div class="tt">${v.title.replace(/</g,'&lt;')}</div><div class="m"><span>${dur}</span><span>${v.channel.replace(/</g,'&lt;')}</span></div></div>`;
document.getElementById('r').appendChild(c);})}catch(e){document.getElementById('l').classList.remove('a');alert(e)}}
function pl(id,t){document.getElementById('o').classList.add('a');document.getElementById('pt').textContent=t;
document.getElementById('vp').src='/stream/'+id;document.body.style.overflow='hidden';}
function cl(){document.getElementById('o').classList.remove('a');document.getElementById('vp').src='';document.body.style.overflow='';}
document.addEventListener('keydown',e=>{if(e.key==='Escape')cl()})</script></body></html>'''

# ── HTTP Server ─────────────────────────────────────────
class ProxyHandler(BaseHTTPRequestHandler):
    server_version = 'RailwayProxy/1.0'

    def log_message(self, fmt, *args):
        pass  # suppress logs

    # ── CONNECT proxy (HTTPS tunnel) ─────────────────
    def do_CONNECT(self):
        try:
            host, port = self.path.rsplit(':', 1)
            port = int(port)
            remote = socket.create_connection((host, port), timeout=10)
            self.send_response(200)
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            local = self.request
            def pipe(a, b):
                try:
                    while True:
                        data = a.recv(65536)
                        if not data: break
                        b.sendall(data)
                except: pass
            t1 = threading.Thread(target=pipe, args=(local, remote), daemon=True)
            t2 = threading.Thread(target=pipe, args=(remote, local), daemon=True)
            t1.start(); t2.start()
            t1.join(timeout=300); t2.join(timeout=5)
            local.close(); remote.close()
        except Exception:
            try: self.send_error(502)
            except: pass

    # ── GET: routes ──────────────────────────────────
    def do_GET(self):
        path = self.path
        if path == '/':
            self._send_html(_HTML)
        elif path.startswith('/search'):
            q = urlparse(path).query.split('=', 1)[1] if '=' in urlparse(path).query else ''
            import urllib.parse
            q = urllib.parse.unquote(q)
            n = 10
            m = re.search(r'n=(\d+)', path)
            if m: n = int(m.group(1))
            results = youtube_search(q, n)
            self._send_json(200, results)
        elif path.startswith('/stream/'):
            self._stream_video(path[8:])
        elif path.startswith('/proxy/'):
            self._proxy_fetch(path[7:])
        elif path.startswith('/fetch/'):
            url = path[7:]
            if not url.startswith(('http://','https://')): url = 'https://' + url
            try:
                resp = fetch_url(url)
                content = resp.read()
                ctype = resp.headers.get('Content-Type', 'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        else:
            self.send_error(404)

    def _send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _stream_video(self, video_id):
        tmpdir = tempfile.mkdtemp()
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'format': 'best[ext=mp4]/best[height<=720][ext=mp4]',
            'socket_timeout': 60, 'retries': 3, 'outtmpl': tmpdir + '/v.%(ext)s'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            files = os.listdir(tmpdir)
            if not files:
                self._send_json(404, {'error': '下载失败'})
                return
            fpath = tmpdir + '/' + files[0]
            size = os.path.getsize(fpath)
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(size))
            self.end_headers()
            with open(fpath, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk: break
                    self.wfile.write(chunk)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _proxy_fetch(self, raw):
        try:
            import urllib.parse as up
            decoded = up.unquote(raw)
            # Handle /proxy/https://... (double slash from path)
            url = decoded
            if url.startswith('//'):
                url = url[1:]
            if '://' not in url:
                url = b64dec(url)
            if not url.startswith(('http://','https://')): url = 'https://' + url
            resp = fetch_url(url)
            content = resp.read()
            ctype = resp.headers.get('Content-Type', 'application/octet-stream')
            if 'html' in ctype.lower():
                text = content.decode('utf-8', errors='replace')
                text = rewrite_html(text, url)
                content = text.encode('utf-8')
                ctype = 'text/html; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json(500, {'error': str(e)})

# ── Main ────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = ThreadingHTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f'Proxy server running on :{port}')
    server.serve_forever()