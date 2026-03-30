// settings.js — WhatsChat AI Settings
// Path: whatschat-frontend/assets/js/settings.js

const DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];

window.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  renderHoursGrid();
  await loadSettings();
  await loadWAStatus();
});

async function loadSettings() {
  try {
    const s = await Settings.get();
    document.getElementById("s-business-name").value = s.business_name || "";
    document.getElementById("s-website").value        = s.website       || "";
    document.getElementById("s-email").value          = s.support_email || "";
    document.getElementById("s-phone").value          = s.support_phone || "";
    document.getElementById("s-timezone").value       = s.timezone      || "Asia/Karachi";
    document.getElementById("s-address").value        = s.address       || "";
    document.getElementById("s-welcome").value        = s.welcome_message || "";
    document.getElementById("s-away").value           = s.away_message    || "";

    // Welcome media fields
    const welEnabled = document.getElementById("s-welcome-enabled");
    if (welEnabled) welEnabled.checked = s.welcome_enabled !== false;
    const welMediaType = document.getElementById("s-welcome-media-type");
    if (welMediaType) welMediaType.value = s.welcome_media_type || "";
    const welMediaUrl = document.getElementById("s-welcome-media-url");
    if (welMediaUrl) welMediaUrl.value = s.welcome_media_url || "";
    onWelcomeMediaTypeChange();

    if (s.logo_url) {
      const prev = document.getElementById("logoPreview");
      if (prev) prev.innerHTML = `<img src="${s.logo_url}" alt="logo">`;
    }
    // Business hours
    if (s.business_hours) {
      DAYS.forEach(d => {
        const val = s.business_hours[d.toLowerCase()];
        if (!val) return;
        const closed = document.getElementById(`h-closed-${d}`);
        if (val === "closed") {
          if (closed) closed.checked = true;
        } else {
          const parts = val.split("-");
          const from  = document.getElementById(`h-from-${d}`);
          const to    = document.getElementById(`h-to-${d}`);
          if (from && parts[0]) from.value = parts[0];
          if (to   && parts[1]) to.value   = parts[1];
        }
      });
    }
  } catch(e) { console.error("Settings load failed", e); }
}

async function loadWAStatus() {
  try {
    const s    = await WhatsApp.getStatus();
    const pill = document.getElementById("waStatusPill");
    const text = document.getElementById("waStatusText");
    if (s.connected) {
      if (pill) { pill.textContent = "✅ Connected"; pill.className = "status-pill status-connected"; }
      if (text) text.textContent = `Connected: ${s.phone_number_id}`;
      const pidEl = document.getElementById("s-phone-id");
      if (pidEl) pidEl.value = s.phone_number_id || "";
    } else {
      if (pill) { pill.textContent = "❌ Not Connected"; pill.className = "status-pill status-disconnected"; }
    }
  } catch(e) {}
}

window.switchTab = function(tab, btn) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(`tab-${tab}`).classList.add("active");
};

window.saveGeneral = async function() {
  const body = {
    business_name: document.getElementById("s-business-name").value,
    website:       document.getElementById("s-website").value,
    support_email: document.getElementById("s-email").value,
    support_phone: document.getElementById("s-phone").value,
    timezone:      document.getElementById("s-timezone").value,
    address:       document.getElementById("s-address").value,
  };
  try {
    await Settings.update(body);
    showToast("Settings saved ✅","success");
  } catch(e) { showToast("Save failed","error"); }
};

window.saveMessages = async function() {
  const welEnabledEl = document.getElementById("s-welcome-enabled");
  const body = {
    welcome_message:    document.getElementById("s-welcome").value,
    welcome_media_type: document.getElementById("s-welcome-media-type")?.value || null,
    welcome_media_url:  document.getElementById("s-welcome-media-url")?.value || null,
    welcome_enabled:    welEnabledEl ? welEnabledEl.checked : true,
  };
  try {
    await Settings.update(body);
    showToast("Welcome message saved ✅","success");
  } catch(e) { showToast("Save failed","error"); }
};

window.saveAway = async function() {
  const body = {
    away_message: document.getElementById("s-away").value,
  };
  try {
    await Settings.update(body);
    showToast("Away message saved ✅","success");
  } catch(e) { showToast("Save failed","error"); }
};

window.onWelcomeMediaTypeChange = function() {
  const type   = document.getElementById("s-welcome-media-type")?.value;
  const fields = document.getElementById("welcome-media-fields");
  if (fields) fields.style.display = type ? "block" : "none";
};

