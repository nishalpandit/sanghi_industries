/* ========================================
   Charts - Beautiful, gradient-rich
   ======================================== */

const ChartDefaults = {
  font: "'Inter', sans-serif",
  gridColor: 'rgba(148,163,184,0.08)',
  tick: '#94a3b8',

  gradient(ctx, c1, c2) {
    const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
    g.addColorStop(0, c1);
    g.addColorStop(1, c2);
    return g;
  },

  line(opts = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: {
          display: opts.legend !== false,
          position: 'top',
          align: 'end',
          labels: { font: { family: this.font, size: 12, weight: 500 }, usePointStyle: true, pointStyleWidth: 8, padding: 20, boxWidth: 6, boxHeight: 6 }
        },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.95)',
          titleFont: { family: this.font, size: 13, weight: 600 },
          bodyFont: { family: this.font, size: 12, weight: 400 },
          padding: { x: 14, y: 10 },
          cornerRadius: 10,
          displayColors: true,
          boxWidth: 8, boxHeight: 8, boxPadding: 4,
          ...(opts.tooltip || {})
        }
      },
      scales: {
        x: {
          border: { display: false },
          grid: { display: false },
          ticks: { font: { family: this.font, size: 11, weight: 500 }, color: this.tick, padding: 8 }
        },
        y: {
          border: { display: false },
          grid: { color: this.gridColor },
          ticks: { font: { family: this.font, size: 11, weight: 500 }, color: this.tick, padding: 12, ...(opts.yTicks || {}) },
          beginAtZero: true
        }
      },
      elements: {
        line: { tension: 0.4, borderWidth: 2.5 },
        point: { radius: 0, hoverRadius: 5, hoverBorderWidth: 2, hoverBackgroundColor: '#fff' }
      }
    };
  },

  bar(opts = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: opts.legend !== false,
          position: 'top',
          align: 'end',
          labels: { font: { family: this.font, size: 12, weight: 500 }, usePointStyle: true, pointStyleWidth: 8, padding: 20, boxWidth: 6, boxHeight: 6 }
        },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.95)',
          titleFont: { family: this.font, size: 13, weight: 600 },
          bodyFont: { family: this.font, size: 12 },
          padding: { x: 14, y: 10 },
          cornerRadius: 10,
          ...(opts.tooltip || {})
        }
      },
      scales: {
        x: {
          border: { display: false },
          grid: { display: false },
          ticks: { font: { family: this.font, size: 11, weight: 500 }, color: this.tick, padding: 8 }
        },
        y: {
          border: { display: false },
          grid: { color: this.gridColor },
          ticks: { font: { family: this.font, size: 11, weight: 500 }, color: this.tick, padding: 12, ...(opts.yTicks || {}) },
          beginAtZero: true
        }
      },
      borderRadius: 8,
      borderSkipped: false,
      barPercentage: 0.6,
      categoryPercentage: 0.7,
      ...(opts.extra || {})
    };
  },

  donut(opts = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      cutout: opts.cutout || '70%',
      plugins: {
        legend: {
          display: opts.legend !== false,
          position: opts.legendPos || 'bottom',
          labels: { font: { family: this.font, size: 12, weight: 500 }, usePointStyle: true, pointStyleWidth: 10, padding: 20, boxWidth: 8, boxHeight: 8 }
        },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.95)',
          titleFont: { family: this.font, size: 13, weight: 600 },
          bodyFont: { family: this.font, size: 12 },
          padding: { x: 14, y: 10 },
          cornerRadius: 10
        }
      }
    };
  }
};

/* ---- Chart functions ---- */

function createUserGrowthChart(id) {
  const el = document.getElementById(id); if (!el) return;
  const ctx = el.getContext('2d');
  const grad1 = ChartDefaults.gradient(ctx, 'rgba(79,70,229,0.25)', 'rgba(79,70,229,0.01)');
  const grad2 = ChartDefaults.gradient(ctx, 'rgba(16,185,129,0.2)', 'rgba(16,185,129,0.01)');

  return new Chart(el, {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'New Users', data: [], backgroundColor: 'rgba(79,70,229,0.85)', hoverBackgroundColor: '#4f46e5', borderRadius: 0 },
        { label: 'Active Users', data: [], backgroundColor: 'rgba(16,185,129,0.85)', hoverBackgroundColor: '#10b981', borderRadius: 0 }
      ]
    },
    options: ChartDefaults.bar()
  });
}

function createRevenueChart(id) {
  const el = document.getElementById(id); if (!el) return;
  const ctx = el.getContext('2d');
  const grad1 = ChartDefaults.gradient(ctx, 'rgba(79,70,229,0.25)', 'rgba(79,70,229,0.01)');
  const grad2 = ChartDefaults.gradient(ctx, 'rgba(239,68,68,0.2)', 'rgba(239,68,68,0.01)');

  return new Chart(el, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Revenue (₹)', data: [], borderColor: '#4f46e5', backgroundColor: grad1, fill: true, pointBackgroundColor: '#4f46e5' }
      ]
    },
    options: ChartDefaults.line({ tooltip: { callbacks: { label: c => c.dataset.label + ': ₹' + c.parsed.y.toFixed(1) + ' L' } } })
  });
}



