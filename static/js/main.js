/* Secret Snakes — shared front-end helpers.
   Loaded on every page via base.html. No dependencies. */

(function () {
    'use strict';

    /* ---------- Toast notifications (replacement for alert()) ----------- */

    function toastRegion() {
        var region = document.querySelector('.toast-region');
        if (!region) {
            region = document.createElement('div');
            region.className = 'toast-region';
            region.setAttribute('aria-live', 'polite');
            document.body.appendChild(region);
        }
        return region;
    }

    /**
     * Show a toast. snakeToast('Saved!') or snakeToast('Nope', { type: 'error' }).
     * Returns the toast element in case the caller wants it.
     */
    window.snakeToast = function (message, opts) {
        opts = opts || {};
        var toast = document.createElement('div');
        toast.className = 'toast' + (opts.type === 'error' ? ' toast-error' : '');
        toast.setAttribute('role', 'status');
        toast.textContent = (opts.type === 'error' ? '🙈 ' : '🐍 ') + message;
        toastRegion().appendChild(toast);

        var lifetime = opts.duration || 4000;
        setTimeout(function () {
            toast.classList.add('toast-out');
            setTimeout(function () { toast.remove(); }, 350);
        }, lifetime);
        return toast;
    };

    /* ---------- Modals: click the dark backdrop to close ---------------- */

    document.addEventListener('click', function (e) {
        if (e.target.classList && e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    /* ---------- Snakesmas countdown (footer) ----------------------------- */

    var countdown = document.getElementById('snake-countdown');
    if (countdown) {
        var now = new Date();
        var snakesmas = new Date(now.getFullYear(), 11, 25);
        if (now > snakesmas) {
            snakesmas = new Date(now.getFullYear() + 1, 11, 25);
        }
        var days = Math.ceil((snakesmas - now) / 86400000);
        countdown.textContent = days === 0
            ? "It's Snakesmas! Go shake your presents 🎁"
            : days + ' day' + (days === 1 ? '' : 's') + ' until Snakesmas';
    }
})();
