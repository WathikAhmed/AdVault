"""
Meta Ad Library Scraper
Paste a Facebook Ad Library URL → scrapes all details + downloads media locally.
Run: python app.py  →  open http://localhost:5000
"""

import os
import re
import json
import time
import shutil
import hashlib
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory

app = Flask(__name__)

SAVE_DIR = Path.home() / "MetaAdArchive"
SAVE_DIR.mkdir(exist_ok=True)

job_status = {}  # job_id -> status dict

# ─────────────────────────────────────────────
# HTML TEMPLATE
# ─────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ad Vault — Meta Ad Archiver</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0a0b0d;
  --surface: #111318;
  --card: #161b22;
  --border: #21262d;
  --accent: #f0a500;
  --accent2: #e05c2a;
  --text: #e6edf3;
  --muted: #7d8590;
  --green: #3fb950;
  --red: #f85149;
  --radius: 10px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Syne', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Noise overlay */
body::before {
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.035'/%3E%3C/svg%3E");
  pointer-events: none; z-index: 0; opacity: 0.5;
}

/* Ambient glow */
body::after {
  content: '';
  position: fixed;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(240,165,0,0.07) 0%, transparent 70%);
  top: -100px; left: 50%; transform: translateX(-50%);
  pointer-events: none; z-index: 0;
}

.wrap { position: relative; z-index: 1; max-width: 860px; margin: 0 auto; padding: 0 24px 80px; }

/* ── HEADER ── */
header {
  padding: 52px 0 36px;
  display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 40px;
}
.logo {
  display: flex; align-items: center; gap: 12px;
}
.logo-icon {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem;
}
.logo-text {
  font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
header p {
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem; color: var(--muted);
  letter-spacing: 0.5px;
  margin-left: 52px;
}

/* ── INPUT SECTION ── */
.input-section {
  margin-bottom: 32px;
}
.input-label {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; color: var(--muted);
  margin-bottom: 10px; display: block;
}
.input-row {
  display: flex; gap: 10px;
}
.url-input {
  flex: 1;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  font-family: 'DM Mono', monospace;
  font-size: 0.82rem;
  color: var(--text);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.url-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(240,165,0,0.12);
}
.url-input::placeholder { color: var(--muted); }

.scrape-btn {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #000;
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 0.88rem;
  padding: 14px 24px;
  border: none;
  border-radius: var(--radius);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s, transform 0.1s;
  letter-spacing: 0.3px;
}
.scrape-btn:hover { opacity: 0.9; transform: translateY(-1px); }
.scrape-btn:active { transform: translateY(0); }
.scrape-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* ── PROGRESS ── */
#progressBox {
  display: none;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 24px;
}
.progress-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.progress-title {
  font-size: 0.78rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--muted);
}
.progress-bar-wrap {
  background: var(--border);
  border-radius: 99px; height: 4px; margin-bottom: 10px;
}
.progress-bar {
  height: 4px; border-radius: 99px;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  transition: width 0.4s ease;
  width: 0%;
}
#progressLog {
  font-family: 'DM Mono', monospace;
  font-size: 0.75rem;
  color: var(--muted);
  max-height: 120px;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 3px;
}
.log-line { display: flex; gap: 8px; }
.log-line .ts { color: var(--accent); opacity: 0.6; flex-shrink: 0; }
.log-line.ok .msg { color: var(--green); }
.log-line.err .msg { color: var(--red); }

/* ── RESULT CARD ── */
#resultBox { display: none; }

.result-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 24px;
  animation: slideUp 0.35s ease;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.result-topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px;
  background: linear-gradient(90deg, rgba(240,165,0,0.08), rgba(224,92,42,0.06));
  border-bottom: 1px solid var(--border);
}
.result-status {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.78rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
}
.result-timestamp {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem; color: var(--muted);
}

.result-body { padding: 24px; }

.page-name {
  font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px;
  margin-bottom: 4px;
}
.page-id {
  font-family: 'DM Mono', monospace;
  font-size: 0.75rem; color: var(--muted); margin-bottom: 20px;
}

.meta-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 12px; margin-bottom: 24px;
}
@media (max-width: 580px) { .meta-grid { grid-template-columns: 1fr; } }

.meta-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
}
.meta-key {
  font-size: 0.65rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--muted); margin-bottom: 4px;
}
.meta-val {
  font-size: 0.88rem; color: var(--text); font-weight: 600;
}

.section-label {
  font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; color: var(--muted);
  margin-bottom: 12px; display: block;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
}

.ad-text {
  font-size: 0.9rem; line-height: 1.65; color: var(--text);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px;
  margin-bottom: 24px;
  white-space: pre-wrap; word-break: break-word;
  font-family: 'DM Mono', monospace;
  max-height: 200px; overflow-y: auto;
}

