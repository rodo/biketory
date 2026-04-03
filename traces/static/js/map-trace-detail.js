/* map-trace-detail.js — full map on the trace detail page */

(function () {
  var config = readJSON('map-config');
  if (!config) return;

  var map = initMap(config.elementId, config);

  var mapEl = document.getElementById(config.elementId);
  var ownerUsername = mapEl.dataset.owner || '';
  var currentUser  = mapEl.dataset.currentUser || '';
  var hexStyle = (currentUser === ownerUsername) ? STYLE_HEXAGONS_OWN : STYLE_HEXAGONS_OTHER;

  var traceGroup   = L.layerGroup().addTo(map);
  var surfaceGroup = L.layerGroup().addTo(map);
  var hexGroup     = L.layerGroup().addTo(map);

  var route    = readJSON('route-geojson');
  var surfaces = readJSON('surfaces-geojson');
  var hexagons = readJSON('hexagons-geojson');

  var layers = [];

  layers.push(addLayer(map, route, STYLE_ROUTE, { group: traceGroup }));
  layers.push(addLayer(map, surfaces, STYLE_SURFACES, { group: surfaceGroup }));
  layers.push(addLayer(map, hexagons, hexStyle, {
    group: hexGroup,
    onEachFeature: function (feature, layer) {
      var pts = feature.properties.points;
      layer.bindTooltip(
        ownerUsername + ' \u00b7 ' + pts + 'pt',
        { sticky: true, className: 'surface-tooltip' }
      );
    },
  }));

  fitOrDefault(map, layers, [40, 40], [47.75, -3.37], 12);

  /* ── Layer toggles ── */
  function makeToggle(btnId, group) {
    var btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener('click', function () {
      var active = btn.classList.toggle('active');
      if (active) group.addTo(map); else group.remove();
    });
  }
  makeToggle('btn-trace',    traceGroup);
  makeToggle('btn-surfaces', surfaceGroup);
  makeToggle('btn-hexagons', hexGroup);

  /* ── Poll trace analysis status ── */
  var statusUrl = mapEl.dataset.statusUrl;
  var currentStatus = mapEl.dataset.status;
  if (statusUrl && currentStatus && currentStatus !== 'analyzed') {
    var interval = setInterval(function () {
      fetch(statusUrl)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status !== currentStatus) {
            clearInterval(interval);
            location.reload();
          }
        })
        .catch(function () {});
    }, 5000);
  }

  /* ── Delete confirmation modal ── */
  var modal  = document.getElementById('confirm-modal');
  var cancel = document.getElementById('btn-cancel');
  var openBtn = document.getElementById('btn-open-delete');
  if (modal && cancel && openBtn) {
    openBtn.addEventListener('click', function () { modal.classList.add('open'); });
    cancel.addEventListener('click', function () { modal.classList.remove('open'); });
    modal.addEventListener('click', function (e) {
      if (e.target === modal) modal.classList.remove('open');
    });
  }
})();
