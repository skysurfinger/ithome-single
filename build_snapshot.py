# -*- coding: utf-8 -*-
"""抓取最新数据并嵌入 index.html（快照兜底），图片下载到本地 img/ 供 Pages 托管"""
import hashlib
import io
import json
import os
import re
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import server

IMG_DIR = os.path.join(BASE, 'img')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36', 'Referer': 'https://www.ithome.com/'}


def download_img(url):
    """下载图片到 img/，返回相对路径；失败返回原 URL"""
    if not url:
        return url
    try:
        path_part = url.split('?')[0]
        ext = os.path.splitext(path_part)[1] or '.jpg'
        name = hashlib.md5(url.encode()).hexdigest()[:20] + ext
        p = os.path.join(IMG_DIR, name)
        if not os.path.exists(p):
            os.makedirs(IMG_DIR, exist_ok=True)
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 100:
                return url
            with open(p, 'wb') as f:
                f.write(data)
        return 'img/' + name
    except Exception:
        return url


print('抓取 IT之家 首页数据…')
data = server.fetch_news()
print('news=%d hot=%d today=%s focus=%d ranks=%d/%d/%d' % (
    len(data['news']), len(data['hot']), data['today'], len(data['focus']),
    len(data['ranks']['day']), len(data['ranks']['week']), len(data['ranks']['month'])))

# 图片本地化（轮播 + 产品/资源图标）
for f in data['focus']:
    f['img'] = download_img(f.get('img', ''))
for group in ('products', 'resources'):
    for it in data.get(group, []):
        it['icon'] = download_img(it.get('icon', ''))
print('images localized to img/')

snapshot_json = json.dumps(data, ensure_ascii=False)

html_path = os.path.join(BASE, 'index.html')
html = open(html_path, 'r', encoding='utf-8').read()
new_html, n = re.subn(r'const SNAPSHOT = .*?;\n', 'const SNAPSHOT = ' + snapshot_json + ';\n', html, count=1, flags=re.S)
if n != 1:
    raise SystemExit('index.html 中未找到 SNAPSHOT 定义')
html = new_html
open(html_path, 'w', encoding='utf-8').write(html)
print('已写入快照 → index.html (%d KB)' % (len(html) // 1024))