/* admin-auto-refresh.js — auto-reload page every 5s for 2 minutes */
(function() {
  var MAX_MS = 2 * 60 * 1000;
  var INTERVAL_MS = 5000;
  var start = Date.now();
  var timer = setInterval(function() {
    if (Date.now() - start >= MAX_MS) {
      clearInterval(timer);
      return;
    }
    location.reload();
  }, INTERVAL_MS);
})();
