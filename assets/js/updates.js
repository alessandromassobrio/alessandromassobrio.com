fetch("/data/updates.md", { cache: "no-cache" })
  .then(res => res.text())
  .then(text => {
    const updates = text.split(/^---$/gm).filter(Boolean);

    const container = document.querySelector("#updates-container");
    updates.forEach(updateText => {
      const lines = updateText.trim().split("\n");
      let meta = {};
      // legge front-matter (title, date, description)
      lines.forEach(line => {
        if (line.startsWith("title:")) meta.title = line.replace("title:", "").trim();
        else if (line.startsWith("date:")) meta.date = line.replace("date:", "").trim();
        else if (line.startsWith("description:")) meta.description = line.replace("description:", "").trim();
        else if (line.startsWith("logo:")) meta.logo = line.replace("logo:", "").trim();
        else if (line.startsWith("logo_alt:")) meta.logoAlt = line.replace("logo_alt:", "").trim();
        else if (line.startsWith("logo_link:")) meta.logoLink = line.replace("logo_link:", "").trim();
      });

      const updateDiv = document.createElement("div");
      updateDiv.className = "update";

      updateDiv.innerHTML = `
        <div class="update-body">
          <strong>${meta.title}</strong>
          <p>${meta.description ?? ""}</p>
          ${renderUpdateLogo(meta)}
        </div>
        <div class="update-date">${meta.date}</div>
      `;
      container.appendChild(updateDiv);
    });
  })
  .catch(err => console.error("Cannot load updates:", err));

// Logo facoltativo sotto la news: logo, logo_alt, logo_link nel front matter.
// Se il file non esiste ancora, l'immagine viene semplicemente nascosta.
function renderUpdateLogo(meta) {
  if (!meta.logo) return "";
  const img = `<img src="${meta.logo}" alt="${meta.logoAlt || ""}" loading="lazy" onerror="this.closest('.update-logo').remove()">`;
  return `<div class="update-logo">${
    meta.logoLink ? `<a href="${meta.logoLink}" target="_blank" rel="noopener">${img}</a>` : img
  }</div>`;
}
