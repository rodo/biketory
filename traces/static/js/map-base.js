/* map-base.js — shared Leaflet map utilities */

const STYLE_ROUTE = { color: '#e74c3c', weight: 3, opacity: 0.9 };

const STYLE_SURFACES = {
  color: '#2980b9', weight: 2, opacity: 0.9,
  fillColor: '#2980b9', fillOpacity: 0.3,
};

const STYLE_HEXAGONS_OWN = {
  color: '#2980b9', weight: 1, opacity: 0.7,
  fillColor: '#2980b9', fillOpacity: 0.45,
};

const STYLE_HEXAGONS_OTHER = {
  color: '#4f6814', weight: 1, opacity: 0.7,
  fillColor: '#4f6814', fillOpacity: 0.45,
};

/**
 * Read a JSON blob injected via Django's json_script filter.
 * Returns the parsed object, or null if the element is missing.
 */
function readJSON(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

/**
 * Create a Leaflet map with a tile layer.
 *
 * @param {string} elementId  - DOM id of the map container
 * @param {Object} config     - { tileUrl, zoomMin, zoomMax, zoomControl, attribution }
 * @returns {L.Map}
 */
function initMap(elementId, config) {
  const map = L.map(elementId, {
    minZoom: config.zoomMin,
    maxZoom: config.zoomMax,
    zoomControl: config.zoomControl !== false,
    attributionControl: config.attribution !== false,
  });

  const tileOpts = {};
  if (config.attribution !== false) {
    tileOpts.attribution = '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  }

  L.tileLayer(config.tileUrl, tileOpts).addTo(map);
  return map;
}

/**
 * Add a GeoJSON layer to the map if the data is non-empty.
 *
 * @param {L.Map}   map     - Leaflet map instance
 * @param {Object}  geojson - GeoJSON object (Feature or FeatureCollection)
 * @param {Object}  style   - Leaflet path style
 * @param {Object}  [opts]  - { onEachFeature, group }
 * @returns {L.GeoJSON|null} the created layer, or null if data was empty
 */
function addLayer(map, geojson, style, opts) {
  if (!geojson) return null;

  const isCollection = geojson.type === 'FeatureCollection';
  if (isCollection && (!geojson.features || geojson.features.length === 0)) return null;

  const layerOpts = { style: style };
  if (opts && opts.onEachFeature) {
    layerOpts.onEachFeature = opts.onEachFeature;
  }

  const layer = L.geoJSON(geojson, layerOpts);
  const target = (opts && opts.group) ? opts.group : map;
  layer.addTo(target);
  return layer;
}

/**
 * Fit the map to the combined bounds of the given layers,
 * or fall back to a default center/zoom.
 *
 * @param {L.Map}     map
 * @param {L.Layer[]} layers       - non-null layers to include in bounds
 * @param {number[]}  padding      - e.g. [20, 20]
 * @param {number[]}  defaultCenter - e.g. [47.75, -3.37]
 * @param {number}    defaultZoom
 */
function fitOrDefault(map, layers, padding, defaultCenter, defaultZoom) {
  const valid = layers.filter(Boolean);
  if (valid.length > 0) {
    map.fitBounds(L.featureGroup(valid).getBounds(), { padding: padding });
  } else {
    map.setView(defaultCenter, defaultZoom);
  }
}
