/* admin-toggle-zone.js — toggle active/inactive status for geozones */

/**
 * @param {Object} config
 * @param {string} config.selector      - CSS selector for toggle buttons
 * @param {string} config.urlTemplate   - URL with /0/ as PK placeholder
 * @param {string} config.csrfToken     - CSRF token
 * @param {string} config.activeText    - translated "Active"
 * @param {string} config.inactiveText  - translated "Inactive"
 * @param {string} config.activateText  - translated "Activate"
 * @param {string} config.deactivateText - translated "Deactivate"
 * @param {Function} [config.findBadge] - given (btn, pk), return the badge element
 */
function initZoneToggle(config) {
  var defaultFindBadge = function(btn, pk) {
    var row = document.querySelector('tr[data-zone-id="' + pk + '"]');
    return row ? row.querySelector('.status-badge') : null;
  };
  var findBadge = config.findBadge || defaultFindBadge;

  document.querySelectorAll(config.selector).forEach(function(btn) {
    btn.addEventListener('click', function() {
      var pk = this.dataset.pk;
      var url = config.urlTemplate.replace('/0/', '/' + pk + '/');

      fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': config.csrfToken,
          'Content-Type': 'application/json',
        },
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var badge = findBadge(btn, pk);
        if (!badge) return;

        var baseClass = badge.className.replace(/badge-active|badge-inactive/g, '').trim();
        if (data.active) {
          badge.className = baseClass ? baseClass + ' badge-active' : 'badge-active';
          badge.textContent = config.activeText;
          btn.textContent = config.deactivateText;
        } else {
          badge.className = baseClass ? baseClass + ' badge-inactive' : 'badge-inactive';
          badge.textContent = config.inactiveText;
          btn.textContent = config.activateText;
        }
      });
    });
  });
}