function createSubscriptionChart(id) {
  const el = document.getElementById(id); if (!el) return;
  return new Chart(el, {
    type: 'doughnut',
    data: {
      labels: [],
      datasets: [{ data: [], backgroundColor: ['#94a3b8', '#3b82f6', '#6366f1', '#8b5cf6'], hoverBackgroundColor: ['#64748b', '#2563eb', '#4f46e5', '#7c3aed'], borderWidth: 0, spacing: 4 }]
    },
    options: ChartDefaults.donut()
  });
}

function createDAUChart(id, labels = [], data = []) {
  const el = document.getElementById(id); if (!el) return;
  const ctx = el.getContext('2d');
  const grad = ChartDefaults.gradient(ctx, 'rgba(99,102,241,0.3)', 'rgba(99,102,241,0.01)');
  return new Chart(el, {
    type: 'line',
    data: { labels, datasets: [{ label: 'DAU', data, borderColor: '#6366f1', backgroundColor: grad, fill: true, pointBackgroundColor: '#6366f1' }] },
    options: ChartDefaults.line({ legend: false })
  });
}

function createSessionChart(id, labels = [], data = []) {
  const el = document.getElementById(id); if (!el) return;
  return new Chart(el, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: 'Avg Session (min)', data: data, backgroundColor: ['rgba(99,102,241,0.7)', 'rgba(124,58,237,0.7)', 'rgba(99,102,241,0.7)', 'rgba(124,58,237,0.7)', 'rgba(99,102,241,0.7)', 'rgba(124,58,237,0.7)', 'rgba(99,102,241,0.7)'], hoverBackgroundColor: '#6366f1', borderRadius: 8 }]
    },
    options: ChartDefaults.bar({ legend: false })
  });
}

function createConversionFunnel(id, labels = [], data = []) {
  const el = document.getElementById(id); if (!el) return;
  return new Chart(el, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ data: data, backgroundColor: ['rgba(59,130,246,0.75)', 'rgba(99,102,241,0.75)', 'rgba(124,58,237,0.75)', 'rgba(16,185,129,0.75)', 'rgba(245,158,11,0.75)'], hoverBackgroundColor: ['#3b82f6', '#6366f1', '#7c3aed', '#10b981', '#f59e0b'], borderRadius: 8 }]
    },
    options: {
      ...ChartDefaults.bar({ legend: false }),
      indexAxis: 'y',
      scales: {
        x: { border: { display: false }, grid: { color: ChartDefaults.gridColor }, ticks: { font: { family: ChartDefaults.font, size: 11, weight: 500 }, color: ChartDefaults.tick, callback: v => (typeof formatNumber === 'function' ? formatNumber(v) : v) } },
        y: { border: { display: false }, grid: { display: false }, ticks: { font: { family: ChartDefaults.font, size: 11, weight: 500 }, color: ChartDefaults.tick } }
      }
    }
  });
}

function createFeatureUsageChart(id, labels = [], thisMonth = [], lastMonth = []) {
  const el = document.getElementById(id); if (!el) return;
  return new Chart(el, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [
        { label: 'This Month', data: thisMonth, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.15)', pointBackgroundColor: '#6366f1', pointRadius: 4, pointHoverRadius: 6, borderWidth: 2 },
        { label: 'Last Month', data: lastMonth, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', pointBackgroundColor: '#f59e0b', pointRadius: 4, pointHoverRadius: 6, borderWidth: 2 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', align: 'end', labels: { font: { family: ChartDefaults.font, size: 12, weight: 500 }, usePointStyle: true, pointStyleWidth: 8, padding: 20 } } },
      scales: { r: { ticks: { display: false }, grid: { color: 'rgba(148,163,184,0.12)' }, angleLines: { color: 'rgba(148,163,184,0.08)' }, pointLabels: { font: { family: ChartDefaults.font, size: 11, weight: 500 }, color: ChartDefaults.tick } } }
    }
  });
}

function createRevenueTrendChart(id, period, labels = [], data = []) {
  const el = document.getElementById(id); if (!el) return;
  const ctx = el.getContext('2d');
  const grad = ChartDefaults.gradient(ctx, 'rgba(16,185,129,0.3)', 'rgba(16,185,129,0.01)');

  return new Chart(el, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Revenue', data, borderColor: '#10b981', backgroundColor: grad, fill: true, pointBackgroundColor: '#10b981' }] },
    options: ChartDefaults.line({ legend: false, tooltip: { callbacks: { label: c => '₹' + c.parsed.y.toLocaleString('en-IN') } } })
  });
}

function createPosterCreationChart(id, labels = [], created = [], exported = []) {
  const el = document.getElementById(id); if (!el) return;
  return new Chart(el, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Posters Created', data: created, backgroundColor: 'rgba(99,102,241,0.8)', hoverBackgroundColor: '#6366f1', borderRadius: 8 },
        { label: 'Posters Exported', data: exported, backgroundColor: 'rgba(59,130,246,0.35)', hoverBackgroundColor: 'rgba(59,130,246,0.6)', borderRadius: 8 }
      ]
    },
    options: ChartDefaults.bar({ tooltip: { callbacks: { label: c => c.dataset.label + ': ' + (typeof formatNumber === 'function' ? formatNumber(c.parsed.y) : c.parsed.y) } } })
  });
}
