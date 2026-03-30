// bot-replies.js — WhatsChat AI Auto Replies + Interactive Menus
// Path: whatschat-frontend/assets/js/bot-replies.js

let selectedType = "text";
let menuItems = [];

window.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadRules();
  await loadMenus();
});

// ═══════════════════════════════════════════════════════════════════════════
// TAB SWITCHING
// ═══════════════════════════════════════════════════════════════════════════

window.switchBotTab = function(tab, btn) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(`tab-${tab}`).classList.add("active");
};


// ═══════════════════════════════════════════════════════════════════════════
// SIMPLE RULES — EXISTING FUNCTIONALITY
// ═══════════════════════════════════════════════════════════════════════════

async function loadRules() {
  try {
    const rules = await AutoReplies.getAll();
    renderStats(rules);
    renderRules(rules);
  } catch(e) {
    document.getElementById("rulesBody").innerHTML =
      `<div style="text-align:center;padding:40px;color:var(--text-light);">Could not load rules</div>`;
  }
}

function renderStats(rules) {
  setVal("stat-total",    rules.length);
  setVal("stat-active",   rules.filter(r => r.is_active).length);
  setVal("stat-triggered",rules.reduce((a,r) => a + r.total_triggered, 0).toLocaleString());
}

function renderRules(rules) {
  const el = document.getElementById("rulesBody");
  if (!rules.length) {
    el.innerHTML = `<div class="empty-state">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4"/></svg>
      <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;">Koi rule nahi</h3>
      <p>"New Rule" button se pehla auto reply rule banao</p>
    </div>`;
    return;
  }
  const typeBadge = t => ({text:"badge-text",image:"badge-image",video:"badge-video",audio:"badge-audio",document:"badge-document"})[t] || "badge-text";
  const typeEmoji = t => ({text:"💬",image:"🖼️",video:"🎬",audio:"🎵",document:"📄"})[t] || "💬";
  el.innerHTML = `<table>
    <thead><tr>
      <th>Rule Name</th><th>Keyword</th><th>Match</th>
      <th>Reply Type</th><th>Triggered</th><th>Status</th><th>Actions</th>
    </tr></thead>
    <tbody>
    ${rules.map(r => `<tr>
      <td><strong>${r.name}</strong></td>
      <td><span class="keyword-tag">${r.trigger_keyword}</span></td>
      <td style="color:var(--text-secondary);font-size:12px;">${r.match_type}</td>
      <td><span class="badge ${typeBadge(r.reply_type)}">${typeEmoji(r.reply_type)} ${r.reply_type}</span></td>
      <td><span class="triggered">${r.total_triggered} times</span></td>
      <td>
        <label class="toggle">
          <input type="checkbox" ${r.is_active ? "checked" : ""} onchange="toggleRule(${r.id},this)">
          <span class="slider"></span>
        </label>
      </td>
      <td>
        <div class="action-btns">
          <button class="action-btn" onclick='editRule(${JSON.stringify(r).replace(/'/g,"&#39;")})' title="Edit">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="action-btn delete" onclick="deleteRule(${r.id})" title="Delete">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
          </button>
        </div>
      </td>
    </tr>`).join("")}
    </tbody>
  </table>`;
}

window.selectType = function(type) {
  selectedType = type;
  document.querySelectorAll(".type-option").forEach(el => {
    el.classList.toggle("selected", el.dataset.type === type);
  });
  document.getElementById("textField").style.display = type === "text" ? "block" : "none";
  document.getElementById("mediaFields").classList.toggle("show", type !== "text");
  const accepts = { image:"image/*", video:"video/*", audio:"audio/*", document:".pdf,.doc,.docx" };
  const mf = document.getElementById("mediaFile");
  if (mf) mf.accept = accepts[type] || "*";
};

window.openModal = function() {
  document.getElementById("modalTitle").textContent = "New Auto Reply Rule";
  document.getElementById("editingId").value = "";
  ["r-name","r-keyword","r-text","r-media-url","r-caption"].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = "";
  });
  document.getElementById("r-match").value = "contains";
  document.getElementById("uploadedMediaUrl").value = "";
  const prev = document.getElementById("uploadedPreview");
  if (prev) prev.classList.remove("show");
  selectType("text");
  document.getElementById("modalOverlay").classList.add("show");
};

