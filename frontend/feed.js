renderChrome("/feed.html");
(async () => {
  try {
    const rows = await api("/public/concerns");
    $("#feed").innerHTML = rows.map((r) => `<div class="upd"><b>${esc(r.title)}</b> <span class="pill ${r.status === "resolved" || r.status === "closed" ? "good" : ""}">${esc(r.status.replace("_", " "))}</span><br><small>${esc(r.category)} · ${esc(r.campus)} · ${new Date(r.created_at).toLocaleDateString()}</small><p>${esc(r.description)}</p>
      ${r.public_replies.map((p) => `<p class="ok"><b>${esc(p.from)}:</b> ${esc(p.message)}</p>`).join("")}</div>`).join("") || '<p class="muted">No public concerns yet.</p>';
  } catch { $("#feed").textContent = "Could not load public concerns."; }
})();