.notes-section {
  margin-bottom: 24px;
}
.notes-textarea {
  width: 100%;
  min-height: 100px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  font-family: 'DM Mono', monospace;
  font-size: 0.85rem;
  color: var(--text);
  resize: vertical;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  line-height: 1.6;
}
.notes-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(240,165,0,0.12);
}
.notes-textarea::placeholder { color: var(--muted); }
.notes-save-row {
  display: flex; align-items: center; gap: 10px;
  margin-top: 8px;
}
.notes-save-btn {
  background: var(--border); border: none;
  border-radius: 6px; padding: 7px 16px;
  color: var(--text); font-family: 'Syne', sans-serif;
  font-size: 0.78rem; font-weight: 600;
  cursor: pointer; transition: background 0.15s;
}
.notes-save-btn:hover { background: #2d333b; }
.notes-saved-msg {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem; color: var(--green);
  opacity: 0; transition: opacity 0.3s;
}
.notes-saved-msg.show { opacity: 1; }

.media-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px; margin-bottom: 24px;
}
.media-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}
.media-item img, .media-item video {
  width: 100%; display: block;
  max-height: 200px; object-fit: cover;
}
.media-badge {
  position: absolute; top: 8px; left: 8px;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  border-radius: 4px; padding: 2px 8px;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem; font-weight: 500; color: var(--accent);
}
.media-filename {
  padding: 8px 10px;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem; color: var(--muted);
  border-top: 1px solid var(--border);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.save-path {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  display: flex; align-items: center; gap: 12px;
}
.save-path-icon { font-size: 1.2rem; flex-shrink: 0; }
.save-path-info .label {
  font-size: 0.65rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--muted); margin-bottom: 3px;
}
.save-path-info .path {
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem; color: var(--accent);
  word-break: break-all;
}
.open-btn {
  margin-left: auto;
  background: var(--border); border: none;
  border-radius: 6px; padding: 7px 14px;
  color: var(--text); font-family: 'Syne', sans-serif;
  font-size: 0.78rem; font-weight: 600;
  cursor: pointer; transition: background 0.15s;
  white-space: nowrap;
  text-decoration: none; display: inline-block;
}
.open-btn:hover { background: #2d333b; }

/* ── ARCHIVE LIST ── */
.archive-section { margin-top: 48px; }
.archive-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.archive-title {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; color: var(--muted);
}
.archive-count {
  background: var(--border); border-radius: 99px;
  padding: 3px 10px; font-size: 0.72rem;
  font-family: 'DM Mono', monospace; color: var(--muted);
}
.archive-empty {
  text-align: center; padding: 40px;
  color: var(--muted); font-size: 0.85rem;
  background: var(--card); border: 1px dashed var(--border);
  border-radius: var(--radius);
}

.archive-item {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 18px;
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.archive-item:hover { border-color: var(--accent); background: rgba(240,165,0,0.03); }
.archive-thumb {
  width: 48px; height: 48px;
  border-radius: 6px;
  background: var(--surface);
  overflow: hidden; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem;
}
.archive-thumb img { width: 100%; height: 100%; object-fit: cover; }
.archive-info { flex: 1; min-width: 0; }
.archive-name { font-weight: 700; font-size: 0.9rem; margin-bottom: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.archive-meta {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem; color: var(--muted);
}
.archive-arrow { color: var(--muted); font-size: 0.9rem; }

/* scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="logo">
      <div class="logo-icon">📦</div>
      <div class="logo-text">Ad Vault</div>
    </div>
    <p>// paste a meta ad library url → scrape & archive locally forever</p>
  </header>

  <section class="input-section">
    <span class="input-label">Meta Ad Library URL</span>
    <div class="input-row">
      <input class="url-input" id="urlInput" type="text"
        placeholder="https://www.facebook.com/ads/library/?id=25735814926036478"
        onkeydown="if(event.key==='Enter') startScrape()">
      <button class="scrape-btn" id="scrapeBtn" onclick="startScrape()">⬇ Archive Ad</button>
    </div>
  </section>

  <div id="progressBox">
    <div class="progress-header">
      <span class="progress-title">Archiving</span>
      <span id="progressPct" style="font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);">0%</span>
    </div>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progressBar"></div></div>
    <div id="progressLog"></div>
  </div>

  <div id="resultBox"></div>

  <div class="archive-section">
    <div class="archive-header">
      <span class="archive-title">Local Archive</span>
      <span class="archive-count" id="archiveCount">0 ads</span>
    </div>
    <div id="archiveList"><div class="archive-empty">No ads archived yet — paste a URL above to get started.</div></div>
  </div>

</div>

<script>
let currentJobId = null;
let pollTimer = null;

async function startScrape() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { alert('Please paste a Meta Ad Library URL'); return; }
  if (!url.includes('facebook.com/ads/library')) { alert('Please use a Facebook Ad Library URL (facebook.com/ads/library)'); return; }

  document.getElementById('scrapeBtn').disabled = true;
  document.getElementById('progressBox').style.display = 'block';
  document.getElementById('resultBox').style.display = 'none';
  setProgress(5, 'Starting browser...');
  clearLog();

  try {
    const resp = await fetch('/api/scrape', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({url})
    });
    const data = await resp.json();
    if (data.error) { setError(data.error); return; }
    currentJobId = data.job_id;
    pollTimer = setInterval(pollJob, 800);
  } catch(e) {
    setError('Failed to connect to local server: ' + e.message);
  }
}

async function pollJob() {
  if (!currentJobId) return;
  try {
    const resp = await fetch('/api/status/' + currentJobId);
    const data = await resp.json();
    
    if (data.log && data.log.length) {
      renderLog(data.log);
    }
    if (data.progress !== undefined) {
      setProgress(data.progress, '');
    }
    if (data.status === 'done') {
      clearInterval(pollTimer);
      setProgress(100, 'Complete!');
      renderResult(data.result);
      loadNotes(data.result.folder);
      loadArchive();
      document.getElementById('scrapeBtn').disabled = false;
    } else if (data.status === 'error') {
      clearInterval(pollTimer);
      setError(data.error || 'Unknown error');
      document.getElementById('scrapeBtn').disabled = false;
    }
  } catch(e) { console.error(e); }
}

function setProgress(pct, msg) {
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPct').textContent = pct + '%';
  if (msg) addLog(msg, 'info');
}

function clearLog() { document.getElementById('progressLog').innerHTML = ''; }

function addLog(msg, type='info') {
  const log = document.getElementById('progressLog');
  const ts = new Date().toLocaleTimeString('en-AU', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const el = document.createElement('div');
  el.className = 'log-line' + (type==='ok' ? ' ok' : type==='err' ? ' err' : '');
  el.innerHTML = `<span class="ts">${ts}</span><span class="msg">${msg}</span>`;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

let lastLogCount = 0;
function renderLog(logs) {
  if (logs.length <= lastLogCount) return;
  const newLogs = logs.slice(lastLogCount);
  newLogs.forEach(l => addLog(l.msg, l.type || 'info'));
  lastLogCount = logs.length;
}

function setError(msg) {
  addLog('ERROR: ' + msg, 'err');
  setProgress(0, '');
}

function renderResult(r) {
  if (!r) return;
  const box = document.getElementById('resultBox');
  box.style.display = 'block';

  const mediaHtml = (r.media || []).map(m => {
    const src = '/archive/' + encodeURIComponent(r.folder) + '/' + encodeURIComponent(m.filename);
    if (m.type === 'video') {
      return `<div class="media-item">
        <div class="media-badge">VIDEO</div>
        <video src="${src}" controls muted playsinline style="max-height:200px;width:100%;"></video>
        <div class="media-filename">${m.filename}</div>
      </div>`;
    } else {
      return `<div class="media-item">
        <div class="media-badge">IMAGE</div>
        <img src="${src}" alt="ad media" loading="lazy">
        <div class="media-filename">${m.filename}</div>
      </div>`;
    }
  }).join('');

  const metaItems = [
    {k:'Page Name', v: r.page_name || '—'},
    {k:'Page ID', v: r.page_id || '—'},
    {k:'Ad Status', v: r.status || '—'},
    {k:'Started Running', v: r.started || '—'},
    {k:'Platforms', v: (r.platforms||[]).join(', ') || '—'},
    {k:'Ad ID', v: r.ad_id || '—'},
    {k:'Media Files', v: (r.media||[]).length + ' file(s) saved'},
    {k:'Archived', v: new Date().toLocaleDateString('en-AU')},
  ].map(i => `<div class="meta-item"><div class="meta-key">${i.k}</div><div class="meta-val">${i.v}</div></div>`).join('');

  box.innerHTML = `
    <div class="result-card">
      <div class="result-topbar">
        <div class="result-status"><div class="status-dot"></div> Archived Successfully</div>
        <div class="result-timestamp">${new Date().toLocaleString('en-AU')}</div>
      </div>
      <div class="result-body">
        <div class="page-name">${r.page_name || 'Unknown Page'}</div>
        <div class="page-id">ID: ${r.ad_id || '—'}</div>
        <div class="meta-grid">${metaItems}</div>
        ${r.ad_text ? `<span class="section-label">Ad Copy</span><div class="ad-text">${escHtml(r.ad_text)}</div>` : ''}
        ${r.extra_text ? `<span class="section-label">Additional Content</span><div class="ad-text">${escHtml(r.extra_text)}</div>` : ''}
        <div class="notes-section">
          <span class="section-label">My Notes</span>
          <textarea class="notes-textarea" id="notesTextarea" placeholder="Add your notes about this ad — strategy observations, hooks, angles, what's working..."></textarea>
          <div class="notes-save-row">
            <button class="notes-save-btn" onclick="saveNotes('${r.folder}')">💾 Save Notes</button>
            <span class="notes-saved-msg" id="notesSavedMsg">Notes saved ✓</span>
          </div>
        </div>
        ${mediaHtml ? `<span class="section-label">Media</span><div class="media-grid">${mediaHtml}</div>` : ''}
        <div class="save-path">
          <div class="save-path-icon">💾</div>
          <div class="save-path-info">
            <div class="label">Saved to</div>
            <div class="path">${r.save_path}</div>
          </div>
        </div>
      </div>
    </div>`;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function loadArchive() {
  try {
    const resp = await fetch('/api/archive');
    const data = await resp.json();
    const list = document.getElementById('archiveList');
    document.getElementById('archiveCount').textContent = data.ads.length + ' ad' + (data.ads.length !== 1 ? 's' : '');
    if (!data.ads.length) {
      list.innerHTML = '<div class="archive-empty">No ads archived yet.</div>';
      return;
    }
    list.innerHTML = data.ads.map(ad => {
      let thumbHtml = '<div class="archive-thumb">📦</div>';
      if (ad.thumb) {
        thumbHtml = `<div class="archive-thumb"><img src="/archive/${encodeURIComponent(ad.folder)}/${encodeURIComponent(ad.thumb)}" alt=""></div>`;
      }
      return `<div class="archive-item" onclick="loadArchivedAd('${ad.folder}')">
        ${thumbHtml}
        <div class="archive-info">
          <div class="archive-name">${escHtml(ad.page_name || ad.folder)}</div>
          <div class="archive-meta">${ad.ad_id || ''} · ${ad.saved || ''} · ${ad.media_count || 0} file(s)</div>
        </div>
        <span class="archive-arrow">›</span>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

async function saveNotes(folder) {
  const text = document.getElementById('notesTextarea').value;
  try {
    await fetch('/api/notes/' + encodeURIComponent(folder), {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({notes: text})
    });
    const msg = document.getElementById('notesSavedMsg');
    msg.classList.add('show');
    setTimeout(() => msg.classList.remove('show'), 2000);
  } catch(e) { console.error(e); }
}

async function loadNotes(folder) {
  try {
    const resp = await fetch('/api/notes/' + encodeURIComponent(folder));
    const data = await resp.json();
    const ta = document.getElementById('notesTextarea');
    if (ta && data.notes) ta.value = data.notes;
  } catch(e) {}
}

async function openFolder(folder) {
  await fetch('/api/open_folder', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({folder})
  });
}

async function loadArchivedAd(folder) {
  try {
    const resp = await fetch('/api/archive/' + encodeURIComponent(folder));
    const r = await resp.json();
    if (r.error) { alert(r.error); return; }
    renderResult(r);
    loadNotes(folder);
    // Add open folder button to result card
    const topbar = document.querySelector('#resultBox .result-topbar');
    if (topbar && !topbar.querySelector('.open-btn')) {
      const btn = document.createElement('a');
      btn.className = 'open-btn';
      btn.textContent = '📂 Open Folder';
      btn.href = '#';
      btn.onclick = (e) => { e.preventDefault(); openFolder(folder); };
      topbar.appendChild(btn);
    }
    document.getElementById('resultBox').scrollIntoView({behavior:'smooth'});
  } catch(e) { console.error(e); }
}

loadArchive();
</script>
</body>
</html>"""

# ─────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────

def extract_ad_id(url: str):
    m = re.search(r'[?&]id=(\d+)', url)
    return m.group(1) if m else None


def run_scrape_job(job_id: str, url: str):
    status = job_status[job_id]
    logs = status['log']

    def log(msg, t='info'):
        logs.append({'msg': msg, 'type': t})

    def progress(p):
        status['progress'] = p

    try:
        ad_id = extract_ad_id(url)
        if not ad_id:
            raise ValueError("Could not extract ad ID from URL")

        log(f'Ad ID detected: {ad_id}')
        progress(10)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            log('Launching browser...')
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 900}
            )
            page = context.new_page()

            # ── NETWORK INTERCEPTION ──
            # Track ALL responses. We'll correlate to the ad modal AFTER page load
            # by only keeping URLs that appear AFTER the background page has settled.
            # Key insight: the modal ad media loads AFTER the background search results.
            # We use a two-phase approach: ignore early responses, capture late ones.
            
            all_responses = []   # (timestamp, type, url, content_type)
            page_load_time = [0]

            def handle_response(response):
                ts = time.time()
                ctype = response.headers.get('content-type', '')
                rurl = response.url
                # Only track substantial media
                if any(x in ctype for x in ['video/', 'mp4', 'webm']):
                    all_responses.append((ts, 'video', rurl, ctype))
                elif any(x in ctype for x in ['image/jpeg', 'image/png', 'image/webp', 'image/gif']):
                    if len(rurl) > 50 and 'favicon' not in rurl and 'emoji' not in rurl:
                        all_responses.append((ts, 'image', rurl, ctype))

            page.on('response', handle_response)

            log('Loading Ad Library page...')
            try:
                page.goto(url, wait_until='networkidle', timeout=35000)
            except Exception:
                page.goto(url, wait_until='domcontentloaded', timeout=35000)

            page_load_time[0] = time.time()
            progress(25)
            
            # Wait for the modal to appear — Facebook loads background results first,
            # then the specific ad modal renders on top ~1-2s later
            log('Waiting for ad modal to load...')
            time.sleep(9)

            # ── FIND THE AD MODAL CONTAINER ──
            # Facebook renders the specific ad in a modal/dialog overlay.
            # We need to find that container and ONLY extract data from it.
            log('Isolating ad modal container...')

            ad_data = page.evaluate(f"""() => {{
                const adId = '{ad_id}';
                
                // ── STRATEGY 1: Find element containing the ad ID ──
                // Facebook often embeds the ad ID in data attributes or nearby text
                let adContainer = null;
                
                // Look for any element with the ad ID in its subtree text
                const allEls = Array.from(document.querySelectorAll('div'));
                
                // Try: find the modal/dialog overlay (usually highest z-index or role=dialog)
                const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]'));
                if (dialogs.length > 0) {{
                    // Use the last/deepest dialog (most specific overlay)
                    adContainer = dialogs[dialogs.length - 1];
                }}
                
                // If no dialog, look for a div that contains the ad ID text 
                // AND has limited siblings (not the main results list)
                if (!adContainer) {{
                    for (const el of allEls) {{
                        if (el.innerText && el.innerText.includes(adId) && 
                            el.children.length < 20 &&
                            el.getBoundingClientRect().width > 300) {{
                            adContainer = el;
                            break;
                        }}
                    }}
                }}
                
                // Fallback: look for a fixed/absolute positioned overlay div
                if (!adContainer) {{
                    for (const el of allEls) {{
                        const style = window.getComputedStyle(el);
                        if ((style.position === 'fixed' || style.position === 'absolute') &&
                            style.zIndex > 10 &&
                            el.getBoundingClientRect().height > 400) {{
                            adContainer = el;
                            break;
                        }}
                    }}
                }}
                
                // If still nothing, use the element with "Started running" text
                // as anchor - that's always inside the specific ad card
                if (!adContainer) {{
                    for (const el of allEls) {{
                        if (el.innerText && el.innerText.includes('Started running on') &&
                            el.children.length < 50) {{
                            adContainer = el;
                            break;
                        }}
                    }}
                }}

                const scope = adContainer || document.body;
                const scopeText = scope.innerText || '';
                const isFullPage = scope === document.body;
                
                // ── EXTRACT DATA FROM SCOPED CONTAINER ──
                
                // Page/advertiser name
                let pageName = null;
                const nameEls = Array.from(scope.querySelectorAll(
                    'a[href*="/"], h1, h2, h3, [role="heading"], strong'
                ));
                for (const el of nameEls) {{
                    const t = el.innerText.trim();
                    // Skip generic UI text
                    if (t.length > 1 && t.length < 80 && 
                        !['Ad Library', 'Facebook', 'Search', 'Filter', 'Log in', 
                          'Sign up', 'See ad details', 'Active', 'Inactive',
                          'About this ad', 'Learn more'].some(s => t.includes(s))) {{
                        pageName = t;
                        break;
                    }}
                }}
                
                // Started running date
                let startedRunning = null;
                const dateMatch = scopeText.match(/Started running on ([A-Za-z]+ \\d{{1,2}}, \\d{{4}})/);
                if (dateMatch) startedRunning = dateMatch[1];
                
                // Also try alternative date formats
                if (!startedRunning) {{
                    const dateMatch2 = scopeText.match(/Started running[:\\s]+([A-Za-z]+ \\d{{1,2}}, \\d{{4}})/);
                    if (dateMatch2) startedRunning = dateMatch2[1];
                }}
                
                // Ad status
                let adStatus = 'Unknown';
                if (scopeText.match(/\\bActive\\b/)) adStatus = 'Active';
                else if (scopeText.match(/\\bInactive\\b/)) adStatus = 'Inactive';
                
                // Platforms
                const platforms = [];
                if (scopeText.includes('Facebook')) platforms.push('Facebook');
                if (scopeText.includes('Instagram')) platforms.push('Instagram');
                if (scopeText.includes('Messenger')) platforms.push('Messenger');
                if (scopeText.includes('Audience Network')) platforms.push('Audience Network');
                
                // ── MEDIA: ONLY from the scoped container ──
                const images = Array.from(scope.querySelectorAll('img[src]'))
                    .map(img => ({{
                        src: img.src,
                        w: img.naturalWidth || img.width,
                        h: img.naturalHeight || img.height
                    }}))
                    .filter(img => 
                        img.src.startsWith('http') && 
                        img.w > 200 && img.h > 200 &&   // skip small UI icons/avatars
                        !img.src.includes('favicon') && 
                        !img.src.includes('emoji') &&
                        !img.src.includes('static.xx.fbcdn') &&  // FB UI chrome
                        !img.src.includes('rsrc.php') &&          // FB static resources
                        !img.src.includes('safe_image') &&        // FB proxy thumbs
                        !(img.w === img.h && img.w < 300)         // skip square avatars/icons
                    )
                    .map(img => img.src);
                
                const videos = Array.from(scope.querySelectorAll('video'))
                    .flatMap(v => {{
                        const srcs = [];
                        if (v.src) srcs.push(v.src);
                        if (v.poster) srcs.push(('POSTER:' + v.poster));
                        Array.from(v.querySelectorAll('source')).forEach(s => {{
                            if (s.src) srcs.push(s.src);
                        }});
                        return srcs;
                    }})
                    .filter(Boolean);
                
                // ── ADDITIONAL ASSETS / CONTENT ITEMS ──
                // Find the heading span, walk up to its container, grab text + links
                const extraImages = [];
                const extraVideos = [];
                let extraText = '';
                const allSpans = Array.from(document.querySelectorAll('span'));
                for (const span of allSpans) {{
                    const t = span.innerText.trim();
                    if (t === 'Additional assets from this ad' || t === 'Additional content items from this ad') {{
                        // Walk up to a meaningful container (has siblings/children with content)
                        let container = span.parentElement;
                        while (container && container.children.length < 2 && container !== document.body)
                            container = container.parentElement;
                        if (!container) continue;
                        const ct = container.innerText.trim();
                        if (ct.length > extraText.length) extraText = ct;
                        Array.from(container.querySelectorAll('img[src]')).forEach(img => {{
                            if (img.src.startsWith('http') && !img.src.includes('rsrc.php') && !img.src.includes('emoji'))
                                extraImages.push(img.src);
                        }});
                        Array.from(container.querySelectorAll('video')).forEach(v => {{
                            if (v.src) extraVideos.push(v.src);
                            if (v.poster) extraImages.push(v.poster);
                            Array.from(v.querySelectorAll('source')).forEach(s => {{ if (s.src) extraVideos.push(s.src); }});
                        }});
                    }}
                }}
                
                // Ad copy text - the actual ad body text
                // Look for the longest meaningful text block in the container
                // that isn't navigation/metadata
                let adText = '';
                const textCandidates = Array.from(scope.querySelectorAll('div, p, span'))
                    .filter(el => {{
                        const t = el.innerText.trim();
                        const rect = el.getBoundingClientRect();
                        return t.length > 30 && 
                               t.length < 5000 && 
                               el.children.length < 8 &&
                               rect.width > 100;
                    }});
                
                for (const el of textCandidates) {{
                    const t = el.innerText.trim();
                    // Skip metadata lines
                    if (t.includes('Started running') || 
                        t.includes('Ad Library') ||
                        t.length < adText.length) continue;
                    adText = t;
                }}
                
                // Page name = first non-empty line of ad copy
                const adTextFirstLine = adText.split('\\n').map(l => l.trim()).find(l => l.length > 0) || null;
                pageName = adTextFirstLine || pageName;
                
                // Screenshot of just the modal
                const containerRect = scope !== document.body ? 
                    JSON.stringify(scope.getBoundingClientRect()) : null;
                
                return {{
                    pageName,
                    startedRunning,
                    adStatus,
                    platforms,
                    images: [...new Set(images)],
                    videos: [...new Set(videos)],
                    extraImages: [...new Set(extraImages)],
                    extraVideos: [...new Set(extraVideos)],
                    extraText: extraText.slice(0, 5000),
                    adText: adText.slice(0, 3000),
                    scopeText: scopeText.slice(0, 5000),
                    containerRect,
                    usedFallback: isFullPage,
                    modalFound: adContainer !== null && adContainer !== document.body
                }};
            }}""")

            progress(50)
            modal_status = "modal isolated ✓" if ad_data.get('modalFound') else "used full page (no modal found)"
            log(f'DOM scraped — {modal_status}')
            log(f'Found {len(ad_data.get("images", []))} images, {len(ad_data.get("videos", []))} video sources, {len(ad_data.get("extraImages", []))} extra images, {len(ad_data.get("extraVideos", []))} extra videos')

            # ── SCREENSHOT: crop to modal if possible ──
            screenshot_bytes = None
            try:
                clip = None
                if ad_data.get('containerRect'):
                    r = json.loads(ad_data['containerRect'])
                    if r.get('width', 0) > 200 and r.get('height', 0) > 200:
                        clip = {
                            'x': max(0, r['x']),
                            'y': max(0, r['y']),
                            'width': min(r['width'], 1280),
                            'height': min(r['height'], 900)
                        }
                screenshot_bytes = page.screenshot(clip=clip) if clip else page.screenshot()
            except Exception as e:
                log(f'Screenshot warning: {e}')

            # ── PARSE PAGE NAME ──
            page_name = ad_data.get('pageName') or _parse_page_name(ad_data.get('scopeText', ''), ad_id)
            
            # Clean up
            safe_name = re.sub(r'[^\w\s-]', '', page_name or 'Unknown')[:40].strip()
            today = datetime.now().strftime('%Y-%m-%d')
            folder_name = f"{safe_name}_{ad_id}_{today}"
            save_path = SAVE_DIR / folder_name
            save_path.mkdir(exist_ok=True)
            log(f'Saving to folder: {folder_name}')
            progress(55)

            if screenshot_bytes:
                with open(save_path / 'screenshot.png', 'wb') as f:
                    f.write(screenshot_bytes)
                log('Screenshot saved ✓', 'ok')

            # ── BUILD MEDIA LIST ──
            # page_load_time[0] is stamped right after goto() completes.
            # Background search results load DURING goto().
            # The specific ad modal loads AFTER goto() — during our 9s wait.
            # So: responses timestamped AFTER page_load_time = modal media only.

            after_load_cutoff = page_load_time[0]

            modal_network = [
                (t, mtype, rurl) for (t, mtype, rurl, _) in all_responses
                if t > after_load_cutoff
            ]

            log(f'Network: {len(all_responses)} total, {len(modal_network)} after page load (modal)')

            all_media_urls = []

            # Priority 1: DOM from isolated modal container (most precise)
            for img_url in ad_data.get('images', []):
                all_media_urls.append(('image', img_url, 'dom_modal'))

            for vid_entry in ad_data.get('videos', []):
                if vid_entry.startswith('POSTER:'):
                    all_media_urls.append(('image', vid_entry[7:], 'dom_poster'))
                else:
                    all_media_urls.append(('video', vid_entry, 'dom_video'))

            # Priority 1b: Additional assets / content items sections
            for img_url in ad_data.get('extraImages', []):
                all_media_urls.append(('image', img_url, 'extra_assets'))
            for vid_url in ad_data.get('extraVideos', []):
                all_media_urls.append(('video', vid_url, 'extra_assets'))

            # Priority 2: Network responses that fired AFTER background page loaded
            for _, mtype, rurl in modal_network:
                all_media_urls.append((mtype, rurl, 'network_modal'))

            # NO fallback to all_responses — that pulls in background ad images

            # Deduplicate
            seen_urls = set()
            unique_media = []
            for mtype, murl, source in all_media_urls:
                key = murl.split('?')[0][:120]
                if key not in seen_urls and murl.startswith('http'):
                    seen_urls.add(key)
                    unique_media.append((mtype, murl, source))

            # Edge case: nothing found — fall back to video-only from full session
            # (videos are rarely present in background ad cards, so safer to include)
            if not unique_media:
                log('No modal media found — falling back to video-only from full session')
                for (_, mtype, rurl, _) in all_responses:
                    if mtype == 'video':
                        key = rurl.split('?')[0][:120]
                        if key not in seen_urls:
                            seen_urls.add(key)
                            unique_media.append((mtype, rurl, 'fallback_video'))

            log(f'Unique media URLs to download: {len(unique_media)}')
            progress(60)

            # ── DOWNLOAD MEDIA ──
            saved_media = []
            cookies = context.cookies()
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])

            for i, (mtype, murl, source) in enumerate(unique_media[:20]):
                try:
                    ext = _get_ext(murl, mtype)
                    h = hashlib.md5(murl.encode()).hexdigest()[:8]
                    filename = f"{mtype}_{i+1:02d}_{h}{ext}"
                    filepath = save_path / filename

                    req = urllib.request.Request(murl, headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                        'Referer': 'https://www.facebook.com/',
                        'Cookie': cookie_str[:500] if cookie_str else '',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8' if mtype == 'image' else 'video/mp4,video/*,*/*'
                    })
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data_bytes = resp.read()
                    
                    if len(data_bytes) > 2000:  # skip tiny placeholder images
                        with open(filepath, 'wb') as f:
                            f.write(data_bytes)
                        size_kb = len(data_bytes) // 1024
                        saved_media.append({'type': mtype, 'filename': filename, 'size': len(data_bytes), 'source': source})
                        log(f'Saved {filename} ({size_kb}KB) [{source}]', 'ok')
                    else:
                        log(f'Skip tiny file {mtype} #{i+1} ({len(data_bytes)}B)')
                        
                except Exception as e:
                    log(f'Skip {mtype} #{i+1}: {str(e)[:60]}')
                
                progress(60 + int(35 * (i + 1) / max(len(unique_media[:20]), 1)))

            # ── SAVE METADATA ──
            meta = {
                'ad_id': ad_id,
                'url': url,
                'page_name': page_name,
                'status': ad_data.get('adStatus'),
                'started': ad_data.get('startedRunning'),
                'platforms': ad_data.get('platforms', []),
                'ad_text': ad_data.get('adText', ''),
                'extra_text': ad_data.get('extraText', ''),
                'media': saved_media,
                'archived_at': datetime.now().isoformat(),
                'save_path': str(save_path),
                'scrape_notes': {
                    'modal_found': ad_data.get('modalFound'),
                    'used_fallback': ad_data.get('usedFallback'),
                    'total_responses_intercepted': len(all_responses),
                    'modal_network_responses': len(modal_network)
                }
            }
            with open(save_path / 'ad_meta.json', 'w') as f:
                json.dump(meta, f, indent=2)
            log('Metadata JSON saved ✓', 'ok')

            browser.close()
            progress(100)

            # Find best thumb for UI
            thumb = None
            for m in saved_media:
                if m['type'] == 'image' and m.get('size', 0) > 10000:
                    thumb = m['filename']
                    break
            if not thumb and (save_path / 'screenshot.png').exists():
                thumb = 'screenshot.png'
                if not any(m['filename'] == 'screenshot.png' for m in saved_media):
                    saved_media.insert(0, {'type': 'image', 'filename': 'screenshot.png', 'size': 0})

            status['status'] = 'done'
            status['result'] = {
                'ad_id': ad_id,
                'page_name': page_name or 'Unknown Page',
                'page_id': '',
                'status': ad_data.get('adStatus', ''),
                'started': ad_data.get('startedRunning', ''),
                'platforms': ad_data.get('platforms', []),
                'ad_text': ad_data.get('adText', ''),
                'extra_text': ad_data.get('extraText', ''),
                'media': saved_media,
                'folder': folder_name,
                'save_path': str(save_path),
                'thumb': thumb,
            }
            log(f'Done! {len(saved_media)} files archived to {folder_name}', 'ok')

    except Exception as e:
        import traceback
        status['status'] = 'error'
        status['error'] = str(e)
        logs.append({'msg': f'Fatal error: {e}', 'type': 'err'})
        print(traceback.format_exc())


def _parse_page_name(text, ad_id):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:30]:
        if 5 < len(line) < 60 and not any(x in line.lower() for x in ['ad library', 'facebook', 'search', 'filter', 'log in', 'sign']):
            return line
    return f'Ad_{ad_id}'


