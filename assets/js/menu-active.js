// Evidenzia il link attivo nel menu
document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.site-nav a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || currentPath.startsWith(href)) {
      link.classList.add('active');
    }
  });
});
