// inbox.js — WhatsChat AI Live Inbox (UPGRADED)
// Path: whatschat-frontend/assets/js/inbox.js

let currentPhone      = null;
let conversations     = [];
let filteredConvs     = [];
let allMessages       = [];
let selectedMedia     = null;
let selectedMediaType = null;
let showStarredOnly   = false;

// ── Pagination state ─────────────────────────────────────────────────────────
let convSkip          = 0;
const convLimit       = 50;
let hasMoreConvs      = true;
let isLoadingConvs    = false;

// ── Audio Recorder state ─────────────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks   = [];
let recordTimer   = null;
let recordSeconds = 0;
let isRecording   = false;

// ── Quote Reply state ────────────────────────────────────────────────────────
let replyTo = null;

// ── Scroll state ─────────────────────────────────────────────────────────────
let userScrolledUp = false;


// ═══════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════

window.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  const user = await Auth.getMe();
  if (user) {
    setVal("user-name",  user.business_name || "Business");
    setVal("user-email", user.email || "");
    const av = document.getElementById("user-avatar");
    if (av) av.textContent = (user.business_name || "B")[0].toUpperCase();
  }
  await loadConversations();
  await loadUnreadBadge();

  // Scroll listener
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages) {
    chatMessages.addEventListener("scroll", () => {
      const threshold = 80;
      const distanceFromBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight;
      userScrolledUp = distanceFromBottom > threshold;
      // Scroll-to-bottom button toggle
      const scrollBtn = document.getElementById("scrollToBottomBtn");
      if (scrollBtn) {
        scrollBtn.style.display = userScrolledUp ? "flex" : "none";
      }
    });
  }

  // Initial token refresh to keep session alive
  Auth.refresh().catch(() => {});

  // Auto-refresh every 5 seconds (faster for real-time feel)
  setInterval(async () => {
    const listEl = document.getElementById("convList");
    // Only refresh if at the top and not loading
    if (listEl && listEl.scrollTop < 50 && !isLoadingConvs) {
      await loadConversations();
    }
    if (currentPhone) await loadMessages(currentPhone, false);
    await loadUnreadBadge();
  }, 5000);

  // Silent token refresh every 24 hours
  setInterval(async () => {
    await Auth.refresh().catch(() => {});
  }, 24 * 60 * 60 * 1000);
});


// ═══════════════════════════════════════════════════════════════════════════
// CONVERSATIONS
// ═══════════════════════════════════════════════════════════════════════════

async function loadConversations(append = false) {
  if (isLoadingConvs) return;
  if (!append) {
    convSkip = 0;
    hasMoreConvs = true;
    conversations = [];
  }
  if (!hasMoreConvs) return;

  isLoadingConvs = true;
  try {
    const newList = await Inbox.getConversations({ skip: convSkip, limit: convLimit }) || [];
    if (newList.length < convLimit) hasMoreConvs = false;
    
    conversations = append ? [...conversations, ...newList] : newList;
    convSkip += newList.length;
    
    filterConversations(document.getElementById("convSearch")?.value || "");
  } catch(e) {
    console.error(e);
    if (!append) {
      document.getElementById("convList").innerHTML =
        `<div style="text-align:center;padding:30px;color:var(--text-light);">Could not load conversations</div>`;
    }
  } finally {
    isLoadingConvs = false;
  }
}

