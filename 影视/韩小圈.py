# -*- coding: utf-8 -*-
"""韩小圈（jennyhow.com）Yingxia / CatVod Python Spider.

Converted from guoapp-modules/hanxiaoquan/main.js.
Supported source behavior:
- Categories: latest Korean dramas, Korean movies, Korean variety, Korean anime.
- Catalogue pages: /hxq/{category}.html and /hxq/{category}-{page}.html
- Search: /search.php?searchword=...
- Details: /hanxiaoquan/{numeric_id}.html
- Episodes: /play/{a}-{b}-{c}.html, choosing the playlist group with most episodes
- Playback: parse `var now = "..."` or find a direct m3u8/mp4 URL on the play page.

The original JS has no dedicated home recommendation method. For CatVod/Yingxia
compatibility, homeVideoContent uses page 1 of the first category (最新韩剧).
"""

import html
import json
import random
import re
import time
from urllib.parse import quote_plus, urljoin, urlsplit

import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:  # Permit syntax/fixture tests outside Yingxia.
    class BaseSpider(object):
        pass


SITE = "https://www.jennyhow.com"
SOURCE_NAME = "韩小圈"
PAGE_SIZE = 24
TIMEOUT = (8, 20)
UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Mobile Safari/537.36"
)

CATEGORIES = [
    {"type_id": "1", "type_name": "最新韩剧"},
    {"type_id": "2", "type_name": "韩国电影"},
    {"type_id": "3", "type_name": "韩国综艺"},
    {"type_id": "4", "type_name": "韩国动漫"},
]

CARD_PIC_RE = re.compile(
    r'<a href="/hanxiaoquan/(\d+)\.html"[^>]*title="([^"]*)"[^>]*class="module-item-pic"',
    re.I | re.S,
)
CARD_IMAGE_RE = re.compile(r'<img[^>]*data-src="([^"]+)"', re.I | re.S)
CARD_TEXT_RE = re.compile(
    r'<a href="/hanxiaoquan/\d+\.html"[^>]*class="module-item-title"[^>]*>([^<]*)</a>',
    re.I | re.S,
)
CARD_NOTE_RE = re.compile(r'class="module-item-text"[^>]*>([^<]*)<', re.I | re.S)
AD_TEXT_RE = re.compile(r"@[^@]{1,60}@")
TITLE_RE = re.compile(r'<h1 class="page-title"[^>]*>(.*?)</h1>', re.I | re.S)
OG_IMAGE_RE = re.compile(r'property="og:image"\s+content="([^"]+)"', re.I | re.S)
COVER_SOURCE_RE = re.compile(
    r'<div class="video-cover">.*?<img[^>]*data-src="([^"]+)"', re.I | re.S
)
INFO_ITEM_RE = re.compile(
    r'<span class="video-info-itemtitle">([^<]*)</span>\s*'
    r'<div class="video-info-item[^"]*">(.*?)</div>',
    re.I | re.S,
)
LINE_TAB_RE = re.compile(
    r'href="#playlist(\d+)"[^>]*>\s*<i[^>]*></i>\s*([^<]+)', re.I | re.S
)
EPISODE_RE = re.compile(
    r'<a title="([^"]*)" href="(/play/\d+-\d+-\d+\.html)"', re.I | re.S
)
NOW_RE = re.compile(r'var\s+now\s*=\s*["\']([^"\']+)["\']', re.I | re.S)
MEDIA_RE = re.compile(
    r'https?://[^"\'\s<>\\]+\.(?:m3u8|mp4)(?:\?[^"\'\s<>\\]*)?', re.I
)
BROWSER_CHECK_RE = re.compile(r'document\.cookie\s*=\s*["\'](idc_search_browser=[0-9a-f]+)', re.I)
TAG_RE = re.compile(r"<[^>]+>")
LEADING_NUMBER_RE = re.compile(r"(\d+)")


def _json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _text(value, default=""):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _decode_html_entities(value):
    text = str(value or "")
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    return text


