/* map-dashboard.js — mini-map on the dashboard page */

(function () {
  var config = readJSON('map-config');
  if (!config) return;

  var map = initMap(config.elementId, config);

  var route    = readJSON('route-geojson');
  var surfaces = readJSON('surfaces-geojson');
  var hexagons = readJSON('hexagons-geojson');

  var layers = [];

  layers.push(addLayer(map, route, STYLE_ROUTE));
  layers.push(addLayer(map, hexagons, STYLE_HEXAGONS_OWN));
  layers.push(addLayer(map, surfaces, STYLE_SURFACES));

  fitOrDefault(map, layers, [20, 20], [47.75, -3.37], 10);
})();
