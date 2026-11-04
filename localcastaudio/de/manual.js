(() => {
  const toc = document.getElementById('toc');
  const main = document.querySelector('main');
  const mobile = window.matchMedia('(max-width: 760px)');
  const links = [...document.querySelectorAll('.toc-links a')];
  let observer;
  function configure() {
    toc.open = !mobile.matches;
    observer?.disconnect();
    if (!('IntersectionObserver' in window)) return;
    observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        links.forEach(a => {
          if (a.hash === '#' + entry.target.id) a.setAttribute('aria-current', 'location');
          else a.removeAttribute('aria-current');
        });
      }
    }, {root: mobile.matches ? null : main, rootMargin: '0px 0px -70% 0px'});
    document.querySelectorAll('h2[id], h3[id]').forEach(h => observer.observe(h));
  }
  links.forEach(a => a.addEventListener('click', event => {
    if (!mobile.matches) return;
    const target = document.getElementById(a.hash.slice(1));
    if (!target) return;
    event.preventDefault();
    toc.open = false;
    // Wait for the collapsed contents to settle before calculating the target.
    requestAnimationFrame(() => {
      target.scrollIntoView({behavior: 'auto', block: 'start'});
      target.tabIndex = -1;
      target.focus({preventScroll: true});
      history.replaceState(null, '', a.hash);
    });
  }));
  mobile.addEventListener('change', configure);
  document.getElementById('print').addEventListener('click', () => window.print());
  configure();
})();