def _clean(value):
    if value is None:
        return ""
    text = _decode_html_entities(TAG_RE.sub("", str(value)))
    text = text.replace("　", " ")
    return " ".join(text.split())


def _truncate(value, limit):
    value = _text(value)
    return value if len(value) <= limit else value[:limit] + "..."


def _valid_numeric_id(value):
    value = _text(value)
    return bool(re.fullmatch(r"\d{1,12}", value)) and int(value) > 0


def _http_url(raw, base=SITE):
    raw = _text(raw)
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    absolute = urljoin(base.rstrip("/") + "/", raw)
    try:
        parsed = urlsplit(absolute)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return ""
        return absolute
    except Exception:
        return ""


def _play_page_url(raw):
    url = _http_url(raw)
    if not url:
        return ""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in ("jennyhow.com", "www.jennyhow.com"):
        return ""
    if "/play/" not in parsed.path.lower() or not parsed.path.lower().endswith(".html"):
        return ""
    if not re.search(r"/play/\d+-\d+-\d+\.html$", parsed.path, re.I):
        return ""
    return url


def _parse_cards(body):
    body = str(body or "")
    items = []
    seen = set()
    for match in CARD_PIC_RE.finditer(body):
        source_id = match.group(1)
        title = _clean(match.group(2))
        if not _valid_numeric_id(source_id) or source_id in seen:
            continue
        chunk = body[match.end():match.end() + 600]
        image_match = CARD_IMAGE_RE.search(chunk)
        cover = _http_url(image_match.group(1)) if image_match else ""
        note_match = CARD_NOTE_RE.search(chunk)
        note = _clean(note_match.group(1)) if note_match else ""
        if not title:
            title_match = CARD_TEXT_RE.search(chunk)
            title = _clean(title_match.group(1)) if title_match else ""
        if not title:
            continue
        seen.add(source_id)
        items.append({
            "vod_id": source_id,
            "vod_name": _truncate(title, 512),
            "vod_pic": cover,
            "vod_remarks": _truncate(note, 64),
        })
        if len(items) >= 500:
            break
    return items


def _page_count(body, category, page, count):
    pattern = re.compile(r"/hxq/" + re.escape(str(category)) + r"-(\d+)\.html", re.I)
    max_page = page
    for match in pattern.finditer(str(body or "")):
        try:
            value = int(match.group(1))
            if max_page < value < 100000:
                max_page = value
        except Exception:
            continue
    if max_page > page:
        return max_page
    return page + 1 if count >= PAGE_SIZE else page


def _info_fields(body):
    fields = {}
    for match in INFO_ITEM_RE.finditer(str(body or "")):
        label = _clean(match.group(1)).rstrip("：:").strip()
        value = _clean(match.group(2))
        if label and value and label not in fields:
            fields[label] = value
    return fields


def _pick_playlist(body, source_id):
    body = str(body or "")
    line_ids = sorted(set(match.group(1) for match in LINE_TAB_RE.finditer(body)))
    if not line_ids:
        line_ids = [""]
    best = []

    for line_id in line_ids:
        segment = body
        if line_id:
            marker = 'id="playlist' + line_id + '"'
            start = body.find(marker)
            if start < 0:
                continue
            segment = body[start + len(marker):]
            end = segment.find('id="playlist')
            if end < 0:
                end = segment.find('class="module-footer"')
            if end >= 0:
                segment = segment[:end]

        chapters = []
        seen_urls = set()
        index = 0
        for episode in EPISODE_RE.finditer(segment):
            index += 1
            title = _clean(episode.group(1))
            page_url = _play_page_url(episode.group(2))
            if not page_url or page_url in seen_urls:
                continue
            seen_urls.add(page_url)
            order = index
            number_match = LEADING_NUMBER_RE.search(title)
            if number_match and len(number_match.group(1)) <= 6:
                parsed = int(number_match.group(1))
                if 0 < parsed <= 100000:
                    order = parsed
            if not title:
                title = "第 %d 集" % order
            title = re.sub(r"[$#\r\n]+", " ", title).strip() or ("第 %d 集" % order)
            chapters.append((order, title, page_url))

        if len(chapters) > len(best):
            best = chapters

    if not best:
        return []
    best.sort(key=lambda item: item[0])
    return best


