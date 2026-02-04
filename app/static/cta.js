document.addEventListener('DOMContentLoaded', () => {
  const CTA_KEY = 'creator_cta_dismissed';

  const cta = document.getElementById('creator-cta');
  const modal = document.getElementById('login-modal');
  const backToTopBtn = document.getElementById('btn');

  /* ---------------- CTA LOGIC ---------------- */

  if (cta && !localStorage.getItem(CTA_KEY)) {
    let shown = false;

    window.dismissCreatorCTA = function () {
      localStorage.setItem(CTA_KEY, '1');
      cta.remove();
    };

    window.openLoginModal = function () {
      modal?.classList.remove('hidden');
    };

    window.closeLoginModal = function () {
      modal?.classList.add('hidden');
    };

    function showCTA(reason) {
      if (shown) return;
      shown = true;

      cta.classList.remove('hidden');
      console.log('CTA shown by:', reason);

      window.removeEventListener('scroll', onScroll);
      clearTimeout(timer);
    }

    function onScroll() {
      const scrollable =
        document.body.scrollHeight - window.innerHeight;

      if (scrollable <= 0) return;

      if (window.scrollY / scrollable > 0.25) {
        showCTA('scroll');
      }
    }

    window.addEventListener('scroll', onScroll);

    const timer = setTimeout(() => {
      showCTA('time');
    }, 5000);
  } else {
    cta?.remove();
  }

  /* ---------------- BACK TO TOP ---------------- */

  if (backToTopBtn) {
    window.addEventListener('scroll', () => {
      backToTopBtn.style.display =
        window.scrollY > 300 ? 'block' : 'none';
    });

    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
});

/* ---------------- GLOBAL HELPERS ---------------- */

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') window.closeLoginModal?.();
});

function show_pass() {
  const password = document.getElementById('password');
  const checkbox = document.getElementById('show_password');

  if (!password || !checkbox) return;
  password.type = checkbox.checked ? 'text' : 'password';
}