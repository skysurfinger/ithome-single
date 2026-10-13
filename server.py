# -*- coding: utf-8 -*-
"""
IT之家单列版 · 本地刷新服务
- 双击 start.bat 或 python server.py 启动
- 浏览器打开 http://127.0.0.1:18734
- 页面上的"刷新"按钮会实时重新抓取 IT之家 首页内容
- 仅标准库，无第三方依赖
"""
import json
import os
import re
import sys
import time
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 18734
CACHE_TTL = 45  # 秒

_UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

_cache = {'data': None, 'ts': 0, 'lock': threading.Lock()}


def http_get(url):
    req = Request(url, headers=_UA)
    with urlopen(req, timeout=25) as r:
        return r.read()


def fetch_text(url):
    return http_get(url).decode('utf-8-sig', 'ignore')


def clean_html(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&thinsp;', ' ').replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', s).strip()


def parse_news_items(html):
    """所有 ul.nl 的 li，平铺为单列（保持原时间顺序）"""
    items = []
    for ul in re.finditer(r'<ul class="nl">(.*?)</ul>', html, re.S):
        for li in re.findall(r'<li[^>]*>(.*?)</li>', ul.group(1), re.S):
            a = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', li, re.S)
            if not a:
                continue
            url = a.group(1)
            title = clean_html(a.group(2))
            b = re.search(r'<b[^>]*>(.*?)</b>', li, re.S)
            time_txt = clean_html(b.group(1)) if b else ''
            ad = bool(re.search(r'<b[^>]*class=[\'\"]ad[\'\"]', li))
            if title and url:
                items.append({'t': title, 'u': url, 's': time_txt, 'ad': ad})
    seen, out = set(), []
    for it in items:
        if it['t'] in seen:
            continue
        seen.add(it['t'])
        out.append(it)
    return out


def parse_ranks(html):
    """榜单：日榜/周榜/月榜"""
    ranks = {'day': [], 'week': [], 'month': []}
    for ul in re.finditer(r'<ul class="bd order(?: sel)?" id="d-(\d)">(.*?)</ul>', html, re.S):
        key = {'1': 'day', '2': 'week', '3': 'month'}.get(ul.group(1))
        if not key:
            continue
        for li in re.findall(r'<li>(.*?)</li>', ul.group(2), re.S):
            a = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', li, re.S)
            if a:
                ranks[key].append({'t': clean_html(a.group(2)), 'u': a.group(1)})
    return ranks
    seg = m.group(1)
    for ul in re.finditer(r'<ul class="bd order(?: sel)?" id="d-(\d)">(.*?)</ul>', seg, re.S):
        key = {'1': 'day', '2': 'week', '3': 'month'}.get(ul.group(1))
        if not key:
            continue
        for li in re.findall(r'<li>(.*?)</li>', ul.group(2), re.S):
            a = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', li, re.S)
            if a:
                ranks[key].append({'t': clean_html(a.group(2)), 'u': a.group(1)})
    return ranks


def parse_rmsoft(html):
    """软媒产品 + 常用资源"""
    products, resources = [], []
    for ul in re.finditer(r'<ul class="(?:sel )?bd rmsoft" id="d-(\d)">(.*?)</ul>', html, re.S):
        target = products if ul.group(1) == '1' else resources
        for li in re.findall(r'<li>(.*?)</li>', ul.group(2), re.S):
            img = re.search(r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]+)"', li)
            name = re.search(r'<p class="pro-name"><a href="([^"]+)"[^>]*>(.*?)</a></p>', li, re.S)
            btn = re.search(r'class="down_btn"[^>]*href="([^"]+)"', li)
            if name:
                target.append({
                    'icon': img.group(2) if img else '',
                    'name': clean_html(name.group(2)),
                    'url': name.group(1),
                    'btn': btn.group(1) if btn else name.group(1),
                })
    return products, resources


def parse_focus(html):
    items = []
    m = re.search(r'id="focus-owl-wrap"[^>]*>(.*?)</div>\s*</div>', html, re.S)
    seg = m.group(1) if m else html
    for a in re.finditer(r'<a href="([^"]+)"[^>]*>(.*?)</a>', seg, re.S):
        img = re.search(r'data-src="([^"]+)"[^>]*alt="([^"]+)"', a.group(2))
        if img:
            items.append({'u': a.group(1), 'img': img.group(1), 'alt': img.group(2)})
    return items


def fetch_news():
    """抓取并解析首页全部数据"""
    html = fetch_text('https://www.ithome.com/')
    data = {
        'ts': int(time.time()),
        'news': parse_news_items(html),
        'ranks': parse_ranks(html),
        'products': [], 'resources': [],
        'focus': parse_focus(html),
        'tt': [], 'hot': [], 'today': '',
    }
    data['products'], data['resources'] = parse_rmsoft(html)

    m = re.search(r'<div id="tt"[^>]*>(.*?)</div>', html, re.S)
    if m:
        for a in re.finditer(r'<a href="([^"]+)"[^>]*class="tt\d+"[^>]*>(.*?)</a>', m.group(1), re.S):
            data['tt'].append({'u': a.group(1), 't': clean_html(a.group(2))})

    try:
        hot_raw = fetch_text('https://api.ithome.com/api/newssearch/gethotwords?callback=keywordcallback')
        data['hot'] = re.findall(r'"keyword"\s*:\s*"([^"]+)"', hot_raw)
    except Exception:
        data['hot'] = []

    try:
        data['today'] = fetch_text('https://www.ithome.com/home/gettodaydata').strip()
    except Exception:
        data['today'] = ''

    return data


def get_data():
    with _cache['lock']:
        now = time.time()
        if _cache['data'] and (now - _cache['ts']) < CACHE_TTL:
            return _cache['data']
    try:
        data = fetch_news()
    except Exception as e:
        with _cache['lock']:
            if _cache['data']:
                data = dict(_cache['data'])
                data['ts'] = int(time.time())
                data['note'] = '抓取失败，已返回上次缓存：%s' % e
            else:
                data = {'error': '抓取失败: %s' % e, 'ts': int(time.time()), 'news': [], 'hot': [], 'today': ''}
    with _cache['lock']:
        _cache['data'] = data
        _cache['ts'] = time.time()
    return data


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == '/api/news':
            data = get_data()
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == '/':
            path = '/index.html'
        return super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write('[server] %s\n' % (fmt % args))


def open_browser():
    time.sleep(1.0)
    try:
        import webbrowser
        webbrowser.open('http://127.0.0.1:%d' % PORT)
    except Exception:
        pass


if __name__ == '__main__':
    print('=' * 46)
    print(' IT之家单列版 · 本地刷新服务')
    print(' 地址: http://127.0.0.1:%d' % PORT)
    print(' 提示: 页面上的"刷新"按钮会实时重新抓取')
    print('=' * 46)
    threading.Thread(target=open_browser, daemon=True).start()
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')