#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱看机器人（ikanbot）Yingxia/TVBox Spider 适配版
基于原仓库 GPL-3.0 代码移植；请保留 GPL-3.0 许可声明。
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import gzip
import zlib
from html.parser import HTMLParser

try:
    from base.spider import Spider as SpiderBase
except Exception:
    class SpiderBase(object):
        def __init__(self): pass


HOSTS = (
    "https://www1.ikanbot.com",  # 首选域名
    "https://www.ikanbot.com",   # 备用域名
)
BASE = HOSTS[0]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
PAGE_SIZE = 36
MAX_LINES = 40
LINE_TTL = 600

CATEGORIES = [
    ("movie-热门", "热门电影"),
    ("tv-热门", "热门剧集"),
    ("tv-国产剧", "国产剧"),
    ("tv-日剧", "日剧"),
    ("tv-韩剧", "韩剧"),
    ("tv-美剧", "美剧"),
    ("tv-英剧", "英剧"),
    ("tv-港剧", "港剧"),
    ("tv-日本动画", "日本动画"),
    ("tv-综艺", "综艺"),
    ("tv-纪录片", "纪录片"),
]


def clean(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip()


def fix_url(value):
    value = clean(value)
    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("http://", "https://")):
        return ""
    value = value.replace(r"\/", "/")
    return re.sub(r"^(https?://)img9\.doubanio\.com/",
                  r"\1img3.doubanio.com/", value, flags=re.I)


def numeric_id(value):
    return bool(re.fullmatch(r"\d{1,12}", str(value or "").strip())) and int(value) > 0


class Node:
    def __init__(self, tag="", attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []
        self.text = ""

    def all(self):
        out, stack = [], [self]
        while stack:
            node = stack.pop()
            out.append(node)
            stack.extend(reversed(node.children))
        return out

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def text_content(self):
        parts = [self.text]
        for child in self.children:
            parts.append(child.text_content())
        return "".join(parts)


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower(), attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag.lower() not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].text += data


def parse_tree(source):
    parser = TreeParser()
    try:
        parser.feed(source or "")
    except Exception:
        pass
    return parser.root


def first(nodes, predicate):
    for node in nodes:
        if predicate(node):
            return node
    return None


def sign_token(current_id, token):
    cid, rest = str(current_id or ""), str(token or "")
    if len(cid) < 4 or len(rest) < 16:
        return ""
    out = ""
    for ch in cid[-4:]:
        if not ch.isdigit():
            return ""
        start = int(ch) % 3 + 1
        if start + 8 > len(rest):
            return ""
        out += rest[start:start + 8]
        rest = rest[start + 8:]
    return out


def split_episodes(raw):
    result = []
    for part in str(raw or "").split("#"):
        part = part.strip()
        if "$" not in part:
            continue
        name, address = part.split("$", 1)
        address = address.split("$", 1)[0].strip()
        if address:
            result.append((clean(name), address))
    return result


def valid_media_url(value):
    value = fix_url(value)
    if not value:
        return ""
    if not re.search(r"\.(m3u8|mp4|ts)(\?|$|#)", value, re.I) and ".m3u8" not in value.lower():
        return ""
    try:
        p = urllib.parse.urlsplit(value)
        if not p.hostname or p.username or p.password:
            return ""
    except Exception:
        return ""
    return value


