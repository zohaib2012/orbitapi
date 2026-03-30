// campaigns.js — Path: whatschat-frontend/assets/js/campaigns.js

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadStats();
  await loadCampaigns();
});

async function loadStats() {
  try {
    const s = await Campaigns.getStats();
    setVal("stat-total",     s.total);
    setVal("stat-active",    s.active);
    setVal("stat-scheduled", s.scheduled);
    setVal("stat-completed", s.completed);
  } catch(e) { console.error(e); }
}

async function loadCampaigns() {
  try {
    const list = await Campaigns.getAll();
    const el = document.getElementById("campaigns-list");
    if (!el) return;
    if (!list.length) { el.innerHTML = `<div style="padding:30px;text-align:center;color:#9ca3af">No campaigns yet</div>`; return; }
    el.innerHTML = list.map(c => {
      const rate = c.total_sent > 0 ? ((c.total_read/c.total_sent)*100).toFixed(1)+"%" : "0%";
      const statusColor = { active:"#dcfce7", completed:"#dbeafe", scheduled:"#fef3c7", draft:"#f3f4f6" };
      const statusText  = { active:"#16a34a", completed:"#2563eb", scheduled:"#d97706", draft:"#6b7280" };
      return `
      <div style="background:white;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:16px;font-weight:700">${c.name}</span>
            <span style="padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:${statusColor[c.status]||'#f3f4f6'};color:${statusText[c.status]||'#6b7280'}">${capitalize(c.status)}</span>
          </div>
          <div style="display:flex;gap:6px">
            ${c.status==='draft'||c.status==='scheduled' ? `<button onclick="sendCampaign(${c.id})" style="background:#25D366;color:white;border:none;border-radius:6px;padding:5px 14px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif;font-weight:600">▶ Send</button>` : ""}
            ${c.status==='active' ? `<button onclick="pauseCampaign(${c.id})" style="background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;padding:5px 14px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif">⏸ Pause</button>` : ""}
            <button onclick="deleteCampaign(${c.id})" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:6px;padding:5px 14px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif">Delete</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
          <div><div style="font-size:11px;color:#9ca3af;margin-bottom:2px">Sent</div><div style="font-size:18px;font-weight:700">${c.total_sent.toLocaleString()}</div></div>
          <div><div style="font-size:11px;color:#9ca3af;margin-bottom:2px">Delivered</div><div style="font-size:18px;font-weight:700">${c.total_delivered.toLocaleString()}</div></div>
          <div><div style="font-size:11px;color:#9ca3af;margin-bottom:2px">Read</div><div style="font-size:18px;font-weight:700">${c.total_read.toLocaleString()}</div></div>
          <div><div style="font-size:11px;color:#9ca3af;margin-bottom:2px">Read Rate</div><div style="font-size:18px;font-weight:700">${rate}</div></div>
        </div>
        <div style="display:flex;gap:16px;margin-top:10px;font-size:12px;color:#9ca3af">
          ${c.scheduled_at ? `<span>📅 ${new Date(c.scheduled_at).toLocaleString()}</span>` : ""}
          ${c.target_audience ? `<span>👥 ${c.target_audience}</span>` : ""}
        </div>
      </div>`;
    }).join("");
  } catch(e) { showToast("Load error","error"); }
}

// Create modal
function openCreateModal() { document.getElementById("campaignModalOverlay")?.classList.add("open"); document.getElementById("campaignForm")?.reset(); }
function closeCampaignModal() { document.getElementById("campaignModalOverlay")?.classList.remove("open"); }
function closeCampaignOutside(e) { if (e.target.id==="campaignModalOverlay") closeCampaignModal(); }

async function saveCampaign() {
  const name        = document.getElementById("c-name")?.value.trim();
  const message     = document.getElementById("c-message")?.value.trim();
  const audience    = document.getElementById("c-audience")?.value.trim();
  const status      = document.getElementById("c-status")?.value || "draft";
  const scheduledAt = document.getElementById("c-scheduled")?.value;
  const btn         = document.getElementById("saveCampaignBtn");

  if (!name || !message) { showToast("Name aur message zaroori hain","error"); return; }
  setLoading(btn, true);
  try {
    await Campaigns.create({ name, message_template:message, target_audience:audience||null, status, scheduled_at:scheduledAt?new Date(scheduledAt).toISOString():null });
    showToast("Campaign created ✅");
    closeCampaignModal();
    await loadStats(); await loadCampaigns();
  } catch(e) { showToast(e.message||"Error","error"); }
  finally { setLoading(btn, false); }
}

async function sendCampaign(id) {
  if (!confirm("Campaign send karna chahte ho?")) return;
  try { await Campaigns.send(id); showToast("Campaign send ✅"); await loadStats(); await loadCampaigns(); }
  catch(e) { showToast(e.message||"Error","error"); }
}

async function pauseCampaign(id) {
  try { await Campaigns.pause(id); showToast("Paused"); await loadCampaigns(); }
  catch(e) { showToast(e.message||"Error","error"); }
}

async function deleteCampaign(id) {
  if (!confirm("Delete karna chahte ho?")) return;
  try { await Campaigns.delete(id); showToast("Deleted"); await loadStats(); await loadCampaigns(); }
  catch(e) { showToast(e.message||"Error","error"); }
}