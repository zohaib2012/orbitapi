// chatbot.js — Path: whatschat-frontend/assets/js/chatbot.js

let selectedFlowId = null;

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadStats();
  await loadFlows();
});

async function loadStats() {
  try {
    const s = await Chatbot.getStats();
    setVal("stat-active-flows",    s.active_flows);
    setVal("stat-total-responses", s.total_responses?.toLocaleString());
    setVal("stat-success-rate",    s.success_rate + "%");
    setVal("stat-avg-response",    s.avg_response_time + "s");
  } catch(e) { console.error(e); }
}

async function loadFlows() {
  try {
    const flows = await Chatbot.getAll();
    const el = document.getElementById("flows-list");
    if (!el) return;
    if (!flows.length) { el.innerHTML = `<div style="padding:20px;text-align:center;color:#9ca3af;font-size:13px">No flows yet. Create one!</div>`; return; }
    el.innerHTML = flows.map(f => `
      <div onclick="selectFlow(${f.id})" id="flow-item-${f.id}" style="padding:14px;border-radius:8px;cursor:pointer;margin-bottom:6px;border:1px solid ${selectedFlowId===f.id?'#25D366':'transparent'};background:${selectedFlowId===f.id?'#f0fdf4':'transparent'}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <div style="font-weight:600;font-size:14px">${f.name}</div>
            <div style="font-size:12px;color:#9ca3af;margin-top:2px">${f.trigger_type==='keyword'?'Keyword: '+f.trigger_value:f.trigger_type||''}</div>
            <div style="font-size:12px;color:#9ca3af">${f.total_responses} responses</div>
          </div>
          <span style="padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:${f.status==='active'?'#111827':'#e5e7eb'};color:${f.status==='active'?'white':'#6b7280'}">${capitalize(f.status)}</span>
        </div>
      </div>`).join("");
    if (flows.length && !selectedFlowId) selectFlow(flows[0].id, flows[0]);
  } catch(e) { console.error(e); }
}

async function selectFlow(id) {
  selectedFlowId = id;
  document.querySelectorAll("[id^='flow-item-']").forEach(el => { el.style.border="1px solid transparent"; el.style.background="transparent"; });
  const el = document.getElementById(`flow-item-${id}`);
  if (el) { el.style.border="1px solid #25D366"; el.style.background="#f0fdf4"; }
  try {
    const flows = await Chatbot.getAll();
    const f = flows.find(x=>x.id===id);
    if (!f) return;
    const ni = document.getElementById("flow-name"); if (ni) ni.value = f.name;
    const di = document.getElementById("flow-desc"); if (di) di.value = f.description||"";
  } catch(e) {}
}

async function saveFlow() {
  if (!selectedFlowId) { showToast("Pehle flow select karo","error"); return; }
  const name = document.getElementById("flow-name")?.value.trim();
  const desc = document.getElementById("flow-desc")?.value.trim();
  if (!name) { showToast("Name zaroori hai","error"); return; }
  try { await Chatbot.update(selectedFlowId, { name, description:desc }); showToast("Saved ✅"); await loadFlows(); }
  catch(e) { showToast(e.message||"Error","error"); }
}

async function toggleFlow() {
  if (!selectedFlowId) return;
  try { const r = await Chatbot.toggle(selectedFlowId); showToast(`Flow ${r.status} ✅`); await loadStats(); await loadFlows(); }
  catch(e) { showToast(e.message||"Error","error"); }
}

function openNewFlowModal()  { document.getElementById("newFlowModalOverlay")?.classList.add("open"); }
function closeNewFlowModal() { document.getElementById("newFlowModalOverlay")?.classList.remove("open"); }
function closeNewFlowOutside(e) { if (e.target.id==="newFlowModalOverlay") closeNewFlowModal(); }

async function createFlow() {
  const name        = document.getElementById("nf-name")?.value.trim();
  const triggerType = document.getElementById("nf-trigger-type")?.value||"keyword";
  const triggerVal  = document.getElementById("nf-trigger-value")?.value.trim();
  const response    = document.getElementById("nf-response")?.value.trim();
  const btn         = document.getElementById("createFlowBtn");
  if (!name||!response) { showToast("Name aur response zaroori hain","error"); return; }
  setLoading(btn,true);
  try {
    await Chatbot.create({ name, trigger_type:triggerType, trigger_value:triggerVal||null, response_message:response });
    showToast("Flow created ✅"); closeNewFlowModal(); await loadStats(); await loadFlows();
  } catch(e) { showToast(e.message||"Error","error"); }
  finally { setLoading(btn,false); }
}