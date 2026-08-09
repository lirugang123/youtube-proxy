# yt-dlp web server for Railway
import yt_dlp, json, os, tempfile
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

def search(q, n=10):
    try:
        with yt_dlp.YoutubeDL({'extractor': f'ytsearch{n}', 'quiet': True, 'no_warnings': True, 'socket_timeout': 10}) as ydl:
            info = ydl.extract_info(f"ytsearch{n}:{q}", download=False)
            if not info or not info.get('entries'): return {'error': '无结果'}
            return [{'id': e.get('id'), 'title': e.get('title',''), 'duration': e.get('duration',0),
                     'thumbnail': e.get('thumbnail',''), 'channel': e.get('channel',''),
                     'view_count': e.get('view_count',0)} for e in info['entries']]
    except Exception as e: return {'error': str(e)}

@app.route('/')
def index():
    return open('/app/index.html', encoding='utf-8').read() if os.path.exists('/app/index.html') else _HTML

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
.m{font-size:11px;color:#aaa;flex-wrap:wrap;gap:6px}.o{display:none;position:fixed;inset:0;background:#000;z-index:999;flex-direction:column}
.o.a{display:flex}.ph{padding:10px 16px;background:#1a1a1a;display:flex;align-items:center;gap:10px}
.cb{background:none;border:none;color:#fff;font-size:18px;cursor:pointer}.pt{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:600px}
.pc{flex:1;display:flex;align-items:center;justify-content:center}video{width:100%;max-height:100%;aspect-ratio:16/9}
.l{display:none;text-align:center;padding:30px;color:#aaa}.l.a{display:block}.e{color:#ff4444;text-align:center;padding:20px}
.f{text-align:center;padding:25px;color:#555;font-size:11px;margin-top:15px}</style></head>
<body><div class="c"><h1>&#9654; YouTube</h1><div class="s"><input id="qi" placeholder="搜索..." onkeydown="if(event.key==='Enter')sr()"><button onclick="sr()">搜索</button></div>
<div class="l" id="l">搜索中...</div><div class="r" id="r"></div><div class="f">YouTube Proxy via yt-dlp</div></div>
<div class="o" id="o"><div class="ph"><button class="cb" onclick="cl()">✕</button><span class="pt" id="pt"></span></div><div class="pc"><video id="vp" controls autoplay></video></div></div>
<script>async function sr(){const q=document.getElementById('qi').value.trim();if(!q)return;
document.getElementById('l').classList.add('a');document.getElementById('r').innerHTML='';
try{const d=await(await fetch('/search?q='+encodeURIComponent(q))).json();
document.getElementById('l').classList.remove('a');
if(d.error){document.getElementById('r').innerHTML='<div class="e">'+d.error+'</div>';return;}
d.forEach(v=>{const dur=v.duration?Math.floor(v.duration/60)+':'+('0'+Math.floor(v.duration%60)).slice(-2):'';
const c=document.createElement('div');c.className='v';c.onclick=()=>pl(v.id,v.title);
c.innerHTML=`<img class="t" src="${v.thumbnail}" loading="lazy"><div class="i"><div class="tt">${v.title.replace(/</g,'&lt;')}</div><div class="m" style="display:flex"><span>${dur}</span><span>${v.channel.replace(/</g,'&lt;')}</span></div></div>`;
document.getElementById('r').appendChild(c);})}catch(e){document.getElementById('l').classList.remove('a');alert(e)}}
function pl(id,t){document.getElementById('o').classList.add('a');document.getElementById('pt').textContent=t;
document.getElementById('vp').src='/stream/'+id;document.body.style.overflow='hidden';}
function cl(){document.getElementById('o').classList.remove('a');document.getElementById('vp').src='';document.body.style.overflow='';}
document.addEventListener('keydown',e=>{if(e.key==='Escape')cl()})</script></body></html>'''

@app.route('/search')
def search_ep():
    return jsonify(search(request.args.get('q','')) if request.args.get('q') else {'error': '请输入搜索词'})

@app.route('/stream/<video_id>')
def stream(video_id):
    tmpdir = tempfile.mkdtemp()
    outtmpl = tmpdir + '/video.%(ext)s'
    ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True,
        'format': 'best[ext=mp4]/best[height<=720][ext=mp4]',
        'socket_timeout': 60, 'retries': 3, 'outtmpl': outtmpl}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        files = os.listdir(tmpdir)
        if not files: return jsonify({'error': '下载失败'}), 404
        return send_file(tmpdir + '/' + files[0], as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import re, base64
from urllib.parse import urlparse

PROXY_BASE = os.environ.get('PROXY_BASE', 'https://youtube-proxy-production-2720.up.railway.app')

def b64encode(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')

def b64decode(s):
    s = s + '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s).decode()

def rewrite_url(s):
    """Rewrite a URL to go through the proxy"""
    try:
        return f"/proxy/{b64encode(s)}"
    except:
        return s

def rewrite_html(content, base_url):
    """Rewrite all links in HTML to go through proxy"""
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    # Rewrite href attributes
    content = re.sub(
        r'(href\s*=\s*)(["\'])(https?://[^\2]*)\2',
        lambda m: f'{m.group(1)}{m.group(2)}{rewrite_url(m.group(3))}{m.group(2)}',
        content
    )
    content = re.sub(
        r'(href\s*=\s*)(["\'])(/[^\2]*?)\2',
        lambda m: f'{m.group(1)}{m.group(2)}{rewrite_url(domain + m.group(3))}{m.group(2)}',
        content
    )
    # Rewrite src attributes
    content = re.sub(
        r'(src\s*=\s*)(["\'])(https?://[^\2]*?)\2',
        lambda m: f'{m.group(1)}{m.group(2)}{rewrite_url(m.group(3))}{m.group(2)}',
        content
    )
    content = re.sub(
        r'(src\s*=\s*)(["\'])(/[^\2]*?)\2',
        lambda m: f'{m.group(1)}{m.group(2)}{rewrite_url(domain + m.group(3))}{m.group(2)}',
        content
    )
    # Rewrite action attributes
    content = re.sub(
        r'(action\s*=\s*)(["\'])(https?://[^\2]*?)\2',
        lambda m: f'{m.group(1)}{m.group(2)}{rewrite_url(m.group(3))}{m.group(2)}',
        content
    )
    # Rewrite background-image in inline CSS
    content = re.sub(
        r'(url\s*\(\s*)(["\']?)(https?://[^\1]*?\3)',
        lambda m: f'url({rewrite_url(m.group(3))})',
        content
    )
    # Rewrite <base href>
    content = re.sub(
        r'(<base\s+[^>]*href\s*=\s*)["\'](https?://[^"\']*)["\']',
        lambda m: f'\\1"{rewrite_url(m.group(2))}"',
        content
    )
    # Inject script to handle JS-initiated navigation
    inject = f'''
<script>
(function(){{
    const origOpen = window.open;
    window.open = function(url) {{
        if(url && !url.startsWith('/') && !url.startsWith('javascript:')) {{
            url = '/proxy/{b64encode("PLACEHOLDER")}'
        }}
        return origOpen.call(window, url);
    }};
    document.querySelectorAll('a,form').forEach(function(el) {{
        el.addEventListener('click', function(e) {{
            var href = this.getAttribute('href');
            var action = this.getAttribute('action');
            var target = href || action;
            if(target && target.startsWith('http')) {{
                e.preventDefault();
                window.location.href = target;
            }}
        }});
    }});
}})();
</script>'''
    content = content.replace('</body>', inject + '</body>', 1)

    return content

@app.route('/fetch/<path:url>')
def fetch(url):
    """Fetch any external URL and return raw content (old endpoint)"""
    try:
        if not url.startswith(('http://','https://')):
            url = 'https://' + url
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            ctype = resp.headers.get('Content-Type', 'application/octet-stream')
            return Response(content, content_type=ctype)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy/<path:url_b64>')
def proxy(url_b64):
    """Full web proxy with link rewriting"""
    try:
        url = b64decode(url_b64)
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'https://' + url

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            ctype = resp.headers.get('Content-Type', 'application/octet-stream')

            # Only rewrite HTML pages
            if 'html' in ctype.lower() or 'xml' in ctype.lower():
                try:
                    text = content.decode('utf-8', errors='replace')
                    text = rewrite_html(text, url)
                    content = text.encode('utf-8')
                    ctype = 'text/html; charset=utf-8'
                except:
                    pass

            # Redirect browser to proxy for relative URLs
            return Response(content, content_type=ctype, headers={
                'X-Proxy': 'Railway Proxy'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import urllib.request
from flask import Response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))