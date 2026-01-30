const flashContainer = document.getElementById('flash-messages');
  if (flashContainer) {
      // Remove the messages after 3 seconds
    setTimeout(() => {
      flashContainer.remove();
    }, 3000); // 3000ms = 3 seconds
  }

const messages = document.querySelectorAll('.fade-message');
  messages.forEach(msg => {
      // Wait 3 seconds before starting fade
    setTimeout(() => {
      msg.classList.add('hide');
        // Remove from DOM after transition
      setTimeout(() => msg.remove(), 500);
    }, 3000); // 3000ms = 3 seconds
  });