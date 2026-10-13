# -*- coding: utf-8 -*-
"""抓取最新数据并嵌入 index.html（快照兜底），同时用于 GitHub Pages 部署版本"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r"C:\Users\Administrator\.local\share\TeleAgent\TeleAgent的工作空间\IT之家单列版"
sys.path.insert(0, BASE)

import server

print('抓取 IT之家 首页数据…')
data = server.fetch_news()
print('news=%d hot=%d today=%s focus=%d ranks=%d/%d/%d' % (
    len(data['news']), len(data['hot']), data['today'], len(data['focus']),
    len(data['ranks']['day']), len(data['ranks']['week']), len(data['ranks']['month'])))

snapshot_json = json.dumps(data, ensure_ascii=False)

html_path = os.path.join(BASE, 'index.html')
html = open(html_path, 'r', encoding='utf-8').read()
assert '__SNAPSHOT__' in html, 'index.html 缺少 __SNAPSHOT__ 占位符'
html = html.replace('__SNAPSHOT__', snapshot_json)
open(html_path, 'w', encoding='utf-8').write(html)
print('已写入快照 → index.html (%d KB)' % (len(html) // 1024))