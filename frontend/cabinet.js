renderChrome("/cabinet.html");
(async () => {
  try {
    const response = await fetch("/cabinet-data.json");
    if (!response.ok) throw new Error("Could not load cabinet data");
    const rows = await response.json();
    $("#people").innerHTML = rows.map((p) => {
      const president = p.position.toLowerCase().includes("president") && !p.position.toLowerCase().includes("vice");
      const portrait = p.photo
        ? `<img class="portrait" src="${esc(p.photo)}" alt="Portrait of ${esc(p.name)}" loading="lazy">`
        : `<div class="av">${esc(initials(p.name))}</div>`;
      const responsibilities = p.responsibilities
        ? `<details class="responsibilities"><summary>Responsibilities</summary><p>${esc(p.responsibilities)}</p></details>`
        : '<p class="person-note">Elected student representative at ISBAT University.</p>';
      return `<article class="person ${president ? "pres" : ""}">${portrait}<b>${esc(p.name)}</b><div class="role">${esc(p.position)}</div>${responsibilities}</article>`;
    }).join("") || '<p class="muted">No cabinet members listed yet.</p>';
  } catch { $("#people").textContent = "Could not load the cabinet list."; }
})();
