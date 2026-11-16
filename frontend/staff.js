let token = sessionStorage.getItem("saagi_token"), me = null, workload = [];

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault(); $("#loginErr").textContent = "";
  const f = new FormData(e.target);
  try {
    const r = await api("/auth/login", { method: "POST", form: { username: f.get("email"), password: f.get("password") } });
    token = r.access_token; sessionStorage.setItem("saagi_token", token); start();
  } catch (err) { $("#loginErr").textContent = err.message; }
});
$("#logout").onclick = () => { sessionStorage.removeItem("saagi_token"); location.reload(); };

async function start() {
  try { me = await api("/auth/me", { token }); } catch { sessionStorage.removeItem("saagi_token"); return; }
  $("#loginBox").classList.add("hide"); $("#app").classList.remove("hide");
  $("#who").textContent = `${me.name} (${me.role})`; $("#who").classList.remove("hide"); $("#logout").classList.remove("hide");
  me.role === "delegate" ? delegateView() : leaderView();
}

/* ---------------- leader (Guild President) ---------------- */
async function leaderView() {
  const [stats, queue, wl, esc_] = await Promise.all([api("/leader/analytics", { token }), api("/leader/queue", { token }), api("/leader/workload", { token }), api("/leader/escalations", { token })]);
  workload = wl;
  const max = Math.max(1, ...Object.values(stats.by_category));
  $("#app").innerHTML = `
  <div class="kpis">
    <div class="kpi"><small>Open concerns</small><div class="v">${stats.open}</div></div>
    <div class="kpi"><small>Critical + High</small><div class="v">${stats.critical_high}</div></div>
    <div class="kpi alert"><small>Overdue</small><div class="v">${stats.overdue}</div></div>
    <div class="kpi"><small>Avg first response</small><div class="v">${stats.avg_first_response_hrs ?? "–"}${stats.avg_first_response_hrs != null ? "h" : ""}</div></div>
    <div class="kpi"><small>Resolution rate</small><div class="v">${stats.resolution_rate}%</div></div></div>
  <div class="card"><h2>Priority queue</h2><p class="sub">Ranked by priority score. You keep the final say on every assignment.</p>
    <div class="tablewrap"><table><thead><tr><th>Concern</th><th>Priority</th><th>Related</th><th>Assigned / recommended</th><th>Age</th></tr></thead><tbody>
    ${queue.map(row).join("") || '<tr><td colspan="5" class="muted">No open concerns.</td></tr>'}</tbody></table></div></div>
  <div class="grid2">
    <div class="card"><h2>Delegate workload</h2><p class="sub">Open concerns per delegate</p>
      ${wl.map((w) => `<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between"><b>${esc(w.name)}</b><span class="muted">${w.open}/${w.max}</span></div>
        <div class="bar"><i style="width:${Math.min(100, (w.open / w.max) * 100)}%;background:${w.open / w.max > 0.8 ? "var(--red)" : w.open / w.max > 0.5 ? "var(--amber)" : "var(--green)"}"></i></div></div>`).join("")}</div>
    <div class="card"><h2>Concerns by category</h2><p class="sub">All time</p>
      ${Object.entries(stats.by_category).map(([k, v]) => `<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between"><span>${esc(k)}</span><b>${v}</b></div><div class="bar"><i style="width:${(v / max) * 100}%;background:var(--navy2)"></i></div></div>`).join("") || '<p class="muted">No data yet.</p>'}</div></div>
  <div class="card"><h2>Reminders and escalations</h2><p class="sub">Generated automatically when time limits are exceeded.
    <button class="btn sm alt" id="runEsc">Check now</button></p>
    ${esc_.map((e) => `<div class="upd"><span class="pill ${e.type === "escalation" ? "over" : ""}">${esc(e.type)}</span> <b>${esc(e.title)}</b> <small>${new Date(e.at).toLocaleString()}</small><br>${esc(e.reason)}</div>`).join("") || '<p class="muted">None yet.</p>'}</div>
  <div class="card"><h2>Leadership handover</h2><p class="sub">Snapshot of all open concerns and who holds them, for the incoming team.</p>
    <div class="row"><input id="term" placeholder="Term label, e.g. 2026/27"><button class="btn" id="handoverBtn">Generate handover record</button></div><div id="handoverOut"></div></div>`;
  $("#runEsc").onclick = async () => { await api("/leader/run-escalation", { method: "POST", token }); leaderView(); };
  $("#handoverBtn").onclick = async () => {
    const t = $("#term").value.trim() || "Current term";
    const h = await api("/leader/handover?term=" + encodeURIComponent(t), { method: "POST", token });
    $("#handoverOut").innerHTML = `<p class="ok" style="margin-top:10px">Saved: ${h.count} open concern(s) recorded for ${esc(h.term)}.</p>
      <div class="tablewrap"><table><thead><tr><th>Ref</th><th>Title</th><th>Priority</th><th>Assigned to</th></tr></thead><tbody>${h.open_concerns.map((c) => `<tr><td>${esc(c.reference)}</td><td>${esc(c.title)}</td><td>${esc(c.priority)}</td><td>${esc(c.assigned_to || "unassigned")}</td></tr>`).join("")}</tbody></table></div>`;
  };
  document.querySelectorAll("[data-accept]").forEach((b) => b.onclick = () => assign(b.dataset.cid, b.dataset.accept));
  document.querySelectorAll("[data-assign]").forEach((b) => b.onclick = () => assign(b.dataset.assign, $("#sel" + b.dataset.assign).value));
  document.querySelectorAll("[data-explain]").forEach((d) => d.addEventListener("toggle", () => d.open && explain(d)));
}

function row(c) {
  const recId = c.recommended ? c.recommended.delegate_id : null;
  const opts = workload.map((w) => `<option value="${w.delegate_id}"${w.delegate_id === recId ? " selected" : ""}>${esc(w.name)} (${w.open}/${w.max})</option>`).join("");
  const who = c.assigned_to ? `<b>${esc(c.assigned_to)}</b>` : c.recommended
    ? `<b>${esc(c.recommended.name)}</b> <span class="muted">score ${c.recommended.score} · ${esc(c.recommended.reasons.join(", "))}</span><br>
       <button class="btn sm amber" data-cid="${c.id}" data-accept="${c.recommended.delegate_id}">Accept recommendation</button>`
    : '<span class="muted">No delegate available</span>';
  return `<tr><td><span class="muted">${esc(c.reference)}</span><br><b>${esc(c.title)}</b><br><span class="muted">${esc(c.category)} · ${c.students_affected} student(s)${c.safety_flag ? " · safety" : ""}</span>
      <details data-explain data-id="${c.id}"><summary>Why this score?</summary><div class="why muted">Loading…</div></details></td>
    <td><span class="badge ${c.priority_level}">${c.priority_level}</span><br><b>${c.priority_score}</b>${c.is_overdue ? '<br><span class="pill over">Overdue</span>' : ""}</td>
    <td>${c.related_reports ? `<span class="pill">${c.related_reports} related</span>` : "–"}</td>
    <td>${who}<br><select id="sel${c.id}" style="margin-top:6px;max-width:200px">${opts}</select> <button class="btn sm alt" data-assign="${c.id}">Assign</button></td>
    <td>${fmtAge(c.age_hours)}</td></tr>`;
}
async function explain(d) {
  const x = await api("/leader/concerns/" + d.dataset.id, { token });
  const p = x.explanation.points, f = x.explanation.factors;
  $(".why", d).innerHTML = `Severity ${f.S} → ${p.S} pts · Urgency ${f.U} → ${p.U} · Students ${f.N.toFixed(2)} → ${p.N} · Duration ${f.D.toFixed(2)} → ${p.D} · Repeats ${f.R} → ${p.R}${p.safety_rule ? " · <b>safety rule applied</b>" : ""}
    ${x.related.length ? "<br>Related: " + x.related.map((r) => esc(r.reference)).join(", ") : ""}`;
}
async function assign(cid, delegateId) {
  try { await api(`/leader/concerns/${cid}/assign`, { method: "POST", token, body: { delegate_id: +delegateId } }); leaderView(); }
  catch (e) { alert(e.message); }
}

/* ---------------- delegate workspace ---------------- */
async function delegateView() {
  const rows = await api("/delegate/concerns", { token });
  $("#app").innerHTML = `<div class="card"><h2>My assigned concerns</h2><p class="sub">Highest priority first. Replies marked "Student" are visible to the student; "Internal" stays within the Guild.</p></div>` +
    (rows.map((c) => `<div class="card"><span class="badge ${c.priority_level}">${c.priority_level}</span> <b>${esc(c.title)}</b> <span class="pill">${esc(c.status.replace("_", " "))}</span>
      ${c.is_overdue ? '<span class="pill over">Overdue</span>' : ""}<p class="muted">${esc(c.reference)} · ${esc(c.category)} · ${esc(c.location)}</p><p style="margin:8px 0">${esc(c.description)}</p>
      <textarea id="msg${c.id}" placeholder="Write an update or reply"></textarea>
      <div class="row" style="margin-top:8px"><select id="vis${c.id}"><option value="private">Reply to student (private)</option><option value="public">Public reply</option><option value="internal">Internal note</option></select>
        <select id="st${c.id}"><option value="">Keep status</option><option value="in_progress">Mark in progress</option><option value="resolved">Mark resolved</option></select></div>
      <button class="btn sm" style="margin-top:8px" data-send="${c.id}">Post update</button></div>`).join("") || '<div class="card muted">Nothing assigned to you right now.</div>');
  document.querySelectorAll("[data-send]").forEach((b) => b.onclick = async () => {
    const id = b.dataset.send;
    try { await api(`/delegate/concerns/${id}/update`, { method: "POST", token, body: { message: $("#msg" + id).value, visibility: $("#vis" + id).value, status: $("#st" + id).value || null } }); delegateView(); }
    catch (e) { alert(e.message); }
  });
}

if (token) start();
