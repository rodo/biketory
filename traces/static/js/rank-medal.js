(function () {
  'use strict';

  var medals = {
    1: '/static/img/medal-gold.svg',
    2: '/static/img/medal-silver.svg',
    3: '/static/img/medal-bronze.svg'
  };

  /**
   * Return HTML for a rank cell: medal image for top 3, plain number otherwise.
   */
  window.rankMedalHtml = function (rank) {
    var html = String(rank);
    if (medals[rank]) {
      html += ' <img class="medal" src="' + medals[rank] + '" alt="" width="18" height="18">';
    }
    return html;
  };
})();
