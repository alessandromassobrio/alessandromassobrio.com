// site.js
const SITE_NAME = "Alessandro Massobrio";

function setPageTitle(customTitle) {
  const title = customTitle?.trim() || document.querySelector("main h1")?.textContent?.trim();
  document.title = title ? `${SITE_NAME} | ${title}` : SITE_NAME;
}

document.addEventListener("DOMContentLoaded", () => {
  if (!window.isWorksPage) {
    setPageTitle();
  }
  youtubefacades();
});

function makeMarkdownLinksExternal(container = document) {
  const links = container.querySelectorAll("a");
  links.forEach(link => {
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");
  });
}

function youtubefacades(container = document) {
  container.querySelectorAll('.video-fullscreen iframe[src*="youtube"]').forEach(iframe => {
    const match = iframe.src.match(/embed\/([a-zA-Z0-9_-]{11})/);
    if (!match) return;
    const videoId = match[1];
    const params = iframe.src.split("?")[1] || "";

    const facade = document.createElement("div");
    facade.className = "yt-facade";
    facade.setAttribute("role", "button");
    facade.setAttribute("aria-label", "Play video");

    const img = new Image();
    img.src = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
    img.alt = iframe.title || "YouTube video";
    img.loading = "lazy";
    img.onerror = function () {
      this.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
    };
    facade.appendChild(img);

    const btn = document.createElement("div");
    btn.className = "yt-facade-play";
    facade.appendChild(btn);

    facade.addEventListener("click", () => {
      const newIframe = document.createElement("iframe");
      newIframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1${params ? "&" + params : ""}`;
      newIframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      newIframe.allowFullscreen = true;
      newIframe.frameBorder = "0";
      facade.replaceWith(newIframe);
    });

    iframe.replaceWith(facade);
  });
}
