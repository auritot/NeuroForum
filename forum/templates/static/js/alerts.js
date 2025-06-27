document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert-animated.fade-in');
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.classList.remove('fade-in');
      alert.classList.add('fade-out');
      alert.addEventListener('animationend', () => {
        if (alert.classList.contains('fade-out')) {
          alert.remove();
        }
      });
    }, 5000);
  });
});
