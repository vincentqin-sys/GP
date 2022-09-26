
temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.setAttribute('charset', "UTF-8");
temp.src = chrome.extension.getURL('longhu.js');
temp.async = false;
document.documentElement.appendChild(temp);
