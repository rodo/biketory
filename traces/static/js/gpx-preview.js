(function () {
  'use strict';

  var R = 6371; // Earth radius in km

  function haversine(lat1, lon1, lat2, lon2) {
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function parseGPX(xmlText) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(xmlText, 'application/xml');
    if (doc.querySelector('parsererror')) return null;

    var trksegs = doc.querySelectorAll('trkseg');
    if (trksegs.length === 0) return null;

    var segments = [];
    var totalPoints = 0;
    var totalDistance = 0;
    var firstTime = null;
    var lastTime = null;

    trksegs.forEach(function (seg) {
      var pts = seg.querySelectorAll('trkpt');
      var points = [];
      pts.forEach(function (pt) {
        var lat = parseFloat(pt.getAttribute('lat'));
        var lon = parseFloat(pt.getAttribute('lon'));
        if (isNaN(lat) || isNaN(lon)) return;

        var timeEl = pt.querySelector('time');
        var time = timeEl ? new Date(timeEl.textContent) : null;

        if (time && !isNaN(time.getTime())) {
          if (!firstTime || time < firstTime) firstTime = time;
          if (!lastTime || time > lastTime) lastTime = time;
        }

        if (points.length > 0) {
          var prev = points[points.length - 1];
          totalDistance += haversine(prev.lat, prev.lon, lat, lon);
        }

        points.push({ lat: lat, lon: lon, time: time });
      });
      if (points.length > 0) {
        segments.push(points);
        totalPoints += points.length;
      }
    });

    if (totalPoints === 0) return null;

    return {
      segments: segments,
      totalPoints: totalPoints,
      totalDistance: totalDistance,
      firstTime: firstTime,
      lastTime: lastTime
    };
  }

  function formatDistance(km) {
    if (km < 1) return (km * 1000).toFixed(0) + ' m';
    return km.toFixed(1) + ' km';
  }

  function formatDuration(ms) {
    var totalMin = Math.floor(ms / 60000);
    var h = Math.floor(totalMin / 60);
    var m = totalMin % 60;
    if (h === 0) return m + ' min';
    return h + 'h ' + (m < 10 ? '0' : '') + m + 'min';
  }

  var map = null;
  var polylines = [];

  function showPreview(data, tileUrl) {
    var panel = document.getElementById('gpx-preview');
    var card = document.getElementById('upload-card');
    panel.style.display = '';
    if (card) card.classList.add('has-preview');

    document.getElementById('stat-distance').textContent = formatDistance(data.totalDistance);
    document.getElementById('stat-points').textContent = data.totalPoints.toLocaleString();
    document.getElementById('stat-segments').textContent = data.segments.length;

    if (data.firstTime) {
      document.getElementById('stat-date').textContent =
        data.firstTime.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } else {
      document.getElementById('stat-date').textContent = '\u2014';
    }

    if (data.firstTime && data.lastTime) {
      var durationMs = data.lastTime.getTime() - data.firstTime.getTime();
      document.getElementById('stat-duration').textContent =
        durationMs > 0 ? formatDuration(durationMs) : '\u2014';
    } else {
      document.getElementById('stat-duration').textContent = '\u2014';
    }

    // Map
    var mapContainer = document.getElementById('preview-map');
    if (map) {
      polylines.forEach(function (pl) { map.removeLayer(pl); });
      polylines = [];
    } else {
      map = L.map(mapContainer, {
        zoomControl: false,
        attributionControl: true,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        touchZoom: false
      });
      L.tileLayer(tileUrl, {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
    }

    var allLatLngs = [];
    data.segments.forEach(function (seg) {
      var latlngs = seg.map(function (p) { return [p.lat, p.lon]; });
      allLatLngs = allLatLngs.concat(latlngs);
      var pl = L.polyline(latlngs, { color: '#4f6814', weight: 3 }).addTo(map);
      polylines.push(pl);
    });

    if (allLatLngs.length > 0) {
      map.fitBounds(L.latLngBounds(allLatLngs), { padding: [20, 20] });
    }

    setTimeout(function () {
      map.invalidateSize();
      if (allLatLngs.length > 0) {
        map.fitBounds(L.latLngBounds(allLatLngs), { padding: [20, 20] });
      }
    }, 0);
  }

  function hidePreview() {
    var panel = document.getElementById('gpx-preview');
    var card = document.getElementById('upload-card');
    if (panel) panel.style.display = 'none';
    if (card) card.classList.remove('has-preview');
  }

  function init() {
    var input = document.getElementById('gpx-input');
    var fileNameEl = document.getElementById('file-name');
    var mapContainer = document.getElementById('preview-map');
    if (!input || !mapContainer) return;

    var tileUrl = mapContainer.getAttribute('data-tile-url') || '';

    input.addEventListener('change', function () {
      if (!input.files || !input.files[0]) {
        hidePreview();
        fileNameEl.textContent = '';
        return;
      }

      var file = input.files[0];
      fileNameEl.textContent = file.name;

      var reader = new FileReader();
      reader.onload = function (e) {
        var data = parseGPX(e.target.result);
        if (data) {
          showPreview(data, tileUrl);
        } else {
          hidePreview();
        }
      };
      reader.readAsText(file);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
