fetch("/data/updates.md")
  .then(res => res.text())
  .then(text => {
    const updates = text.split(/^---$/gm).filter(Boolean);

    const container = document.querySelector("#updates-container");
    updates.forEach(updateText => {
      const lines = updateText.trim().split("\n");
      let meta = {};
      let bodyLines = [];

      // legge front-matter (title e date)
      if (lines[0].startsWith("title:")) {
        meta.title = lines[0].replace("title:", "").trim();
        meta.date = lines[1].replace("date:", "").trim();
        bodyLines = lines.slice(2);
      } else {
        bodyLines = lines;
      }

      const updateDiv = document.createElement("div");
      updateDiv.className = "update";

      updateDiv.innerHTML = `
        <div class="update-body">
          <strong>${meta.title}</strong>
          <p>${bodyLines.join("\n")}</p>
        </div>
        <div class="update-date">${meta.date}</div>
      `;
      container.appendChild(updateDiv);
    });
  })
  .catch(err => console.error("Cannot load updates:", err));
