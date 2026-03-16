fetch("/data/updates.md")
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
      });

      const updateDiv = document.createElement("div");
      updateDiv.className = "update";

      updateDiv.innerHTML = `
        <div class="update-body">
          <strong>${meta.title}</strong>
          <p>${meta.description ?? ""}</p>
        </div>
        <div class="update-date">${meta.date}</div>
      `;
      container.appendChild(updateDiv);
    });
  })
  .catch(err => console.error("Cannot load updates:", err));
