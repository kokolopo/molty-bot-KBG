"""
==============================================================================
MOLTY ROYALE BOT - LIVE LOG DASHBOARD
==============================================================================
Web-based dashboard that runs alongside the bot.
Open http://localhost:5000 in your browser to see live logs & stats.
"""

import json
import logging
import threading
from collections import deque
from pathlib import Path

from flask import Flask, jsonify, Response


# =============================================================================
# LOG HANDLER — captures log records for the dashboard
# =============================================================================

class DashboardLogHandler(logging.Handler):
    """Custom handler that stores log records in a circular buffer."""

    def __init__(self, maxlen=500):
        super().__init__()
        self._buffer = deque(maxlen=maxlen)
        self._counter = 0

    def emit(self, record):
        self._counter += 1
        entry = {
            "id": self._counter,
            "ts": self.format_time(record),
            "level": record.levelname,
            "module": record.name.replace("MoltyBot.", ""),
            "message": self._strip_ansi(record.getMessage()),
        }
        self._buffer.append(entry)

    @staticmethod
    def format_time(record):
        import time as _time
        ct = _time.localtime(record.created)
        return _time.strftime("%H:%M:%S", ct)

    @staticmethod
    def _strip_ansi(text):
        """Remove ANSI escape codes for clean display."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)

    def get_logs(self, after_id=0):
        """Return logs with id > after_id."""
        return [e for e in self._buffer if e["id"] > after_id]


# =============================================================================
# DASHBOARD SERVER
# =============================================================================

# Shared handler instance
_handler = DashboardLogHandler(maxlen=500)


def get_handler():
    return _handler


def create_app():
    app = Flask(__name__)
    app.logger.setLevel(logging.WARNING)  # suppress Flask logs

    DATA_DIR = Path("data")

    @app.route("/")
    def index():
        return Response(DASHBOARD_HTML, content_type="text/html; charset=utf-8")

    @app.route("/api/logs")
    def api_logs():
        from flask import request
        after = int(request.args.get("after", 0))
        logs = _handler.get_logs(after)
        return jsonify(logs)

    @app.route("/api/stats")
    def api_stats():
        history_path = DATA_DIR / "game_history.json"
        if not history_path.exists():
            return jsonify({"games": 0, "wins": 0, "kills": 0, "moltz": 0,
                            "win_rate": 0, "avg_rank": 0})
        try:
            history = json.loads(history_path.read_text())
            total = len(history)
            if total == 0:
                return jsonify({"games": 0, "wins": 0, "kills": 0, "moltz": 0,
                                "win_rate": 0, "avg_rank": 0})
            wins = sum(1 for g in history if g.get("is_winner"))
            kills = sum(g.get("kills", 0) for g in history)
            moltz = sum(g.get("moltz_earned", 0) for g in history)
            avg_rank = sum(g.get("final_rank", 99) for g in history) / total
            return jsonify({
                "games": total, "wins": wins, "kills": kills,
                "moltz": moltz, "win_rate": round(wins / total * 100, 1),
                "avg_rank": round(avg_rank, 1)
            })
        except Exception:
            return jsonify({"games": 0, "wins": 0, "kills": 0, "moltz": 0,
                            "win_rate": 0, "avg_rank": 0})

    return app


def start_dashboard(port=5000):
    """Start the dashboard in a background daemon thread."""
    app = create_app()

    # Suppress Werkzeug request logs
    wlog = logging.getLogger("werkzeug")
    wlog.setLevel(logging.ERROR)

    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False,
                               use_reloader=False),
        daemon=True,
        name="DashboardThread",
    )
    thread.start()
    return thread


# =============================================================================
# FRONTEND HTML
# =============================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Molty Royale Bot — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary:   #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary:  #1c2333;
    --bg-card:      #21262d;
    --border:       #30363d;
    --text-primary: #e6edf3;
    --text-secondary:#8b949e;
    --text-dim:     #484f58;
    --accent-blue:  #58a6ff;
    --accent-green: #3fb950;
    --accent-yellow:#d29922;
    --accent-red:   #f85149;
    --accent-purple:#bc8cff;
    --accent-cyan:  #39d2c0;
    --accent-orange:#f0883e;
    --glow-blue:    rgba(88,166,255,0.15);
    --glow-green:   rgba(63,185,80,0.15);
    --glow-red:     rgba(248,81,73,0.15);
    --glow-yellow:  rgba(210,153,34,0.15);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── Header ─────────────────────────────────────────────────── */
  .header {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(12px);
  }
  .header-icon {
    font-size: 28px;
    filter: drop-shadow(0 0 8px rgba(88,166,255,0.4));
  }
  .header h1 {
    font-size: 18px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 0.5px;
  }
  .header-status {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-secondary);
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent-green);
    box-shadow: 0 0 8px var(--accent-green);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* ── Stats Grid ─────────────────────────────────────────────── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    padding: 16px 24px;
  }
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }
  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    border-radius: 12px 12px 0 0;
  }
  .stat-card:nth-child(1)::before { background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); }
  .stat-card:nth-child(2)::before { background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan)); }
  .stat-card:nth-child(3)::before { background: linear-gradient(90deg, var(--accent-red), var(--accent-orange)); }
  .stat-card:nth-child(4)::before { background: linear-gradient(90deg, var(--accent-yellow), var(--accent-orange)); }
  .stat-card:nth-child(5)::before { background: linear-gradient(90deg, var(--accent-purple), var(--accent-blue)); }
  .stat-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  }
  .stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 6px;
    font-weight: 600;
  }
  .stat-value {
    font-size: 24px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }
  .stat-card:nth-child(1) .stat-value { color: var(--accent-blue); }
  .stat-card:nth-child(2) .stat-value { color: var(--accent-green); }
  .stat-card:nth-child(3) .stat-value { color: var(--accent-red); }
  .stat-card:nth-child(4) .stat-value { color: var(--accent-yellow); }
  .stat-card:nth-child(5) .stat-value { color: var(--accent-purple); }

  /* ── Controls ───────────────────────────────────────────────── */
  .controls {
    padding: 0 24px 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
  .filter-btn {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--bg-card);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: 'JetBrains Mono', monospace;
  }
  .filter-btn:hover {
    border-color: var(--accent-blue);
    color: var(--text-primary);
  }
  .filter-btn.active {
    background: var(--accent-blue);
    border-color: var(--accent-blue);
    color: #fff;
    box-shadow: 0 0 12px var(--glow-blue);
  }
  .filter-btn[data-level="DEBUG"].active  { background: var(--accent-cyan);   border-color: var(--accent-cyan); }
  .filter-btn[data-level="INFO"].active   { background: var(--accent-blue);   border-color: var(--accent-blue); }
  .filter-btn[data-level="WARNING"].active{ background: var(--accent-yellow); border-color: var(--accent-yellow); color: #000; }
  .filter-btn[data-level="ERROR"].active  { background: var(--accent-red);    border-color: var(--accent-red); }
  .search-box {
    flex: 1;
    min-width: 200px;
    padding: 7px 14px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--bg-card);
    color: var(--text-primary);
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-box:focus {
    border-color: var(--accent-blue);
    box-shadow: 0 0 0 3px var(--glow-blue);
  }
  .search-box::placeholder { color: var(--text-dim); }
  .log-count {
    font-size: 12px;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
  }

  /* ── Log Container ──────────────────────────────────────────── */
  .log-container {
    margin: 0 24px 24px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }
  .log-header {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
    gap: 8px;
  }
  .log-header span { font-weight: 600; }
  .col-time    { width: 70px; }
  .col-level   { width: 70px; }
  .col-module  { width: 100px; }
  .col-message { flex: 1; }
  .log-scroll {
    height: calc(100vh - 340px);
    min-height: 300px;
    overflow-y: auto;
    scroll-behavior: smooth;
  }
  .log-scroll::-webkit-scrollbar { width: 6px; }
  .log-scroll::-webkit-scrollbar-track { background: transparent; }
  .log-scroll::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
  }
  .log-scroll::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }

  /* ── Log Entries ────────────────────────────────────────────── */
  .log-entry {
    display: flex;
    padding: 5px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    line-height: 1.6;
    border-bottom: 1px solid rgba(48,54,61,0.4);
    transition: background 0.15s;
    gap: 8px;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .log-entry:hover { background: rgba(88,166,255,0.04); }
  .log-entry .ts      { color: var(--text-dim); width: 70px; flex-shrink: 0; }
  .log-entry .level   { width: 70px; flex-shrink: 0; font-weight: 600; }
  .log-entry .module  { width: 100px; flex-shrink: 0; color: var(--accent-purple); }
  .log-entry .message { flex: 1; word-break: break-word; color: var(--text-primary); }

  /* Level colors */
  .log-entry.l-DEBUG   .level { color: var(--accent-cyan); }
  .log-entry.l-INFO    .level { color: var(--accent-blue); }
  .log-entry.l-WARNING .level { color: var(--accent-yellow); }
  .log-entry.l-ERROR   .level { color: var(--accent-red); }
  .log-entry.l-WARNING { background: rgba(210,153,34,0.04); }
  .log-entry.l-ERROR   { background: rgba(248,81,73,0.06); }

  /* Module colors */
  .log-entry .module[data-mod="GameLoop"]  { color: var(--accent-blue); }
  .log-entry .module[data-mod="API"]       { color: var(--accent-purple); }
  .log-entry .module[data-mod="Analyzer"]  { color: var(--accent-cyan); }
  .log-entry .module[data-mod="Strategy"]  { color: var(--accent-orange); }
  .log-entry .module[data-mod="Memory"]    { color: var(--text-dim); }
  .log-entry .module[data-mod="ML"]        { color: var(--accent-green); }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: var(--text-dim);
    gap: 8px;
  }
  .empty-state .icon { font-size: 36px; opacity: 0.5; }

  /* ── Auto-scroll toggle ─────────────────────────────────────── */
  .auto-scroll-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    cursor: pointer;
    font-size: 12px;
    color: var(--text-secondary);
    user-select: none;
  }
  .auto-scroll-toggle input { display: none; }
  .toggle-track {
    width: 32px; height: 16px;
    border-radius: 8px;
    background: var(--border);
    position: relative;
    transition: background 0.2s;
  }
  .toggle-track::after {
    content: '';
    position: absolute;
    top: 2px; left: 2px;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: var(--text-secondary);
    transition: all 0.2s;
  }
  .auto-scroll-toggle input:checked + .toggle-track {
    background: var(--accent-green);
  }
  .auto-scroll-toggle input:checked + .toggle-track::after {
    transform: translateX(16px);
    background: #fff;
  }

  /* ── Responsive ─────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); padding: 12px 16px; }
    .controls { padding: 0 16px 8px; }
    .log-container { margin: 0 12px 16px; }
    .col-module { display: none; }
    .log-entry .module { display: none; }
  }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <span class="header-icon">🤖</span>
  <h1>MOLTY ROYALE BOT</h1>
  <div class="header-status">
    <div class="status-dot"></div>
    <span id="status-text">Live</span>
  </div>
</div>

<!-- Stats -->
<div class="stats-grid" id="stats-grid">
  <div class="stat-card">
    <div class="stat-label">Games Played</div>
    <div class="stat-value" id="s-games">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Win Rate</div>
    <div class="stat-value" id="s-winrate">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Total Kills</div>
    <div class="stat-value" id="s-kills">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Moltz Earned</div>
    <div class="stat-value" id="s-moltz">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Avg Rank</div>
    <div class="stat-value" id="s-rank">—</div>
  </div>
</div>

<!-- Controls -->
<div class="controls">
  <button class="filter-btn active" data-level="ALL">ALL</button>
  <button class="filter-btn" data-level="DEBUG">DEBUG</button>
  <button class="filter-btn" data-level="INFO">INFO</button>
  <button class="filter-btn" data-level="WARNING">WARN</button>
  <button class="filter-btn" data-level="ERROR">ERROR</button>
  <input class="search-box" type="text" id="search" placeholder="🔍 Search logs...">
  <span class="log-count" id="log-count">0 logs</span>
  <label class="auto-scroll-toggle">
    <input type="checkbox" id="auto-scroll" checked>
    <div class="toggle-track"></div>
    Auto-scroll
  </label>
</div>

<!-- Log Viewer -->
<div class="log-container">
  <div class="log-header">
    <span class="col-time">TIME</span>
    <span class="col-level">LEVEL</span>
    <span class="col-module">MODULE</span>
    <span class="col-message">MESSAGE</span>
  </div>
  <div class="log-scroll" id="log-scroll">
    <div class="empty-state" id="empty-state">
      <div class="icon">📡</div>
      <div>Waiting for logs...</div>
      <div style="font-size:11px">Logs will appear here in real-time</div>
    </div>
  </div>
</div>

<script>
(function() {
  const logScroll  = document.getElementById('log-scroll');
  const emptyState = document.getElementById('empty-state');
  const searchBox  = document.getElementById('search');
  const logCount   = document.getElementById('log-count');
  const autoScroll = document.getElementById('auto-scroll');
  const filterBtns = document.querySelectorAll('.filter-btn');

  let allLogs      = [];
  let lastId       = 0;
  let activeLevel  = 'ALL';
  let searchTerm   = '';

  // ── Filter buttons ──────────────────────────────────────────
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeLevel = btn.dataset.level;
      renderLogs();
    });
  });

  searchBox.addEventListener('input', () => {
    searchTerm = searchBox.value.toLowerCase();
    renderLogs();
  });

  // ── Render visible logs ─────────────────────────────────────
  function renderLogs() {
    const filtered = allLogs.filter(log => {
      if (activeLevel !== 'ALL' && log.level !== activeLevel) return false;
      if (searchTerm && !log.message.toLowerCase().includes(searchTerm)
          && !log.module.toLowerCase().includes(searchTerm)) return false;
      return true;
    });

    logCount.textContent = filtered.length + ' / ' + allLogs.length + ' logs';

    if (filtered.length === 0) {
      logScroll.innerHTML = '';
      logScroll.appendChild(emptyState);
      emptyState.style.display = 'flex';
      return;
    }

    emptyState.style.display = 'none';

    // Only show last 300 to keep performance
    const visible = filtered.slice(-300);

    const html = visible.map(log =>
      `<div class="log-entry l-${log.level}">` +
        `<span class="ts">${esc(log.ts)}</span>` +
        `<span class="level">${esc(log.level)}</span>` +
        `<span class="module" data-mod="${esc(log.module)}">${esc(log.module)}</span>` +
        `<span class="message">${esc(log.message)}</span>` +
      `</div>`
    ).join('');

    logScroll.innerHTML = html;

    if (autoScroll.checked) {
      logScroll.scrollTop = logScroll.scrollHeight;
    }
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Poll for new logs ───────────────────────────────────────
  async function pollLogs() {
    try {
      const res = await fetch('/api/logs?after=' + lastId);
      const newLogs = await res.json();
      if (newLogs.length > 0) {
        allLogs.push(...newLogs);
        // Keep buffer bounded
        if (allLogs.length > 2000) {
          allLogs = allLogs.slice(-1500);
        }
        lastId = newLogs[newLogs.length - 1].id;
        renderLogs();
      }
    } catch (e) {
      document.getElementById('status-text').textContent = 'Disconnected';
      document.querySelector('.status-dot').style.background = 'var(--accent-red)';
    }
  }

  // ── Poll for stats ──────────────────────────────────────────
  async function pollStats() {
    try {
      const res = await fetch('/api/stats');
      const s = await res.json();
      document.getElementById('s-games').textContent   = s.games || '0';
      document.getElementById('s-winrate').textContent  = (s.win_rate || 0) + '%';
      document.getElementById('s-kills').textContent    = s.kills || '0';
      document.getElementById('s-moltz').textContent    = (s.moltz || 0).toLocaleString();
      document.getElementById('s-rank').textContent     = s.avg_rank ? '#' + s.avg_rank : '—';
    } catch (e) { /* ignore */ }
  }

  // ── Start polling ───────────────────────────────────────────
  pollLogs();
  pollStats();
  setInterval(pollLogs, 2000);
  setInterval(pollStats, 15000);
})();
</script>
</body>
</html>
"""
