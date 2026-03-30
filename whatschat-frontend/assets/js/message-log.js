// message-log.js — WhatsChat AI Message Log
// Path: whatschat-frontend/assets/js/message-log.js

let currentFilter = "";
let currentSearch = "";
let currentPage   = 0;
const LIMIT = 50;

window.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadStats();
  await loadLogs();
});

async function loadStats() {
  try {
    const s = await MessageLog.getStats();
    setVal("stat-sent",      (s.total_sent      || 0).toLocaleString());
    setVal("stat-received",  (s.total_received  || 0).toLocaleString());
    setVal("stat-delivered", (s.total_delivered || 0).toLocaleString());
    setVal("stat-read",      (s.total_read      || 0).toLocaleString());
  } catch(e) {}
}

async function loadLogs() {
  const params = { skip: currentPage * LIMIT, limit: LIMIT };
  if (currentFilter) params.direction = currentFilter;
  if (currentSearch) params.search    = currentSearch;
  try {
    const res = await MessageLog.getAll(params);
    renderLogs(res.logs || [], res.total || 0);
  } catch(e) {
    document.getElementById("logsTable").innerHTML =
      `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-light);">Could not load logs</td></tr>`;
  }
}

function renderLogs(logs, total) {
  const tbody = document.getElementById("logsTable");
  if (!logs.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <p>Koi message nahi mila</p>
    </div></td></tr>`;
    return;
  }
  const typeIcon = t => ({text:"💬",image:"🖼️",video:"🎬",audio:"🎵",document:"📄"})[t] || "💬";
  tbody.innerHTML = logs.map(l => {
    const time = l.sent_at
      ? new Date(l.sent_at).toLocaleString("en-PK", {dateStyle:"short", timeStyle:"short"})
      : "—";
    const name = l.contact_name
      ? `<div style="font-weight:600">${l.contact_name}</div><div style="font-size:11px;color:var(--text-light)">${l.contact_phone}</div>`
      : `<div style="font-family:'DM Mono',monospace">${l.contact_phone}</div>`;
    const content = l.content
      ? (l.content.length > 50 ? l.content.slice(0,50)+"…" : l.content)
      : (l.media_url ? "📎 Media" : "—");
    return `<tr>
      <td>${name}</td>
      <td><span class="dir-badge ${l.direction==="inbound"?"dir-in":"dir-out"}">${l.direction==="inbound"?"↙ In":"↗ Out"}</span></td>
      <td><span class="type-icon">${typeIcon(l.message_type)}</span></td>
      <td style="max-width:200px;color:var(--text-secondary)">${content}</td>
      <td><span class="status-dot ${l.is_delivered?"dot-green":"dot-gray"}"></span>${l.is_delivered?"Yes":"No"}</td>
      <td><span class="status-dot ${l.is_read?"dot-blue":"dot-gray"}"></span>${l.is_read?"Yes":"No"}</td>
      <td style="color:var(--text-secondary);font-size:12px;white-space:nowrap">${time}</td>
    </tr>`;
  }).join("");
  const info = document.getElementById("paginationInfo");
  if (info) info.textContent = `Showing ${currentPage*LIMIT+1}–${Math.min((currentPage+1)*LIMIT,total)} of ${total}`;
}

window.setFilter = function(dir, btn) {
  currentFilter = dir; currentPage = 0;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  loadLogs();
};

let searchTimer;
window.searchLogs = function(val) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { currentSearch = val; currentPage = 0; loadLogs(); }, 400);
};