window.editRule = function(r) {
  document.getElementById("modalTitle").textContent = "Edit Rule";
  document.getElementById("editingId").value    = r.id;
  document.getElementById("r-name").value       = r.name;
  document.getElementById("r-keyword").value    = r.trigger_keyword;
  document.getElementById("r-match").value      = r.match_type;
  document.getElementById("r-text").value       = r.reply_text || "";
  document.getElementById("r-media-url").value  = r.media_url || "";
  document.getElementById("r-caption").value    = r.media_caption || "";
  selectType(r.reply_type);
  document.getElementById("modalOverlay").classList.add("show");
};

window.closeModal = function() {
  document.getElementById("modalOverlay").classList.remove("show");
};
window.closeModalOutside = function(e) {
  if (e.target.id === "modalOverlay") closeModal();
};

window.saveRule = async function() {
  const name    = document.getElementById("r-name").value.trim();
  const keyword = document.getElementById("r-keyword").value.trim();
  if (!name || !keyword) return showToast("Name aur keyword zaroori hain","error");
  if (selectedType === "text" && !document.getElementById("r-text").value.trim())
    return showToast("Text reply likho","error");
  const mediaUrl = document.getElementById("uploadedMediaUrl").value ||
                   document.getElementById("r-media-url").value.trim();
  if (selectedType !== "text" && !mediaUrl)
    return showToast("Media URL ya file zaroori hai","error");

  const body = {
    name, trigger_keyword: keyword,
    match_type:    document.getElementById("r-match").value,
    reply_type:    selectedType,
    reply_text:    document.getElementById("r-text").value.trim() || null,
    media_url:     mediaUrl || null,
    media_caption: document.getElementById("r-caption").value.trim() || null,
  };
  const id = document.getElementById("editingId").value;
  try {
    if (id) await AutoReplies.update(id, body);
    else    await AutoReplies.create(body);
    closeModal();
    showToast("Rule save ho gaya ✅","success");
    await loadRules();
  } catch(e) { showToast(e.message || "Error","error"); }
};

window.toggleRule = async function(id, checkbox) {
  try {
    const res = await AutoReplies.toggle(id);
    checkbox.checked = res.is_active;
  } catch(e) { checkbox.checked = !checkbox.checked; }
};

window.deleteRule = async function(id) {
  if (!confirm("Yeh rule delete karna chahte ho?")) return;
  try {
    await AutoReplies.delete(id);
    showToast("Deleted ✅","success");
    await loadRules();
  } catch(e) { showToast("Delete failed","error"); }
};

window.handleMediaUpload = async function(input) {
  const file = input.files[0];
  if (!file) return;
  const btn = document.getElementById("saveBtn");
  setLoading(btn, true);
  try {
    const data = await uploadMedia(file);
    const url  = `https://api.rajacloud.online${data.url}`;
    document.getElementById("uploadedMediaUrl").value = url;
    const icons = { image:"🖼️", video:"🎬", audio:"🎵", document:"📄" };
    document.getElementById("uploadedIcon").textContent = icons[data.media_type] || "📎";
    document.getElementById("uploadedName").textContent = file.name;
    document.getElementById("uploadedSize").textContent = `${data.size_kb} KB`;
    document.getElementById("uploadedPreview").classList.add("show");
    showToast("Upload complete ✅","success");
  } catch(e) { showToast(e.message || "Upload failed","error"); }
  setLoading(btn, false);
};

window.clearMedia = function() {
  document.getElementById("uploadedMediaUrl").value = "";
  document.getElementById("uploadedPreview").classList.remove("show");
  const mf = document.getElementById("mediaFile");
  if (mf) mf.value = "";
};


// ═══════════════════════════════════════════════════════════════════════════
// INTERACTIVE MENUS — NEW
// ═══════════════════════════════════════════════════════════════════════════

async function loadMenus() {
  try {
    const menus = await InteractiveMenus.getAll();
    setVal("stat-menus", menus.length);
    renderMenus(menus);
  } catch(e) {
    const el = document.getElementById("menusBody");
    if (el) el.innerHTML =
      `<div style="text-align:center;padding:40px;color:var(--text-light);">Could not load menus</div>`;
  }
}

