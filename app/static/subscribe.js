let exitShown = false;
let idleTimer;

// Function to show popup only once
function showExitPopup() {
  if (!exitShown) {
    const popup = document.getElementById("exit-popup");
    if (popup) {
      popup.style.display = "flex";
      exitShown = true;
    }
  }
  if (localStorage.getItem("exitPopupShown")) return;
  localStorage.setItem("exitPopupShown", "true");
}

// Close popup
const closeBtn = document.getElementById("close-exit-popup");
if (closeBtn) {
  closeBtn.onclick = function () {
    document.getElementById("exit-popup").style.display = "none";
  };
}

// Desktop exit intent
document.addEventListener("mouseout", function (e) {
  if (e.clientY < 10) {
    showExitPopup();
  }
});

// Idle detection (60 seconds)
function resetIdleTimer() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(showExitPopup, 60000);
}

document.addEventListener("mousemove", resetIdleTimer);
document.addEventListener("touchstart", resetIdleTimer);
resetIdleTimer();

// Mobile back button detection
history.pushState(null, null, location.href);
window.onpopstate = function () {
  showExitPopup();
};