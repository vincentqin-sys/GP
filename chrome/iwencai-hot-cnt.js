let temp = document.createElement('script');
temp.setAttribute('type', 'text/javascript');
temp.src = chrome.extension.getURL('ajax-hook.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type', 'text/javascript');
temp.src = chrome.extension.getURL('iwencai-hot-inject.js');
temp.async = false;
document.documentElement.appendChild(temp);


window.addEventListener("message", function (evt) {
    console.log('Recevie Inject Message: ', evt.data);
    chrome.runtime.sendMessage(evt.data);
}, false);