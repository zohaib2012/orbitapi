(async function() {
    const PROTECTED = ['inbox.html', 'whatsapp-api.html'];
    const currentPage = window.location.pathname.split('/').pop();
    if (!PROTECTED.includes(currentPage)) return;

    const token = localStorage.getItem('wc_token');
    if (!token) { window.location.href = '/auth/login.html'; return; }

    // Fresh API call
    let userData = null;
    try {
        const res = await fetch('https://orbitconnects.online/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` },
            cache: 'no-store'
        });
        if (res.ok) {
            userData = await res.json();
            localStorage.setItem('wc_user', JSON.stringify(userData));
        } else {
            window.location.href = '/auth/login.html';
            return;
        }
    } catch(e) {
        const u = localStorage.getItem('wc_user');
        if (u) userData = JSON.parse(u);
    }

    if (!userData) return;
    if (userData.email === 'admin@orbitapi.com') return;
    if (userData.is_approved === true) return;

    // Block karo
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div style="background:#fff;border-radius:16px;padding:40px;max-width:420px;width:90%;text-align:center;font-family:'DM Sans',sans-serif;">
            <div style="font-size:48px;margin-bottom:16px;">⏳</div>
            <h2 style="font-size:20px;font-weight:700;color:#111827;margin-bottom:12px;">Approval Pending</h2>
            <p style="font-size:14px;color:#6b7280;margin-bottom:24px;line-height:1.6;">
                Aapka account admin review mein hai.<br>
                Approve hone ke baad inbox aur WhatsApp API<br>
                access mil jayega.
            </p>
            <a href="/subscriptions.html" style="display:inline-block;background:#25D366;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">View Plans</a>
        </div>`;
    document.body.appendChild(overlay);
})();
