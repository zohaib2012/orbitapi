// dashboard.js — Path: whatschat-frontend/assets/js/dashboard.js

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Auth check — login nahi toh login page
  Auth.requireAuth();

  // 2. Sidebar mein user ka naam fill karo
  fillSidebarUser();

  // 3. Sab data ek saath load karo
  await Promise.all([
    loadOverview(),
    loadCampaignStats(),
    loadRecentCampaigns(),
    loadCharts(),
    checkWhatsApp(),
  ]);
});

// ── STATS CARDS ───────────────────────────────────────────────
async function loadOverview() {
  try {
    const d = await Analytics.getOverview("7days");
    setVal("stat-total-sent", d.total_sent?.toLocaleString());
    setVal("stat-delivered",  d.total_delivered?.toLocaleString());
    setVal("stat-read-rate",  d.read_rate + "%");
  } catch(e) {
    // Agar backend se data nahi aaya toh 0 dikhao
    setVal("stat-total-sent", "0");
    setVal("stat-delivered",  "0");
    setVal("stat-read-rate",  "0%");
    console.error("Overview error:", e);
  }
}

async function loadCampaignStats() {
  try {
    const s = await Campaigns.getStats();
    setVal("stat-active-campaigns", s.active);
  } catch(e) {
    setVal("stat-active-campaigns", "0");
    console.error("Campaign stats error:", e);
  }
}

// ── RECENT CAMPAIGNS LIST ─────────────────────────────────────
async function loadRecentCampaigns() {
  try {
    const list = await Campaigns.getAll({ limit: 5 });
    const el = document.getElementById("recent-campaigns");
    if (!el) return;

    if (!list || !list.length) {
      el.innerHTML = `
        <div style="padding:24px;text-align:center;color:#9ca3af;font-size:13px">
          No campaigns yet.
          <a href="campaigns.html" style="color:#25D366;font-weight:600;text-decoration:none"> Create one →</a>
        </div>`;
      return;
    }

    el.innerHTML = list.map(c => `
      <div class="campaign-item">
        <div>
          <div class="campaign-name">${c.name}</div>
          <div class="campaign-meta">${c.total_sent.toLocaleString()} sent • ${c.total_delivered.toLocaleString()} delivered</div>
        </div>
        <span class="badge badge-${c.status}">${capitalize(c.status)}</span>
      </div>
    `).join("");
  } catch(e) {
    const el = document.getElementById("recent-campaigns");
    if (el) el.innerHTML = `<div style="padding:20px;text-align:center;color:#9ca3af;font-size:13px">Could not load campaigns</div>`;
    console.error("Recent campaigns error:", e);
  }
}

// ── CHARTS ────────────────────────────────────────────────────
async function loadCharts() {
  try {
    // Line chart data — 7 din ka
    const daily = await Analytics.getDaily("7days");

    const ctx1 = document.getElementById("activityChart");
    if (ctx1) {
      new Chart(ctx1.getContext("2d"), {
        type: "line",
        data: {
          labels: daily.map(d => d.date),
          datasets: [
            {
              label: "Sent",
              data: daily.map(d => d.sent),
              borderColor: "#25D366",
              backgroundColor: "rgba(37,211,102,0.08)",
              tension: 0.4,
              pointRadius: 4,
              pointBackgroundColor: "#25D366",
              fill: false,
            },
            {
              label: "Delivered",
              data: daily.map(d => d.delivered),
              borderColor: "#3b82f6",
              backgroundColor: "rgba(59,130,246,0.08)",
              tension: 0.4,
              pointRadius: 4,
              pointBackgroundColor: "#3b82f6",
              fill: false,
            },
            {
              label: "Read",
              data: daily.map(d => d.read),
              borderColor: "#f97316",
              backgroundColor: "rgba(249,115,22,0.08)",
              tension: 0.4,
              pointRadius: 4,
              pointBackgroundColor: "#f97316",
              fill: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              grid: { color: "#f3f4f6", drawBorder: false },
              ticks: { font: { family: "DM Sans", size: 12 }, color: "#9ca3af" },
            },
            y: {
              grid: { color: "#f3f4f6", drawBorder: false },
              ticks: { font: { family: "DM Sans", size: 12 }, color: "#9ca3af" },
              beginAtZero: true,
            },
          },
        },
      });
    }

    // Pie chart — campaign status breakdown
    const s = await Campaigns.getStats();
    const total = s.total || 1; // divide by zero se bachao
    const draft = Math.max(0, total - s.completed - s.active - s.scheduled);

    const completedPct  = Math.round((s.completed  / total) * 100);
    const activePct     = Math.round((s.active     / total) * 100);
    const scheduledPct  = Math.round((s.scheduled  / total) * 100);
    const draftPct      = Math.round((draft        / total) * 100);

    // Legend mein % update karo
    setVal("pct-completed", completedPct + "%");
    setVal("pct-active",    activePct    + "%");
    setVal("pct-scheduled", scheduledPct + "%");
    setVal("pct-draft",     draftPct     + "%");

    const ctx2 = document.getElementById("statusChart");
    if (ctx2) {
      new Chart(ctx2.getContext("2d"), {
        type: "pie",
        data: {
          labels: ["Completed", "Active", "Scheduled", "Draft"],
          datasets: [{
            data: [s.completed, s.active, s.scheduled, draft],
            backgroundColor: ["#3b82f6", "#25D366", "#f97316", "#9ca3af"],
            borderWidth: 2,
            borderColor: "#fff",
            hoverOffset: 6,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: { label: (c) => ` ${c.label}: ${c.raw}` },
            },
          },
        },
      });
    }

  } catch(e) {
    console.error("Charts error:", e);
  }
}

// ── WHATSAPP STATUS ───────────────────────────────────────────
async function checkWhatsApp() {
  try {
    const s = await WhatsApp.getStatus();
    const btn = document.getElementById("connect-btn");
    if (btn && s.connected) {
      btn.style.background   = "#f0fdf4";
      btn.style.borderColor  = "#bbf7d0";
      btn.style.color        = "#16a34a";
      btn.innerHTML          = `<svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> WhatsApp Connected`;
    }
  } catch(e) {
    // WhatsApp connect nahi — button as-is rahega
  }
}

// ── HELPER ────────────────────────────────────────────────────
function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

// Update connect button based on WA connection status
function updateConnectBtn() {
  const user = JSON.parse(localStorage.getItem('wc_user') || localStorage.getItem('user') || '{}');
  const btn  = document.getElementById('connect-btn');
  if (!btn) return;
  if (user.phone_number_id) {
    btn.innerHTML = '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg> Live Inbox';
    btn.style.background = '#f0fdf4';
    btn.style.color = '#166534';
    btn.style.border = '1px solid #bbf7d0';
  }
}
document.addEventListener('DOMContentLoaded', updateConnectBtn);