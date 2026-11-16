renderChrome("/track.html");
let creds = null;
async function showTrack() {
  const v = $("#trackView");
  try {
    const c = await api("/track", { method: "POST", body: creds });
    v.innerHTML = `<hr style="margin:14px 0;border:0;border-top:1px solid #E1E7F3"><h2>${esc(c.title)}</h2>
      <p><span class="pill ${c.status === "closed" || c.status === "resolved" ? "good" : ""}">${esc(c.status.replace("_", " "))}</span> <span class="muted">${esc(c.category)} · ${esc(c.reference)}</span></p>
      <p style="margin:10px 0">${esc(c.description)}</p>
      <h3 style="font-size:14px;color:#7A1426">Replies and updates</h3>
      ${c.updates.map((u) => `<div class="upd"><b>${esc(u.from)}</b> <small>${new Date(u.at).toLocaleString()}</small><br>${esc(u.message)}</div>`).join("") || '<p class="muted">No replies yet.</p>'}
      ${c.status === "resolved" ? `<div class="notice"><b>Was your concern resolved?</b><br><button class="btn sm" id="yes">Yes, resolved</button> <button class="btn sm alt" id="no">No, still a problem</button></div>` : ""}
      ${c.status !== "closed" ? `<label>Add more information</label><textarea id="more"></textarea><button class="btn sm" id="moreBtn" style="margin-top:6px">Send</button>` : ""}
      <div class="err" id="actErr"></div>`;
    const confirm = async (resolved) => { try { await api("/track/confirm", { method: "POST", body: { ...creds, resolved } }); showTrack(); } catch (er) { $("#actErr").textContent = er.message; } };
    if ($("#yes")) { $("#yes").onclick = () => confirm(true); $("#no").onclick = () => confirm(false); }
    if ($("#moreBtn")) $("#moreBtn").onclick = async () => { try { await api("/track/info", { method: "POST", body: { ...creds, message: $("#more").value } }); showTrack(); } catch (er) { $("#actErr").textContent = er.message; } };
  } catch (err) { $("#trackErr").textContent = err.message; v.innerHTML = ""; }
}
$("#trackForm").addEventListener("submit", (e) => {
  e.preventDefault(); $("#trackErr").textContent = "";
  const f = new FormData(e.target); creds = { reference: f.get("reference"), access_code: f.get("access_code") }; showTrack();
});
