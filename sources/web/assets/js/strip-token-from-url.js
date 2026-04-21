/**
 * Убирает access_token из hash URL сразу при загрузке страницы.
 * Keycloak (и другие OAuth) возвращают токен в fragment (#access_token=...).
 * Мы сохраняем токен в localStorage и убираем его из адресной строки.
 * Подключать первым в <head>, без type="module", чтобы выполнился до отрисовки.
 */
(function () {
  var hash = window.location.hash;
  if (!hash || hash.indexOf("access_token=") === -1) return;
  var match = /(?:^|&)access_token=([^&]+)/.exec(hash);
  if (match) {
    try {
      var token = decodeURIComponent(match[1]);
      if (token) window.localStorage.setItem("access_token", token);
    } catch (e) {}
    var clean = window.location.pathname + window.location.search;
    window.history.replaceState(null, "", clean);
  }
})();
