// =====================================================
// api.js — WhatsChat AI
// Path: whatschat-frontend/assets/js/api.js
// =====================================================

const API_BASE = "https://api.rajacloud.online/api";

function getToken()    { return localStorage.getItem("wc_token"); }
function setToken(t)   { localStorage.setItem("wc_token", t); }
function removeToken() { localStorage.removeItem("wc_token"); localStorage.removeItem("wc_user"); }
function getUser()     { const u = localStorage.getItem("wc_user"); return u ? JSON.parse(u) : null; }
function setUser(u)    { localStorage.setItem("wc_user", JSON.stringify(u)); }

let _isRefreshing = false;
let _refreshQueue = [];

async function apiFetch(endpoint, options = {}, _isRetry = false) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(token ? { "Authorization": `Bearer ${token}` } : {}), ...options.headers };
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

    if (res.status === 401 && !_isRetry) {
      // Try silent token refresh before logging out
      const skip401 = ["/auth/login", "/auth/register", "/auth/refresh"];
      if (!skip401.some(p => endpoint.includes(p))) {
        if (!_isRefreshing) {
          _isRefreshing = true;
          try {
            const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
              method: "POST",
              headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
            });
            if (refreshRes.ok) {
              const refreshData = await refreshRes.json();
              setToken(refreshData.access_token);
              if (refreshData.user) setUser(refreshData.user);
              _refreshQueue.forEach(fn => fn(refreshData.access_token));
              _refreshQueue = [];
              _isRefreshing = false;
              return apiFetch(endpoint, options, true);
            } else {
              _isRefreshing = false;
              _refreshQueue = [];
              // If we are on the login page or registering, don't redirect
              if (!["login.html", "register.html"].some(p => window.location.pathname.includes(p))) {
                removeToken();
                window.location.href = "auth/login.html";
              }
              return;
            }
          } catch (_) {
            _isRefreshing = false;
            removeToken();
            window.location.href = "auth/login.html";
            return;
          }
        } else {
          // Queue the retry
          return new Promise((resolve, reject) => {
            _refreshQueue.push(newToken => {
              options.headers = { ...options.headers, "Authorization": `Bearer ${newToken}` };
              resolve(apiFetch(endpoint, options, true));
            });
          });
        }
      }
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Something went wrong");
    return data;
  } catch (err) { console.error(`API Error [${endpoint}]:`, err.message); throw err; }
}

async function apiUpload(endpoint, formData) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", headers: { "Authorization": `Bearer ${token}` }, body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

const Auth = {
  async register(businessName, email, password, phone = null) {
    const data = await apiFetch("/auth/register", { method: "POST", body: JSON.stringify({ business_name: businessName, email, password, phone }) });
    setToken(data.access_token); setUser(data.user); return data;
  },
  async login(email, password) {
    const data = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    setToken(data.access_token); setUser(data.user); return data;
  },
  async me()    { return await apiFetch("/auth/me"); },
  async getMe() {
    try { const data = await apiFetch("/auth/me"); setUser(data); return data; }
    catch(e) { const u = JSON.parse(localStorage.getItem("wc_user") || "{}"); if (u.email) return u; throw e; }
  },
  async updatePlan(plan) { return await apiFetch("/auth/me/plan", { method: "PUT", body: JSON.stringify({ plan }) }); },
  logout()      { removeToken(); window.location.href = "auth/login.html"; },
  getToken()    { return getToken(); },
  isLoggedIn()  { return !!getToken(); },

  requireAuth() {
    if (!getToken()) {
      window.location.href = "auth/login.html";
      return;
    }
    if (!isPlanActive()) {
      showSubscriptionGate();
    }
  },

  requireAuthOnly() {
    if (!getToken()) {
      window.location.href = "auth/login.html";
    }
  },

  async refresh() {
    const token = getToken();
    if (!token) return;
    try {
      const data = await apiFetch("/auth/refresh", { method: "POST" });
      setToken(data.access_token);
      if (data.user) setUser(data.user);
      return data;
    } catch(e) {
      console.error("Refresh failed:", e);
      throw e;
    }
  }
};

