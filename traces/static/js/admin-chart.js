/* admin-chart.js — bar + cumulative line chart for admin dashboards */

/**
 * @param {Object} config
 * @param {string} config.canvasId   - DOM id of the <canvas>
 * @param {string} config.emptyId    - DOM id of the empty-message element
 * @param {Object} config.data       - { labels, cumulative, [barKey] }
 * @param {string} config.barKey     - key in data for bar values
 * @param {string} config.barLabel   - display label for bar dataset
 * @param {string} config.barColor   - CSS color for bars
 * @param {string} config.cumulLabel - display label for cumulative line
 */
function initAdminChart(config) {
  var data = config.data;

  if (data.labels.length === 0) {
    document.getElementById(config.emptyId).style.display = 'flex';
    document.getElementById(config.canvasId).style.display = 'none';
    return;
  }

  var ctx = document.getElementById(config.canvasId).getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [
        {
          label: config.barLabel,
          data: data[config.barKey],
          backgroundColor: config.barColor,
          borderRadius: 4,
          order: 2
        },
        {
          label: config.cumulLabel,
          data: data.cumulative,
          type: 'line',
          borderColor: '#e0a020',
          backgroundColor: 'rgba(224,160,32,0.1)',
          borderWidth: 2,
          pointRadius: 2,
          fill: true,
          tension: 0.3,
          order: 1,
          yAxisID: 'yCumul'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { size: 12 }, boxWidth: 14, padding: 16 }
        },
        tooltip: {
          callbacks: {
            title: function(items) { return items[0].label; }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 11 }, maxRotation: 45 }
        },
        y: {
          beginAtZero: true,
          position: 'left',
          title: { display: true, text: config.barLabel },
          ticks: { precision: 0, font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,0.06)' }
        },
        yCumul: {
          beginAtZero: true,
          position: 'right',
          title: { display: true, text: config.cumulLabel },
          ticks: { precision: 0, font: { size: 11 } },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}