def quality(flag):
    m = re.search(r"(2160|1440|1080|720|480)", str(flag or ""), re.I)
    return int(m.group(1)) if m else 0


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = BASE
        self.siteName = "爱看机器人"
        self._active_host = BASE
        self._configured_host = ""
        self._lines_cache = {}
        self._sid_hosts = {}
        self._ua = UA

    def init(self, extend=""):
        host = ""
        if isinstance(extend, dict):
            host = extend.get("host", "")
        elif extend:
            try:
                obj = json.loads(extend)
                if isinstance(obj, dict):
                    host = obj.get("host", "")
            except Exception:
                host = str(extend).strip()
        if host:
            host = str(host).strip().rstrip("/")
            if not host.startswith(("http://", "https://")):
                host = "https://" + host
            try:
                parsed = urllib.parse.urlsplit(host)
                if parsed.hostname:
                    self._configured_host = host
                    self._active_host = host
                    self.siteUrl = host
            except Exception:
                pass
        return True

    def _host_candidates(self, preferred=None):
        """返回本次操作可尝试的域名，根域名不参与自动轮换。"""
        configured = self._configured_host
        if configured:
            # 用户显式传入非标准域名时，尊重其配置，不擅自改用其他站点。
            if configured not in HOSTS:
                return [configured]
            first_host = preferred or configured
        else:
            first_host = preferred or self._active_host or BASE

        candidates = [first_host]
        candidates.extend(h for h in HOSTS if h != first_host)
        result = []
        for host in candidates:
            host = str(host or "").rstrip("/")
            if host and host not in result:
                result.append(host)
        return result

    def getName(self):
        return self.siteName

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|ts|mpd)(\?|$)", str(url or ""), re.I))

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, referer=None, as_json=False, host=None):
        base = str(host or self.siteUrl or BASE).rstrip("/")
        if url.startswith("/"):
            url = base + url
        if referer and str(referer).startswith("/"):
            referer = base + str(referer)
        headers = {
            "User-Agent": self._ua,
            "Referer": referer or base + "/",
            "Accept": "application/json, text/plain, */*" if as_json else
                      "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    try:
                        raw = zlib.decompress(raw)
                    except Exception:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                return raw.decode("utf-8", "ignore"), resp.getcode()
        except Exception:
            return "", 0

    def _fetch_failover(self, path, referer=None, as_json=False, preferred=None):
        """普通页面/API请求的域名故障切换；成功后记住可用入口。"""
        last_code = 0
        for host in self._host_candidates(preferred):
            body, code = self._fetch(path, referer=referer, as_json=as_json, host=host)
            last_code = code
            if code == 200 and body:
                self._active_host = host
                self.siteUrl = host
                return body, code, host
        return "", last_code, self._active_host

    def _parse_cards(self, root, category=""):
        items, seen = [], set()
        for card in root.all():
            if not card.has_class("item"):
                continue
            m = re.match(r"^/play/(\d+)", card.attrs.get("href", ""))
            if not m or not numeric_id(m.group(1)):
                continue
            sid = m.group(1)
            if sid in seen:
                continue
            nodes = card.all()
            img = first(nodes, lambda n: n.tag == "img")
            title = clean(img.attrs.get("alt", "")) if img else ""
            if not title:
                p = first(nodes, lambda n: n.tag == "p")
                title = clean(p.text_content()) if p else ""
            if not title:
                continue
            seen.add(sid)
            cover = fix_url((img.attrs.get("data-src") or img.attrs.get("src")) if img else "")
            kind = "电影" if str(category).startswith("movie-") else "剧集"
            items.append({
                "vod_id": sid, "vod_name": title, "vod_pic": cover,
                "vod_remarks": "", "type_name": kind,
                "style": {"type": "rect", "ratio": 0.67}
            })
            if len(items) >= 500:
                break
        return items

    def _parse_search(self, root):
        items, seen = [], set()
        for block in root.all():
            if not block.has_class("media"):
                continue
            nodes = block.all()
            link = first(nodes, lambda n: n.tag == "a" and n.has_class("title-text")
                         and re.match(r"^/play/(\d+)", n.attrs.get("href", "")))
            if not link:
                continue
            m = re.match(r"^/play/(\d+)", link.attrs.get("href", ""))
            sid = m.group(1)
            if sid in seen:
                continue
            title = clean(link.text_content())
            img = first(nodes, lambda n: n.tag == "img")
            if not title and img:
                title = clean(img.attrs.get("alt", ""))
            if not title:
                continue
            seen.add(sid)
            label = first(nodes, lambda n: n.has_class("label"))
            small = first(nodes, lambda n: n.has_class("small"))
            items.append({
                "vod_id": sid, "vod_name": title,
                "vod_pic": fix_url((img.attrs.get("data-src") or img.attrs.get("src")) if img else ""),
                "vod_remarks": clean(label.text_content()) if label else "",
                "vod_content": clean(small.text_content()) if small else "",
                "style": {"type": "rect", "ratio": 0.67}
            })
            if len(items) >= 100:
                break
        return items

    def homeContent(self, filter):
        return {"class": [{"type_id": x, "type_name": n} for x, n in CATEGORIES]}

    def homeVideoContent(self):
        html_text, _, _ = self._fetch_failover("/hot/index-movie-%E7%83%AD%E9%97%A8.html")
        return {"list": self._parse_cards(parse_tree(html_text), "movie-热门")}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        valid = dict(CATEGORIES)
        if str(tid) not in valid:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}
        category = str(tid)
        path = "/hot/index-" + urllib.parse.quote(category, safe="-") + (
            "-p-" + str(page) if page > 1 else "") + ".html"
        body, _, _ = self._fetch_failover(path)
        items = self._parse_cards(parse_tree(body), category)
        max_page = page
        for p in re.findall(r"-p-(\d+)\.html", body):
            try:
                max_page = max(max_page, int(p))
            except Exception:
                pass
        pagecount = max_page if max_page > page else (page + 1 if len(items) >= PAGE_SIZE else page)
        return {"page": page, "pagecount": pagecount, "limit": PAGE_SIZE,
                "total": pagecount * PAGE_SIZE, "list": items}

    def searchContent(self, key, quick, pg="1"):
        keyword = str(key or "").strip()
        try:
            page = int(pg)
        except Exception:
            page = 1
        if not keyword or page > 1:
            return {"page": page, "pagecount": 1, "limit": 100, "total": 0, "list": []}
        path = "/search?q=" + urllib.parse.quote(keyword)
        body, _, _ = self._fetch_failover(path)
        return {"page": 1, "pagecount": 1, "limit": 100,
                "total": 0, "list": self._parse_search(parse_tree(body))}

    def _parse_play_page(self, body, source_id):
        root = parse_tree(body)
        nodes = root.all()
        title_node = first(nodes, lambda n: n.tag == "h1" and n.attrs.get("id") == "video_title")
        title = clean(title_node.text_content()) if title_node else ""
        if not title:
            raise ValueError("详情页缺少影片名称")
        cover_node = first(nodes, lambda n: n.tag == "img" and n.has_class("cover") and n.attrs.get("data-src"))
        if not cover_node:
            cover_node = first(nodes, lambda n: n.tag == "img" and n.attrs.get("data-src"))
        cover = fix_url((cover_node.attrs.get("data-src") if cover_node else "") or "")
        def hidden(name):
            node = first(nodes, lambda n: n.tag == "input" and n.attrs.get("id") == name)
            return (node.attrs.get("value", "").strip() if node else "")
        current_id = hidden("current_id") or source_id
        token = hidden("e_token")
        mtype = hidden("mtype") or "1"
        if not token:
            raise ValueError("详情页缺少播放令牌")
        metas = [n for n in nodes if n.tag == "h3" and n.has_class("meta")]
        texts = [clean(n.text_content()) for n in metas if clean(n.text_content())]
        return {"title": title, "cover": cover, "current_id": current_id,
                "token": token, "mtype": mtype, "texts": texts,
                "desc": " · ".join(texts)}

    def _fetch_lines(self, source_id, meta, host=None):
        base = str(host or self.siteUrl or BASE).rstrip("/")
        signed = sign_token(meta["current_id"], meta["token"])
        if not signed:
            raise ValueError("播放令牌签名失败")
        query = urllib.parse.urlencode({
            "videoId": meta["current_id"], "mtype": meta["mtype"], "token": signed
        })
        url = base + "/api/getResN?" + query
        body, code = self._fetch(url, referer=base + "/play/" + source_id,
                                 as_json=True, host=base)
        if code != 200 or not body:
            raise ValueError("线路接口请求失败")
        payload = json.loads(body)
        if payload.get("state") != 1:
            raise ValueError("线路获取失败：" + clean(payload.get("message", "unauthorized")))
        lines, seen = [], set()
        data = payload.get("data") or {}
        for item in data.get("list") or []:
            try:
                entries = json.loads(str(item.get("resData") or "[]"))
            except Exception:
                continue
            for entry in entries or []:
                episodes, orders, signature = [], set(), []
                for idx, (name, raw_url) in enumerate(split_episodes(entry.get("url", "")), 1):
                    address = valid_media_url(raw_url)
                    if not address:
                        continue
                    m = re.search(r"(\d+)", name)
                    order = int(m.group(1)) if m and 0 < int(m.group(1)) <= 100000 else idx
                    if order in orders:
                        continue
                    orders.add(order)
                    episodes.append({"name": name, "url": address, "order": order})
                    signature.append(address)
                sig = "\n".join(signature)
                if episodes and sig not in seen:
                    seen.add(sig)
                    lines.append({"flag": clean(entry.get("flag", "")), "episodes": episodes})
        lines.sort(key=lambda x: len(x["episodes"]), reverse=True)
        return lines[:MAX_LINES]

    def _load_play_bundle(self, sid, preferred_host=None):
        """在单一域名内完成详情页与线路 API，失败才整体切换备用域名。"""
        cached = self._lines_cache.get(sid)
        remembered = self._sid_hosts.get(sid)
        preferred = preferred_host or remembered
        if not preferred and cached and len(cached) > 2:
            preferred = cached[2]

        errors = []
        for host in self._host_candidates(preferred):
            try:
                body, code = self._fetch("/play/" + sid, host=host)
                if code != 200 or not body:
                    raise ValueError("详情页请求失败")
                meta = self._parse_play_page(body, sid)

                cached = self._lines_cache.get(sid)
                if cached and cached[0] > time.time() and len(cached) > 2 and cached[2] == host:
                    lines = cached[1]
                else:
                    lines = self._fetch_lines(sid, meta, host=host)
                    if not lines:
                        raise ValueError("该域名未返回有效播放线路")
                    self._lines_cache[sid] = (time.time() + LINE_TTL, lines, host)

                if not lines:
                    raise ValueError("该域名未返回有效播放线路")
                self._active_host = host
                self.siteUrl = host
                self._sid_hosts[sid] = host
                return meta, lines, host
            except Exception as exc:
                errors.append(str(exc) or "请求失败")

        message = errors[-1] if errors else "所有域名均不可用"
        raise ValueError("主域名及备用域名均未能获取播放信息：" + message)

    def detailContent(self, ids):
        sid = str(ids[0] if isinstance(ids, (list, tuple)) else ids or "").strip()
        if not numeric_id(sid):
            return {"list": []}
        try:
            meta, lines, _ = self._load_play_bundle(sid)
        except Exception:
            return {"list": []}
        if not lines:
            return {"list": []}
        play_from, play_url = [], []
        for line_index, line in enumerate(lines):
            # 客户端统一显示为“线路1、线路2……”。原始 entry.flag 保留在
            # line["flag"] 中，供 playerContent 的画质识别使用，不对播放地址做改动。
            display_name = "线路%d" % (line_index + 1)
            episodes = []
            for ep in line["episodes"]:
                episodes.append("%s$%s@@%s@@%s" %
                                (ep["name"] or ("第%d集" % ep["order"]), sid,
                                 line_index, ep["order"]))
            play_from.append(display_name)
            play_url.append("#".join(episodes))
        texts = meta["texts"]
        year = next((x for x in texts if re.fullmatch(r"(19|20)\d{2}", x)), "")
        tags = [x for x in texts if "/" in x]
        vod = {
            "vod_id": sid, "vod_name": meta["title"],
            "vod_pic": meta["cover"], "vod_bg": meta["cover"],
            "vod_actor": "", "vod_director": "",
            "vod_remarks": str(len(lines[0]["episodes"])) + "集",
            "vod_content": meta["desc"],
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }
        if year:
            vod["vod_year"] = year
        if tags:
            vod["vod_class"] = "/".join(tags)
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        try:
            sid, line_s, order_s = str(id or "").split("@@")
            if not numeric_id(sid):
                raise ValueError()
            line_index, order = int(line_s), int(order_s)
            meta, lines, host = self._load_play_bundle(
                sid, preferred_host=self._sid_hosts.get(sid)
            )
            if line_index < 0 or line_index >= len(lines):
                raise ValueError("线路不存在")
            selected = None
            for ep in lines[line_index]["episodes"]:
                if ep["order"] == order:
                    selected = ep
                    break
            if not selected:
                raise ValueError("该线路没有对应集数")
            q = quality(lines[line_index]["flag"])
            result = {"parse": 0, "jx": 0, "url": selected["url"],
                      "header": {"User-Agent": self._ua,
                                 "Referer": host + "/play/" + sid}}
            if q:
                result["quality"] = q
            return result
        except Exception as e:
            return {"parse": 1, "jx": 0, "url": "", "msg": str(e) or "播放地址解析失败"}

    def action(self, action):
        return {}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]

    def destroy(self):
        self._lines_cache.clear()
        self._sid_hosts.clear()