window.uploadWelcomeMedia = async function(input) {
  const file = input.files[0];
  if (!file) return;
  try {
    const data = await uploadMedia(file);
    const url  = `https://api.rajacloud.online${data.url}`;
    document.getElementById("s-welcome-media-url").value = url;
    const icons = { image:"🖼️", video:"🎬", audio:"🎵" };
    const preview = document.getElementById("welcomeMediaPreview");
    if (preview) preview.style.display = "block";
    const icon = document.getElementById("welcomeMediaIcon");
    if (icon) icon.textContent = icons[data.media_type] || "📎";
    const nameEl = document.getElementById("welcomeMediaName");
    if (nameEl) nameEl.textContent = file.name;
    showToast("Welcome media uploaded ✅","success");
  } catch(e) { showToast("Upload failed","error"); }
};

window.clearWelcomeMedia = function() {
  document.getElementById("s-welcome-media-url").value = "";
  const preview = document.getElementById("welcomeMediaPreview");
  if (preview) preview.style.display = "none";
};

window.saveHours = async function() {
  const hours = {};
  DAYS.forEach(d => {
    const from   = document.getElementById(`h-from-${d}`)?.value;
    const to     = document.getElementById(`h-to-${d}`)?.value;
    const closed = document.getElementById(`h-closed-${d}`)?.checked;
    hours[d.toLowerCase()] = closed ? "closed" : `${from}-${to}`;
  });
  try {
    await Settings.update({ business_hours: hours });
    showToast("Hours saved ✅","success");
  } catch(e) { showToast("Save failed","error"); }
};

function renderHoursGrid() {
  const grid = document.getElementById("hoursGrid");
  if (!grid) return;
  grid.innerHTML = DAYS.map(d => `
    <div class="hours-row">
      <span class="day">${d}</span>
      <input type="time" id="h-from-${d}" value="09:00">
      <span class="sep">to</span>
      <input type="time" id="h-to-${d}" value="18:00">
      <label class="closed-toggle">
        <input type="checkbox" id="h-closed-${d}"> Closed
      </label>
    </div>
  `).join("");
}

window.uploadLogo = async function(input) {
  const file = input.files[0];
  if (!file) return;
  try {
    const data = await uploadMedia(file);
    const url  = `https://api.rajacloud.online${data.url}`;
    const prev = document.getElementById("logoPreview");
    if (prev) prev.innerHTML = `<img src="${url}" alt="logo">`;
    await Settings.update({ logo_url: url });
    showToast("Logo uploaded ✅","success");
  } catch(e) { showToast("Upload failed","error"); }
};

window.launchFBSignup = function() {
  const FB_APP_ID = '889776090331985';
  const CONFIG_ID = ''; // Agar config ID hai toh yahan daalo

  // Agar FB SDK load hai aur CONFIG_ID set hai — proper embedded signup
  if (typeof FB !== 'undefined' && CONFIG_ID) {
    FB.login(function(response) {
      if (response.authResponse) {
        const code = response.authResponse.code;
        fetch('https://api.rajacloud.online/api/whatsapp/fb-exchange', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('wc_token')
          },
          body: JSON.stringify({ code: code })
        })
        .then(r => r.json())
        .then(data => {
          if (data.phone_number_id) {
            showToast('✅ WhatsApp connected! Phone: ' + data.phone_number_id, 'success');
            setTimeout(() => window.location.reload(), 1500);
          } else {
            showToast('Connected! Token refresh karein', 'success');
            setTimeout(() => window.location.href = 'whatsapp-api.html', 1500);
          }
        })
        .catch(() => {
          showToast('✅ Facebook connected!', 'success');
          setTimeout(() => window.location.href = 'whatsapp-api.html', 1500);
        });
      } else {
        showToast('Facebook login cancel hua', 'info');
      }
    }, {
      config_id: CONFIG_ID,
      response_type: 'code',
      override_default_response_type: true,
      extras: { sessionInfoVersion: 2 }
    });
  } else {
    // Direct Meta Developer Console pe le jaao — exactly jaise screenshot mein tha
    const metaUrl = `https://www.facebook.com/dialog/oauth?client_id=${FB_APP_ID}&redirect_uri=${encodeURIComponent(window.location.origin + '/settings.html')}&scope=whatsapp_business_management,whatsapp_business_messaging&response_type=code`;
    
    // Popup window kholo
    const popup = window.open(metaUrl, 'MetaLogin', 'width=600,height=700,scrollbars=yes');
    
    // Monitor popup
    showToast('Meta login window khulja hai...', 'info');
    
    const timer = setInterval(() => {
      try {
        if (popup && popup.closed) {
          clearInterval(timer);
          showToast('Login complete — ab WhatsApp API page pe token paste karein', 'success');
          setTimeout(() => window.location.href = 'whatsapp-api.html', 1500);
        }
      } catch(e) { clearInterval(timer); }
    }, 1000);
  }
};


window.copyWebhook = function() {
  const el = document.getElementById("webhookUrl");
  if (el) navigator.clipboard.writeText(el.value).then(() => showToast("Webhook URL copied!","success"));
};