function renderConversations(list) {
  const el = document.getElementById("convList");
  if (!list.length && convSkip <= convLimit) {
    el.innerHTML = `<div class="conv-empty">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
      <p>No conversations yet</p>
      <p style="font-size:11px;margin-top:4px">Customer ka message aane par yahan dikhe ga</p>
    </div>`;
    return;
  }

  const html = list.map(c => {
    const rawPhone = c.customer_phone || "";
    const phone    = rawPhone.startsWith("+") ? rawPhone : `+${rawPhone}`;
    const name     = c.customer_name || phone;
    const initial  = name[0].toUpperCase();
    const preview  = c.last_message_type !== "text"
      ? `📎 ${c.last_message_type}`
      : (c.last_message || "");
    const time     = c.last_time ? formatTime(c.last_time) : "";
    const isActive = c.customer_phone === currentPhone ? "active" : "";
    const unread   = c.unread_count > 0 ? `<span class="conv-unread">${c.unread_count}</span>` : "";
    const dirIcon  = c.direction === "outbound" ? "↗ " : "";
    const favIcon = c.is_favorite ? "❤️" : "🤍";
    return `<div class="conv-item ${isActive}"
                 onclick="openConversation('${c.customer_phone}','${name.replace(/'/g,"\\'")}')">
      <div class="conv-avatar">${initial}</div>
      <div class="conv-info">
        <div class="conv-name">${name}</div>
        <div class="conv-preview">${dirIcon}${preview}</div>
      </div>
      <div class="conv-meta">
        <span class="conv-time">${time}</span>
        ${unread}
        <span onclick="event.stopPropagation(); toggleFavConv('${c.customer_phone}')" style="cursor:pointer; font-size:12px; margin-top:4px;" title="Favorite">${favIcon}</span>
      </div>
    </div>`;
  }).join("");

  el.innerHTML = html;
  
  // Add scroll listener for infinite scroll if not already added
  if (!el.dataset.scrollInit) {
    el.dataset.scrollInit = "true";
    el.addEventListener("scroll", () => {
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
        if (!isLoadingConvs && hasMoreConvs && currentConvTab === 'all') {
          loadConversations(true);
        }
      }
    });
  }
}

let currentConvTab = 'all';

window.setConvTab = function(tab) {
  currentConvTab = tab;
  document.getElementById("tab-all").classList.remove("active");
  document.getElementById("tab-unread").classList.remove("active");
  document.getElementById("tab-fav").classList.remove("active");
  document.getElementById("tab-" + tab).classList.add("active");
  filterConversations(document.getElementById("convSearch").value);
};

window.filterConversations = function(q) {
  let filtered = conversations;
  if (currentConvTab === 'unread') {
    filtered = filtered.filter(c => c.unread_count > 0);
  } else if (currentConvTab === 'fav') {
    filtered = filtered.filter(c => c.is_favorite);
  }
  
  if (q) {
    filtered = filtered.filter(c =>
      (c.customer_name || "").toLowerCase().includes(q.toLowerCase()) ||
      (c.customer_phone || "").toLowerCase().includes(q.toLowerCase())
    );
  }
  
  filteredConvs = filtered;
  renderConversations(filteredConvs);
};

window.toggleFavConv = async function(phone) {
  try {
    const res = await apiFetch(`/inbox/conversation/${encodeURIComponent(phone)}/favorite`, { method: "POST" });
    const conv = conversations.find(c => c.customer_phone === phone);
    if (conv) conv.is_favorite = res.is_favorite;
    filterConversations(document.getElementById("convSearch").value);
  } catch(e) {
    showToast("Failed to toggle favorite", "error");
  }
};

window.openConversation = async function(phone, name) {
  currentPhone   = phone;
  userScrolledUp = false;
  showStarredOnly = false;
  document.getElementById("chatEmpty").style.display  = "none";
  const ac = document.getElementById("activeChat");
  ac.style.display = "flex";
  setVal("chatName",  name);
  setVal("chatPhone", phone);
  const av = document.getElementById("chatAvatar");
  if (av) av.textContent = name[0].toUpperCase();
  document.querySelectorAll(".conv-item").forEach(el => el.classList.remove("active"));
  event?.currentTarget?.classList.add("active");

  // Reset star filter button
  const starBtn = document.getElementById("starFilterBtn");
  if (starBtn) starBtn.classList.remove("active-filter");

  await loadMessages(phone, true);
  await updateStatusUI(phone);
};

let statusPoll = null;
async function updateStatusUI(phone) {
  const container = document.getElementById("chatStatusContainer");
  const dot       = document.getElementById("statusDot");
  const text      = document.getElementById("statusText");
  if (!container || !dot || !text) return;

  try {
    const data = await Inbox.getContactStatus(phone);
    container.style.display = "flex";
    if (data.status === "online") {
      dot.className = "status-dot online";
      text.textContent = "Online";
    } else if (data.status === "recent") {
      dot.className = "status-dot online"; // recent can also be green but different text
      text.textContent = "Recently active";
    } else {
      dot.className = "status-dot";
      text.textContent = data.last_seen ? `Last seen: ${timeAgo(data.last_seen)}` : "Offline";
    }

    // Restart polling
    if (statusPoll) clearTimeout(statusPoll);
    if (currentPhone === phone) {
      statusPoll = setTimeout(() => updateStatusUI(phone), 30000); // Pool status every 30s
    }
  } catch(_) {}
}


