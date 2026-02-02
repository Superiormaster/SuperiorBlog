const openDrawer = document.getElementById('openDrawer');
const drawer = document.getElementById('mainDrawer');
const overlay = document.getElementById('drawerOverlay');

function openMenu() {
  drawer.classList.remove('translate-x-full');
  overlay.classList.remove('hidden');
  document.documentElement.classList.add('overflow-hidden');
}

function closeMenu() {
  drawer.classList.add('translate-x-full');
  overlay.classList.add('hidden');
  document.documentElement.classList.remove('overflow-hidden');
}

openDrawer.addEventListener('click', openMenu);
overlay.addEventListener('click', closeMenu);