document.addEventListener('DOMContentLoaded', () => {
  const header = document.querySelector('.site-header');
  const page = document.querySelector('.page-container');

  if (header) {
    // header presente → slittamento dal basso
    header.offsetHeight; // forza reflow
    header.classList.add('visible');
    page.classList.add('visible');
  } else {
    // header assente → contenuto parte dall’alto
    page.classList.add('visible');
  }
});
