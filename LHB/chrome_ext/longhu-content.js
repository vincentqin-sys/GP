
temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.setAttribute('charset', "UTF-8");
temp.src = chrome.extension.getURL('longhu-name-parse.js');
temp.async = false;
document.documentElement.appendChild(temp);


temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.setAttribute('charset', "UTF-8");
temp.src = chrome.extension.getURL('longhu-data-parse.js');
temp.async = false;
document.documentElement.appendChild(temp);