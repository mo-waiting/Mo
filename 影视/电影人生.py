#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import gzip
import http.cookiejar
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

try:
    from base.spider import Spider as SpiderBase
except Exception:
    class SpiderBase(object):
        def init(self, extend=""):
            pass
        def getName(self):
            return ""
        def isVideoFormat(self, url):
            return False
        def manualVideoCheck(self):
            return False
        def homeContent(self, filter):
            return {}
        def homeVideoContent(self):
            return {}
        def categoryContent(self, tid, pg, filter, extend):
            return {}
        def detailContent(self, ids):
            return {}
        def searchContent(self, key, quick, pg="1"):
            return {}
        def playerContent(self, flag, id, vipFlags):
            return {}
        def action(self, action):
            return {}
        def liveContent(self):
            return ""
        def localProxy(self, params):
            return [404, "text/plain; charset=utf-8", "Proxy not configured"]
        def destroy(self):
            pass
        def getCache(self, key):
            return None
        def setCache(self, key, value):
            return "fail"
        def delCache(self, key):
            return "fail"


def dump_to_shared_folder(filename, content):
    if isinstance(content, (dict, list)):
        body = json.dumps(content, ensure_ascii=False, indent=2)
    else:
        body = str(content)
    target_paths = [
        "/sdcard/Pictures/" + filename,
        "/storage/emulated/0/Pictures/" + filename,
        "/sdcard/Download/" + filename,
        "/storage/emulated/0/Download/" + filename,
        filename
    ]
    for path in target_paths:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            return path
        except Exception:
            continue
    return None


