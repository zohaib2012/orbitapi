// subscriptions.js — Path: whatschat-frontend/assets/js/subscriptions.js

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuthOnly(); // ← sirf login check, plan gate nahi (warna user plan choose nahi kar payega)
  fillSidebarUser();
  loadCurrentPlan();
});

function loadCurrentPlan() {
  const user = getUser();
  if (!user) return;
  const planName  = { starter:"Starter", professional:"Professional", enterprise:"Enterprise" };
  const planPrice = { starter:"Rs.2,500", professional:"Rs.4,000", enterprise:"Rs.8,000" };
  setVal("current-plan-name",  planName[user.plan]  || "Free");
  setVal("current-plan-price", planPrice[user.plan] || "—");

  // Pending status banner
  const status = user.subscription_status || "";
  if (user.plan && user.plan !== "free" && status === "pending") {
    showPendingBanner(user.plan);
  }

  // Highlight current plan card
  document.querySelectorAll(".plan-card").forEach(card => {
    card.style.border = "1px solid #e5e7eb";
    const btn = card.querySelector(".plan-btn");
    if (btn) { btn.textContent = "Choose Plan"; btn.style.background = "#111827"; btn.disabled = false; }
  });

  const currentCard = document.getElementById(`plan-${user.plan}`);
  if (currentCard) {
    currentCard.style.border = "2px solid #25D366";
    const btn = currentCard.querySelector(".plan-btn");
    if (btn) {
      if (status === "pending") {
        btn.textContent = "⏳ Pending Approval";
        btn.style.background = "#f59e0b";
        btn.disabled = true;
      } else if (status === "active" || status === "approved") {
        btn.textContent = "✓ Current Plan";
        btn.style.background = "#25D366";
        btn.disabled = true;
      }
    }
  }
}

function showPendingBanner(plan) {
  if (document.getElementById("__pendingBanner")) return;
  const names = { starter:"Starter", professional:"Professional", enterprise:"Enterprise" };
  const banner = document.createElement("div");
  banner.id = "__pendingBanner";
  banner.style.cssText = "background:#fffbeb;border:1.5px solid #fbbf24;border-radius:12px;padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;gap:12px;font-family:'DM Sans',sans-serif;";
  banner.innerHTML = `
    <span style="font-size:22px;">⏳</span>
    <div>
      <div style="font-size:14px;font-weight:700;color:#92400e;">
        ${names[plan] || capitalize(plan)} Plan — Admin Approval Pending
      </div>
      <div style="font-size:12.5px;color:#b45309;margin-top:2px;">
        Aapki request admin ke paas hai. 24 ghante mein approve ho jayegi aur sab features unlock ho jayenge.
      </div>
    </div>
  `;

  // Page ke content area mein sabse upar inject karo
  const targets = [".main-content", ".content", "main", "#main", ".main", "#content", ".container"];
  for (const sel of targets) {
    const el = document.querySelector(sel);
    if (el) { el.insertBefore(banner, el.firstChild); return; }
  }
  document.body.prepend(banner);
}