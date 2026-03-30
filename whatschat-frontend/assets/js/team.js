// team.js — Path: whatschat-frontend/assets/js/team.js

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadStats();
  await loadMembers();
});

async function loadStats() {
  try {
    const s = await Team.getStats();
    setVal("stat-total",   s.total_members);
    setVal("stat-active",  s.active);
    setVal("stat-pending", s.pending_invites);
    setVal("stat-seats",   s.seats_used + "/" + s.seats_total);
  } catch(e) { console.error(e); }
}

async function loadMembers() {
  try {
    const members = await Team.getAll();
    const tbody = document.getElementById("team-table");
    if (!tbody) return;
    if (!members.length) { tbody.innerHTML=`<tr><td colspan="6" style="text-align:center;padding:30px;color:#9ca3af">No team members yet</td></tr>`; return; }
    const roleColors = { owner:"#fef3c7|#d97706", admin:"#dbeafe|#2563eb", manager:"#dcfce7|#16a34a", agent:"#f3f4f6|#6b7280" };
    tbody.innerHTML = members.map(m => {
      const [bg,tc] = (roleColors[m.role]||"#f3f4f6|#6b7280").split("|");
      return `
      <tr>
        <td style="padding:12px 16px">
          <div style="font-weight:600">${m.name}</div>
          <div style="font-size:12px;color:#9ca3af">${m.email}</div>
        </td>
        <td style="padding:12px 16px"><span style="padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;background:${bg};color:${tc}">${roleIcon(m.role)} ${capitalize(m.role)}</span></td>
        <td style="padding:12px 16px">
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            ${(m.permissions||[]).length ? (m.permissions||[]).map(p=>`<span style="background:#f3f4f6;border-radius:4px;padding:2px 8px;font-size:11px">${capitalize(p)}</span>`).join("") : '<span style="background:#f3f4f6;border-radius:4px;padding:2px 8px;font-size:11px">All</span>'}
          </div>
        </td>
        <td style="padding:12px 16px">
          <span style="padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;background:${m.status==='active'?'#111827':'#f3f4f6'};color:${m.status==='active'?'white':'#6b7280'}">${capitalize(m.status)}</span>
        </td>
        <td style="padding:12px 16px;font-size:13px;color:#9ca3af">${timeAgo(m.last_active)}</td>
        <td style="padding:12px 16px">
          ${m.role!=='owner'?`<button onclick="removeMember(${m.id})" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;font-family:'DM Sans',sans-serif">Remove</button>`:""}
        </td>
      </tr>`;
    }).join("");
  } catch(e) { console.error(e); }
}

function openInviteModal()  { document.getElementById("inviteModalOverlay")?.classList.add("open"); document.getElementById("inviteForm")?.reset(); }
function closeInviteModal() { document.getElementById("inviteModalOverlay")?.classList.remove("open"); }
function closeInviteOutside(e) { if (e.target.id==="inviteModalOverlay") closeInviteModal(); }

async function inviteMember() {
  const name  = document.getElementById("inv-name")?.value.trim();
  const email = document.getElementById("inv-email")?.value.trim();
  const role  = document.getElementById("inv-role")?.value||"agent";
  const perms = [...document.querySelectorAll(".perm-check:checked")].map(el=>el.value);
  const btn   = document.getElementById("inviteBtn");
  if (!name||!email) { showToast("Name aur email zaroori hain","error"); return; }
  setLoading(btn,true);
  try {
    await Team.invite({ name, email, role, permissions:perms });
    showToast(`${name} invite bhej diya ✅`);
    closeInviteModal(); await loadStats(); await loadMembers();
  } catch(e) { showToast(e.message||"Error","error"); }
  finally { setLoading(btn,false); }
}

async function removeMember(id) {
  if (!confirm("Remove karna chahte ho?")) return;
  try { await Team.remove(id); showToast("Removed"); await loadStats(); await loadMembers(); }
  catch(e) { showToast(e.message||"Error","error"); }
}

function roleIcon(r) { return {owner:"👑",admin:"🛡️",manager:"⭐",agent:"👤"}[r]||"👤"; }