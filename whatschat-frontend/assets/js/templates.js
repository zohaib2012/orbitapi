// templates.js — WhatsChat AI Templates
// Path: whatschat-frontend/assets/js/templates.js

window.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadTemplates();
  document.getElementById("t-header-type")?.addEventListener("change", function() {
    const f = document.getElementById("headerContentField");
    if (f) f.style.display = this.value ? "block" : "none";
  });
});

async function loadTemplates() {
  try {
    const templates = await Templates.getAll();
    renderTemplates(templates);
  } catch(e) {
    document.getElementById("templatesGrid").innerHTML =
      `<div style="text-align:center;padding:40px;color:var(--text-light);grid-column:1/-1;">Could not load templates</div>`;
  }
}

function renderTemplates(templates) {
  const grid = document.getElementById("templatesGrid");
  if (!templates.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
      <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;">Koi template nahi</h3>
      <p>"New Template" se apna pehla template banao</p>
    </div>`;
    return;
  }
  const statusBadge = s => ({approved:"badge-approved",pending:"badge-pending",rejected:"badge-rejected"})[s] || "badge-pending";
  const catBadge    = c => ({MARKETING:"badge-marketing",UTILITY:"badge-utility",AUTHENTICATION:"badge-auth"})[c] || "badge-marketing";
  grid.innerHTML = templates.map(t => `
    <div class="template-card">
      <div class="template-card-header">
        <div>
          <div class="template-name">${t.name}</div>
          <div class="template-meta">
            <span class="badge ${statusBadge(t.status)}">${t.status}</span>
            <span class="badge ${catBadge(t.category)}">${t.category}</span>
          </div>
        </div>
      </div>
      <div class="template-body">
        <div class="template-preview">${t.body}</div>
        ${t.footer ? `<div class="template-footer">${t.footer}</div>` : ""}
      </div>
      <div class="template-actions">
        <button class="action-btn" onclick="copyToClipboard('TEMPLATE:${t.name}')">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          Copy Name
        </button>
        <button class="action-btn delete" onclick="deleteTemplate(${t.id})">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
          Delete
        </button>
      </div>
    </div>
  `).join("");
}

window.openModal = function() {
  document.getElementById("modalOverlay").classList.add("show");
};
window.closeModal = function() {
  document.getElementById("modalOverlay").classList.remove("show");
};
window.closeModalOutside = function(e) {
  if (e.target.id === "modalOverlay") closeModal();
};

window.updatePreview = function() {
  const body   = document.getElementById("t-body")?.value || "Your message...";
  const footer = document.getElementById("t-footer")?.value || "";
  setVal("previewBody",   body);
  setVal("previewFooter", footer);
};

window.saveTemplate = async function() {
  const name = document.getElementById("t-name")?.value.trim();
  const body = document.getElementById("t-body")?.value.trim();
  if (!name || !body) return showToast("Name aur body zaroori hain","error");
  const headerType = document.getElementById("t-header-type")?.value;
  const payload = {
    name, body,
    language:       document.getElementById("t-language")?.value || "en_US",
    category:       document.getElementById("t-category")?.value || "MARKETING",
    header_type:    headerType || null,
    header_content: headerType ? (document.getElementById("t-header-content")?.value || null) : null,
    footer:         document.getElementById("t-footer")?.value || null,
  };
  try {
    await Templates.create(payload);
    closeModal();
    showToast("Template saved ✅","success");
    await loadTemplates();
  } catch(e) { showToast(e.message || "Save failed","error"); }
};

window.deleteTemplate = async function(id) {
  if (!confirm("Delete karein?")) return;
  try {
    await Templates.delete(id);
    showToast("Deleted ✅","success");
    await loadTemplates();
  } catch(e) { showToast("Failed","error"); }
};

window.copyToClipboard = function(text) {
  navigator.clipboard.writeText(text).then(() => showToast("Copied!","success"));
};