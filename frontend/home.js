renderChrome("/");
const STAGE = { new: "New", assigned: "Assigned", in_progress: "In progress", resolved: "Resolved", closed: "Closed" };

async function home() {
  const [stats, cabinet, recent] = await Promise.allSettled([
    api("/public/stats"),
    fetch("/cabinet-data.json").then((res) => { if (!res.ok) throw new Error("Cabinet data unavailable"); return res.json(); }),
    api("/public/concerns?limit=3"),
  ]);

  if (stats.status === "fulfilled") {
    const s = stats.value;
    $("#stats").innerHTML = `
      <div class="stat"><small>Concerns received</small><div class="v">${s.total}</div><div class="n">${s.open} still open</div></div>
      <div class="stat"><small>Resolved</small><div class="v">${s.resolved}</div><div class="n">${s.resolution_rate}% of all concerns</div></div>
      <div class="stat"><small>Average first response</small><div class="v">${s.avg_first_response_hrs == null ? "–" : s.avg_first_response_hrs + "h"}</div><div class="n">time until a leader replies</div></div>
      <div class="stat ${s.overdue_now ? "warn" : ""}"><small>Overdue right now</small><div class="v">${s.overdue_now}</div><div class="n">${s.overdue_pct}% of open concerns</div></div>`;
    const max = Math.max(1, ...Object.values(s.stages));
    $("#stages").innerHTML = Object.entries(s.stages).map(([k, v]) => `<div class="stagebar"><span>${STAGE[k]}</span><div class="bar"><i style="width:${(v / max) * 100}%;background:var(--navy2)"></i></div><b>${v}</b></div>`).join("");
    $("#topcats").innerHTML = s.top_categories.map(([n, v]) => `<div class="stagebar" style="grid-template-columns:1fr 30px"><span>${esc(n)}</span><b>${v}</b></div>`).join("") || '<p class="muted">Topics appear once concerns are submitted.</p>';
  } else { $("#stages").textContent = "Live numbers are unavailable right now."; }

  if (cabinet.status === "fulfilled") {
    $("#people").innerHTML = cabinet.value.slice(0, 4).map(personCard).join("") || '<p class="muted">The cabinet list will appear here.</p>';
  } else { $("#people").textContent = "Cabinet list is unavailable right now."; }

  if (recent.status === "fulfilled") {
    $("#recent").innerHTML = recent.value.map((r) => `<div class="upd"><b>${esc(r.title)}</b> <span class="pill ${r.status === "resolved" || r.status === "closed" ? "good" : ""}">${esc(STAGE[r.status] || r.status)}</span><br><small>${esc(r.category)} · ${esc(r.campus)}</small></div>`).join("") || '<p class="muted">No public concerns yet. Be the first to raise one.</p>';
  } else { $("#recent").textContent = "Unavailable right now."; }
}
function personCard(p) {
  const president = p.position.toLowerCase().includes("president") && !p.position.toLowerCase().includes("vice");
  const portrait = p.photo
    ? `<img class="portrait" src="${esc(p.photo)}" alt="Portrait of ${esc(p.name)}" loading="lazy">`
    : `<div class="av">${esc(initials(p.name))}</div>`;
  return `<article class="person ${president ? "pres" : ""}">${portrait}<b>${esc(p.name)}</b><div class="role">${esc(p.position)}</div></article>`;
}
home();