function renderMenus(menus) {
  const el = document.getElementById("menusBody");
  if (!el) return;

  if (!menus.length) {
    el.innerHTML = `<div style="text-align:center;padding:50px;color:var(--text-light);">
      <div style="font-size:40px;margin-bottom:10px;">📋</div>
      <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;">Koi interactive menu nahi</h3>
      <p>"New Interactive Menu" se WhatsApp list/button menu banao</p>
    </div>`;
    return;
  }

  el.innerHTML = menus.map(m => {
    const items = m.items || [];
    const typeClass = m.menu_type === "buttons" ? "buttons" : "list";
    const typeLabel = m.menu_type === "buttons" ? "🔘 Buttons" : "📋 List";
    return `
    <div class="menu-card">
      <div class="menu-card-header">
        <div>
          <span class="menu-card-title">${m.name}</span>
          <span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">
            Keyword: <strong>${m.trigger_keyword}</strong> (${m.match_type})
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="menu-card-type ${typeClass}">${typeLabel}</span>
          <label class="toggle" style="margin:0;">
            <input type="checkbox" ${m.is_active ? "checked" : ""} onchange="toggleMenu(${m.id}, this)">
            <span class="slider"></span>
          </label>
        </div>
      </div>
      <div style="font-size:13px;color:var(--text-secondary);margin-bottom:6px;">${m.body_text || ""}</div>
      <div class="menu-items-preview">
        ${items.map(i => `<span class="menu-item-chip">${i.title || i.id}</span>`).join("")}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);">
        <span style="font-size:12px;color:var(--text-light);">Triggered: ${m.total_triggered} times</span>
        <div class="action-btns">
          <button class="action-btn" onclick='editMenu(${JSON.stringify(m).replace(/'/g,"&#39;")})' title="Edit">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="action-btn delete" onclick="deleteMenu(${m.id})" title="Delete">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
          </button>
        </div>
      </div>
    </div>`;
  }).join("");
}

// ── Menu Modal ───────────────────────────────────────────────────────────────

window.openMenuModal = function() {
  document.getElementById("menuModalTitle").textContent = "New Interactive Menu";
  document.getElementById("editingMenuId").value = "";
  ["m-name","m-keyword","m-header","m-body","m-footer"].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = "";
  });
  document.getElementById("m-match").value = "contains";
  document.getElementById("m-type").value = "list";
  document.getElementById("m-button-text").value = "Menu";
  menuItems = [];
  addMenuItem(); // Start with 1 empty item
  renderFollowUps();
  onMenuTypeChange();
  document.getElementById("menuModalOverlay").classList.add("show");
};

window.closeMenuModal = function() {
  document.getElementById("menuModalOverlay").classList.remove("show");
};

window.editMenu = function(m) {
  document.getElementById("menuModalTitle").textContent = "Edit Menu";
  document.getElementById("editingMenuId").value = m.id;
  document.getElementById("m-name").value    = m.name;
  document.getElementById("m-keyword").value = m.trigger_keyword;
  document.getElementById("m-match").value   = m.match_type;
  document.getElementById("m-type").value    = m.menu_type;
  document.getElementById("m-header").value  = m.header_text || "";
  document.getElementById("m-body").value    = m.body_text || "";
  document.getElementById("m-footer").value  = m.footer_text || "";
  document.getElementById("m-button-text").value = m.button_text || "Menu";
  menuItems = (m.items || []).map((item, i) => ({
    id: item.id || String(i + 1),
    title: item.title || "",
    description: item.description || "",
  }));
  if (!menuItems.length) addMenuItem();
  renderMenuItems();
  // Load follow-up rules
  window._editingFollowUps = m.follow_up_rules || {};
  renderFollowUps();
  onMenuTypeChange();
  document.getElementById("menuModalOverlay").classList.add("show");
};

window._editingFollowUps = {};

window.onMenuTypeChange = function() {
  const type = document.getElementById("m-type").value;
  const btnField = document.getElementById("buttonTextField");
  if (btnField) btnField.style.display = type === "list" ? "block" : "none";
};

// ── Items Builder ────────────────────────────────────────────────────────────

window.addMenuItem = function() {
  const maxItems = document.getElementById("m-type").value === "buttons" ? 3 : 10;
  if (menuItems.length >= maxItems) {
    showToast(`Max ${maxItems} items allowed`, "error");
    return;
  }
  menuItems.push({ id: String(menuItems.length + 1), title: "", description: "" });
  renderMenuItems();
  renderFollowUps();
};

window.removeMenuItem = function(index) {
  menuItems.splice(index, 1);
  // Re-number IDs
  menuItems.forEach((item, i) => item.id = String(i + 1));
  renderMenuItems();
  renderFollowUps();
};

function renderMenuItems() {
  const container = document.getElementById("menuItemsContainer");
  if (!container) return;
  const isButtons = document.getElementById("m-type").value === "buttons";

  container.innerHTML = menuItems.map((item, i) => `
    <div class="item-row">
      <span style="font-size:12px;font-weight:600;color:var(--green);min-width:24px;">${i + 1}.</span>
      <input type="text" placeholder="Title (e.g. Service Info)" value="${item.title}"
             onchange="menuItems[${i}].title=this.value; menuItems[${i}].id='${i + 1}'; renderFollowUps();"
             style="flex:1;">
      ${!isButtons ? `<input type="text" placeholder="Description" value="${item.description || ""}"
             onchange="menuItems[${i}].description=this.value"
             style="flex:1.5;">` : ""}
      <button class="remove-item-btn" onclick="removeMenuItem(${i})" title="Remove">✕</button>
    </div>
  `).join("");
}

