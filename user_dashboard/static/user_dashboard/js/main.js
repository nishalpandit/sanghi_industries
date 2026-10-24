/* ==========================================================
   PosterAI — User Dashboard
   Shared UI behaviors (Vanilla JS — UI toggles only, no state)
   ========================================================== */

/* ---- Sidebar Toggle (Mobile) ---- */
function openSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}

/* ---- Subscription Modal ---- */
function openSubscriptionModal() {
    var modal = document.getElementById('subscriptionModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeSubscriptionModal() {
    var modal = document.getElementById('subscriptionModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

/* ---- FAQ Accordion Toggle ---- */
function toggleFaq(button) {
    var faqItem = button.closest('.faq-item');
    if (faqItem) faqItem.classList.toggle('open');
}

/* ---- Toast Notifications (UI feedback only) ---- */
function showToast(message) {
    var container = document.getElementById('toastContainer');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>' +
        '<p>' + message + '</p>';
    container.appendChild(toast);

    setTimeout(function () {
        toast.classList.add('hiding');
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    }, 3000);
}

/* ---- Init on DOM ready ---- */
document.addEventListener('DOMContentLoaded', function () {

    /* Hamburger + overlay wiring */
    var hamburger = document.getElementById('hamburgerBtn');
    var overlay = document.getElementById('sidebarOverlay');
    if (hamburger) hamburger.addEventListener('click', openSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    /* Filter pills — single-active toggle within each group */
    document.querySelectorAll('.filter-pills').forEach(function (group) {
        group.querySelectorAll('.filter-pill').forEach(function (pill) {
            pill.addEventListener('click', function () {
                group.querySelectorAll('.filter-pill').forEach(function (p) {
                    p.classList.remove('active');
                });
                this.classList.add('active');
            });
        });
    });

    /* Close subscription modal on overlay click */
    var modal = document.getElementById('subscriptionModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeSubscriptionModal();
        });
    }

    /* Escape key closes modal / mobile sidebar / mobile search */
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeSubscriptionModal();
            closeSidebar();
            closeMobileSearch();
        }
    });
});

/* ---- Mobile Search Bar Toggle (phones ≤640px) ---- */
function toggleMobileSearch() {
    var bar = document.getElementById('mobileSearchBar');
    if (!bar) return;
    bar.classList.toggle('active');
    if (bar.classList.contains('active')) {
        var input = bar.querySelector('input');
        if (input) setTimeout(function () { input.focus(); }, 250);
    }
}

function closeMobileSearch() {
    var bar = document.getElementById('mobileSearchBar');
    if (bar) bar.classList.remove('active');
}
