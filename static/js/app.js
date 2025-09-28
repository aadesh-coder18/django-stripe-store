document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('buy-form');
  const button = document.getElementById('buy-button');
  if (form && button) {
    form.addEventListener('submit', function () {
      // Prevent accidental double submits
      button.disabled = true;
      button.innerText = 'Redirecting to Stripe...';
    });
  }
});