def _safe_page(value):
    try:
        return max(1, min(int(value), 100000))
    except Exception:
        return 1


def _b36(value):
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    value = max(0, int(value))
    if value == 0:
        return "0"
    out = ""
    while value:
        value, rem = divmod(value, 36)
        out = chars[rem] + out
    return out


class Spider(BaseSpider):
    def getName(self):
        return SOURCE_NAME

    def init(self, extend=""):
        self.extend = {}
        if isinstance(extend, dict):
            self.extend = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                parsed = json.loads(extend)
                if isinstance(parsed, dict):
                    self.extend = parsed
            except Exception:
                self.extend = {}

        self.site = _text(self.extend.get("site") or SITE).rstrip("/")
        try:
            parsed = urlsplit(self.site)
            if parsed.scheme not in ("http", "https") or parsed.hostname not in ("jennyhow.com", "www.jennyhow.com"):
                self.site = SITE
        except Exception:
            self.site = SITE

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Referer": self.site + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _get(self, path_or_url, headers=None, timeout=TIMEOUT):
        url = path_or_url if str(path_or_url).startswith(("http://", "https://")) else self.site + str(path_or_url)
        request_headers = {"User-Agent": UA, "Referer": self.site + "/"}
        if headers:
            request_headers.update(headers)
        response = self.session.get(url, headers=request_headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() in ("iso-8859-1", "ascii"):
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text or "", response.url

    @staticmethod
    def _failure(message):
        return _json({"list": [], "msg": _text(message, "韩小圈请求失败")})

    # Home and category navigation
    def homeContent(self, filter):
        return _json({"class": CATEGORIES, "filters": {}})

    def homeVideoContent(self):
        # main.js defines no separate homepage recommendation endpoint.
        # Use the first page of its first catalog category for the host contract.
        return self.categoryContent("1", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            category = _text(tid)
            if category not in ("1", "2", "3", "4"):
                raise RuntimeError("韩小圈内容分类无效")
            page = _safe_page(pg)
            path = "/hxq/%s.html" % category if page == 1 else "/hxq/%s-%d.html" % (category, page)
            body, _ = self._get(path)
            items = _parse_cards(body)
            return _json({
                "page": page,
                "pagecount": _page_count(body, category, page, len(items)),
                "limit": PAGE_SIZE,
                "total": 0,
                "list": items,
            })
        except Exception as exc:
            return self._failure(exc)

    # Search; main.js supports only the first result page and includes a browser check retry.
    def searchContent(self, key, quick, pg="1"):
        try:
            query = _text(key).strip()
            if not query or len(query) > 256:
                return _json({"list": []})
            page = _safe_page(pg)
            if page > 1:
                return _json({"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []})

            path = "/search.php?searchword=" + quote_plus(query, safe="")
            body, actual_url = self._get(path)
            browser_check = BROWSER_CHECK_RE.search(body)
            if browser_check:
                cookie_value = browser_check.group(1)
                pass_token = _b36(int(time.time() * 1000)) + _b36(random.randint(36 ** 4, 36 ** 6 - 1))[:6]
                separator = "&" if "?" in actual_url else "?"
                retry_url = actual_url + separator + "_idc_pass=" + quote_plus(pass_token)
                body, _ = self._get(
                    retry_url,
                    headers={"Referer": actual_url, "Cookie": cookie_value},
                )
            items = _parse_cards(body)
            return _json({"page": 1, "pagecount": 1, "limit": PAGE_SIZE, "total": len(items), "list": items})
        except Exception as exc:
            return self._failure(exc)

    # Detail
    def detailContent(self, ids):
        try:
            if isinstance(ids, (list, tuple)):
                source_id = _text(ids[0]) if ids else ""
            elif isinstance(ids, dict):
                source_id = _text(ids.get("vod_id") or ids.get("id") or ids.get("vodId"))
            else:
                source_id = _text(ids)
                if source_id.startswith("["):
                    try:
                        decoded = json.loads(source_id)
                        if isinstance(decoded, list) and decoded:
                            source_id = _text(decoded[0])
                    except Exception:
                        pass
            if not _valid_numeric_id(source_id):
                raise RuntimeError("韩小圈影片 ID 无效")

            body, _ = self._get("/hanxiaoquan/%s.html" % source_id)
            title_match = TITLE_RE.search(body)
            name = _clean(title_match.group(1)) if title_match else ""
            if not name:
                raise RuntimeError("韩小圈详情缺少视频名称")

            image_match = OG_IMAGE_RE.search(body)
            cover = _http_url(image_match.group(1), self.site) if image_match else ""
            if not cover:
                cover_match = COVER_SOURCE_RE.search(body)
                cover = _http_url(cover_match.group(1), self.site) if cover_match else ""

            fields = _info_fields(body)
            description = _truncate(AD_TEXT_RE.sub("", fields.get("剧情") or fields.get("简介") or ""), 12000)
            chapters = _pick_playlist(body, source_id)

            vod = {
                "vod_id": source_id,
                "vod_name": _truncate(name, 512),
                "vod_content": description,
            }
            if cover:
                vod["vod_pic"] = cover

            update_note = fields.get("更新") or fields.get("状态") or ""
            if update_note:
                vod["vod_remarks"] = _truncate(update_note, 64)
            if fields.get("上映"):
                vod["vod_year"] = fields["上映"]
            if fields.get("导演"):
                vod["vod_director"] = fields["导演"]
            if fields.get("主演"):
                vod["vod_actor"] = fields["主演"]
            if fields.get("类型"):
                vod["vod_class"] = fields["类型"]
            if fields.get("地区"):
                vod["vod_area"] = fields["地区"]
            if fields.get("语言"):
                vod["vod_lang"] = fields["语言"]

            if chapters:
                vod["vod_play_from"] = SOURCE_NAME
                vod["vod_play_url"] = "#".join(
                    "%s$%s" % (title, page_url) for _, title, page_url in chapters
                )

            return _json({"list": [vod]})
        except Exception as exc:
            return self._failure(exc)

    # Playback
    def playerContent(self, flag, id, vipFlags):
        try:
            page_url = _play_page_url(_text(id))
            if not page_url:
                raise RuntimeError("韩小圈播放页地址无效")
            body, _ = self._get(page_url, headers={"Referer": self.site + "/"})
            now_match = NOW_RE.search(body)
            media_url = _text(now_match.group(1)) if now_match else ""
            if not media_url:
                media_match = MEDIA_RE.search(body)
                media_url = media_match.group(0) if media_match else ""
            if media_url.startswith("//"):
                media_url = "https:" + media_url
            media_url = _http_url(media_url, page_url)
            if not media_url:
                raise RuntimeError("韩小圈该集暂无可用播放地址")
            parsed = urlsplit(media_url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise RuntimeError("韩小圈播放地址无效")
            return _json({"parse": 0, "url": media_url, "header": {"Referer": self.site + "/", "User-Agent": UA}})
        except Exception as exc:
            return self._failure(exc)

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|m4v|mpd|flv|ts)(?:\?|$)", _text(url), re.I))

    def manualVideoCheck(self):
        return False


# Optional TVBox/CatVod registration snippet.
TVBOX_SOURCE_CONFIG = {
    "sites": [{
        "key": "hanxiaoquan",
        "name": SOURCE_NAME,
        "type": 3,
        "api": "./hanxiaoquan.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 0,
        "changeable": 1,
        "timeout": 30,
        "ext": "",
    }]
}
TVBOX_SOURCE_CONFIG_JSON = _json(TVBOX_SOURCE_CONFIG)
