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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))