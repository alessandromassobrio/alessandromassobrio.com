/**
 * Carica un partial HTML dentro un elemento con id
 * @param {string} id - id dell'elemento dove inserire il partial
 * @param {string} url - path del file partial
 */
function includeHTML(id, url) {
  fetch(url)
    .then(res => res.text())
    .then(html => {
      document.getElementById(id).innerHTML = html;

      // Se stiamo caricando l'header, attiva link menu
      if (id === "header-placeholder") {
        activateMenuLink();
      }
    })
    .catch(err => console.error("Cannot load partial:", url, err));
}

/**
 * Evidenzia il link del menu corrispondente alla pagina corrente
 */
function activateMenuLink() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.site-nav a').forEach(link => {
    const href = link.getAttribute('href');
    // Aggiunge classe active se href corrisponde alla pagina o è prefix
    if (href === currentPath || currentPath.startsWith(href)) {
      link.classList.add('active');
    }
  });
}

// Carica header e footer
includeHTML("header-placeholder", "/assets/partials/header.html");
includeHTML("footer-placeholder", "/assets/partials/footer.html");
