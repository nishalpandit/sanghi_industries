/* ========================================
   Main JavaScript - Global Functionality
   SPA Architecture - No page reloads
   ======================================== */

// ---- Theme (fixed light) ----
const ThemeManager = { init() {} };

// ---- SPA Router Removed (Using Django) ----
// ---- Sidebar Dropdown Groups ----
const SidebarManager = {
  init() {
    const sidebar = document.querySelector('.sidebar');
    const toggles = document.querySelectorAll('.sidebar-toggle');
    const overlay = document.querySelector('.sidebar-overlay');

    toggles.forEach(toggle => {
      toggle.addEventListener('click', () => {
        if (window.innerWidth <= 1024) {
          sidebar.classList.toggle('mobile-open');
          overlay.classList.toggle('show');
        } else {
          sidebar.classList.toggle('collapsed');
          document.querySelector('.main-content').classList.toggle('sidebar-collapsed');
        }
      });
    });

    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('show');
      });
    }

    // Dropdown toggles
    document.querySelectorAll('.nav-group-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const group = btn.closest('.nav-group');
        // Close other groups
        document.querySelectorAll('.nav-group').forEach(g => {
          if (g !== group) g.classList.remove('open');
        });
        group.classList.toggle('open');
      });
    });
  }
};

// ---- Toast Notifications ----
const Toast = {
  container: null,
  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    document.body.appendChild(this.container);
  },
  show(message, type = 'info', duration = 4000) {
    if (!this.container) this.init();
    const icons = { success: 'fa-check-circle', error: 'fa-times-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
    const colors = { success: 'var(--success)', error: 'var(--danger)', warning: 'var(--warning)', info: 'var(--info)' };
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <i class="fas ${icons[type]}" style="color:${colors[type]};font-size:1.1rem"></i>
      <span style="flex:1">${message}</span>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;padding:4px"><i class="fas fa-times"></i></button>
    `;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
};

// ---- Modal Management ----
const Modal = {
  open(id) {
    const o = document.getElementById(id);
    if (o) { o.classList.add('active'); document.body.style.overflow = 'hidden'; }
  },
  close(id) {
    const o = document.getElementById(id);
    if (o) { o.classList.remove('active'); document.body.style.overflow = ''; }
  },
  init() {
    document.querySelectorAll('.modal-overlay').forEach(o => {
      o.addEventListener('click', (e) => {
        if (e.target === o) { o.classList.remove('active'); document.body.style.overflow = ''; }
      });
    });
  }
};

// ---- Dropdown ----
const Dropdown = {
  init() {
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-dropdown]');
      if (trigger) {
        e.stopPropagation();
        const menu = trigger.nextElementSibling || document.getElementById(trigger.dataset.dropdown);
        document.querySelectorAll('.dropdown-menu.show, .notification-panel.show').forEach(m => { if (m !== menu) m.classList.remove('show'); });
        if (menu) menu.classList.toggle('show');
        return;
      }
      document.querySelectorAll('.dropdown-menu.show, .notification-panel.show').forEach(m => m.classList.remove('show'));
    });
  }
};

// ---- Tabs ----
const Tabs = {
  init() {
    document.querySelectorAll('.tabs').forEach(tc => {
      tc.querySelectorAll('.tab-item').forEach(tab => {
        tab.addEventListener('click', () => {
          const target = tab.dataset.tab;
          tc.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          const parent = tc.parentElement;
          parent.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
          const content = parent.querySelector('#' + target);
          if (content) content.classList.add('active');
        });
      });
    });
  }
};

// ---- Data Export ----
const ExportManager = {
  toCSV(data, filename) {
    if (!data || !data.length) return;
    const headers = Object.keys(data[0]);
    const csv = [headers.join(','), ...data.map(row => headers.map(h => '"' + (row[h] || '') + '"').join(','))].join('\n');
    this.download(csv, filename + '.csv', 'text/csv');
    Toast.show('CSV exported successfully!', 'success');
  },
  toJSON(data, filename) {
    this.download(JSON.stringify(data, null, 2), filename + '.json', 'application/json');
    Toast.show('JSON exported successfully!', 'success');
  },
  download(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  },
  print() { window.print(); }
};

// ---- Indian Formatting ----
function formatNumber(num) {
  if (num >= 10000000) return (num / 10000000).toFixed(1) + ' Cr';
  if (num >= 100000) return (num / 100000).toFixed(1) + ' L';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function formatCurrency(num) {
  return '₹' + num.toLocaleString('en-IN');
}

function formatCurrencyShort(num) {
  if (num >= 10000000) return '₹' + (num / 10000000).toFixed(1) + ' Cr';
  if (num >= 100000) return '₹' + (num / 100000).toFixed(1) + ' L';
  if (num >= 1000) return '₹' + (num / 1000).toFixed(1) + 'K';
  return '₹' + num;
}

function formatDate(date) {
  return new Date(date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
}

function timeAgo(date) {
  const diff = Math.floor((new Date() - new Date(date)) / 1000);
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
  return formatDate(date);
}



const avatarColors = ['#4f46e5','#7c3aed','#2563eb','#059669','#d97706','#dc2626','#0891b2','#7c2d12','#4338ca','#6d28d9','#1d4ed8','#047857'];

function getAvatarColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

function getInitials(name) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
}

function debounce(func, wait) {
  let timeout;
  return function (...args) { clearTimeout(timeout); timeout = setTimeout(() => func.apply(this, args), wait); };
}



// Spinner animation
const _style = document.createElement('style');
_style.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
document.head.appendChild(_style);

// Prevent number inputs from changing value on mouse scroll
document.addEventListener('wheel', function(event) {
  if (document.activeElement.type === 'number') {
    document.activeElement.blur();
  }
});

// ---- Initialize ----

document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  SidebarManager.init();
  Toast.init();
  Dropdown.init();
  Tabs.init();
});
