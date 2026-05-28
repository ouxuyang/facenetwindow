from flask import Flask, Response, render_template_string, request, send_from_directory
import queue
import json
import time
import os
import uuid

app = Flask(__name__)
clients = []
messages = []

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)



HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>局域网消息板</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0d0d0d;
      --surface: #161616;
      --border: #2a2a2a;
      --accent: #c8f542;
      --accent-dim: #8fad2a;
      --text: #e8e8e8;
      --text-muted: #666;
      --danger: #ff4d4d;
      --file-bg: #0f1a1f;
      --file-border: #1e3a4a;
      --file-accent: #42b8f5;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg); color: var(--text);
      font-family: 'Noto Serif SC', serif;
      min-height: 100vh; display: flex; flex-direction: column;
    }
    header {
      border-bottom: 1px solid var(--border);
      padding: 18px 28px; display: flex;
      align-items: center; justify-content: space-between;
      position: sticky; top: 0; background: var(--bg); z-index: 10;
    }
    .logo {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px; color: var(--accent);
      letter-spacing: 0.15em; text-transform: uppercase;
    }
    .status {
      display: flex; align-items: center; gap: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px; color: var(--text-muted);
    }
    .dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--accent); animation: pulse 2s infinite;
    }
    .dot.offline { background: var(--danger); animation: none; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .compose {
      padding: 16px 28px; border-bottom: 1px solid var(--border);
      display: flex; flex-direction: column; gap: 10px;
    }
    .compose-row { display: flex; gap: 10px; align-items: flex-end; }
    .compose textarea {
      flex: 1; background: var(--surface); border: 1px solid var(--border);
      border-radius: 6px; color: var(--text);
      font-family: 'Noto Serif SC', serif; font-size: 15px;
      padding: 12px 16px; resize: none; outline: none;
      min-height: 52px; max-height: 160px;
      transition: border-color 0.2s; line-height: 1.6;
    }
    .compose textarea::placeholder { color: var(--text-muted); }
    .compose textarea:focus { border-color: var(--accent-dim); }

    .btn {
      border: none; border-radius: 6px; padding: 13px 20px;
      font-family: 'JetBrains Mono', monospace; font-size: 13px;
      font-weight: 600; cursor: pointer; white-space: nowrap;
      transition: background 0.15s, transform 0.1s; letter-spacing: 0.05em;
    }
    .btn:active { transform: scale(0.97); }
    .btn-primary { background: var(--accent); color: #0d0d0d; }
    .btn-primary:hover { background: #d8ff55; }
    .btn-secondary {
      background: var(--surface); color: var(--text-muted);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover { border-color: var(--accent-dim); color: var(--text); }

    .drop-zone {
      border: 1px dashed var(--border); border-radius: 6px;
      padding: 20px 18px; text-align: center;
      font-family: 'JetBrains Mono', monospace; font-size: 12px;
      color: var(--text-muted); cursor: pointer;
      transition: border-color 0.2s, background 0.2s; display: none;
    }
    .drop-zone.visible { display: block; }
    .drop-zone.dragover { border-color: var(--accent); background: #1a1f0d; color: var(--accent); }

    .file-preview {
      display: none; align-items: center; gap: 10px;
      background: var(--file-bg); border: 1px solid var(--file-border);
      border-radius: 6px; padding: 10px 14px;
      font-family: 'JetBrains Mono', monospace; font-size: 12px;
    }
    .file-preview.visible { display: flex; }
    .file-preview .fname { flex: 1; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .file-preview .fsize { color: var(--text-muted); flex-shrink: 0; }
    .file-preview .remove { cursor: pointer; color: var(--danger); font-size: 16px; line-height: 1; flex-shrink: 0; }

    .progress-wrap { display: none; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
    .progress-wrap.visible { display: block; }
    .progress-bar { height: 100%; background: var(--accent); width: 0%; transition: width 0.15s; }

    .feed {
      flex: 1; padding: 24px 28px;
      display: flex; flex-direction: column; gap: 14px; overflow-y: auto;
    }
    .empty {
      margin: auto; text-align: center; color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 2;
    }
    .msg {
      background: var(--surface); border: 1px solid var(--border);
      border-left: 3px solid var(--accent); border-radius: 6px;
      padding: 14px 18px; animation: slideIn 0.25s ease;
    }
    .msg.new { background: #1a1f0d; }
    .msg.file-msg { border-left-color: var(--file-accent); }
    @keyframes slideIn { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }

    .msg-meta {
      font-family: 'JetBrains Mono', monospace; font-size: 10px;
      color: var(--text-muted); margin-bottom: 6px; letter-spacing: 0.05em;
    }
    .msg-text { font-size: 15px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }

    .file-card {
      display: flex; align-items: center; gap: 14px;
      background: var(--file-bg); border: 1px solid var(--file-border);
      border-radius: 6px; padding: 12px 16px;
      text-decoration: none; transition: border-color 0.2s;
    }
    .file-card:hover { border-color: var(--file-accent); }
    .file-icon { font-size: 28px; line-height: 1; flex-shrink: 0; }
    .file-info { flex: 1; overflow: hidden; }
    .file-name {
      font-family: 'JetBrains Mono', monospace; font-size: 13px;
      color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .file-size { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text-muted); margin-top: 3px; }
    .download-hint { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--file-accent); flex-shrink: 0; }

    footer {
      border-top: 1px solid var(--border); padding: 10px 28px;
      font-family: 'JetBrains Mono', monospace; font-size: 10px;
      color: var(--text-muted); display: flex; justify-content: space-between;
    }
    @media (max-width: 480px) {
      header, .compose, .feed, footer { padding-left: 16px; padding-right: 16px; }
      .compose-row { flex-wrap: wrap; }
      .btn { flex: 1; text-align: center; }
    }
  </style>
</head>
<body>

<header>
  <div class="logo">📡 LAN Board</div>
  <div class="status">
    <div class="dot" id="dot"></div>
    <span id="status-text">连接中...</span>
  </div>
</header>

<div class="compose">
  <div class="compose-row">
    <textarea id="input" placeholder="输入消息，Ctrl+Enter 发送..." rows="1"></textarea>
    <button class="btn btn-secondary" onclick="toggleDrop()">📎 文件</button>
    <button class="btn btn-primary" onclick="sendAll()">发 送</button>
  </div>

  <div class="drop-zone" id="dropZone"
       onclick="document.getElementById('fileInput').click()"
       ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
    点击选择文件，或将文件拖到这里<br>

  </div>
  <input type="file" id="fileInput" style="display:none" onchange="onFileSelect(event)">

  <div class="file-preview" id="filePreview">
    <span class="file-icon" id="previewIcon">📄</span>
    <span class="fname" id="previewName"></span>
    <span class="fsize" id="previewSize"></span>
    <span class="remove" onclick="clearFile()">✕</span>
  </div>

  <div class="progress-wrap" id="progressWrap">
    <div class="progress-bar" id="progressBar"></div>
  </div>
</div>

<div class="feed" id="feed">
  <div class="empty" id="empty">暂无消息<br>发送第一条试试</div>
</div>

<footer>
  <span id="count">0 条消息</span>
  <span>实时同步</span>
</footer>

<script>
  let msgCount = 0;
  let pendingFile = null;
  let dropVisible = false;

  function fileIcon(name) {
    const ext = (name.split('.').pop() || '').toLowerCase();
    const map = {
      pdf:'📕', doc:'📘', docx:'📘', xls:'📗', xlsx:'📗',
      ppt:'📙', pptx:'📙', zip:'🗜️', rar:'🗜️', '7z':'🗜️',
      jpg:'🖼️', jpeg:'🖼️', png:'🖼️', gif:'🖼️', webp:'🖼️', svg:'🖼️',
      mp4:'🎬', mov:'🎬', avi:'🎬', mkv:'🎬',
      mp3:'🎵', wav:'🎵', flac:'🎵', aac:'🎵',
      txt:'📄', md:'📄', py:'🐍', js:'📜', html:'🌐', css:'🎨',
    };
    return map[ext] || '📄';
  }

  function fmtSize(b) {
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
    return (b/1048576).toFixed(1) + ' MB';
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // 历史记录
  fetch('/history').then(r => r.json()).then(msgs => {
    msgs.forEach(m => addItem(m, false));
  });

  // SSE
  const es = new EventSource('/stream');
  es.onopen = () => {
    document.getElementById('dot').classList.remove('offline');
    document.getElementById('status-text').textContent = '已连接';
  };
  es.onmessage = e => addItem(JSON.parse(e.data), true);
  es.onerror = () => {
    document.getElementById('dot').classList.add('offline');
    document.getElementById('status-text').textContent = '连接断开，重连中...';
  };

  function addItem(data, isNew) {
    const empty = document.getElementById('empty');
    if (empty) empty.remove();
    msgCount++;
    const feed = document.getElementById('feed');
    const div = document.createElement('div');

    if (data.type === 'file') {
      div.className = 'msg file-msg' + (isNew ? ' new' : '');
      div.innerHTML = `
        <div class="msg-meta">${escHtml(data.time)} · 文件</div>
        <a class="file-card" href="/uploads/${data.file_id}/${encodeURIComponent(data.filename)}" download="${escHtml(data.filename)}">
          <div class="file-icon">${fileIcon(data.filename)}</div>
          <div class="file-info">
            <div class="file-name">${escHtml(data.filename)}</div>
            <div class="file-size">${fmtSize(data.size)}</div>
          </div>
          <div class="download-hint">↓ 下载</div>
        </a>`;
    } else {
      div.className = 'msg' + (isNew ? ' new' : '');
      div.innerHTML = `
        <div class="msg-meta">${escHtml(data.time)}</div>
        <div class="msg-text">${escHtml(data.text)}</div>`;
    }

    feed.prepend(div);
    document.getElementById('count').textContent = msgCount + ' 条消息';
    if (isNew) setTimeout(() => div.classList.remove('new'), 2000);
  }

  function sendAll() {
    if (pendingFile) uploadFile();
    else sendMsg();
  }

  function sendMsg() {
    const input = document.getElementById('input');
    const text = input.value.trim();
    if (!text) return;
    fetch('/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    input.value = '';
    input.style.height = 'auto';
  }

  document.getElementById('input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.ctrlKey) sendAll();
  });
  document.getElementById('input').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 160) + 'px';
  });

  function toggleDrop() {
    dropVisible = !dropVisible;
    document.getElementById('dropZone').classList.toggle('visible', dropVisible);
  }

  function onDragOver(e) { e.preventDefault(); document.getElementById('dropZone').classList.add('dragover'); }
  function onDragLeave() { document.getElementById('dropZone').classList.remove('dragover'); }
  function onDrop(e) {
    e.preventDefault();
    document.getElementById('dropZone').classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
  }
  function onFileSelect(e) { const f = e.target.files[0]; if (f) setFile(f); }

  function setFile(file) {
    pendingFile = file;
    document.getElementById('previewIcon').textContent = fileIcon(file.name);
    document.getElementById('previewName').textContent = file.name;
    document.getElementById('previewSize').textContent = fmtSize(file.size);
    document.getElementById('filePreview').classList.add('visible');
    document.getElementById('dropZone').classList.remove('visible');
    dropVisible = false;
  }

  function clearFile() {
    pendingFile = null;
    document.getElementById('filePreview').classList.remove('visible');
    document.getElementById('fileInput').value = '';
  }

  function uploadFile() {
    if (!pendingFile) return;
    const fd = new FormData();
    fd.append('file', pendingFile);
    const prog = document.getElementById('progressBar');
    const wrap = document.getElementById('progressWrap');
    wrap.classList.add('visible');
    prog.style.width = '0%';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.onprogress = e => {
      if (e.lengthComputable) prog.style.width = (e.loaded / e.total * 100) + '%';
    };
    xhr.onload = () => {
      wrap.classList.remove('visible');
      prog.style.width = '0%';
      clearFile();
    };
    xhr.onerror = () => { wrap.classList.remove('visible'); alert('上传失败'); };
    xhr.send(fd);
  }
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/history')
def history():
    return json.dumps(messages, ensure_ascii=False)

@app.route('/stream')
def stream():
    q = queue.Queue()
    clients.append(q)
    def generate():
        try:
            while True:
                msg = q.get()
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        except GeneratorExit:
            if q in clients:
                clients.remove(q)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return 'empty', 400
    msg = {'type': 'text', 'text': text, 'time': time.strftime('%Y-%m-%d %H:%M:%S')}
    _broadcast(msg)
    return 'ok'

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if not f:
        return 'no file', 400
    file_id = uuid.uuid4().hex
    save_dir = os.path.join(UPLOAD_DIR, file_id)
    os.makedirs(save_dir, exist_ok=True)
    filename = f.filename
    filepath = os.path.join(save_dir, filename)
    with open(filepath, 'wb') as out:
        while True:
            chunk = f.stream.read(1024 * 1024)  # 每次读 1MB
            if not chunk:
                break
            out.write(chunk)
    size = os.path.getsize(filepath)
    msg = {
        'type': 'file',
        'file_id': file_id,
        'filename': filename,
        'size': size,
        'time': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    _broadcast(msg)
    return 'ok'

@app.route('/uploads/<file_id>/<filename>')
def download(file_id, filename):
    save_dir = os.path.join(UPLOAD_DIR, file_id)
    return send_from_directory(save_dir, filename, as_attachment=True)

def _broadcast(msg):
    messages.append(msg)
    if len(messages) > 100:
        messages.pop(0)
    for q in clients:
        q.put(msg)

if __name__ == '__main__':
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    print(f"""
╔══════════════════════════════════╗
║        局域网消息板已启动        ║
╠══════════════════════════════════╣
║  本机访问: http://localhost:8080 ║
║  手机访问: http://{local_ip}:8080
║  Ctrl+C 停止服务                 ║
╚══════════════════════════════════╝
""")
    from waitress import serve

    serve(app, host='0.0.0.0', port=8080, channel_timeout=3600, threads=32)