// ── Follow-up Builder ────────────────────────────────────────────────────────

function renderFollowUps() {
  const container = document.getElementById("followupContainer");
  if (!container) return;
  const followUps = window._editingFollowUps || {};

  container.innerHTML = menuItems.map((item, i) => {
    const itemId = item.id || String(i + 1);
    const fu = followUps[itemId] || { type: "text", content: "" };
    const title = item.title || `Item ${i + 1}`;
    return `
    <div class="followup-row">
      <div class="followup-label">${title}:</div>
      <div style="flex:1;">
        <select onchange="updateFollowUp('${itemId}','type',this.value)" style="width:100%;margin-bottom:6px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
          <option value="text" ${fu.type === "text" ? "selected" : ""}>💬 Text Reply</option>
          <option value="media" ${fu.type === "media" ? "selected" : ""}>📎 Media (Image/Video/Audio)</option>
        </select>
        <textarea placeholder="Response message..."
                  onchange="updateFollowUp('${itemId}','content',this.value)"
                  style="width:100%;min-height:50px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;resize:vertical;">${fu.content || ""}</textarea>
        ${fu.type === "media" ? `
          <input type="text" placeholder="Media URL" value="${fu.media_url || ""}"
                 onchange="updateFollowUp('${itemId}','media_url',this.value)"
                 style="width:100%;margin-top:4px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;">
        ` : ""}
      </div>
    </div>`;
  }).join("");
}

window.updateFollowUp = function(itemId, field, value) {
  if (!window._editingFollowUps) window._editingFollowUps = {};
  if (!window._editingFollowUps[itemId]) window._editingFollowUps[itemId] = { type: "text", content: "" };
  window._editingFollowUps[itemId][field] = value;
  if (field === "type") renderFollowUps();
};

// ── Save Menu ────────────────────────────────────────────────────────────────

window.saveMenu = async function() {
  const name    = document.getElementById("m-name").value.trim();
  const keyword = document.getElementById("m-keyword").value.trim();
  const body    = document.getElementById("m-body").value.trim();

  if (!name || !keyword) return showToast("Name aur keyword zaroori hain", "error");
  if (!body) return showToast("Body text zaroori hai", "error");

  // Sync item titles from inputs
  const itemInputs = document.querySelectorAll("#menuItemsContainer .item-row");
  itemInputs.forEach((row, i) => {
    const inputs = row.querySelectorAll("input");
    if (inputs[0]) menuItems[i].title = inputs[0].value;
    if (inputs[1]) menuItems[i].description = inputs[1].value;
    menuItems[i].id = String(i + 1);
  });

  const validItems = menuItems.filter(i => i.title.trim());
  if (!validItems.length) return showToast("Kam az kam 1 item ka title dein", "error");

  const data = {
    name,
    trigger_keyword: keyword,
    match_type:      document.getElementById("m-match").value,
    menu_type:       document.getElementById("m-type").value,
    header_text:     document.getElementById("m-header").value.trim() || null,
    body_text:       body,
    footer_text:     document.getElementById("m-footer").value.trim() || null,
    button_text:     document.getElementById("m-button-text").value.trim() || "Menu",
    items:           validItems,
    follow_up_rules: window._editingFollowUps || {},
  };

  const id = document.getElementById("editingMenuId").value;

  try {
    if (id) await InteractiveMenus.update(id, data);
    else    await InteractiveMenus.create(data);
    closeMenuModal();
    showToast("Interactive menu saved ✅", "success");
    await loadMenus();
  } catch(e) { showToast(e.message || "Error", "error"); }
};

window.toggleMenu = async function(id, checkbox) {
  try {
    const res = await InteractiveMenus.toggle(id);
    checkbox.checked = res.is_active;
  } catch(e) { checkbox.checked = !checkbox.checked; }
};

window.deleteMenu = async function(id) {
  if (!confirm("Yeh interactive menu delete karna chahte ho?")) return;
  try {
    await InteractiveMenus.delete(id);
    showToast("Menu deleted ✅", "success");
    await loadMenus();
  } catch(e) { showToast("Delete failed", "error"); }
};