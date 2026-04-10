/* admin-challenge-create.js — challenge creation form: hex picker, rewards, capture mode toggle */

/**
 * @param {Object} config
 * @param {string} config.tileUrl        - tile server URL
 * @param {string} config.csrfToken      - CSRF token
 * @param {string} config.hexagonsApiUrl - URL for api_challenge_hexagons
 * @param {Array}  config.rewardTypes    - [{ value, label }, ...]
 * @param {Object} config.translations   - { zoomBoth, zoomGenerate }
 */
function initChallengeCreate(config) {
  var map = L.map('hex-map').setView([46.5, 2.5], 10);
  L.tileLayer(config.tileUrl, {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  var MIN_ZOOM_LOAD = 11;
  var MIN_ZOOM_GENERATE = 14;
  var hexLayer = null;
  var selectedIds = new Set();
  var btnLoad = document.getElementById('btn-load');
  var btnGenerate = document.getElementById('btn-generate');
  var zoomWarn = document.getElementById('hex-zoom-warn');

  function updateCount() {
    document.querySelector('#hex-count strong').textContent = selectedIds.size;
    document.getElementById('hexagon_ids').value = Array.from(selectedIds).join(',');
  }

  function updateButtons() {
    var zoom = map.getZoom();
    var canLoad = zoom >= MIN_ZOOM_LOAD;
    var canGenerate = zoom >= MIN_ZOOM_GENERATE;
    btnLoad.disabled = !canLoad;
    btnGenerate.disabled = !canGenerate;

    if (!canLoad) {
      zoomWarn.textContent = config.translations.zoomBoth;
      zoomWarn.style.display = '';
    } else if (!canGenerate) {
      zoomWarn.textContent = config.translations.zoomGenerate;
      zoomWarn.style.display = '';
    } else {
      zoomWarn.style.display = 'none';
    }
  }

  function displayHexagons(data) {
    if (data.error) return;
    if (hexLayer) map.removeLayer(hexLayer);
    hexLayer = L.geoJSON(data, {
      style: function(feature) {
        var selected = selectedIds.has(feature.properties.id);
        return {
          color: selected ? '#4f6814' : '#999',
          weight: 1,
          fillColor: selected ? '#4f6814' : '#ddd',
          fillOpacity: selected ? 0.5 : 0.15,
        };
      },
      onEachFeature: function(feature, layer) {
        layer.on('click', function() {
          var id = feature.properties.id;
          if (selectedIds.has(id)) {
            selectedIds.delete(id);
          } else {
            selectedIds.add(id);
          }
          hexLayer.resetStyle(layer);
          updateCount();
        });
      }
    }).addTo(map);
  }

  function fetchHexagons(method) {
    var zoom = map.getZoom();
    var b = map.getBounds();
    var bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(',');
    var url = config.hexagonsApiUrl + '?bbox=' + bbox + '&zoom=' + zoom;

    var opts = { method: method, headers: {} };
    if (method === 'POST') {
      opts.headers['X-CSRFToken'] = config.csrfToken;
    }

    fetch(url, opts).then(function(r) { return r.json(); }).then(displayHexagons);
  }

  btnLoad.addEventListener('click', function() {
    if (map.getZoom() >= MIN_ZOOM_LOAD) fetchHexagons('GET');
  });

  btnGenerate.addEventListener('click', function() {
    if (map.getZoom() >= MIN_ZOOM_GENERATE) fetchHexagons('POST');
  });

  map.on('zoomend', updateButtons);
  updateButtons();

  // Rewards
  var rewardsList = document.getElementById('rewards-list');

  function addRewardRow() {
    var row = document.createElement('div');
    row.className = 'reward-row';

    var options = config.rewardTypes.map(function(t) {
      return '<option value="' + t.value + '">' + t.label + '</option>';
    }).join('');

    row.innerHTML =
      '<input type="number" class="rw-rank" min="1" max="3" value="1" placeholder="#">' +
      '<select class="rw-type">' + options + '</select>' +
      '<input type="text" class="rw-badge" placeholder="badge_id">' +
      '<button type="button" class="btn-remove" onclick="this.parentElement.remove()">&times;</button>';
    rewardsList.appendChild(row);
  }

  document.getElementById('btn-add-reward').addEventListener('click', addRewardRow);

  document.getElementById('challenge-form').addEventListener('submit', function() {
    var rows = rewardsList.querySelectorAll('.reward-row');
    var rewards = [];
    rows.forEach(function(row) {
      rewards.push({
        rank_threshold: parseInt(row.querySelector('.rw-rank').value, 10),
        reward_type: row.querySelector('.rw-type').value,
        badge_id: row.querySelector('.rw-badge').value,
      });
    });
    document.getElementById('rewards_json').value = JSON.stringify(rewards);
  });

  // Show/hide fields based on type
  var typeSelect = document.getElementById('challenge_type');
  var captureModeGroup = document.getElementById('capture-mode-group');
  var hexagonsCard = document.getElementById('hexagons-card');
  var goalThresholdGroup = document.getElementById('goal-threshold-group');
  var geozoneGroup = document.getElementById('geozone-group');
  var distinctZonesGroup = document.getElementById('distinct-zones-group');
  var datasetGroup = document.getElementById('dataset-group');

  function toggleTypeFields() {
    var t = typeSelect.value;
    captureModeGroup.style.display = t === 'capture_hexagon' ? '' : 'none';
    hexagonsCard.style.display = (t === 'capture_hexagon' || t === 'max_points') ? '' : 'none';
    goalThresholdGroup.style.display = (t === 'active_days' || t === 'new_hexagons' || t === 'distinct_zones' || t === 'visit_hexagons') ? '' : 'none';
    geozoneGroup.style.display = (t === 'max_points' || t === 'new_hexagons') ? '' : 'none';
    distinctZonesGroup.style.display = t === 'distinct_zones' ? '' : 'none';
    if (datasetGroup) datasetGroup.style.display = t === 'dataset_points' ? '' : 'none';
  }
  typeSelect.addEventListener('change', toggleTypeFields);
  toggleTypeFields();
}
