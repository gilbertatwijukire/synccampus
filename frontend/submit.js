renderChrome("/submit.html");
let cats = [];
async function loadCats() {
  cats = await api("/categories");
  $("#category").innerHTML = cats.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  syncSensitive();
}
function syncSensitive() {
  const c = cats.find((x) => String(x.id) === $("#category").value), sens = c && c.is_sensitive;
  $("#isPublic").disabled = !!sens; if (sens) $("#isPublic").checked = false;
  $("#sensNote").classList.toggle("hide", !sens);
}
$("#category").addEventListener("change", syncSensitive);
$("#submitForm").addEventListener("submit", async (e) => {
  e.preventDefault(); $("#submitErr").textContent = "";
  const f = new FormData(e.target);
  const body = { title: f.get("title"), description: f.get("description"), category_id: +f.get("category_id"), campus: f.get("campus"),
    location: f.get("location") || "", urgency: +f.get("urgency"), students_affected: +f.get("students_affected") || 1,
    safety_flag: f.get("safety_flag") === "on", is_public: f.get("is_public") === "on" };
  try {
    const r = await api("/concerns", { method: "POST", body });
    e.target.classList.add("hide");
    const box = $("#result"); box.classList.remove("hide");
    box.innerHTML = `<h2>Concern received</h2><p>Reference: <b>${esc(r.reference)}</b></p><p>Your private access code:</p><div class="code">${esc(r.access_code)}</div>
      <div class="notice"><b>Save this code now.</b> It is shown only once and nobody, including the Guild, can recover it. Never share it.</div>
      <button class="btn alt" id="copyBtn">Copy reference and code</button> <a class="btn" href="/track.html" style="text-decoration:none;display:inline-block">Go to tracking</a> <button class="btn alt" id="againBtn">Submit another</button>`;
    $("#copyBtn").onclick = () => navigator.clipboard.writeText(`${r.reference} ${r.access_code}`);
    $("#againBtn").onclick = () => { box.classList.add("hide"); e.target.reset(); e.target.classList.remove("hide"); syncSensitive(); };
  } catch (err) { $("#submitErr").textContent = err.message; }
});
loadCats();
