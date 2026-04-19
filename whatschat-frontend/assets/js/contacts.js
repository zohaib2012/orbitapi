// contacts.js — Path: whatschat-frontend/assets/js/contacts.js

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadStats();
  await loadContacts();
});

async function loadStats() {
  try {
    const s = await Contacts.getStats();
    setVal("stat-total",    s.total?.toLocaleString());
    setVal("stat-active",   s.active?.toLocaleString());
    setVal("stat-inactive", s.inactive?.toLocaleString());
    setVal("stat-lists",    s.total_lists);
  } catch(e) { console.error(e); }
}

// selected contact ids
const selectedContacts = new Set();

async function loadContacts(search = "") {
  try {
    const params = { limit: 10000 };
    if (search) params.search = search;
    const list = await Contacts.getAll(params);
    const tbody = document.getElementById("contactsTable");
    if (!tbody) return;
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:30px;color:#9ca3af">No contacts found</td></tr>`;
      return;
    }
    tbody.innerHTML = list.map(c => `
      <tr>
        <td style="padding:12px 16px;text-align:center;">
          <input type="checkbox" class="contact-checkbox" value="${c.id}" onclick="toggleContactSelection(${c.id}, this)" ${selectedContacts.has(c.id) ? "checked" : ""}>
        </td>
        <td style="padding:12px 16px;font-weight:500">${c.name}</td>
        <td style="padding:12px 16px;font-size:13px;color:#6b7280">
          <div>📞 ${c.phone}</div>
          ${c.email ? `<div>✉️ ${c.email}</div>` : ""}
        </td>
        <td style="padding:12px 16px">
          ${(c.tags||[]).map(t=>`<span style="background:#f3f4f6;border-radius:20px;padding:2px 8px;font-size:11px;margin-right:4px">${t}</span>`).join("")}
        </td>
        <td style="padding:12px 16px">
          <span style="padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:${c.status==='active'?'#dcfce7':'#f3f4f6'};color:${c.status==='active'?'#16a34a':'#6b7280'}">${capitalize(c.status)}</span>
        </td>
        <td style="padding:12px 16px;font-size:12px;color:#9ca3af">${c.created_at?.split("T")[0]||""}</td>
        <td style="padding:12px 16px">
          <button onclick="editContact(${c.id})" style="border:1px solid #e5e7eb;background:white;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;margin-right:4px">Edit</button>
          <button onclick="deleteContact(${c.id})" style="border:1px solid #fecaca;background:#fef2f2;color:#dc2626;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer">Delete</button>
        </td>
      </tr>`).join("");
    updateBulkBar();
  } catch(e) { showToast("Contacts load nahi hue", "error"); }
}

function toggleContactSelection(id, el) {
  if (el.checked) selectedContacts.add(id);
  else selectedContacts.delete(id);
  updateBulkBar();
  syncSelectAllCheckbox();
}

function toggleSelectAll(el) {
  const boxes = document.querySelectorAll(".contact-checkbox");
  if (el.checked) {
    boxes.forEach(b => { b.checked = true; selectedContacts.add(parseInt(b.value)); });
  } else {
    boxes.forEach(b => { b.checked = false; });
    selectedContacts.clear();
  }
  updateBulkBar();
}

function syncSelectAllCheckbox() {
  const all = document.querySelectorAll(".contact-checkbox");
  const header = document.getElementById("selectAllCheckbox");
  if (!header || !all.length) return;
  const checkedCount = Array.from(all).filter(b => b.checked).length;
  header.checked = checkedCount === all.length;
  header.indeterminate = checkedCount > 0 && checkedCount < all.length;
}

function updateBulkBar() {
  const bar = document.getElementById("bulkActionBar");
  const count = document.getElementById("bulkCount");
  if (!bar) return;
  if (selectedContacts.size > 0) {
    bar.style.display = "flex";
    if (count) count.textContent = selectedContacts.size;
  } else {
    bar.style.display = "none";
  }
}

