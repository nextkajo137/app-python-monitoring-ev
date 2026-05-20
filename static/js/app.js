const MAX_POINTS = 48;

const fmtRp = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0
});

const fmtNum = new Intl.NumberFormat('id-ID', {
  maximumFractionDigits: 3
});

const els = {
  statusLabel: document.getElementById('statusLabel'),
  sourceBadge: document.getElementById('sourceBadge'),
  levelRing: document.getElementById('levelRing'),
  levelText: document.getElementById('levelText'),
  lastUpdate: document.getElementById('lastUpdate'),
  powerKw: document.getElementById('powerKw'),
  powerW: document.getElementById('powerW'),
  chargerVoltage: document.getElementById('chargerVoltage'),
  plnVoltage: document.getElementById('plnVoltage'),
  cycleCost: document.getElementById('cycleCost'),
  cycleEnergy: document.getElementById('cycleEnergy'),
  historyTable: document.getElementById('historyTable'),
  totalCost: document.getElementById('totalCost'),
  activeCycleCost: document.getElementById('activeCycleCost'),
  totalKwh: document.getElementById('totalKwh'),
  activeKwh: document.getElementById('activeKwh'),
  totalCycles: document.getElementById('totalCycles'),
};

const ctx = document.getElementById('liveChart');

const liveChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
  {
    label: 'Daya Charger (kW)',
    data: [],
    borderWidth: 3,
    tension: 0.38,
    pointRadius: 0,
    yAxisID: 'yPower',
    borderColor: '#00eaff',
    backgroundColor: 'rgba(0, 234, 255, 0.12)',
    fill: true,
  },
  {
    label: 'Tegangan PLN (V)',
    data: [],
    borderWidth: 3,
    tension: 0.38,
    pointRadius: 0,
    yAxisID: 'yVoltage',
    borderColor: '#a855f7',
    backgroundColor: 'rgba(168, 85, 247, 0.08)',
    fill: true,
  }
]
  },
  options: {
    responsive: true,
    interaction: {
      intersect: false,
      mode: 'index'
    },
    plugins: {
  legend: {
    labels: {
      color: '#dbe8ff',
      usePointStyle: true,
      font: {
        weight: 'bold'
      }
    }
  },
  tooltip: {
    backgroundColor: 'rgba(3, 7, 18, 0.92)',
    titleColor: '#00eaff',
    bodyColor: '#ffffff',
    borderColor: 'rgba(0, 234, 255, 0.35)',
    borderWidth: 1
  }
},
    scales: {
      x: {
        ticks: {
          color: '#8ea2bd',
          maxRotation: 0
        },
        grid: {
          color: 'rgba(255,255,255,0.06)'
        }
      },
      yPower: {
        position: 'left',
        beginAtZero: true,
        ticks: {
          color: '#8ea2bd'
        },
        grid: {
          color: 'rgba(255,255,255,0.06)'
        }
      },
      yVoltage: {
        position: 'right',
        min: 200,
        max: 245,
        ticks: {
          color: '#8ea2bd'
        },
        grid: {
          drawOnChartArea: false
        }
      }
    }
  }
});

function setText(el, value) {
  if (el) {
    el.textContent = value;
  }
}

function addChartPoint(data) {
  const label =
    (data.timestamp || '').split(' ')[1] ||
    new Date().toLocaleTimeString('id-ID');

  liveChart.data.labels.push(label);
  liveChart.data.datasets[0].data.push(Number(data.charger_power_kw || 0));
  liveChart.data.datasets[1].data.push(Number(data.pln_voltage_v || 0));

  if (liveChart.data.labels.length > MAX_POINTS) {
    liveChart.data.labels.shift();
    liveChart.data.datasets.forEach(ds => ds.data.shift());
  }

  liveChart.update('none');
}

function renderLive(data) {
  const level = Number(data.level_percent || 0);
  const deg = Math.max(0, Math.min(100, level)) * 3.6;

  els.levelRing.style.setProperty('--level', `${deg}deg`);

  setText(els.levelText, `${level.toFixed(1)}%`);
  setText(els.statusLabel, data.status_label || data.status || '-');
  setText(els.sourceBadge, data.source || 'api');
  setText(els.lastUpdate, data.timestamp || '-');

  setText(els.powerKw, Number(data.charger_power_kw || 0).toFixed(2));
  setText(els.powerW, fmtNum.format(Number(data.charger_power_w || 0)));

  setText(els.chargerVoltage, Number(data.charger_voltage_v || 0).toFixed(1));
  setText(els.plnVoltage, Number(data.pln_voltage_v || 0).toFixed(1));

  setText(
    els.cycleCost,
    data.cycle_cost_text || fmtRp.format(Number(data.cycle_cost_rp || 0))
  );

  setText(els.cycleEnergy, Number(data.cycle_energy_kwh || 0).toFixed(4));

  setText(
    els.activeCycleCost,
    data.cycle_cost_text || fmtRp.format(Number(data.cycle_cost_rp || 0))
  );

  setText(els.activeKwh, Number(data.cycle_energy_kwh || 0).toFixed(4));

  addChartPoint(data);
}