// ═══════════════════════════════════════════════════════════════════════════
// MESSAGES
// ═══════════════════════════════════════════════════════════════════════════

async function loadMessages(phone, scroll = true) {
  try {
    const msgs = await Inbox.getMessages(phone);
    allMessages = msgs || [];
    const shouldScroll = scroll || !userScrolledUp;
    renderMessages(allMessages, shouldScroll);
    await loadConversations();
  } catch(e) { console.error(e); }
}
window.loadMessages = loadMessages;

window.deleteMsg = async function(id) {
  if (!confirm("Are you sure you want to delete this message?")) return;
  try {
    await Inbox.deleteMessage(id);
    showToast("Message deleted", "success");
    // Refresh UI
    allMessages = allMessages.filter(m => m.id !== id);
    renderMessages(allMessages, false);
  } catch(e) {
    showToast(e.message || "Failed to delete message", "error");
  }
};

function renderMessages(msgs, scroll = true) {
  const el = document.getElementById("chatMessages");
  if (!msgs.length) {
    el.innerHTML = `<div style="text-align:center;color:#9ca3af;padding:20px;font-size:13px;">No messages yet</div>`;
    return;
  }

  // Filter starred if active
  let displayMsgs = msgs;
  if (showStarredOnly) {
    displayMsgs = msgs.filter(m => m.is_starred);
    if (!displayMsgs.length) {
      el.innerHTML = `<div style="text-align:center;color:#9ca3af;padding:40px;font-size:13px;">⭐ Koi starred message nahi hai</div>`;
      return;
    }
  }

  let lastDate = "";
  let foundFirstUnread = false;
  el.innerHTML = "";

  displayMsgs.forEach(m => {
    const dt      = m.received_at ? new Date(m.received_at) : new Date();
    const dateStr = dt.toLocaleDateString("en-PK", { day:"numeric", month:"short", year:"numeric" });
    const timeStr = dt.toLocaleTimeString("en-PK", { hour:"2-digit", minute:"2-digit" });

    // Date divider
    if (dateStr !== lastDate) {
      lastDate = dateStr;
      const div = document.createElement("div");
      div.className   = "msg-date-divider";
      div.textContent = dateStr;
      el.appendChild(div);
    }

    // ── Unread separator ─────────────────────────────────────────────────
    if (m.direction === "inbound" && !m.is_read && !foundFirstUnread && !showStarredOnly) {
      foundFirstUnread = true;
      const sep = document.createElement("div");
      sep.className = "unread-separator";
      sep.innerHTML = `<span>Unread Messages</span>`;
      el.appendChild(sep);
    }

    // Message bubble
    const bubble = document.createElement("div");
    const cls    = m.direction === "inbound" ? "inbound" : "outbound";
    bubble.className     = `msg-bubble ${cls}`;
    bubble.dataset.msgId = m.id;

    let html = "";

    // ── Quote bar ──────────────────────────────────────────────────────
    if (m.quoted_message_id) {
      const quoted = allMessages.find(x => x.id == m.quoted_message_id);
      if (quoted) {
        const icons    = { image: "📷 Image", video: "🎥 Video", audio: "🎵 Voice" };
        const qPreview = icons[quoted.message_type] || (quoted.content || "").substring(0, 50);
        html += `
          <div class="quote-bar" onclick="scrollToMsg(${quoted.id})">
            <span class="q-line"></span>
            <span class="q-text">${qPreview}</span>
          </div>`;
      }
    }

    // ── Media content ──────────────────────────────────────────────────
    if (m.media_url || (m.message_type !== "text" && m.content)) {
      let src = m.media_url || `/uploads/${m.content}`;
      // FIX: Ensure absolute URL
      if (src && !src.startsWith("http") && !src.startsWith("blob:")) {
        src = `https://api.rajacloud.online${src.startsWith('/') ? '' : '/'}${src}`;
      }

      if (m.message_type === "image") {
        html += `<div class="msg-media">
                   <img src="${src}" alt="image" onclick="openLightbox('${src}')" style="cursor:zoom-in;" onerror="this.style.display='none'">
                 </div>`;
      } else if (m.message_type === "video") {
        html += `<div class="msg-media"><video controls src="${src}" preload="metadata" style="max-width:280px;"></video></div>`;
      } else if (m.message_type === "audio") {
        const durText = m.duration ? `<span class="audio-duration-label">${Math.floor(m.duration/60)}:${String(m.duration%60).padStart(2,'0')}</span>` : "";
        html += `<div class="msg-media msg-audio-wrap">
                   <span style="font-size:18px;">🎵</span>
                   <audio controls src="${src}" preload="metadata" style="max-width:200px;height:32px;"></audio>
                   ${durText}
                 </div>`;
      } else {
        const docName = src.split('/').pop() || "Document";
        html += `<div class="msg-media" style="background:#f3f4f6;padding:10px;border-radius:8px;font-size:12px;cursor:pointer;" onclick="window.open('${src}','_blank')">📎 <u>${docName}</u></div>`;
      }
    }

    // ── Text content ───────────────────────────────────────────────────
    if (m.content && m.message_type === "text") {
      html += `<div class="msg-text-body">${m.content}</div>`;
    } else if (m.content && m.message_type !== "text" && m.media_url) {
      html += `<div class="msg-caption">${m.content}</div>`;
    }

    // ── Footer: time + status ticks + action buttons ─────────────────
    const safeContent = (m.message_type === "text" ? (m.content || "") : "").replace(/`/g,"'").replace(/"/g,"&quot;");

    // Copy button (text only)
    const copyBtn = m.message_type === "text" && m.content
      ? `<button class="copy-btn-inline" onclick="copyMsg(this, \`${safeContent}\`)" title="Copy">⎘</button>`
      : "";

    // Star button
    const isStarred = m.is_starred ? "starred" : "";
    const starBtn = `<button class="star-btn-inline ${isStarred}" onclick="toggleStar(${m.id}, this)" title="Star">★</button>`;

    // Status ticks (outbound only)
    let statusIcon = "";
    if (m.direction === "outbound") {
      if (m.isPending) {
        statusIcon = `<div class="msg-loader"></div>`;
      } else {
        const st = m.whatsapp_status || "sent";
        if (st === "read") {
          statusIcon = `<span class="msg-ticks read" title="Read">✓✓</span>`;
        } else if (st === "delivered") {
          statusIcon = `<span class="msg-ticks delivered" title="Delivered">✓✓</span>`;
        } else {
          statusIcon = `<span class="msg-ticks sent" title="Sent">✓</span>`;
        }
      }
    }

    html += `
      <div class="msg-footer-row">
        <span class="msg-time">${timeStr}</span>
        ${statusIcon}
        ${starBtn}
        ${copyBtn}
        <button class="delete-msg-btn" onclick="window.deleteMsg(${m.id})" title="Delete Message">🗑️</button>
        <button class="forward-btn-inline"
                onclick="forwardMsg(${m.id},'${safeContent}','${m.message_type}')"
                style="background:none;border:none;color:var(--text-light);cursor:pointer;font-size:14px;padding:0 2px;"
                title="Forward">➦</button>
        <button class="reply-btn-inline"
                onclick="setReply(${m.id},'${safeContent}','${m.message_type}')"
                title="Reply">↩</button>
      </div>`;

    bubble.innerHTML = html;
    el.appendChild(bubble);
  });

  if (scroll) {
    // Wait for images to render before calculating scrollHeight
    setTimeout(() => {
        el.scrollTop = el.scrollHeight;
    }, 250);
  }
}

// ── Copy Chat History ────────────────────────────────────────────────────────
window.copyChatHistory = function() {
  if (!allMessages.length) {
    showToast("No messages to copy", "info");
    return;
  }
  let chatName = document.getElementById("chatName").textContent;
  let txt = `WhatsApp Chat with ${chatName}\n\n`;
  allMessages.forEach(m => {
    let sender = m.direction === "inbound" ? chatName : "Me";
    let time = new Date(m.received_at).toLocaleString("en-PK");
    let content = m.content || `[${m.message_type}]`;
    txt += `[${time}] ${sender}: ${content}\n`;
  });
  navigator.clipboard.writeText(txt).then(() => {
    showToast("Chat history copied!", "success");
  }).catch(() => {
    showToast("Failed to copy", "error");
  });
};

// ── Delete Conversation ──────────────────────────────────────────────────────
window.deleteConversation = async function() {
  if (!currentPhone) return;
  if (!confirm("Are you sure you want to delete this entire conversation? This cannot be undone.")) return;
  try {
    const res = await apiFetch(`/inbox/conversation/${encodeURIComponent(currentPhone)}`, { method: "DELETE" });
    showToast(res.message || "Conversation deleted", "success");
    currentPhone = null;
    document.getElementById("activeChat").style.display = "none";
    document.getElementById("chatEmpty").style.display = "flex";
    await loadConversations();
  } catch(e) {
    showToast("Failed to delete", "error");
  }
};

// ── Forward Message ──────────────────────────────────────────────────────────
window.forwardMsg = function(msgId, content, type) {
  const targetPhone = prompt("Enter phone number to forward this message to (with country code, e.g. 923...):");
  if (!targetPhone) return;
  
  showToast("Forwarding message...", "info");
  
  let mediaUrl = null;
  const msg = allMessages.find(m => m.id == msgId);
  if (msg && msg.media_url) {
     mediaUrl = msg.media_url;
  }

  Inbox.reply(targetPhone.replace(/\D/g,''), content || "", type, mediaUrl, null)
    .then(() => showToast("Message forwarded!", "success"))
    .catch(e => showToast(e.message || "Failed to forward", "error"));
};

// ── Scroll to bottom button ──────────────────────────────────────────────────
window.scrollToBottom = function() {
  const el = document.getElementById("chatMessages");
  if (el) {
    el.scrollTop = el.scrollHeight;
    userScrolledUp = false;
    const btn = document.getElementById("scrollToBottomBtn");
    if (btn) btn.style.display = "none";
  }
};

// ── Toggle starred filter ────────────────────────────────────────────────────
window.toggleStarredFilter = function() {
  showStarredOnly = !showStarredOnly;
  const btn = document.getElementById("starFilterBtn");
  if (btn) btn.classList.toggle("active-filter", showStarredOnly);
  renderMessages(allMessages, true);
};

// ── Star/Unstar toggle ───────────────────────────────────────────────────────
window.toggleStar = async function(msgId, btn) {
  try {
    const res = await Inbox.starMessage(msgId);
    btn.classList.toggle("starred", res.is_starred);
    // Update local data
    const msg = allMessages.find(m => m.id === msgId);
    if (msg) msg.is_starred = res.is_starred;
  } catch(e) {
    showToast("Star toggle failed", "error");
  }
};

// ── Copy message ─────────────────────────────────────────────────────────────
window.copyMsg = function(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = "✓";
    btn.style.color = "var(--green)";
    setTimeout(() => { btn.textContent = orig; btn.style.color = ""; }, 1500);
  }).catch(() => {
    showToast("Copy nahi hua", "error");
  });
};

function scrollToMsg(id) {
  const el = document.querySelector(`[data-msg-id="${id}"]`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.style.background = "#fffde7";
    setTimeout(() => el.style.background = "", 1500);
  }
}

function openLightbox(src) {
  const lb = document.createElement("div");
  lb.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.88);" +
    "display:flex;align-items:center;justify-content:center;z-index:9999;cursor:zoom-out";
  lb.innerHTML = `<img src="${src}" style="max-width:90vw;max-height:90vh;border-radius:10px;">`;
  lb.onclick = () => lb.remove();
  document.body.appendChild(lb);
}


// ═══════════════════════════════════════════════════════════════════════════
// QUOTE REPLY
// ═══════════════════════════════════════════════════════════════════════════

function setReply(msgId, content, type) {
  replyTo = { id: msgId, content, type };
  const icons   = { image: "📷 Image", video: "🎥 Video", audio: "🎵 Voice message" };
  const preview = icons[type] || content.substring(0, 60);
  document.getElementById("reply-preview-text").textContent = preview;
  document.getElementById("reply-preview-bar").style.display = "flex";
  const inp = document.getElementById("msgInput");
  if (inp) inp.focus();
}
window.setReply = setReply;

function cancelReply() {
  replyTo = null;
  document.getElementById("reply-preview-bar").style.display = "none";
}
window.cancelReply = cancelReply;


// ═══════════════════════════════════════════════════════════════════════════
// SEND — TEXT
// ═══════════════════════════════════════════════════════════════════════════

window.sendMessage = async function() {
  if (!currentPhone) return;
  const input = document.getElementById("msgInput");
  const text  = (input.value || "").trim();

  if (!text && !selectedMedia) return;

  // ── OPTIMISTIC UI ──
  const tempId = Date.now();
  const tempMsg = {
    id: tempId,
    content: text,
    direction: 'outbound',
    message_type: selectedMedia ? selectedMediaType : 'text',
    isPending: true,
    received_at: new Date().toISOString(),
    customer_phone: currentPhone,
    quoted_message_id: replyTo?.id || null
  };

  // For media, add a temporary local URL for preview
  if (selectedMedia) {
    tempMsg.media_url = URL.createObjectURL(selectedMedia);
  }

  // Push and render instantly
  allMessages.push(tempMsg);
  renderMessages(allMessages, true);
  
  if (!selectedMedia) {
    input.value = "";
    input.style.height = "auto";
  }

  try {
    if (selectedMedia) {
      const fd = new FormData();
      fd.append("to",         currentPhone);
      fd.append("media_type", selectedMediaType);
      fd.append("caption",    text);
      fd.append("file",       selectedMedia);
      if (replyTo) fd.append("quoted_message_id", replyTo.id);
      
      const currentSelectedMedia = selectedMedia;
      cancelReply();
      removeMedia();

      const r = await fetch("https://api.rajacloud.online/api/inbox/send-media", {
        method:  "POST",
        headers: { "Authorization": `Bearer ${getToken()}` },
        body:    fd,
      });

      // Cleanup local URL
      URL.revokeObjectURL(tempMsg.media_url);

      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || "Media send failed");
      }
      input.value = "";
      input.style.height = "auto";
      userScrolledUp = false;
      await loadMessages(currentPhone, true);
      await loadConversations();
      return;
    }

    const quotedId = replyTo?.id || null;
    cancelReply();

    await Inbox.reply(currentPhone, text, "text", null, quotedId);
    userScrolledUp = false;
    await loadMessages(currentPhone, true);
    await loadConversations();

  } catch(e) {
    // Remove the failed optimistic message
    allMessages = allMessages.filter(m => m.id !== tempId);
    renderMessages(allMessages, false);
    showToast(e.message || "Send failed", "error");
  }
};

window.handleEnter = function(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

window.autoResize = function(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
};


// ═══════════════════════════════════════════════════════════════════════════
// MEDIA FILE SELECT
// ═══════════════════════════════════════════════════════════════════════════

window.toggleMediaMenu = function() {
  document.getElementById("mediaTypeMenu").classList.toggle("show");
};

window.triggerFileInput = function(type) {
  document.getElementById("mediaTypeMenu").classList.remove("show");
  const ids = { image: "fileImage", video: "fileVideo", audio: "fileAudio", document: "fileDocument" };
  document.getElementById(ids[type])?.click();
};

window.handleFileSelect = function(input, type) {
  const file = input.files[0];
  if (!file) return;

  // WhatsApp 16MB media limit check
  if (file.size > 16 * 1024 * 1024) {
    alert("File size exceeds 16MB limit for WhatsApp. Please select a smaller file.");
    input.value = "";
    return;
  }

  selectedMedia     = file;
  selectedMediaType = type;

  const preview = document.getElementById("mediaPreview");
  const thumb   = document.getElementById("mediaThumb");
  const info    = document.getElementById("mediaInfo");
  preview.classList.add("show");
  info.textContent = `${file.name} (${(file.size / 1024).toFixed(0)} KB)`;

  const icons = { image:"🖼️", video:"🎬", audio:"🎵", document:"📄" };
  if (type === "image") {
    thumb.innerHTML = `<img src="${URL.createObjectURL(file)}" style="height:60px;border-radius:6px;">`;
  } else {
    thumb.innerHTML = `<div style="width:60px;height:60px;background:#e5e7eb;border-radius:6px;
      display:flex;align-items:center;justify-content:center;font-size:24px;">${icons[type] || "📎"}</div>`;
  }
};

window.removeMedia = function() {
  selectedMedia = selectedMediaType = null;
  document.getElementById("mediaPreview").classList.remove("show");
  document.getElementById("mediaThumb").innerHTML = "";
  ["fileImage","fileVideo","fileAudio","fileDocument"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
};


// ═══════════════════════════════════════════════════════════════════════════
// AUDIO RECORDER
// ═══════════════════════════════════════════════════════════════════════════

window.startRecording = async function() {
  if (isRecording) return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks  = [];
    isRecording  = true;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      clearInterval(recordTimer);
      recordTimer  = null;
      isRecording  = false;

      const btn = document.getElementById("record-btn");
      if (btn) { btn.classList.remove("recording"); btn.title = "Hold to record voice"; }
      const timerEl = document.getElementById("record-timer");
      if (timerEl) timerEl.textContent = "";

      if (audioChunks.length === 0 || recordSeconds < 1) return;

      const blob = new Blob(audioChunks, { type: mimeType });
      mediaRecorder = null;
      await sendRecordedAudio(blob);
    };

    mediaRecorder.start(200);

    recordSeconds = 0;
    const btn     = document.getElementById("record-btn");
    if (btn) { btn.classList.add("recording"); btn.title = "Release to send"; }

    recordTimer = setInterval(() => {
      recordSeconds++;
      if (recordSeconds >= 120) stopRecording();
      const m = String(Math.floor(recordSeconds / 60)).padStart(2, "0");
      const s = String(recordSeconds % 60).padStart(2, "0");
      const timerEl = document.getElementById("record-timer");
      if (timerEl) timerEl.textContent = `${m}:${s}`;
    }, 1000);

  } catch(e) {
    isRecording = false;
    alert("Microphone access nahi mila! Browser settings mein permission do.");
  }
};

window.stopRecording = function() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
};

