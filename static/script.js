/* ─── State ────────────────────────────────────────────────────── */
let history = [];   // [{role, content}, ...]
let isLoading = false;
let adminPassword = sessionStorage.getItem('adminPassword') || '';

/* ─── Panel switching ───────────────────────────────────────────── */
function showPanel(name) {
  document.getElementById('chatPanel').classList.toggle('hidden', name !== 'chat');
  document.getElementById('docsPanel').classList.toggle('hidden', name !== 'docs');
  document.getElementById('btnChat').classList.toggle('active', name === 'chat');
  document.getElementById('btnDocs').classList.toggle('active', name === 'docs');
  document.getElementById('panelTitle').textContent =
    name === 'chat' ? 'Ask about Philip Jaisohn' : 'Knowledge Base Documents';
  if (name === 'docs') {
    if (adminPassword) {
      showDocsContent();
    } else {
      showDocsLock();
    }
  }
}

function showDocsLock() {
  document.getElementById('docsLock').classList.remove('hidden');
  document.getElementById('docsContent').classList.add('hidden');
  document.getElementById('lockError').classList.add('hidden');
  document.getElementById('adminPassword').value = '';
  setTimeout(() => document.getElementById('adminPassword').focus(), 50);
}

function showDocsContent() {
  document.getElementById('docsLock').classList.add('hidden');
  document.getElementById('docsContent').classList.remove('hidden');
  loadDocuments();
}

async function submitPassword(e) {
  e.preventDefault();
  const input = document.getElementById('adminPassword');
  const pw = input.value;

  // Verify against the backend
  const res = await fetch('/api/documents/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Password': pw },
    body: JSON.stringify({}),
  });

  if (res.ok) {
    adminPassword = pw;
    sessionStorage.setItem('adminPassword', pw);
    showDocsContent();
  } else {
    document.getElementById('lockError').classList.remove('hidden');
    input.value = '';
    input.focus();
  }
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}
document.getElementById('sidebarClose').onclick = () =>
  document.getElementById('sidebar').classList.remove('open');

/* ─── New chat ──────────────────────────────────────────────────── */
function newChat() {
  history = [];
  const msgs = document.getElementById('messages');
  msgs.innerHTML = `
    <div class="welcome">
      <div class="welcome-avatar">JF</div>
      <h2>Welcome to the Philip Jaisohn AI Assistant</h2>
      <p>Ask me anything about Dr. Philip Jaisohn — his life, legacy, advocacy for Korean independence, medical career, and lasting contributions to democracy.</p>
      <div class="suggestions">
        <button class="suggestion" onclick="sendSuggestion(this)">Who was Philip Jaisohn?</button>
        <button class="suggestion" onclick="sendSuggestion(this)">What was the Independence Club?</button>
        <button class="suggestion" onclick="sendSuggestion(this)">How did Jaisohn become a U.S. citizen?</button>
        <button class="suggestion" onclick="sendSuggestion(this)">What is the Independent newspaper?</button>
      </div>
    </div>`;
  showPanel('chat');
  document.getElementById('sidebar').classList.remove('open');
}

/* ─── Chat ──────────────────────────────────────────────────────── */
function sendSuggestion(btn) {
  document.getElementById('userInput').value = btn.textContent;
  sendMessage();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

async function sendMessage(e) {
  if (e) e.preventDefault();
  if (isLoading) return;

  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;

  // Clear welcome screen on first message
  const welcome = document.querySelector('.welcome');
  if (welcome) welcome.remove();

  input.value = '';
  input.style.height = 'auto';

  history.push({ role: 'user', content: text });
  appendMessage('user', text);

  const typingId = appendTyping();
  setLoading(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history }),
    });
    const data = await res.json();
    removeTyping(typingId);

    if (!res.ok || data.error) {
      appendMessage('assistant', `Sorry, something went wrong: ${data.error || res.statusText}`);
    } else {
      history.push({ role: 'assistant', content: data.reply });
      appendMessage('assistant', data.reply);
    }
  } catch (err) {
    removeTyping(typingId);
    appendMessage('assistant', 'Network error — please check your connection and try again.');
  } finally {
    setLoading(false);
  }
}

function appendMessage(role, text) {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === 'user' ? 'You' : 'JF'}</div>
    <div class="msg-bubble">${formatText(text)}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function appendTyping() {
  const msgs = document.getElementById('messages');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">JF</div>
    <div class="msg-bubble">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function setLoading(val) {
  isLoading = val;
  const btn = document.getElementById('sendBtn');
  btn.disabled = val;
  const input = document.getElementById('userInput');
  input.disabled = val;
}

function formatText(text) {
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/\n/g,'<br>');
}

/* Auto-resize textarea */
document.getElementById('userInput').addEventListener('input', function () {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 140) + 'px';
});

/* ─── Documents ─────────────────────────────────────────────────── */
async function loadDocuments() {
  const list = document.getElementById('docsList');
  list.innerHTML = '<p class="docs-empty">Loading...</p>';
  try {
    const res = await fetch('/api/documents');
    const data = await res.json();
    renderDocuments(data.documents || []);
  } catch {
    list.innerHTML = '<p class="docs-empty">Failed to load documents.</p>';
  }
}

function renderDocuments(docs) {
  const list = document.getElementById('docsList');
  if (!docs.length) {
    list.innerHTML = '<p class="docs-empty">No documents uploaded yet.</p>';
    return;
  }
  list.innerHTML = docs.map(d => `
    <div class="doc-item" id="doc-${d.doc_id}">
      <div class="doc-icon">📄</div>
      <div class="doc-info">
        <div class="doc-name">${esc(d.source)}</div>
        <div class="doc-meta">${d.chunk_count} text chunk${d.chunk_count !== 1 ? 's' : ''} indexed</div>
      </div>
      <button class="doc-delete" onclick="deleteDocument('${d.doc_id}')">Remove</button>
    </div>`).join('');
}

async function deleteDocument(docId) {
  if (!confirm('Remove this document from the knowledge base?')) return;
  try {
    const res = await fetch(`/api/documents/${docId}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Password': adminPassword },
    });
    if (res.ok) {
      document.getElementById(`doc-${docId}`)?.remove();
      if (!document.querySelector('.doc-item')) {
        document.getElementById('docsList').innerHTML = '<p class="docs-empty">No documents uploaded yet.</p>';
      }
    }
  } catch {
    alert('Failed to remove document.');
  }
}

function esc(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ─── Upload ────────────────────────────────────────────────────── */
const uploadZone = document.getElementById('uploadZone');
const fileInput  = document.getElementById('fileInput');

uploadZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => uploadFiles(fileInput.files));

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  uploadFiles(e.dataTransfer.files);
});

async function uploadFiles(files) {
  const arr = Array.from(files);
  if (!arr.length) return;

  const progress = document.getElementById('uploadProgress');
  const bar      = document.getElementById('progressBar');
  const label    = document.getElementById('progressLabel');

  progress.classList.remove('hidden');
  bar.style.width = '0%';
  label.textContent = `Uploading 0 / ${arr.length}…`;

  let done = 0;
  for (const file of arr) {
    label.textContent = `Uploading "${file.name}"…`;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'X-Admin-Password': adminPassword },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Error uploading "${file.name}": ${data.error}`);
      }
    } catch {
      alert(`Network error uploading "${file.name}".`);
    }
    done++;
    bar.style.width = `${(done / arr.length) * 100}%`;
  }

  label.textContent = `Done — ${done} file${done !== 1 ? 's' : ''} processed.`;
  setTimeout(() => progress.classList.add('hidden'), 3000);
  fileInput.value = '';
  await loadDocuments();
}
