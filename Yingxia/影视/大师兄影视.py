# -*- coding: utf-8 -*-

import ast
import base64
import html as html_module
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import requests

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def __init__(self):
            pass
        def getProxyUrl(self):
            return ""


class _HTMLNode:
    __slots__ = ("tag", "attrs", "children", "parent", "start_pos", "end_pos")

    def __init__(self, tag, attrs=None, parent=None, start_pos=None, end_pos=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent
        self.start_pos = start_pos
        self.end_pos = end_pos


class _HTMLTreeParser(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self, source=""):
        super().__init__(convert_charrefs=True)
        self.source = source or ""
        self._line_starts = [0]
        self._line_starts.extend(i + 1 for i, ch in enumerate(self.source) if ch == "\n")
        self.root = _HTMLNode("document", start_pos=0)
        self.stack = [self.root]

    def _source_pos(self):
        line, column = self.getpos()
        if 1 <= line <= len(self._line_starts):
            return self._line_starts[line - 1] + column
        return len(self.source)

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1]
        node = _HTMLNode(tag.lower(), attrs, parent, start_pos=self._source_pos())
        parent.children.append(node)
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(node)
        else:
            end = self.source.find(">", node.start_pos or 0)
            node.end_pos = end + 1 if end >= 0 else None

    def handle_startendtag(self, tag, attrs):
        parent = self.stack[-1]
        start = self._source_pos()
        end = self.source.find(">", start)
        parent.children.append(_HTMLNode(tag.lower(), attrs, parent, start, end + 1 if end >= 0 else None))

    def handle_endtag(self, tag):
        tag = tag.lower()
        close_start = self._source_pos()
        close_end = self.source.find(">", close_start)
        close_end = close_end + 1 if close_end >= 0 else None
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                for node in self.stack[index:]:
                    if node.end_pos is None:
                        node.end_pos = close_end
                del self.stack[index:]
                break

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def _parse_html_tree(source):
    parser = _HTMLTreeParser(source)
    try:
        parser.feed(source or "")
        parser.close()
    except Exception:
        pass
    return parser.root


def _walk_html(node):
    for child in getattr(node, "children", []):
        if isinstance(child, _HTMLNode):
            yield child
            yield from _walk_html(child)


def _html_node_text(node):
    parts = []
    def visit(current):
        for child in getattr(current, "children", []):
            if isinstance(child, str):
                parts.append(child)
            elif isinstance(child, _HTMLNode) and child.tag not in ("script", "style", "noscript"):
                visit(child)
    visit(node)
    return " ".join(" ".join(parts).split())


def _html_descendants(node):
    return list(_walk_html(node))