async function sendRecordedAudio(blob) {
  if (!currentPhone) return;

  // ── OPTIMISTIC UI ──
  const tempId = Date.now();
  const localUrl = URL.createObjectURL(blob);
  const tempMsg = {
    id: tempId,
    content: "",
    direction: 'outbound',
    message_type: 'audio',
    isPending: true,
    received_at: new Date().toISOString(),
    customer_phone: currentPhone,
    media_url: localUrl,
    duration: recordSeconds,
    quoted_message_id: replyTo?.id || null
  };

  allMessages.push(tempMsg);
  renderMessages(allMessages, true);

  const fd = new FormData();
  fd.append("to",       currentPhone);
  fd.append("file",     blob, "voice.ogg");
  fd.append("duration", recordSeconds);
  if (replyTo) fd.append("quoted_message_id", replyTo.id);
  cancelReply();

  try {
    const r = await fetch("https://api.rajacloud.online/api/inbox/send-audio-record", {
      method:  "POST",
      headers: { "Authorization": `Bearer ${getToken()}` },
      body:    fd,
    });
    
    URL.revokeObjectURL(localUrl);

    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Audio send failed");
    }
    userScrolledUp = false;
    await loadMessages(currentPhone, true);
    await loadConversations();
  } catch(e) {
    allMessages = allMessages.filter(m => m.id !== tempId);
    renderMessages(allMessages, false);
    showToast(e.message || "Voice message send nahi hua", "error");
    console.error(e);
  }
}


// ═══════════════════════════════════════════════════════════════════════════
// UNREAD BADGE
// ═══════════════════════════════════════════════════════════════════════════

async function loadUnreadBadge() {
  try {
    const res   = await Inbox.getUnreadCount();
    const badge = document.getElementById("nav-unread");
    if (!badge) return;
    if (res.unread > 0) {
      badge.textContent  = res.unread;
      badge.style.display = "inline-block";
    } else {
      badge.style.display = "none";
    }
  } catch(e) {}
}


// ═══════════════════════════════════════════════════════════════════════════
// CLOSE MEDIA MENU ON OUTSIDE CLICK
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("click", e => {
  if (!e.target.closest(".media-upload-btn") && !e.target.closest("#mediaTypeMenu")) {
    const menu = document.getElementById("mediaTypeMenu");
    if (menu) menu.classList.remove("show");
  }
});