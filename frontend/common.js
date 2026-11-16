// Small helpers shared by both pages. Always escape user-provided text before inserting into HTML.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const $ = (sel, root = document) => root.querySelector(sel);
async function api(path, { method = "GET", body, token, form } = {}) {
  const headers = {};
  if (token) headers.Authorization = "Bearer " + token;
  let payload;
  if (form) { payload = new URLSearchParams(form); headers["Content-Type"] = "application/x-www-form-urlencoded"; }
  else if (body) { payload = JSON.stringify(body); headers["Content-Type"] = "application/json"; }
  const res = await fetch((window.SAAGI_API_BASE || "") + "/api" + path, { method, headers, body: payload });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form and try again");
  return data;
}
const fmtAge = (h) => (h < 24 ? h.toFixed(1) + "h" : Math.floor(h / 24) + "d " + Math.round(h % 24) + "h");
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

/* ---------- shared header / footer for the public pages ---------- */
const NAV = [["/", "Home"], ["/submit.html", "Submit a concern"], ["/track.html", "Track"], ["/feed.html", "Public concerns"], ["/cabinet.html", "Cabinet"], ["/privacy.html", "Privacy"]];
function renderChrome(active) {
  $("#hdr").outerHTML = `<header class="top"><a class="brand" href="/"><span class="logo"><img src="/assets/isbat-logo.png" alt="ISBAT University"></span><span><b>Saagi SyncCampus</b><small>ISBAT University · Student concerns</small></span></a>
    <nav>${NAV.map(([h, t]) => `<a href="${h}" class="${h === active ? "active" : ""}">${t}</a>`).join("")}<a href="/staff.html" class="staff">Staff</a></nav></header>`;
  $("#ftr").outerHTML = `<footer class="site"><div><b>Saagi SyncCampus</b><br><span class="muted">A student concern management and leadership decision-support system for ISBAT University student leadership. Final year project prototype.</span></div>
    <div class="links"><a href="/submit.html">Submit a concern</a><a href="/track.html">Track a concern</a><a href="/cabinet.html">Meet the cabinet</a><a href="/privacy.html">Privacy &amp; accountability</a><a href="/staff.html">Staff sign in</a></div></footer>`;
}
const initials = (n) => n.split(/\s+/).filter(Boolean).slice(-2).map((w) => w[0].toUpperCase()).join("");
