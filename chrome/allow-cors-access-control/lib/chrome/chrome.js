var app = {};

app.version = function () {return chrome.runtime.getManifest().version};
app.homepage = function () {return chrome.runtime.getManifest().homepage_url};

app.hotkey = function (callback) {
  chrome.commands.onCommand.addListener(function (e) {
    if (e === "toggle-default-mode") {
      callback("_mode");
    }
  });
};

app.webrequest = {
  "listener": function () {
    chrome.webRequest.onBeforeRedirect.removeListener(core.listener.before.redirect);
    chrome.webRequest.onHeadersReceived.removeListener(core.listener.headers.received);
    chrome.webRequest.onBeforeSendHeaders.removeListener(core.listener.before.send.headers);
    /*  */
    if (config.addon.state === "ON") {
      chrome.webRequest.onBeforeRedirect.addListener(core.listener.before.redirect, config.addon.URLS);
      chrome.webRequest.onHeadersReceived.addListener(core.listener.headers.received, config.addon.URLS, config.addon.OPTIONS.response);
      chrome.webRequest.onBeforeSendHeaders.addListener(core.listener.before.send.headers, config.addon.URLS, config.addon.OPTIONS.request);
    }
  }
};

app.button = {
  "title": function (text) {chrome.browserAction.setTitle({"title": text})},
  "badge": function (state) {
    chrome.browserAction.setIcon({
      "path": {
        "16": "../../data/icons" + (state ? '/' + state : '') + "/16.png",
        "32": "../../data/icons" + (state ? '/' + state : '') + "/32.png",
        "48": "../../data/icons" + (state ? '/' + state : '') + "/48.png",
        "64": "../../data/icons" + (state ? '/' + state : '') + "/64.png"
      }
    });
  }
};

app.origin = function (url) {
  if (url) {
    var path = url.split('/');
    if (path && path.length) {
      var protocol = path[0];
      var hostname = path[2];
      return protocol + "//" + hostname;
    }
  }
  /*  */
  return '*';
};

app.hostname = function (url) {
  url = url ? url.replace("www.", '') : url;
  var s = url.indexOf("//") + 2;
  if (s > 1) {
    var o = url.indexOf('/', s);
    if (o > 0) return url.substring(s, o);
    else {
      o = url.indexOf('?', s);
      if (o > 0) return url.substring(s, o);
      else return url.substring(s);
    }
  } else return url;
};

app.tab = {
  "options": {"page": function () {chrome.runtime.openOptionsPage()}},
  "open": function (url) {chrome.tabs.create({"url": url, "active": true})},
  "closed": function (callback) {chrome.tabs.onRemoved.addListener(callback)},
  "checkURL": function (tab, callback) {
    if (tab.url) callback(tab);
    else {
      chrome.tabs.executeScript(tab.id, {"code": "document.location.href"}, function (result) {
        var error = chrome.runtime.lastError;
        if (result && result.length) {
          tab.url = result[0];
        }
        /*  */
        callback(tab);
      });
    }
  },
  "active": {
    "reload": function () {chrome.tabs.reload({"bypassCache": true})},
    "query": function (callback) {
      chrome.tabs.query({"currentWindow": true, "active": true}, function (tabs) {
        if (tabs && tabs.length) {        
          app.tab.checkURL(tabs[0], function (tab) {
            if (tab && tab.url) {
              callback(tab);
            }
          });
        }
      });
    }
  }
};

if (!navigator.webdriver) {
  chrome.runtime.setUninstallURL(app.homepage() + "?v=" + app.version() + "&type=uninstall", function () {});
  chrome.runtime.onInstalled.addListener(function (e) {
    chrome.management.getSelf(function (result) {
      if (result.installType === "normal") {
        window.setTimeout(function () {
          var previous = e.previousVersion !== undefined && e.previousVersion !== app.version();
          var doupdate = previous && parseInt((Date.now() - config.welcome.lastupdate) / (24 * 3600 * 1000)) > 45;
          if (e.reason === "install" || (e.reason === "update" && doupdate)) {
            var parameter = (e.previousVersion ? "&p=" + e.previousVersion : '') + "&type=" + e.reason;
            app.tab.open(app.homepage() + "?v=" + app.version() + parameter);
            config.welcome.lastupdate = Date.now();
          }
        }, 3000);
      }
    });
  });
}

app.storage = (function () {
  var objs = {};
  window.setTimeout(function () {
    chrome.storage.local.get(null, function (o) {
      objs = o;
      var script = document.createElement("script");
      script.src = "../common.js";
      document.body.appendChild(script);
    });
  }, 0);
  /*  */
  return {
    "read": function (id) {return objs[id]},
    "write": function (id, data) {
      var tmp = {};
      tmp[id] = data;
      objs[id] = data;
      chrome.storage.local.set(tmp, function () {});
    }
  }
})();

app.popup = (function () {
  var tmp = {};
  chrome.runtime.onMessage.addListener(function (request, sender, sendeponse) {
    for (var id in tmp) {
      if (tmp[id] && (typeof tmp[id] === "function")) {
        if (request.path === "popup-to-background") {
          if (request.method === id) tmp[id](request.data);
        }
      }
    }
  });
  /*  */
  return {
    "receive": function (id, callback) {tmp[id] = callback},
    "send": function (id, data) {
      chrome.runtime.sendMessage({"path": "background-to-popup", "method": id, "data": data});
    }
  }
})();

app.options = (function () {
  var tmp = {};
  chrome.runtime.onMessage.addListener(function (request, sender, sendeponse) {
    for (var id in tmp) {
      if (tmp[id] && (typeof tmp[id] === "function")) {
        if (request.path === "options-to-background") {
          if (request.method === id) tmp[id](request.data);
        }
      }
    }
  });
  /*  */
  return {
    "receive": function (id, callback) {tmp[id] = callback},
    "send": function (id, data) {
      chrome.runtime.sendMessage({"path": "background-to-options", "method": id, "data": data});
    }
  }
})();