const Contacts = {
  async getStats()       { return await apiFetch("/contacts/stats"); },
  async getAll(p = {})   { return await apiFetch("/contacts/?" + new URLSearchParams(p)); },
  async create(data)     { return await apiFetch("/contacts/", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/contacts/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async delete(id)       { return await apiFetch(`/contacts/${id}`, { method: "DELETE" }); },
  async deleteMany(ids)  { return await apiFetch(`/contacts/delete-bulk`, { method: "POST", body: JSON.stringify({ ids }) }); },
  async deleteAll()      { return await apiFetch(`/contacts/delete-bulk`, { method: "POST", body: JSON.stringify({ all: true }) }); },
  async importCSV(file)  { const fd = new FormData(); fd.append("file", file); return await apiUpload("/contacts/import/csv", fd); },
  exportCSV()            { window.open(`${API_BASE}/contacts/export/csv?token=${getToken()}`, "_blank"); },
};

const Campaigns = {
  async getStats()       { return await apiFetch("/campaigns/stats"); },
  async getAll(p = {})   { return await apiFetch("/campaigns/?" + new URLSearchParams(p)); },
  async create(data)     { return await apiFetch("/campaigns/", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/campaigns/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async delete(id)       { return await apiFetch(`/campaigns/${id}`, { method: "DELETE" }); },
  async send(id)         { return await apiFetch(`/campaigns/${id}/send`, { method: "POST" }); },
  async pause(id)        { return await apiFetch(`/campaigns/${id}/pause`, { method: "POST" }); },
};

const Chatbot = {
  async getStats()       { return await apiFetch("/chatbot/stats"); },
  async getAll()         { return await apiFetch("/chatbot/"); },
  async create(data)     { return await apiFetch("/chatbot/", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/chatbot/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async delete(id)       { return await apiFetch(`/chatbot/${id}`, { method: "DELETE" }); },
  async toggle(id)       { return await apiFetch(`/chatbot/${id}/toggle`, { method: "POST" }); },
};

const Analytics = {
  async getOverview(p="7days") { return await apiFetch(`/analytics/overview?period=${p}`); },
  async getDaily(p="7days")    { return await apiFetch(`/analytics/daily?period=${p}`); },
  async getDevices()           { return await apiFetch("/analytics/devices"); },
  async getCampaigns()         { return await apiFetch("/analytics/campaigns"); },
};

const Team = {
  async getStats()       { return await apiFetch("/team/stats"); },
  async getAll()         { return await apiFetch("/team/"); },
  async invite(data)     { return await apiFetch("/team/invite", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/team/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async remove(id)       { return await apiFetch(`/team/${id}`, { method: "DELETE" }); },
};

const WhatsApp = {
  async getStatus()           { return await apiFetch("/whatsapp/status"); },
  async connect(pid, tok)     { return await apiFetch("/whatsapp/connect", { method: "POST", body: JSON.stringify({ phone_number_id: pid, access_token: tok }) }); },
  async disconnect()          { return await apiFetch("/whatsapp/disconnect", { method: "POST" }); },
  async sendMessage(cid, msg) { return await apiFetch("/whatsapp/send", { method: "POST", body: JSON.stringify({ contact_id: cid, message: msg }) }); },
  async sendTest(to, message) { return await apiFetch("/whatsapp/test", { method: "POST", body: JSON.stringify({ to, message }) }); },
};

// ── INBOX — Updated ──────────────────────────────────
const Inbox = {
  getConversations: (p={}) => apiFetch("/inbox/conversations?" + new URLSearchParams(p)),
  getMessages: (phone) => apiFetch(`/inbox/conversation/${encodeURIComponent(phone)}`),
  getUnreadCount: () => apiFetch("/inbox/unread-count"),
  reply: (phone, message, type = "text", mediaUrl = null, quotedMsgId = null) =>
    apiFetch("/inbox/reply", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_phone:    phone,
        message:           message,
        message_type:      type,
        media_url:         mediaUrl || null,
        quoted_message_id: quotedMsgId || null,
      }),
    }),
  sendMedia: async (phone, file, mediaType, caption = "", quotedMsgId = null) => {
    const fd = new FormData();
    fd.append("to",         phone);
    fd.append("media_type", mediaType);
    fd.append("caption",    caption);
    fd.append("file",       file);
    if (quotedMsgId) fd.append("quoted_message_id", quotedMsgId);
    const token = getToken();
    const r = await fetch(`${API_BASE}/inbox/send-media`, {
      method:  "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body:    fd,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Media send failed");
    }
    return r.json();
  },
  sendAudioRecord: async (phone, blob, quotedMsgId = null) => {
    const fd = new FormData();
    fd.append("to",   phone);
    fd.append("file", blob, "voice.ogg");
    if (quotedMsgId) fd.append("quoted_message_id", quotedMsgId);
    const token = getToken();
    const r = await fetch(`${API_BASE}/inbox/send-audio-record`, {
      method:  "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body:    fd,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Audio send failed");
    }
    return r.json();
  },
  starMessage:          (msgId) => apiFetch(`/inbox/star/${msgId}`, { method: "POST" }),
  getStarred:           (phone) => apiFetch(`/inbox/starred/${encodeURIComponent(phone)}`),
  deleteMessage:        (msgId) => apiFetch(`/inbox/message/${msgId}`, { method: "DELETE" }),
  getContactStatus:     (phone) => apiFetch(`/inbox/status/${encodeURIComponent(phone)}`),
};

const InteractiveMenus = {
  async getAll()         { return await apiFetch("/interactive-menus/"); },
  async create(data)     { return await apiFetch("/interactive-menus/", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/interactive-menus/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async delete(id)       { return await apiFetch(`/interactive-menus/${id}`, { method: "DELETE" }); },
  async toggle(id)       { return await apiFetch(`/interactive-menus/${id}/toggle`, { method: "POST" }); },
};

const AutoReplies = {
  async getAll()         { return await apiFetch("/auto-replies/"); },
  async create(data)     { return await apiFetch("/auto-replies/", { method: "POST", body: JSON.stringify(data) }); },
  async update(id, data) { return await apiFetch(`/auto-replies/${id}`, { method: "PUT", body: JSON.stringify(data) }); },
  async delete(id)       { return await apiFetch(`/auto-replies/${id}`, { method: "DELETE" }); },
  async toggle(id)       { return await apiFetch(`/auto-replies/${id}/toggle`, { method: "POST" }); },
};

const Templates = {
  async getAll()     { return await apiFetch("/templates/"); },
  async create(data) { return await apiFetch("/templates/", { method: "POST", body: JSON.stringify(data) }); },
  async delete(id)   { return await apiFetch(`/templates/${id}`, { method: "DELETE" }); },
};

const MessageLog = {
  async getStats()     { return await apiFetch("/message-log/stats"); },
  async getAll(p = {}) { return await apiFetch("/message-log/?" + new URLSearchParams(p)); },
};

const Settings = {
  async get()        { return await apiFetch("/settings/"); },
  async update(data) { return await apiFetch("/settings/", { method: "PUT", body: JSON.stringify(data) }); },
};

const SubRequests = {
  async create(plan, paymentMethod, screenshotUrl=null) {
    return await apiFetch("/subscription-requests/", { method: "POST", body: JSON.stringify({ plan, payment_method: paymentMethod, screenshot_url: screenshotUrl }) });
  },
  async getMy()   { return await apiFetch("/subscription-requests/my"); },
  async adminAll(status=null) { return await apiFetch(`/subscription-requests/admin/all${status?'?status='+status:''}`); },
  async adminReview(id, status, note=null) {
    return await apiFetch(`/subscription-requests/admin/${id}/review`, { method: "POST", body: JSON.stringify({ status, admin_note: note }) });
  },
};

// ── Media Upload Helper ──────────────────────────────
async function uploadMedia(file) {
  const fd = new FormData();
  fd.append("file", file);
  return await apiUpload("/media/upload", fd);
}

// ── Compatibility: API.request() style ───────────────
const API = {
  async request(endpoint, method="GET", body=null) {
    const opts = { method };
    if (body) opts.body = JSON.stringify(body);
    return await apiFetch(endpoint, opts);
  },
  async getUser() { return await Auth.getMe(); },
  Auth, Contacts, Campaigns, Chatbot, Analytics, Team, WhatsApp,
  Inbox, AutoReplies, Templates, MessageLog, Settings, SubRequests, InteractiveMenus,
};

// ── UI Helpers ────────────────────────────────────────
function showToast(message, type="success") {
  const existing = document.getElementById("wc-toast");
  if (existing) existing.remove();
  const toast = document.createElement("div");
  toast.id = "wc-toast";
  const colors = { success:"#25D366", error:"#ef4444", info:"#3b82f6", "":"#1f2937" };
  toast.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;padding:12px 20px;border-radius:10px;font-size:13.5px;font-family:'DM Sans',sans-serif;font-weight:500;box-shadow:0 8px 24px rgba(0,0,0,.15);background:${colors[type]??colors.success};color:white;`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
function setLoading(btn, loading=true) {
  if (!btn) return;
  if (loading) { btn.dataset.orig = btn.textContent; btn.textContent = "Loading..."; btn.disabled = true; btn.style.opacity = ".7"; }
  else         { btn.textContent = btn.dataset.orig || "Submit"; btn.disabled = false; btn.style.opacity = "1"; }
}
function setVal(id, val) { const el = document.getElementById(id); if (el) el.textContent = (val ?? "—"); }
function capitalize(s)   { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }
function fillSidebarUser() {
  const user = getUser();
  if (!user) return;
  ["user-name","sidebar-name"].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = user.business_name || "My Business"; });
  ["user-email","sidebar-email"].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = user.email || ""; });
  ["user-avatar","sidebar-avatar"].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = (user.business_name||"U")[0].toUpperCase(); });
}
function timeAgo(dateStr) {
  if (!dateStr) return "Never";
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return Math.floor(diff/60) + " min ago";
  if (diff < 86400) return Math.floor(diff/3600) + " hrs ago";
  return Math.floor(diff/86400) + " days ago";
}
function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso), now = new Date(), diff = now - d;
  if (diff < 86400000)  return d.toLocaleTimeString("en-PK", {hour:"2-digit",minute:"2-digit"});
  if (diff < 604800000) return d.toLocaleDateString("en-PK", {weekday:"short"});
  return d.toLocaleDateString("en-PK", {day:"numeric",month:"short"});
}

// =====================================================
// ── Subscription Gate Functions ───────────────────────
// =====================================================

function isPlanActive() {
  return true;
}

function showSubscriptionGate() {
  if (document.getElementById("__subGate")) return;
  if (window.location.pathname.includes("subscriptions.html")) return;

  const user      = getUser();
  const plan      = user?.plan || "free";
  const status    = user?.subscription_status || "";
  const isPending = plan !== "free" && status === "pending";
  const rootPath  = window.location.pathname.includes("/auth/") ? "../" : "";

  const overlay = document.createElement("div");
  overlay.id = "__subGate";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(17,24,39,0.88);z-index:9999;display:flex;align-items:center;justify-content:center;font-family:'DM Sans',system-ui,sans-serif;";

  if (isPending) {
    overlay.innerHTML = `
      <div style="background:white;border-radius:18px;padding:44px 40px;max-width:400px;width:90%;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.35);">
        <div style="font-size:52px;margin-bottom:16px;">⏳</div>
        <div style="font-size:21px;font-weight:800;margin-bottom:10px;color:#111827;">Approval Pending Hai</div>
        <div style="font-size:14px;color:#6b7280;margin-bottom:10px;line-height:1.7;">
          Aapne <strong style="color:#111827;">${capitalize(plan)} Plan</strong> choose kiya hai.<br>
          Admin review kar raha hai —<br>
          <strong style="color:#f59e0b;">24 ghante mein approve ho jayega.</strong>
        </div>
        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px;margin-bottom:24px;font-size:13px;color:#92400e;">
          💡 Approve hone ke baad automatically sab features unlock ho jayenge
        </div>
        <a href="${rootPath}subscriptions.html"
          style="display:block;padding:13px;background:#f59e0b;color:white;border-radius:11px;font-size:14px;font-weight:700;text-decoration:none;margin-bottom:10px;">
          📋 Request Status Dekho
        </a>
        <button onclick="Auth.logout()"
          style="width:100%;padding:11px;background:white;color:#6b7280;border:1.5px solid #e5e7eb;border-radius:11px;font-size:13.5px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;">
          🚪 Logout
        </button>
      </div>
    `;
  } else {
    overlay.innerHTML = `
      <div style="background:white;border-radius:18px;padding:44px 40px;max-width:400px;width:90%;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.35);">
        <div style="font-size:52px;margin-bottom:16px;">🔒</div>
        <div style="font-size:21px;font-weight:800;margin-bottom:10px;color:#111827;">Plan Activate Karein</div>
        <div style="font-size:14px;color:#6b7280;margin-bottom:28px;line-height:1.7;">
          Yeh feature use karne ke liye<br>
          <strong style="color:#111827;">pehle subscription plan activate karwana hoga.</strong><br>
          Admin approval ke baad sab features<br>unlock ho jayenge. ✅
        </div>
        <a href="${rootPath}subscriptions.html"
          style="display:block;padding:14px;background:#25D366;color:white;border-radius:11px;font-size:15px;font-weight:700;text-decoration:none;margin-bottom:12px;box-shadow:0 4px 14px rgba(37,211,102,.35);">
          💳 Plan Choose Karein
        </a>
        <button onclick="Auth.logout()"
          style="width:100%;padding:12px;background:white;color:#6b7280;border:1.5px solid #e5e7eb;border-radius:11px;font-size:14px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;">
          🚪 Logout
        </button>
      </div>
    `;
  }

  document.body.appendChild(overlay);
}