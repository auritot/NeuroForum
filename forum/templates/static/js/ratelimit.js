// Countdown with syntax fixes
if (document.getElementById('countdown')) {
    let seconds = parseInt("{{ timeout_seconds|escapejs }}");
    const countdown = setInterval(() => {
        seconds--;
        const countdownEl = document.getElementById('countdown');
        if (countdownEl) countdownEl.textContent = seconds;
        
        if (seconds === 0) {
            clearInterval(countdown);
            const alert = document.querySelector('.alert');
            if (alert) {
                alert.classList.replace('alert-warning', 'alert-success');
                alert.innerHTML = `
                    <i class="bi bi-check-circle me-2"></i>
                    Search re-enabled!
                `;
                setTimeout(() => alert.remove(), 3000);
                
                document.querySelectorAll('input[name="q"], button[type="submit"]')
                    .forEach(el => el.disabled = false);
            }
        }
    }, 1000);
}
