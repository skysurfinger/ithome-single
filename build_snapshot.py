# -*- coding: utf-8 -*-
"""抓取最新数据并嵌入 index.html（快照兜底），本地与定时任务通用"""
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))
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
new_html, n = re.subn(r'const SNAPSHOT = .*?;\n', 'const SNAPSHOT = ' + snapshot_json + ';\n', html, count=1, flags=re.S)
if n != 1:
    raise SystemExit('index.html 中未找到 SNAPSHOT 定义')
html = new_html
open(html_path, 'w', encoding='utf-8').write(html)
print('已写入快照 → index.html (%d KB)' % (len(html) // 1024))