let allHistory = [];
function renderHistory(items) {
  if (!items || !items.length) {
    els.historyTable.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #8ea2bd;">Belum ada data riwayat.</td></tr>';
    return;
  }

  els.historyTable.innerHTML = items.map(item => {
    let badgeColor = '#6c757d'; // Default
    const statusLower = (item.status || '').toLowerCase();
    
    if (statusLower === 'completed') badgeColor = '#10b981';
    else if (statusLower === 'charging') badgeColor = '#3b82f6';
    else if (statusLower === 'paused') badgeColor = '#f59e0b';
    else if (statusLower === 'error') badgeColor = '#ef4444';

    return `
    <tr>
      <td style="font-weight: bold;">${item.cycle_id || '-'}</td>
      <td>${item.started_at || '-'}</td>
      <td>${item.ended_at || '-'}</td>
      <td>${item.duration_min ?? 0} menit</td>
      <td>${Number(item.energy_kwh || 0).toFixed(3)} kWh</td>
      <td>${fmtRp.format(Number(item.cost_rp || 0))}</td>
      <td>
        <span style="background-color: ${badgeColor}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 500; text-transform: uppercase;">
          ${statusLower || '-'}
        </span>
      </td>
    </tr>
  `}).join('');
}

function filterHistoryByDate() {
  const selectedDate = document.getElementById('filterDate')?.value;

  if (!selectedDate) {
    renderHistory(allHistory);
    return;
  }

  const filtered = allHistory.filter(item => {
    return item.started_at?.startsWith(selectedDate);
  });

  renderHistory(filtered);
}

function renderSummary(data) {
  setText(
    els.totalCost,
    data.total_cost_text || fmtRp.format(Number(data.total_cost_rp || 0))
  );

  setText(els.totalKwh, Number(data.total_energy_kwh || 0).toFixed(4));
  setText(els.totalCycles, data.total_cycles ?? 0);

  setText(
    els.activeCycleCost,
    data.active_cycle_cost_text || fmtRp.format(Number(data.active_cycle_cost_rp || 0))
  );

  setText(
    els.activeKwh,
    Number(data.active_cycle_energy_kwh || 0).toFixed(4)
  );
}

async function getJson(url, options = {}) {
  const res = await fetch(url, options);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

async function refreshLive() {
  try {
    const data = await getJson('/api/live');
    renderLive(data);
  } catch (err) {
    console.error(err);
  }
}

async function refreshHistory() {
  try {

    const data = await getJson('/api/history');

    allHistory = data.items || data.history || [];

    const selectedDate =
      document.getElementById('filterDate')?.value;

    if (selectedDate) {

      const filtered = allHistory.filter(item => {
        if (!item.started_at) return false;

        return item.started_at.startsWith(selectedDate);
      });

      renderHistory(filtered);

    } else {

      renderHistory(allHistory);

    }

  } catch (err) {
    console.error(err);
  }
}

async function refreshSummary() { 
  try { 
    const data = await getJson('/api/summary'); renderSummary(data); 
  } catch (err) { console.error(err); } }

async function control(action) {
  const data = await getJson('/api/control', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ action })
  });

  renderLive(data);
  refreshSummary();
  refreshHistory();
}

function downloadCSVReport() {

  const selectedDate =
    document.getElementById('filterDate')?.value;

  let url = '/api/export/csv';

  if (selectedDate) {
    url += `?date=${selectedDate}`;
  }

  window.open(url, '_blank');
}

document.querySelectorAll('.nav-link').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-link').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.page').forEach(x => x.classList.remove('active'));

    btn.classList.add('active');
    document.getElementById(`page-${btn.dataset.page}`).classList.add('active');

    refreshHistory();
    refreshSummary();
  });
});

const btnStart = document.getElementById('btnStart');
if (btnStart) btnStart.addEventListener('click', () => control('start'));

const btnPause = document.getElementById('btnPause');
if (btnPause) btnPause.addEventListener('click', () => control('pause'));

const btnReset = document.getElementById('btnReset');
if (btnReset) btnReset.addEventListener('click', () => control('reset'));

const btnExport = document.getElementById('btnExportCSV');
if (btnExport) {
    btnExport.addEventListener('click', downloadCSVReport);
}
const btnFilter = document.getElementById('btnFilter');

if (btnFilter) {
  btnFilter.addEventListener('click', filterHistoryByDate);
}

const btnResetFilter = document.getElementById('btnResetFilter');

if (btnResetFilter) {
  btnResetFilter.addEventListener('click', () => {
    const filterInput = document.getElementById('filterDate');

    if (filterInput) {
      filterInput.value = '';
    }

    renderHistory(allHistory);
  });
}

refreshLive();
refreshHistory();
refreshSummary();

setInterval(refreshLive, 1000);
setInterval(refreshSummary, 2500);
setInterval(refreshHistory, 5000);
