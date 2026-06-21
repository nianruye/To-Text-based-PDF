pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let currentJobId = null;
let ws = null;
let pollTimer = null;

// DOM elements
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const stageLabel = document.getElementById('stageLabel');
const pageLabel = document.getElementById('pageLabel');
const progressMessage = document.getElementById('progressMessage');
const cancelBtn = document.getElementById('cancelBtn');
const resultSection = document.getElementById('resultSection');
const downloadBtn = document.getElementById('downloadBtn');
const newFileBtn = document.getElementById('newFileBtn');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');

// Upload zone events
uploadZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
});

cancelBtn.addEventListener('click', () => {
  if (ws) { ws.send('cancel'); }
  stopPolling();
  resetUI();
});

newFileBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

function resetUI() {
  if (ws) { ws.close(); ws = null; }
  stopPolling();
  currentJobId = null;
  uploadZone.classList.remove('hidden');
  progressSection.classList.add('hidden');
  resultSection.classList.add('hidden');
  errorSection.classList.add('hidden');
  progressBar.style.width = '0%';
  fileInput.value = '';
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function handleFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showError('请上传 PDF 格式的文件。');
    return;
  }

  uploadZone.classList.add('hidden');
  errorSection.classList.add('hidden');
  progressSection.classList.remove('hidden');
  stageLabel.textContent = '上传中...';
  progressMessage.textContent = '';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await resp.json();

    if (data.status === 'error' || data.error_code) {
      showError(data.message || 'Upload failed.');
      return;
    }

    currentJobId = data.job_id;
    stageLabel.textContent = '准备处理...';
    progressBar.style.width = '0%';
    connectWebSocket(data.websocket_url);
  } catch (err) {
    showError('上传失败: ' + err.message);
  }
}

function connectWebSocket(url) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}${url}`;

  try {
    ws = new WebSocket(wsUrl);
  } catch (e) {
    startPolling();
    return;
  }

  // Fallback to polling if WebSocket doesn't connect within 3 seconds
  const connectTimeout = setTimeout(() => {
    if (ws && ws.readyState === WebSocket.CONNECTING) {
      ws.close();
      ws = null;
      startPolling();
    }
  }, 3000);

  ws.onopen = () => {
    clearTimeout(connectTimeout);
  };

  ws.onmessage = (event) => {
    handleProgressMessage(JSON.parse(event.data));
  };

  ws.onerror = () => {
    // WebSocket failed, fall back to HTTP polling
    if (ws) { ws.close(); ws = null; }
    startPolling();
  };

  ws.onclose = () => {
    ws = null;
  };
}

function startPolling() {
  stopPolling();
  if (!currentJobId) return;

  pollStatus(); // immediate first poll
  pollTimer = setInterval(pollStatus, 2000);
}

async function pollStatus() {
  if (!currentJobId) return;
  try {
    const resp = await fetch(`/api/status/${currentJobId}`);
    const data = await resp.json();

    if (data.error_code) return;

    const total = data.total_pages || 1;
    const pct = total > 0 ? (data.processed_pages / total) * 100 : 0;

    handleProgressMessage({
      job_id: currentJobId,
      stage: data.status,
      progress: pct,
      page: data.processed_pages,
      total_pages: total,
      message: data.error_message || '',
      download_url: data.status === 'complete' ? `/api/download/${currentJobId}` : null,
    });

    if (data.status === 'complete') {
      stopPolling();
    }
  } catch (err) {
    // Retry on next interval
  }
}

function handleProgressMessage(msg) {
  if (msg.status === 'error' || msg.error_code) {
    showError(msg.message || '处理出错。');
    return;
  }

  progressBar.style.width = msg.progress + '%';

  const stageNames = {
    pending: '准备处理...',
    extracting: '提取页面...',
    preprocessing: '图像预处理...',
    ocr: 'OCR 文字识别...',
    generating: '生成 PDF...',
    complete: '完成!',
    failed: '处理失败',
    cancelled: '已取消',
  };

  stageLabel.textContent = stageNames[msg.stage] || msg.stage;
  progressMessage.textContent = msg.message || '';

  if (msg.total_pages > 0) {
    pageLabel.textContent = msg.page ? `${msg.page}/${msg.total_pages} 页` : `共 ${msg.total_pages} 页`;
  }

  if (msg.stage === 'complete') {
    onComplete(msg);
  }
}

function onComplete(msg) {
  stopPolling();
  progressSection.classList.add('hidden');
  resultSection.classList.remove('hidden');
  downloadBtn.href = msg.download_url || `/api/download/${currentJobId}`;

  loadPreview('originalPreview', `/api/download/${currentJobId}`, false);
  loadPreview('enhancedPreview', msg.download_url || `/api/download/${currentJobId}`, true);

  if (ws) { ws.close(); ws = null; }
}

async function loadPreview(containerId, url, isEnhanced) {
  const container = document.getElementById(containerId);
  container.innerHTML = '<p style="padding:20px;color:#999;">加载预览中...</p>';

  try {
    const pdf = await pdfjsLib.getDocument(url).promise;
    container.innerHTML = '';

    for (let i = 1; i <= Math.min(pdf.numPages, 3); i++) {
      const page = await pdf.getPage(i);
      const viewport = page.getViewport({ scale: 0.3 });
      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d');
      await page.render({ canvasContext: ctx, viewport }).promise;
      container.appendChild(canvas);
    }
  } catch (err) {
    container.innerHTML = '<p style="padding:20px;color:#999;">预览加载失败</p>';
  }
}

function showError(msg) {
  stopPolling();
  progressSection.classList.add('hidden');
  uploadZone.classList.add('hidden');
  resultSection.classList.add('hidden');
  errorSection.classList.remove('hidden');
  errorMessage.textContent = msg;
}
