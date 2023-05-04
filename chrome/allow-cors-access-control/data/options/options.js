var background = (function () {
  var tmp = {};
  chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    for (var id in tmp) {
      if (tmp[id] && (typeof tmp[id] === "function")) {
        if (request.path === "background-to-options") {
          if (request.method === id) tmp[id](request.data);
        }
      }
    }
  });
  /*  */
  return {
    "receive": function (id, callback) {tmp[id] = callback},
    "send": function (id, data) {chrome.runtime.sendMessage({"path": "options-to-background", "method": id, "data": data})}
  }
})();

background.receive("storage", function (e) {
  var origin = {};
  var methods = document.getElementById("methods");
  var headers = document.getElementById("headers");
  origin.all = document.getElementById("origin-all");
  origin.top = document.getElementById("origin-top");
  var redirect = document.getElementById("redirect");
  var whitelist = document.getElementById("whitelist");
  var credentials = document.getElementById("credentials");
  /*  */
  origin.top.checked = true;
  methods.value = e.methods;
  headers.checked = e.headers;
  origin.all.checked = e.origin;
  redirect.checked = e.redirect;
  credentials.checked = e.credentials;
  whitelist.value = e.whitelist.join(', ');
});

var load = function () {
  var origin = {};
  var methods = document.getElementById("methods");
  var headers = document.getElementById("headers");
  origin.top = document.getElementById("origin-top");
  origin.all = document.getElementById("origin-all");
  var redirect = document.getElementById("redirect");
  var whitelist = document.getElementById("whitelist");
  var credentials = document.getElementById("credentials");
  /*  */
  headers.addEventListener("change", function (e) {background.send("headers", e.target.checked)});
  redirect.addEventListener("change", function (e) {background.send("redirect", e.target.checked)});
  origin.top.addEventListener("change", function () {background.send("origin", origin.all.checked)});
  origin.all.addEventListener("change", function () {background.send("origin", origin.all.checked)});
  credentials.addEventListener("change", function (e) {background.send("credentials", e.target.checked)});
  methods.addEventListener("change", function (e) {
    var value = "GET, PUT, POST, DELETE, HEAD, OPTIONS";
    if (e.target.value) value = e.target.value.split(',').map(e => e.trim().toLocaleUpperCase()).join(', ');
    background.send("methods", value);
    e.target.value = value;
  });
  /*  */
  whitelist.addEventListener("change", function (e) {
    var domains = [];
    if (e.target.value) {
      var tmp = e.target.value;
      domains = tmp.split(',').map(e => e.trim());
      e.target.value = domains.join(', ');
    }
    /*  */
    background.send("whitelist", domains);
  });
  /*  */
  background.send("load");
  window.removeEventListener("load", load, false);
};

window.addEventListener("load", load, false);
