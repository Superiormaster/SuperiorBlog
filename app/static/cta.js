document.addEventListener('DOMContentLoaded', () => {
  const CTA_KEY = 'creator_cta_dismissed';
  const cta = document.getElementById('creator-cta');
  const modal = document.getElementById('login-modal');
  const btn = document.getElementById('btn');

  if (!cta && !btn) return;

  window.dismissCreatorCTA = function () {
    localStorage.setItem(CTA_KEY, '1');
    cta?.remove();
  };

  window.openLoginModal = function () {
    modal?.classList.remove('hidden');
  };

  window.closeLoginModal = function () {
    modal?.classList.add('hidden');
  };

  if (localStorage.getItem(CTA_KEY)) {
    cta?.remove();
  }

  function onScroll() {
    const scrollPercent =
      window.scrollY / (document.body.scrollHeight - window.innerHeight);

    // CTA logic
    if (cta && scrollPercent > 0.25) {
      cta.classList.remove('hidden');
    }

    // Back to top button logic
    if (btn) {
      btn.style.display = window.scrollY > 300 ? 'block' : 'none';
    }
  }

  window.addEventListener('scroll', onScroll);

  btn?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});