def _get_ext(url, mtype):
    u = url.split('?')[0].lower()
    if '.mp4' in u: return '.mp4'
    if '.webm' in u: return '.webm'
    if '.jpg' in u or '.jpeg' in u: return '.jpg'
    if '.png' in u: return '.png'
    if '.webp' in u: return '.webp'
    return '.mp4' if mtype == 'video' else '.jpg'


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'})
    job_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]
    job_status[job_id] = {'status': 'running', 'progress': 0, 'log': [], 'result': None}
    t = threading.Thread(target=run_scrape_job, args=(job_id, url), daemon=True)
    t.start()
    return jsonify({'job_id': job_id})


@app.route('/api/status/<job_id>')
def status(job_id):
    s = job_status.get(job_id)
    if not s:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(s)


@app.route('/api/archive')
def archive():
    ads = []
    if SAVE_DIR.exists():
        for folder in sorted(SAVE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not folder.is_dir(): continue
            meta_file = folder / 'ad_meta.json'
            meta = {}
            if meta_file.exists():
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                except Exception:
                    pass
            # find thumb
            thumb = None
            for ext in ['*.jpg', '*.png', '*.webp']:
                imgs = list(folder.glob(ext))
                if imgs:
                    thumb = imgs[0].name; break
            media_count = len([f for f in folder.iterdir() if f.suffix in {'.jpg','.png','.webp','.mp4','.webm'}])
            ads.append({
                'folder': folder.name,
                'page_name': meta.get('page_name', folder.name),
                'ad_id': meta.get('ad_id', ''),
                'saved': meta.get('archived_at', '')[:10] if meta.get('archived_at') else '',
                'media_count': media_count,
                'thumb': thumb,
            })
    return jsonify({'ads': ads})


@app.route('/api/archive/<folder>')
def archive_detail(folder):
    safe = re.sub(r'[^\w\s._-]', '', folder)
    meta_file = SAVE_DIR / safe / 'ad_meta.json'
    if not meta_file.exists():
        return jsonify({'error': 'Not found'}), 404
    with open(meta_file) as f:
        meta = json.load(f)
    # Build media list from saved files
    folder_path = SAVE_DIR / safe
    media = []
    for m in meta.get('media', []):
        if (folder_path / m['filename']).exists():
            media.append(m)
    return jsonify({
        'ad_id': meta.get('ad_id', ''),
        'page_name': meta.get('page_name', safe),
        'page_id': '',
        'status': meta.get('status', ''),
        'started': meta.get('started', ''),
        'platforms': meta.get('platforms', []),
        'ad_text': meta.get('ad_text', ''),
        'extra_text': meta.get('extra_text', ''),
        'media': media,
        'folder': safe,
        'save_path': str(folder_path),
        'thumb': media[0]['filename'] if media else None,
    })


@app.route('/archive/<folder>/<filename>')
def serve_archive(folder, filename):
    safe_folder = re.sub(r'[^\w\s._-]', '', folder)
    return send_from_directory(str(SAVE_DIR / safe_folder), filename)


@app.route('/api/notes/<folder>', methods=['GET'])
def get_notes(folder):
    safe = re.sub(r'[^\w\s._-]', '', folder)
    notes_file = SAVE_DIR / safe / 'notes.txt'
    if notes_file.exists():
        return jsonify({'notes': notes_file.read_text(encoding='utf-8')})
    return jsonify({'notes': ''})


@app.route('/api/notes/<folder>', methods=['POST'])
def save_notes(folder):
    safe = re.sub(r'[^\w\s._-]', '', folder)
    folder_path = SAVE_DIR / safe
    if not folder_path.exists():
        return jsonify({'error': 'Folder not found'}), 404
    notes = request.json.get('notes', '')
    (folder_path / 'notes.txt').write_text(notes, encoding='utf-8')
    return jsonify({'ok': True})


@app.route('/api/open_folder', methods=['POST'])
def open_folder():
    folder = request.json.get('folder', '')
    safe = re.sub(r'[^\w\s._-]', '', folder)
    path = SAVE_DIR / safe
    if path.exists():
        import subprocess, sys
        if sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
        elif sys.platform == 'win32':
            subprocess.Popen(['explorer', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])
    return jsonify({'ok': True})


if __name__ == '__main__':
    import sys
    print("\n" + "="*50)
    print("  Ad Vault — Meta Ad Archiver")
    print("="*50)
    print(f"  Archive folder: {SAVE_DIR}")
    print(f"  Open in browser: http://localhost:5001")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False)