CARD_RE = re.compile(r'<a[^>]*title="([^"]+)"[^>]*data-url="/(tv|movie)/([0-9a-f]+)/([0-9]+)\.html"[^>]*>([\s\S]*?)</a>', re.I)
POSTER_RE = re.compile(r'data-src="/img/id/([0-9a-f]+)\.jpg', re.I)
BADGE_RE = re.compile(r'bg-\[#409EFF\]/90[^>]*>([^<]+)</div>', re.I)
LD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', re.I)
# Capture the visible tab text as well as data-origin and episode count.
TAB_RE = re.compile(
    r'data-origin="([^"]+)"[^>]*id="[^"]*Tab"[^>]*>\s*([\s\S]*?)<span[^>]*>(\d+)</span>', re.I
)
TITLE_RE = re.compile(r'data-title="([^"]+)"', re.I)
API_RE = re.compile(r'\\/api\\/m3u8\?origin=([^\\]+)\\u0026url=([0-9a-f]{24})', re.I)
PLAYPATH_RE = re.compile(r'<a[^>]*href="(/[^" ]*?origin=([^"&]+)&amp;p=(\d+))"[^>]*>\s*<button[^>]*>\s*([^<]+?)\s*</button>', re.I)
DOC_RE = re.compile(r"video_player_doc\s*=\s*\{[\s\S]*?aa:\s*JSON\.parse\('((?:[^'\\]|\\.)*)'\)")
PRELOAD_RE = re.compile(r'<link[^>]+rel="preload"[^>]+href="(https?://[^"]+\.m3u8)', re.I)
API_URL_RE = re.compile(r'^/api/m3u8\?origin=([^&]+)&url=([0-9a-f]{24})$', re.I)


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://dyrsvip.net"
        self.domain = "dyrsvip.net"
        # This endpoint is retained because it is part of the site's playback flow,
        # not a display/branding element.
        self.boxHost = "https://box.dyrs.com.de"
        self.siteName = "电影人生"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.options = {}
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx)
        )
        self.cats = [
            {"type_id": "dianying", "type_name": "电影", "path": "/dianying.html",
             "classes": ["剧情", "喜剧", "动作", "爱情", "惊悚", "犯罪", "恐怖", "悬疑", "冒险", "奇幻", "科幻", "院线", "家庭", "历史", "战争", "纪录片", "古装", "音乐", "动画", "传记", "武侠", "运动", "西部", "短片"],
             "sorts": [("", "默认"), ("play_hot", "热度"), ("group_douban", "豆瓣评分")]},
            {"type_id": "dianshiju", "type_name": "电视剧", "path": "/dianshiju.html",
             "classes": ["剧情", "喜剧", "爱情", "犯罪", "悬疑", "家庭", "古装", "惊悚", "动作", "奇幻", "科幻", "都市", "历史", "战争", "冒险", "武侠", "恐怖", "青春", "传记", "谍战", "情感", "纪录", "军旅", "时装", "纪录片"],
             "sorts": [("", "默认"), ("play_hot", "热度")]},
            {"type_id": "zongyi", "type_name": "综艺", "path": "/zongyi.html",
             "classes": ["真人秀", "脱口秀", "国产综艺", "喜剧", "晚会", "综艺", "音乐", "纪录", "游戏", "生活", "港台综艺", "日韩综艺", "剧情", "文化", "相声", "情感", "悬疑", "欧美综艺", "美食", "竞技", "爱情", "犯罪", "家庭", "历史", "纪录片"],
             "sorts": [("", "默认"), ("play_hot", "热度")]},
            {"type_id": "dongman", "type_name": "动漫", "path": "/dongman.html",
             "classes": ["动画", "冒险", "喜剧", "奇幻", "剧情", "科幻", "动作", "儿童", "悬疑", "都市", "家庭", "国漫", "日常", "爱情", "玄幻", "日漫", "音乐", "治愈", "短片", "古风", "犯罪", "武侠", "运动", "校园", "纪录片"],
             "sorts": [("", "默认"), ("play_hot", "热度")]},
            {"type_id": "duanju", "type_name": "短剧", "path": "/duanju.html",
             "classes": ["AI漫剧", "短剧", "剧情", "爱情", "爽文", "古装", "短片", "悬疑", "喜剧", "奇幻", "都市", "玄幻", "犯罪", "家庭", "穿越", "惊悚", "武侠", "科幻", "动作", "冒险", "恐怖", "青春", "历史", "动画", "战争", "纪录片"],
             "sorts": [("", "默认"), ("play_hot", "热度")]}
        ]
        self.years = ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015", "2014", "2013", "2012", "2011", "2010", "2009", "2008", "2007", "2006", "2005", "2004", "2003", "2002", "2001", "2000", "2020年代", "2010年代", "2000年代", "90年代", "80年代", "70年代", "60年代", "50年代", "更早"]

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        host = ""
        if isinstance(self.options, dict):
            host = self.options.get("host") or self.options.get("domain") or ""
        if not host and isinstance(extend, str):
            host = extend.strip()
        if host:
            host = host.strip().rstrip("/")
            if not host.startswith("http"):
                host = "https://" + host
            try:
                netloc = urllib.parse.urlparse(host).netloc
            except Exception:
                netloc = ""
            if netloc:
                hostpart = netloc.split(":")[0]
                if re.match(r"^[A-Za-z0-9][A-Za-z0-9.\-]*[A-Za-z0-9]$", hostpart) and "." in hostpart:
                    self.siteUrl = host
                    self.domain = netloc
        return True

    def getName(self):
        return self.siteName

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd", ".mp3", ".m4a", ".aac"))

    def manualVideoCheck(self):
        return False

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "bytes": b"", "err": "", "final_url": ""}
        if target_url.startswith("//"):
            target_url = "https:" + target_url
        elif target_url.startswith("/"):
            target_url = self.siteUrl + target_url
        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        last_err = ""
        for attempt in range(5):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=3) as resp:
                    code = resp.getcode()
                    final_url = resp.geturl()
                    raw = resp.read()
                    enc = getattr(resp, "headers", {}).get("Content-Encoding", "")
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    try:
                        text = raw.decode("utf-8")
                    except Exception:
                        text = raw.decode("latin1", errors="ignore")
                    if "正在检测" in text and attempt < 4:
                        last_err = "bot check page"
                        time.sleep(0.5)
                        continue
                    return {"code": code, "text": text, "bytes": raw, "err": "", "final_url": final_url}
            except urllib.error.HTTPError as e:
                last_err = "HTTP %s" % e.code
                if e.code in (451, 403, 429) and attempt < 4:
                    time.sleep(0.5)
                    continue
                err_raw = ""
                try:
                    err_raw = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                return {"code": e.code, "text": err_raw, "bytes": b"", "err": str(e), "final_url": target_url}
            except Exception as e:
                last_err = str(e)
                if attempt < 4:
                    time.sleep(0.5)
                    continue
                return {"code": -1, "text": "", "bytes": b"", "err": str(e), "final_url": target_url}
        return {"code": -1, "text": "", "bytes": b"", "err": last_err, "final_url": target_url}

    def _clean(self, text):
        if not text:
            return ""
        text = re.sub(r"&amp;", "&", str(text))
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#39;", "'", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _ep_name(self, name):
        name = self._clean(name)
        name = name.replace("$", "＄").replace("#", "＃")
        return name

    def _poster_url(self, poster_hash):
        return self.siteUrl + "/img/id/" + poster_hash + ".jpg?host=" + self.domain

    def _remarks(self, status):
        # Keep the original update/episode text; do not prepend a third-party brand.
        return self._clean(status)

    def _box_url(self, origin, url_hash):
        return self.boxHost + "/api/super?id=" + url_hash + "&origin=" + urllib.parse.quote(origin) + "&format=.m3u8"

    def _clean_m3u8_url(self, raw):
        if not raw:
            return ""
        text = raw.strip()
        idx = text.lower().find(".m3u8")
        if idx < 0:
            return ""
        end = idx + 5
        cut = len(text)
        for ch in ('"', "'", " ", "<", ">", "\n", "\r", "\t"):
            pos = text.find(ch, end)
            if pos >= 0 and pos < cut:
                cut = pos
        return text[:cut]

    def _parse_cards(self, html):
        items = []
        seen = set()
        if not html:
            return items
        for m in CARD_RE.finditer(html):
            title = self._clean(m.group(1))
            kind = m.group(2)
            card_hash = m.group(3)
            num_id = m.group(4)
            if num_id in seen:
                continue
            seen.add(num_id)
            inner = m.group(5)
            pm = POSTER_RE.search(inner)
            poster_hash = pm.group(1) if pm else card_hash
            bm = BADGE_RE.search(inner)
            badge = bm.group(1) if bm else ""
            items.append({
                "vod_id": kind + "@@" + card_hash + "@@" + num_id,
                "vod_name": title,
                "vod_pic": self._poster_url(poster_hash),
                "vod_remarks": self._remarks(badge),
                "style": {"type": "rect", "ratio": 0.67}
            })
        return items

    def _page_result(self, items, pg):
        page_size = 24
        if not items:
            return {"page": pg, "pagecount": 1, "limit": page_size, "total": 0, "list": []}
        if len(items) >= page_size:
            return {"page": pg, "pagecount": pg + 1, "limit": page_size, "total": pg * len(items) + 100, "list": items}
        return {"page": pg, "pagecount": pg, "limit": page_size, "total": (pg - 1) * page_size + len(items), "list": items}

    def _find_cat(self, tid):
        for cat in self.cats:
            if cat["type_id"] == tid:
                return cat
        return None

    def homeContent(self, filter):
        result = {"class": [{"type_name": c["type_name"], "type_id": c["type_id"]} for c in self.cats]}
        if filter:
            filters = {}
            for cat in self.cats:
                class_values = [{"n": "全部", "v": ""}]
                for cls in cat["classes"]:
                    class_values.append({"n": cls, "v": cls})
                sort_values = []
                for v, n in cat["sorts"]:
                    sort_values.append({"n": n, "v": v})
                year_values = [{"n": "全部", "v": ""}]
                for y in self.years:
                    year_values.append({"n": y, "v": y})
                filters[cat["type_id"]] = [
                    {"key": "class", "name": "类型", "init": "", "value": class_values},
                    {"key": "sort", "name": "排序", "init": "", "value": sort_values},
                    {"key": "year", "name": "年代", "init": "", "value": year_values}
                ]
            result["filters"] = filters
        return result

    def homeVideoContent(self):
        res = self._fetch("/?host=" + self.domain)
        items = self._parse_cards(res.get("text", ""))
        if not items:
            res = self._fetch("/dianying.html?host=" + self.domain)
            items = self._parse_cards(res.get("text", ""))
        return {"list": items[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        del filter
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        cat = self._find_cat(tid)
        if not cat:
            return {"page": pg, "pagecount": 1, "limit": 24, "total": 0, "list": []}
        ext = {}
        if isinstance(extend, dict):
            ext = extend
        elif extend:
            try:
                ext = json.loads(extend)
            except Exception:
                ext = {}
        url = cat["path"] + "?host=" + self.domain + "&page=" + str(pg - 1)
        cls = ext.get("class", "")
        if cls and cls not in cat["classes"]:
            cls = ""
        if cls:
            url += "&class=" + urllib.parse.quote(cls)
        sort = ext.get("sort", "")
        if sort and sort not in [v for v, n in cat["sorts"]]:
            sort = ""
        if sort:
            url += "&sort_field=" + urllib.parse.quote(sort)
        year = ext.get("year", "")
        if year and year not in self.years:
            year = ""
        if year:
            url += "&year=" + urllib.parse.quote(year)
        res = self._fetch(url)
        items = self._parse_cards(res.get("text", ""))
        return self._page_result(items, pg)

    def searchContent(self, key, quick, pg="1"):
        del quick
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        key = (key or "").strip()
        if not key:
            return {"page": pg, "pagecount": 1, "limit": 24, "total": 0, "list": []}
        url = "/s.html?host=" + self.domain + "&name=" + urllib.parse.quote(key) + "&page=" + str(pg - 1)
        res = self._fetch(url)
        items = self._parse_cards(res.get("text", ""))
        return self._page_result(items, pg)

    def _parse_json_ld(self, html):
        m = LD_RE.search(html or "")
        if not m:
            return {}
        try:
            data = json.loads(m.group(1))
        except (ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _parse_tabs(self, html):
        tabs = []
        seen = set()
        for origin, label_html, count in TAB_RE.findall(html or ""):
            try:
                origin = urllib.parse.unquote(origin)
            except Exception:
                pass
            label = self._clean(label_html)
            # The site's visible tab caption is the display name. data-origin
            # remains the playback key used by the site's API.
            name = label or origin
            key = (origin, name)
            if key in seen:
                continue
            seen.add(key)
            try:
                tabs.append({"origin": origin, "name": name, "count": int(count)})
            except ValueError:
                continue
        return tabs

    def _parse_episodes(self, html):
        titles = [self._clean(t) for t in TITLE_RE.findall(html or "")]
        apis = []
        for org, u in API_RE.findall(html or ""):
            try:
                org = urllib.parse.unquote(org)
            except Exception:
                pass
            apis.append({"origin": org, "url": u})
        if titles and apis:
            eps = []
            n = min(len(titles), len(apis))
            for i in range(n):
                eps.append({"name": titles[i], "origin": apis[i]["origin"], "url": apis[i]["url"], "play": "", "p": i})
            return eps
        seen = set()
        eps = []
        for href, org, p, name in PLAYPATH_RE.findall(html or ""):
            try:
                idx = int(p)
            except ValueError:
                continue
            if idx in seen:
                continue
            seen.add(idx)
            try:
                org = urllib.parse.unquote(org)
            except Exception:
                pass
            eps.append({"name": self._clean(name), "origin": org, "url": "", "play": href.replace("&amp;", "&"), "p": idx})
        eps.sort(key=lambda e: e["p"])
        return eps

    def _parse_related(self, html, self_id):
        idx = (html or "").find("其他人还喜欢")
        if idx < 0:
            return []
        related = self._parse_cards(html[idx:])
        out = []
        for r in related:
            rparts = r["vod_id"].split("@@")
            if len(rparts) == 3 and rparts[2] != self_id:
                out.append(r)
        return out

    def _structured_synopsis(self, title, genres, num_id, related):
        lines = ["标题：" + title]
        if genres:
            lines.append("分类：" + "/".join(genres))
        lines.append("编号：" + num_id)
        shown = 0
        for r in related:
            if shown >= 6:
                break
            if shown == 0:
                lines.append("相关推荐：")
            shown += 1
            lines.append(str(shown) + ". " + r["vod_name"])
        return "\n".join(lines)

    def _jsonld_people(self, value):
        """Normalize JSON-LD actor/director fields to a list of names."""
        if isinstance(value, dict):
            value = [value]
        elif isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            return []
        names = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    names.append(str(name).strip())
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
        return names

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        kind = ""
        card_hash = ""
        num_id = ""
        if "@@" in raw_id:
            parts = raw_id.split("@@")
            if len(parts) == 3:
                kind, card_hash, num_id = parts
        elif "/" in raw_id:
            parts = raw_id.split("/")
            if len(parts) == 2 and "-" in parts[1]:
                kind = parts[0]
                card_hash, num_id = parts[1].rsplit("-", 1)
        if kind not in ("tv", "movie") or not card_hash or not num_id:
            return {"list": [], "msg": "Invalid id"}
        detail_path = "/" + kind + "/" + card_hash + "-" + num_id + ".html"
        res = self._fetch(detail_path + "?host=" + self.domain)
        html = res.get("text", "")
        if res.get("code", 0) != 200 or not html:
            return {"list": [], "msg": "Detail unavailable"}
        ld = self._parse_json_ld(html)
        title = ld.get("name") or ""
        if not isinstance(title, str):
            title = str(title)
        ld_type = ld.get("@type") or ""
        genres = ld.get("genre") or []
        if isinstance(genres, str):
            genres = [genres]
        if not isinstance(genres, (list, tuple)):
            genres = []
        genres = [g for g in genres if isinstance(g, str) and g]
        actors = self._jsonld_people(ld.get("actor"))
        directors = self._jsonld_people(ld.get("director"))
        description = ld.get("description") or ""
        if not isinstance(description, str):
            description = str(description)
        year = ld.get("year")
        if year is not None:
            year = str(year)
        area = ld.get("countryOfOrigin") or ""
        if not isinstance(area, str):
            area = ""
        tabs = self._parse_tabs(html)
        eps = self._parse_episodes(html)

        # If tab markup is absent, recover distinct original origin values from
        # episode metadata rather than inventing a branded/fixed line name.
        if not tabs and eps:
            origin_counts = {}
            for ep in eps:
                origin = ep.get("origin") or ""
                if origin:
                    origin_counts[origin] = origin_counts.get(origin, 0) + 1
            tabs = [
                {"origin": origin, "name": origin, "count": count}
                for origin, count in origin_counts.items()
            ]

        default_count = len(eps)
        related = self._parse_related(html, num_id)
        play_from = []
        play_url = []
        variant_left = 1
        for i, tab in enumerate(tabs):
            org = tab["origin"]
            line_name = self._clean(tab.get("name") or org) or org
            if tab["count"] == default_count or not eps:
                line_eps = eps
            elif variant_left > 0:
                variant_left -= 1
                vres = self._fetch(detail_path + "?host=" + self.domain + "&origin=" + urllib.parse.quote(org))
                vepisodes = self._parse_episodes(vres.get("text", ""))
                line_eps = vepisodes if vepisodes else eps
            else:
                line_eps = eps
            ep_parts = []
            for ep in line_eps:
                if ep["url"]:
                    value = self._box_url(ep.get("origin") or org, ep["url"])
                else:
                    value = ep["play"]
                ep_parts.append(self._ep_name(ep["name"]) + "$" + value)
            if i == 0:
                for r in related:
                    rparts = r["vod_id"].split("@@")
                    if len(rparts) != 3:
                        continue
                    rpath = "/" + rparts[0] + "/" + rparts[1] + "-" + rparts[2] + ".html"
                    ep_parts.append(self._ep_name(r["vod_name"]) + "$" + rpath + "@@@" + r["vod_name"])
            # Preserve the line caption displayed by the site, including line 0.
            play_from.append(line_name)
            play_url.append("#".join(ep_parts))

        if description:
            content = description
        else:
            content = self._structured_synopsis(title, genres, num_id, related)
        status = ""
        if ld_type == "Movie":
            if eps:
                status = eps[0]["name"]
        else:
            if eps:
                status = str(len(eps)) + "集"
        poster = self._poster_url(card_hash)
        vod = {
            "vod_id": raw_id,
            "vod_name": title,
            "vod_pic": poster,
            "vod_bg": poster,
            "vod_background": poster,
            "vod_banner": poster,
            "vod_actor": "、".join(actors),
            "vod_remarks": self._remarks(status),
            "vod_content": content,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url)
        }
        if directors:
            vod["vod_director"] = "、".join(directors)
        if genres:
            vod["vod_class"] = "/".join(genres)
        if year:
            vod["vod_year"] = year
        if area:
            vod["vod_area"] = area
        return {"list": [vod]}

    def _resolve_play_path(self, play_path):
        detail_url = self.siteUrl + play_path.split("?")[0]
        res = self._fetch(play_path, referer=detail_url)
        html = res.get("text", "")
        if not html:
            return "", {}
        doc_m = DOC_RE.search(html)
        if doc_m:
            try:
                raw = doc_m.group(1).replace("\\u0022", '"').replace("\\/", "/")
                doc = json.loads(raw)
                doc_url = doc.get("url", "") or ""
                if doc_url.startswith("http"):
                    clean = self._clean_m3u8_url(doc_url)
                    if clean:
                        return clean, {"User-Agent": self._ua, "Referer": self.siteUrl + "/"}
                    return doc_url, {"User-Agent": self._ua, "Referer": self.siteUrl + "/"}
                api_m = API_URL_RE.match(doc_url)
                if api_m:
                    return self._box_url(urllib.parse.unquote(api_m.group(1)), api_m.group(2)), {"User-Agent": self._ua}
            except (ValueError, TypeError):
                pass
        pre_m = PRELOAD_RE.search(html)
        if pre_m:
            return pre_m.group(1), {"User-Agent": self._ua, "Referer": self.siteUrl + "/"}
        return "", {}

    def _resolve_detail_first(self, detail_path):
        res = self._fetch(detail_path + "?host=" + self.domain)
        html = res.get("text", "")
        if not html:
            return "", {}
        apis = API_RE.findall(html)
        if apis:
            org, u = apis[0]
            try:
                org = urllib.parse.unquote(org)
            except Exception:
                pass
            return self._box_url(org, u), {"User-Agent": self._ua}
        eps = self._parse_episodes(html)
        for ep in eps:
            if ep["play"]:
                return self._resolve_play_path(ep["play"])
        pre_m = PRELOAD_RE.search(html)
        if pre_m:
            return pre_m.group(1), {"User-Agent": self._ua, "Referer": self.siteUrl + "/"}
        return "", {}

    def playerContent(self, flag, id, vipFlags):
        del flag, vipFlags
        play_id = str(id).strip()
        if "@@@" in play_id:
            detail_path, title = play_id.split("@@@", 1)
            url, headers = self._resolve_detail_first(detail_path)
            if url:
                return {"parse": 0, "jx": 0, "url": url, "header": headers, "desc": title}
            return {"parse": 0, "msg": "No playable source"}
        if play_id.startswith("http"):
            return {"parse": 0, "jx": 0, "url": play_id, "header": {"User-Agent": self._ua}}
        if play_id.startswith("/"):
            url, headers = self._resolve_play_path(play_id)
            if url:
                return {"parse": 0, "jx": 0, "url": url, "header": headers}
            return {"parse": 0, "msg": "Play page unavailable"}
        return {"parse": 0, "msg": "Invalid play id"}

    def action(self, action):
        return {}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]

    def destroy(self):
        self.options = {}