class Spider(BaseSpider):
    DEFAULT_HOST = "http://www.dsxys8.com"
    DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    # 主分类列表（不展示理论片分类）
    CLASSES = [
        {"type_name": "电影", "type_id": "1"},
        {"type_name": "连续剧", "type_id": "2"},
        {"type_name": "综艺", "type_id": "3"},
        {"type_name": "动漫", "type_id": "4"},
        {"type_name": "短剧", "type_id": "27"},
    ]

    # 二级子分类筛选字典（基于真实探针萃取数据构建）
    FILTERS = {
        "1": [
            {
                "key": "sub_tid",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "1"},
                    {"n": "动作片", "v": "5"},
                    {"n": "喜剧片", "v": "6"},
                    {"n": "爱情片", "v": "7"},
                    {"n": "科幻片", "v": "8"},
                    {"n": "恐怖片", "v": "9"},
                    {"n": "剧情片", "v": "10"},
                    {"n": "战争片", "v": "11"},
                    {"n": "纪录片", "v": "22"},
                    {"n": "动画片", "v": "33"}
                ]
            }
        ],
        "2": [
            {
                "key": "sub_tid",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "2"},
                    {"n": "国产剧", "v": "12"},
                    {"n": "香港剧", "v": "13"},
                    {"n": "台湾剧", "v": "14"},
                    {"n": "日本剧", "v": "15"},
                    {"n": "韩国剧", "v": "16"},
                    {"n": "欧美剧", "v": "17"},
                    {"n": "海外剧", "v": "18"},
                    {"n": "泰国剧", "v": "19"}
                ]
            }
        ],
        "3": [
            {
                "key": "sub_tid",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "3"},
                    {"n": "内地综艺", "v": "23"},
                    {"n": "港台综艺", "v": "24"},
                    {"n": "日韩综艺", "v": "25"},
                    {"n": "欧美综艺", "v": "26"}
                ]
            }
        ],
        "4": [
            {
                "key": "sub_tid",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "4"},
                    {"n": "国产动漫", "v": "28"},
                    {"n": "港台动漫", "v": "29"},
                    {"n": "日韩动漫", "v": "30"},
                    {"n": "欧美动漫", "v": "31"},
                    {"n": "海外动漫", "v": "32"}
                ]
            }
        ]
    }

    DETAIL_RE = re.compile(r"/detail-([^/?#'\"<>]+)/", re.I)
    PLAY_RE = re.compile(r"/play-([^/?#'\"<>]+)-(\d+)-(\d+)/", re.I)
    MEDIA_EXTENSIONS = (".m3u8", ".mp4", ".mkv", ".flv", ".ts", ".webm")
    CF_SIGNS = ("just a moment", "checking your browser", "attention required! | cloudflare")

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = self.DEFAULT_HOST
        self.ua = self.DEFAULT_UA
        self.cookie = ""
        self.timeout = 15
        self.use_cffi = False
        self.proxy_enabled = False
        self.session = requests.Session()
        self.headers = {}
        self._refresh_headers()

    def init(self, extend=""):
        config = self._parse_extend(extend)
        raw_host = str(config.get("host") or self.DEFAULT_HOST).strip().rstrip("/")
        if raw_host.startswith("https://"):
            raw_host = "http://" + raw_host[len("https://"):]
        self.host = raw_host
        self.ua = str(config.get("ua") or self.DEFAULT_UA).strip()
        self.cookie = str(config.get("cookie") or "").strip()
        self.timeout = self._safe_int(config.get("timeout"), 15, 5, 60)
        self.use_cffi = self._as_bool(config.get("use_cffi"), False)
        self.proxy_enabled = self._as_bool(config.get("proxy"), False)
        self.session = requests.Session()
        self._refresh_headers()
        return True

    def getName(self):
        return "大师兄"

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    @staticmethod
    def _safe_int(value, default, minimum=None, maximum=None):
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        if minimum is not None:
            number = max(minimum, number)
        if maximum is not None:
            number = min(maximum, number)
        return number

    @staticmethod
    def _as_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "是", "开启"}

    @staticmethod
    def _parse_extend(extend):
        if isinstance(extend, dict):
            return dict(extend)
        if not extend:
            return {}
        text = str(extend).strip()
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else {}
        except Exception:
            pass
        try:
            parsed = parse_qs(text, keep_blank_values=True)
            return {key: values[-1] for key, values in parsed.items()}
        except Exception:
            return {}

    def _refresh_headers(self):
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if self.cookie:
            self.headers["Cookie"] = self.cookie
        try:
            self.session.headers.clear()
            self.session.headers.update(self.headers)
        except Exception:
            pass

    def _request_raw(self, url, referer="", binary=False):
        if not url:
            return None
        target = self._absolute(url, referer or self.host)
        if target.startswith("https://www.dsxys8.com"):
            target = "http://www.dsxys8.com" + target[len("https://www.dsxys8.com"):]

        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        if binary:
            headers["Accept"] = "*/*"

        if self.use_cffi and cffi_requests is not None:
            try:
                response = cffi_requests.get(
                    target,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    impersonate="chrome131"
                )
                if getattr(response, "status_code", 200) < 400:
                    if not binary:
                        response.encoding = getattr(response, "apparent_encoding", None) or "utf-8"
                        if not self._is_cloudflare_text(response.text):
                            return response
                    else:
                        return response
            except Exception:
                pass

        for attempt in range(2):
            try:
                response = self.session.get(target, headers=headers, timeout=self.timeout, allow_redirects=True)
                if getattr(response, "status_code", 200) >= 400:
                    raise RuntimeError("HTTP %s" % getattr(response, "status_code", 0))
                if not binary:
                    response.encoding = self._response_encoding(response)
                    if self._is_cloudflare_text(response.text):
                        raise RuntimeError("Cloudflare challenge")
                return response
            except Exception:
                if attempt == 0:
                    time.sleep(0.3)
        return None

    @staticmethod
    def _response_encoding(response):
        content = getattr(response, "content", b"")[:3000]
        head = content.decode("ascii", "ignore").lower()
        if "charset=utf-8" in head or "charset=\"utf-8\"" in head or "charset='utf-8'" in head:
            return "utf-8"
        return getattr(response, "apparent_encoding", None) or "utf-8"

    def _get_text(self, url, referer=""):
        response = self._request_raw(url, referer=referer, binary=False)
        if response is None:
            return ""
        try:
            text = response.text or ""
            return "" if self._is_cloudflare_text(text) else text
        except Exception:
            return ""

    @classmethod
    def _is_cloudflare_text(cls, text):
        lower = (text or "")[:100000].lower()
        return any(sign in lower for sign in cls.CF_SIGNS)

    def _absolute(self, url, base):
        if not url:
            return ""
        value = html_module.unescape(str(url).strip()).replace("\\/", "/")
        if value.startswith("//"):
            return "http:" + value
        return urljoin(base, value)

    @staticmethod
    def _clean_text(value):
        if value is None:
            return ""
        text = html_module.unescape(str(value)).replace("\xa0", " ")
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip(" \t\r\n/|")

    @staticmethod
    def _strip_third_party_brand(value):
        text = html_module.unescape(str(value or ""))
        # Strip promotional annotations that were injected by the third-party source,
        # while leaving genuine film/series metadata intact.
        patterns = (
            r"🦋\s*",
            r"(?:官方)?\s*TG群\s*[:：]?\s*@?tvshare23",
            r"https?://t\.me/tvshare23/?",
            r"蝴蝶影视",
            r"蝴蝶极速线路",
        )
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.I)
        text = re.sub(r"[【】〔〕\[\]]", " ", text)
        text = re.sub(r"\s*[-|｜·•]{2,}\s*", " ", text)
        return re.sub(r"\s+", " ", text).strip(" \t\r\n:：-/|｜")

    @classmethod
    def _clean_site_text(cls, value):
        return cls._strip_third_party_brand(cls._clean_text(value))

    @classmethod
    def _clean_site_title(cls, value):
        text = cls._clean_site_text(value)
        return re.sub(
            r"\s*[-_|｜]\s*(?:大师兄影视|海量高清电影大全免费在线观看电视剧|海量高清|免费在线观看|在线播放).*$",
            "", text, flags=re.I
        ).strip()

    @staticmethod
    def _attr(attrs, name):
        match = re.search(rf"\b{re.escape(name)}\s*=\s*[\"']([^\"']*)", attrs or "", re.I)
        return html_module.unescape(match.group(1).strip()) if match else ""

    def _parse_video_list(self, source, page_url):
        records = []
        seen = set()
        pattern = re.compile(r"<a\b([^>]*href=[\"']([^\"']*/detail[-/][^\"']+)[\"'][^>]*)>(.*?)</a>", re.I | re.S)
        for match in pattern.finditer(source or ""):
            attrs, href, body = match.groups()
            absolute = self._absolute(href, page_url or self.host)
            path = urlparse(absolute).path
            if path in seen:
                continue
            seen.add(path)
            title = self._attr(attrs, "title")
            if not title:
                found = re.search(r'class=[\"\'][^\"\']*title[^\"\']*[\"\'][^>]*>(.*?)</', body, re.I | re.S)
                title = self._clean_site_text(found.group(1)) if found else ""
            if not title:
                found = re.search(r'alt=[\"\']([^\"\']+)', body, re.I)
                title = self._clean_site_text(found.group(1)) if found else ""
            if not title:
                continue
            title = self._clean_site_title(title)
            pic_match = re.search(r"(?:data-original|data-src|src)=[\"']([^\"']+)", body, re.I)
            pic = self._absolute(pic_match.group(1), absolute) if pic_match else ""
            remark_match = re.search(r"(?:pic-text|text-right|text-muted|remark|remarks|subtitle|status)[^>]*>(.*?)</(?:span|p|div)>", body, re.I | re.S)
            remark = self._clean_site_text(remark_match.group(1)) if remark_match else ""
            records.append({
                "vod_id": path,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
                "style": {"type": "rect", "ratio": 1.78}
            })
        return records

    def _parse_home_section(self, source, page_url, section_name):
        """Extract one homepage module, then reuse the original raw-HTML card parser.

        The old full-homepage implementation got cover URLs from the original <a> card
        markup. Rebuilding cards from a lightweight DOM tree could detach lazy-loaded
        <img> elements from their original anchors on malformed/nested site markup.
        Keeping the exact source substring avoids changing that proven image extraction.
        """
        root = _parse_html_tree(source)
        known_sections = {"电影", "连续剧", "电视剧", "综艺", "动漫", "短剧", "理论片", "伦理片", "热门推荐", "推荐"}
        candidates = []

        for node in _walk_html(root):
            if _html_node_text(node) != section_name:
                continue
            classes = node.attrs.get("class", "").lower()
            parent = node.parent
            parent_classes = parent.attrs.get("class", "").lower() if parent else ""
            is_heading = node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
            is_heading = is_heading or any(token in classes for token in ("title", "heading", "header", "head"))
            is_heading = is_heading or (parent is not None and (
                parent.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
                or any(token in parent_classes for token in ("title", "heading", "header", "head"))
            ))
            if not is_heading:
                continue

            ancestor = node
            for distance in range(1, 10):
                ancestor = ancestor.parent
                if ancestor is None:
                    break
                detail_links = [
                    child for child in _walk_html(ancestor)
                    if child.tag == "a" and re.search(
                        r"/detail[-/][^/?#]+", child.attrs.get("href", ""), re.I
                    )
                ]
                if not detail_links:
                    continue
                # Reject a wrapper that spans multiple homepage modules.
                has_other_section = False
                for child in _walk_html(ancestor):
                    if child is node:
                        continue
                    child_classes = child.attrs.get("class", "").lower()
                    child_parent = child.parent
                    child_parent_classes = child_parent.attrs.get("class", "").lower() if child_parent else ""
                    child_is_heading = child.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
                    child_is_heading = child_is_heading or any(
                        token in child_classes for token in ("title", "heading", "header", "head")
                    )
                    child_is_heading = child_is_heading or (child_parent is not None and (
                        child_parent.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
                        or any(token in child_parent_classes for token in ("title", "heading", "header", "head"))
                    ))
                    if child_is_heading and _html_node_text(child) in known_sections - {section_name}:
                        has_other_section = True
                        break
                if has_other_section:
                    continue
                if ancestor.start_pos is None or ancestor.end_pos is None:
                    continue
                if ancestor.end_pos <= ancestor.start_pos:
                    continue
                # Retain every valid ancestor candidate. The largest one still confined
                # to this section normally contains the complete card grid.
                candidates.append((len(detail_links), -distance, ancestor))

        if not candidates:
            return []

        # Choose the complete module (largest detail-link group), not an inner one-card
        # wrapper. At equal counts prefer the closest ancestor to the heading.
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _, _, section_root = candidates[0]
        section_html = source[section_root.start_pos:section_root.end_pos]
        return self._parse_video_list(section_html, page_url)

    def homeContent(self, filter=False):
        return {"class": list(self.CLASSES), "filters": self.FILTERS}

    def homeVideoContent(self):
        source = self._get_text(self.host + "/", referer=self.host + "/")
        if not source:
            return {"list": []}
        # The homepage has independent 电影 and 连续剧 modules. Keep only those two.
        movies = self._parse_home_section(source, self.host, "电影")
        series = self._parse_home_section(source, self.host, "连续剧")
        merged, seen = [], set()
        for item in movies + series:
            key = item.get("vod_id")
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
            if len(merged) >= 30:
                break
        return {"list": merged}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        # Category ID 20 (理论片) is intentionally removed.
        if str(tid or "").strip() == "20":
            return {"list": [], "page": self._safe_int(pg, 1, 1), "pagecount": 1, "limit": 0, "total": 0}
        page = self._safe_int(pg, 1, 1)
        ext = extend or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}

        # 核心联动：若用户点击了筛选栏中的子分类，则使用选中的具体子分类 ID
        target_tid = str(ext.get("sub_tid") or tid or "1").strip()
        if target_tid == "20":
            return {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}

        paths = [
            f"/sort-{target_tid}/" if page == 1 else f"/sort-{target_tid}-{page}/",
            f"/sort/{target_tid}.html" if page == 1 else f"/sort/{target_tid}-{page}.html"
        ]
        videos, source = self._fetch_list(paths)
        return {
            "list": videos,
            "page": page,
            "pagecount": self._pagecount(source, page),
            "limit": len(videos),
            "total": len(videos)
        }

    def _fetch_list(self, paths):
        last = ""
        for path in paths:
            url = self._absolute(path, self.host)
            source = self._get_text(url, referer=self.host + "/")
            if source:
                last = source
                videos = self._parse_video_list(source, url)
                if videos:
                    return videos, source
        return [], last

    @staticmethod
    def _pagecount(source, page):
        values = [int(x) for x in re.findall(r"/sort-\d+-(\d+)/", source or "", re.I)]
        return max(values + [page])

    def searchContent(self, key, quick, pg="1"):
        page = self._safe_int(pg, 1, 1)
        keyword = quote(unquote(str(key or "").strip()), safe="")
        if not keyword:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        path = f"/search--------------/?wd={keyword}"
        if page > 1:
            path += f"&page={page}"
        videos, source = self._fetch_list([path])
        return {"list": videos, "page": page, "pagecount": self._pagecount(source, page), "limit": len(videos), "total": len(videos)}

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        raw_id = str(raw_id or "").strip()
        if not raw_id:
            return {"list": []}
        detail_url = self._absolute(raw_id, self.host)
        source = self._get_text(detail_url, referer=self.host + "/")
        item = self._detail_metadata(source, detail_url)
        play_from, play_url = self._extract_plays(source, detail_url)
        item.update({
            "vod_id": raw_id,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        })
        return {"list": [item]}

    def _detail_metadata(self, source, detail_url):
        item = {
            "vod_name": "未知影片",
            "vod_pic": "",
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": ""
        }
        if not source:
            return item

        title_val = ""
        for pat in (
            r'<h1\b[^>]*>(.*?)</h1>',
            r'<h2\b[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>(.*?)</h2>',
            r'<div\b[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>(.*?)</div>',
            r'<meta\b[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)',
            r'<meta\b[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\',]+)'
        ):
            m = re.search(pat, source, re.I | re.S)
            if m:
                cand = self._clean_text(m.group(1))
                if cand and cand != "未知影片" and len(cand) < 40:
                    title_val = cand
                    break

        if not title_val:
            m = re.search(r'<title\b[^>]*>(.*?)</title>', source, re.I | re.S)
            if m:
                raw_t = self._clean_text(m.group(1))
                clean_t = re.sub(r'(-|_|\s+)(大师兄影视|海量高清|免费在线观看|在线播放|电视剧|电影|全集).*$', '', raw_t, flags=re.I).strip()
                if clean_t:
                    title_val = clean_t

        if not title_val:
            m = re.search(r'(?:为您提供|提供).*?片\s*([^\s,，。]+?)\s*在线', source)
            if m:
                title_val = self._clean_text(m.group(1))

        if title_val:
            item["vod_name"] = self._clean_site_title(title_val)

        pic = re.search(r'<meta\b[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)', source, re.I)
        if not pic:
            pic = re.search(r'(?:data-original|data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp))', source, re.I)
        if pic:
            item["vod_pic"] = self._absolute(pic.group(1), detail_url)

        # Prefer visible synopsis blocks when present; fall back to the page's own
        # description metadata. Never add promotional/source-brand text.
        tree = _parse_html_tree(source)
        synopsis = ""
        for node in _walk_html(tree):
            classes = node.attrs.get("class", "").lower()
            if any(token in classes for token in ("vod-content", "vod-desc", "content-desc", "plot", "synopsis", "intro-content", "hl-content")):
                candidate = self._clean_site_text(_html_node_text(node))
                if len(candidate) >= 8 and len(candidate) > len(synopsis):
                    synopsis = candidate
        if synopsis:
            item["vod_content"] = synopsis
        else:
            description = re.search(r'<meta\b[^>]*(?:name|property)=["\'](?:description|og:description)["\'][^>]*content=["\']([^"\']+)', source, re.I)
            if description:
                item["vod_content"] = self._clean_site_text(description.group(1))

        plain = self._clean_text(source)
        for label, field in (("类型", "type_name"), ("年份", "vod_year"), ("地区", "vod_area"), ("主演", "vod_actor"), ("导演", "vod_director"), ("状态", "vod_remarks")):
            found = re.search(label + r"\s*[:：]\s*([^|]{1,120})", plain)
            if found:
                item[field] = self._clean_site_text(found.group(1))

        year = re.search(r"\b(20\d{2})\b", plain)
        if year and not item["vod_year"]:
            item["vod_year"] = year.group(1)

        return item

    def _extract_plays(self, source, detail_url):
        groups, order = {}, []
        for match in re.finditer(r"<a\b([^>]*href=[\"']([^\"']*/play[-/][^\"']+)[\"'][^>]*)>(.*?)</a>", source or "", re.I | re.S):
            attrs, href, body = match.groups()
            play_match = self.PLAY_RE.search(href)
            sid = play_match.group(2) if play_match else "1"
            absolute = self._absolute(href, detail_url)
            name = self._normalize_episode(self._clean_text(body))
            groups.setdefault(sid, {})
            if sid not in order:
                order.append(sid)
            old = groups[sid].get(absolute)
            if old is None or old == "播放" or "第" in name:
                groups[sid][absolute] = name

        line_names = self._extract_line_names(source, order)
        play_from, play_url = [], []
        for sid in sorted(order, key=lambda value: int(value) if value.isdigit() else 1):
            episodes = [f"{name}${url}" for url, name in groups.get(sid, {}).items()]
            if episodes:
                # Only display a name actually found in the website markup.
                display_name = line_names.get(str(sid), "未命名线路")
                play_from.append(display_name)
                play_url.append("#".join(episodes))
        return play_from, play_url

    def _extract_line_names(self, source, sids):
        """Read actual source labels attached to the page's play-source controls."""
        names = {}
        root = _parse_html_tree(source)
        for node in _walk_html(root):
            attrs = node.attrs
            class_text = attrs.get("class", "")
            attr_blob = " ".join(str(v) for v in attrs.values())
            play_match = self.PLAY_RE.search(attr_blob)
            sid = play_match.group(2) if play_match else ""
            # Some templates expose the source id separately from the play URL.
            if not sid and re.search(r"(?:play[-_]?from|source|line|from)", class_text, re.I):
                sid_match = re.search(r"(?:sid|source[-_]?id|from[-_]?id|line[-_]?id)[\"'=:\s-]*(\d+)", attr_blob, re.I)
                if not sid_match:
                    sid_match = re.search(r"(?:hl-)?from[-_]?X[._-]?(\d+)", class_text, re.I)
                sid = sid_match.group(1) if sid_match else ""
            if not sid or str(sid) not in {str(x) for x in sids}:
                continue

            label = ""
            for key in ("data-name", "data-from", "data-source", "data-title", "data-label", "title", "aria-label"):
                value = self._clean_site_text(attrs.get(key, ""))
                if value and value not in {"播放", "线路", "来源", "选集", "切换线路"} and not re.search(r"第\s*\d+\s*[集期]", value):
                    label = value
                    break
            if not label:
                for child in _html_descendants(node):
                    child_class = child.attrs.get("class", "").lower()
                    if any(token in child_class for token in ("from", "source", "line", "player", "play-tab")):
                        value = self._clean_site_text(_html_node_text(child))
                        if value and len(value) <= 40 and not re.search(r"第\s*\d+\s*[集期]", value):
                            label = value
                            break
            if not label:
                direct_value = " ".join(part for part in node.children if isinstance(part, str)).strip()
                direct_value = self._clean_site_text(direct_value)
                if direct_value and len(direct_value) <= 24 and direct_value not in {"播放", "线路", "来源"} and not re.search(r"第\s*\d+\s*[集期]", direct_value):
                    label = direct_value
            if not label:
                value = self._clean_site_text(_html_node_text(node))
                if value and len(value) <= 24 and value not in {"播放", "线路", "来源", "选集", "切换线路"} and not re.search(r"第\s*\d+\s*[集期]", value):
                    label = value
            if label:
                names.setdefault(str(sid), label)

        # Handle source tabs whose class itself carries an X.1 / X_1 identifier.
        for node in _walk_html(root):
            class_text = node.attrs.get("class", "")
            match = re.search(r"(?:hl-)?from[-_]?X[._-]?(\d+)", class_text, re.I)
            if not match:
                continue
            sid = match.group(1)
            if sid not in {str(x) for x in sids} or sid in names:
                continue
            label = self._clean_site_text(_html_node_text(node))
            if label and len(label) <= 24 and not re.search(r"第\s*\d+\s*[集期]", label):
                names[sid] = label
        return names

    @classmethod
    def _normalize_episode(cls, name):
        value = cls._clean_text(name)
        found = re.search(r"第\s*0*(\d+)\s*[集期]", value)
        if found:
            return "第" + str(int(found.group(1))) + "集"
        return value or "播放"

    def playerContent(self, flag, id, vipFlags=None):
        play_url = self._absolute(str(id or ""), self.host)
        headers = self._play_headers(play_url)
        if self._is_media_url(play_url):
            return self._direct_result(play_url, headers)
        source = self._get_text(play_url, referer=self._origin_root(play_url))
        if not source:
            return {"parse": 1, "jx": 0, "url": play_url, "header": headers}
        for variable in ("player_aaaa", "player_data", "MacPlayer"):
            config = self._extract_js_object(source, variable)
            if not config:
                continue
            decoded = self._decode_url(self._find_url(config), config.get("encrypt"), play_url)
            if self._is_media_url(decoded):
                return self._direct_result(decoded, headers)
        direct = self._extract_direct_media(source, play_url)
        if direct:
            return self._direct_result(direct, headers)
        iframe = re.search(r"<iframe\b[^>]*src=[\"']([^\"']+)", source or "", re.I)
        if iframe:
            return {"parse": 1, "jx": 0, "url": self._absolute(iframe.group(1), play_url), "header": headers}
        return {"parse": 1, "jx": 0, "url": play_url, "header": headers}

    @staticmethod
    def _extract_js_object(source, variable):
        match = re.search(rf"(?:var\s+|let\s+|const\s+|window\.)?{re.escape(variable)}\s*=\s*", source or "", re.I)
        if not match:
            return {}
        start = source.find("{", match.end())
        if start < 0:
            return {}
        depth, quote_char, escaped = 0, "", False
        for index in range(start, min(len(source), start + 150000)):
            char = source[index]
            if quote_char:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote_char:
                    quote_char = ""
            elif char in ("'", '"'):
                quote_char = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    text = source[start:index + 1]
                    try:
                        value = json.loads(text)
                    except Exception:
                        try:
                            value = ast.literal_eval(text)
                        except Exception:
                            value = {}
                    return value if isinstance(value, dict) else {}
        return {}

    @classmethod
    def _find_url(cls, config):
        for key in ("url", "play_url", "playUrl", "src", "m3u8"):
            if config.get(key):
                return str(config[key])
        for value in config.values():
            if isinstance(value, dict):
                found = cls._find_url(value)
                if found:
                    return found
        return ""

    def _decode_url(self, raw_url, encrypt, page_url):
        raw = html_module.unescape(str(raw_url or "")).replace("\\/", "/").strip()
        candidates = [raw, unquote(raw)]
        decoded = self._decode_base64(raw)
        if decoded:
            candidates.extend((decoded, unquote(decoded)))
        for candidate in candidates:
            candidate = html_module.unescape(candidate).replace("\\/", "/").strip()
            if candidate.startswith(("http://", "https://", "//", "/")):
                return self._absolute(candidate, page_url)
        return ""

    @staticmethod
    def _decode_base64(value):
        try:
            text = str(value or "").strip()
            return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)).decode("utf-8", "ignore")
        except Exception:
            return ""

    def _extract_direct_media(self, source, page_url):
        text = html_module.unescape(source or "").replace("\\/", "/")
        for pattern in (r"https?://[^\"'<>\s]+?\.m3u8(?:\?[^\"'<>\s]*)?", r"https?://[^\"'<>\s]+?\.(?:mp4|flv|mkv|webm)(?:\?[^\"'<>\s]*)?"):
            found = re.search(pattern, text, re.I)
            if found:
                return self._absolute(found.group(0), page_url)
        return ""

    @classmethod
    def _is_media_url(cls, url):
        lower = html_module.unescape(str(url or "")).lower()
        return lower.startswith(("http://", "https://")) and any(ext in lower for ext in cls.MEDIA_EXTENSIONS)

    def _play_headers(self, referer):
        headers = {"User-Agent": self.ua, "Referer": referer}
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def _direct_result(self, url, headers):
        return {"parse": 0, "jx": 0, "url": url, "header": headers}

    @staticmethod
    def _origin_root(url):
        parsed = urlparse(url)
        return "%s://%s/" % (parsed.scheme, parsed.netloc) if parsed.scheme and parsed.netloc else url

    def isVideoFormat(self, url):
        return self._is_media_url(url)

    def manualVideoCheck(self):
        return False
