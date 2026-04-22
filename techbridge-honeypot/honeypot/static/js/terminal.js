/**
 * TechBridge Academy — Honeypot Terminal JS
 * Handles command input, history, and silent backend logging.
 * No client-side alerts or confrontational popups — all observation is server-side.
 */

(function () {
  const input   = document.getElementById('termInput');
  const history = document.getElementById('history');
  const output  = document.getElementById('output');
  const idleLine = document.getElementById('idle-line');

  let cmdHistory = [];
  let historyIdx = -1;

  // Auto-focus
  input.focus();
  document.addEventListener('click', () => input.focus());

  // ── Key handling ───────────────────────────────────────────────────────────
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      const cmd = input.value.trim();
      input.value = '';
      historyIdx = -1;
      if (!cmd) return;

      // Save history
      cmdHistory.unshift(cmd);
      if (cmdHistory.length > 100) cmdHistory.pop();

      appendCommand(cmd);
      sendCommand(cmd);
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIdx < cmdHistory.length - 1) {
        historyIdx++;
        input.value = cmdHistory[historyIdx];
      }
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx > 0) {
        historyIdx--;
        input.value = cmdHistory[historyIdx];
      } else {
        historyIdx = -1;
        input.value = '';
      }
    }

    // Ctrl+C
    if (e.ctrlKey && e.key === 'c') {
      appendCommand(input.value + '^C');
      input.value = '';
    }

    // Ctrl+L = clear
    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault();
      history.innerHTML = '';
    }
  });

  // ── Render a prompt + command line ────────────────────────────────────────
  function appendCommand(cmd) {
    idleLine.style.display = 'none';
    const line = document.createElement('div');
    line.className = 'cmd-line';
    line.innerHTML =
      '<span class="prompt-user">root</span>' +
      '<span class="prompt-at">@</span>' +
      '<span class="prompt-host">techbridge-prod</span>' +
      '<span class="prompt-path">:/home/admin/courses</span>' +
      '<span class="prompt-dollar"># </span>' +
      '<span class="cmd-text">' + escHtml(cmd) + '</span>';
    history.appendChild(line);
    scrollBottom();
  }

  // ── Render output block ───────────────────────────────────────────────────
  function appendOutput(text, colorClass) {
    if (!text) {
      showIdleCursor();
      return;
    }
    if (text === '__CLEAR__') {
      history.innerHTML = '';
      showIdleCursor();
      return;
    }
    if (text === '__EXIT__') {
      appendOutputLine('logout', 'green');
      setTimeout(() => { window.location.href = '/logout'; }, 800);
      return;
    }

    // Colorize file listings
    const lines = text.split('\n');
    const block = document.createElement('div');
    block.className = 'cmd-output ' + (colorClass || '');
    block.innerHTML = lines.map(line => colorizeOutput(line)).join('\n');
    history.appendChild(block);
    showIdleCursor();
    scrollBottom();
  }

  function appendOutputLine(text, cls) {
    const el = document.createElement('div');
    el.className = 'cmd-output ' + (cls || '');
    el.textContent = text;
    history.appendChild(el);
    scrollBottom();
  }

  function showIdleCursor() {
    idleLine.style.display = 'flex';
    scrollBottom();
  }

  // ── Color file listings ───────────────────────────────────────────────────
  function colorizeOutput(line) {
    line = escHtml(line);
    if (/\.pdf$/i.test(line))  return '<span style="color:#79c0ff">' + line + '</span>';
    if (/\.mp4$/i.test(line))  return '<span style="color:#a5f3a5">' + line + '</span>';
    if (/\.py$/i.test(line))   return '<span style="color:#e3b341">' + line + '</span>';
    if (/\.db$/i.test(line))   return '<span style="color:#bc8cff">' + line + '</span>';
    if (/\/$/.test(line))      return '<span style="color:#79c0ff;font-weight:600">' + line + '</span>';
    if (/^(root|admin)/.test(line)) return '<span style="color:#f85149">' + line + '</span>';
    return line;
  }

  // ── API call ──────────────────────────────────────────────────────────────
  function sendCommand(cmd) {
    fetch('/api/terminal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    })
    .then(r => r.json())
    .then(data => {
      const out = data.output || '';
      appendOutput(out);
    })
    .catch(() => {
      appendOutput('bash: connection error', 'red');
    });
  }

  // ── Utilities ─────────────────────────────────────────────────────────────
  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function scrollBottom() {
    output.scrollTop = output.scrollHeight;
  }

})();