function clearSelection() {
  selectedContacts.clear();
  document.querySelectorAll(".contact-checkbox").forEach(b => b.checked = false);
  const header = document.getElementById("selectAllCheckbox");
  if (header) { header.checked = false; header.indeterminate = false; }
  updateBulkBar();
}

async function deleteSelected() {
  if (!selectedContacts.size) return;
  if (!confirm(`${selectedContacts.size} contacts aur unki inbox conversations delete karna chahte ho?`)) return;
  try {
    const ids = Array.from(selectedContacts);
    const r = await Contacts.deleteMany(ids);
    showToast(`${r.deleted} contacts + inbox deleted ✅`);
    selectedContacts.clear();
    await loadStats();
    await loadContacts();
  } catch(e) { showToast(e.message || "Delete failed", "error"); }
}

async function deleteAllContacts() {
  if (!confirm("SAB contacts aur unki SAARI inbox conversations delete karna chahte ho? Ye action wapis nahi ho sakta.")) return;
  if (!confirm("Confirm once more — SAB contacts + inbox permanently delete ho jayenge!")) return;
  try {
    const r = await Contacts.deleteAll();
    showToast(`${r.deleted} contacts + inbox deleted ✅`);
    selectedContacts.clear();
    await loadStats();
    await loadContacts();
  } catch(e) { showToast(e.message || "Delete failed", "error"); }
}

function exportContactsCSV() {
  Contacts.exportCSV();
  showToast("Export started 📥");
}

// Search
function filterContacts() { loadContacts(document.getElementById("searchInput")?.value || ""); }

// Modal open/close
function openModal()       { document.getElementById("modalOverlay")?.classList.add("open"); document.getElementById("editingId").value=""; document.getElementById("contactForm")?.reset(); }
function closeModal()      { document.getElementById("modalOverlay")?.classList.remove("open"); }
function closeModalOutside(e) { if (e.target.id==="modalOverlay") closeModal(); }

async function saveContact() {
  const editingId = document.getElementById("editingId")?.value;
  const name   = document.getElementById("c-name")?.value.trim();
  const phone  = document.getElementById("c-phone")?.value.trim();
  const email  = document.getElementById("c-email")?.value.trim();
  const tags   = (document.getElementById("c-tags")?.value||"").split(",").map(t=>t.trim()).filter(Boolean);
  const status = document.getElementById("c-status")?.value || "active";
  const btn    = document.getElementById("saveContactBtn");

  if (!name || !phone) { showToast("Name aur phone zaroori hain", "error"); return; }
  setLoading(btn, true);
  try {
    if (editingId) { await Contacts.update(editingId, { name, phone, email:email||null, tags, status }); showToast("Contact updated ✅"); }
    else           { await Contacts.create({ name, phone, email:email||null, tags, status }); showToast("Contact added ✅"); }
    closeModal();
    await loadStats();
    await loadContacts();
  } catch(err) { showToast(err.message||"Error", "error"); }
  finally { setLoading(btn, false); }
}

async function editContact(id) {
  try {
    const list = await Contacts.getAll();
    const c = list.find(x => x.id === id);
    if (!c) return;
    document.getElementById("editingId").value   = id;
    document.getElementById("c-name").value      = c.name;
    document.getElementById("c-phone").value     = c.phone;
    document.getElementById("c-email").value     = c.email||"";
    document.getElementById("c-tags").value      = (c.tags||[]).join(", ");
    document.getElementById("c-status").value    = c.status;
    document.getElementById("modalOverlay")?.classList.add("open");
  } catch(e) { showToast("Load error", "error"); }
}

async function deleteContact(id) {
  if (!confirm("Delete karna chahte ho?")) return;
  try { await Contacts.delete(id); showToast("Deleted"); await loadStats(); await loadContacts(); }
  catch(e) { showToast(e.message||"Error", "error"); }
}

async function importCSV() {
  const input = document.createElement("input");
  input.type = "file"; input.accept = ".csv";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      showToast("Importing...", "info");
      const r = await Contacts.importCSV(file);
      showToast(`${r.imported} contacts imported ✅`);
      await loadStats(); await loadContacts();
    } catch(e) { showToast(e.message||"Import failed","error"); }
  };
  input.click();
}