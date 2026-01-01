// site.js
const SITE_NAME = "Alessandro Massobrio";

function setPageTitle(customTitle) {
  const title = customTitle?.trim() || document.querySelector("main h1")?.textContent?.trim();
  document.title = title ? `${SITE_NAME} | ${title}` : SITE_NAME;
}

document.addEventListener("DOMContentLoaded", () => {
  // Pagine statiche: Home, About, News
  if (!window.isWorksPage) {
    setPageTitle();
  }
});

function makeMarkdownLinksExternal(container = document) {
  // Selettore: tutti i link dentro il container
  const links = container.querySelectorAll("a");
  links.forEach(link => {
    // Evita di sovrascrivere link già configurati
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");
  });
}
