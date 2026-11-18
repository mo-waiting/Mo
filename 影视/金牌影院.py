# -*- coding: utf-8 -*-
"""金牌影院 (jiabaide.cn) - Yingxia / CatVod Python Spider.

Source contract:
  type=3, api="./jpyy.py"
  Python entry points: homeContent, homeVideoContent, categoryContent,
  detailContent, searchContent, playerContent.

API and signing details are ported from the supplied XPTV jpyy source:
  * home:   /api/mw-movie/anonymous/v1/home/all/list (aggregate homepage shelves)
  * list:   /api/mw-movie/anonymous/video/list
  * search: /api/mw-movie/anonymous/video/searchByWordPageable
  * detail: /api/mw-movie/anonymous/video/detail?id=<video id> (episodelist)
             with the original mobile HTML episodeList parser as fallback
  * play:   /api/mw-movie/anonymous/v2/video/episode/url

Blank and placeholder metadata values (for example 未知/暂无/null) are omitted.
The source mirrors the linked jpyy.js endpoints, filter options, and signature scheme. It
contains no account credentials and does not bypass login, CAPTCHA, DRM, or
other access controls. Real network playback must still be verified in Yingxia.
"""

import hashlib
import html
import json
import re
import time
import uuid
from urllib.parse import urlencode, quote

import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:  # Allows local syntax/fixture tests outside Yingxia.
    class BaseSpider(object):
        pass


BASE = "https://www.jiabaide.cn"
MOBILE = "https://m.jiabaide.cn"
SIGN_KEY = "cb808529bae6b6be45ecfab29a4889bc"
PAGE_SIZE = 30
SEARCH_PAGE_SIZE = 12
TIMEOUT = (8, 20)
# Module cache also survives a new Spider instance while the interpreter stays alive.
_VIDEO_CACHE = {}
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

# The linked jpyy.js explicitly supplies User-Agent plus the signing headers
# for JSON endpoints, and only User-Agent for the mobile detail HTML page.
JSON_HEADERS = {"User-Agent": UA}
HTML_HEADERS = {"User-Agent": UA}
PLAY_HEADERS = {"User-Agent": UA}

TYPE_OPTIONS = {
    "1": [
        ("喜剧", "22"), ("动作", "23"), ("科幻", "30"), ("爱情", "26"),
        ("悬疑", "27"), ("奇幻", "87"), ("剧情", "37"), ("恐怖", "36"),
        ("犯罪", "35"), ("动画", "33"), ("惊悚", "34"), ("战争", "25"),
        ("冒险", "31"), ("灾难", "81"), ("伦理", "83"), ("其他", "43"),
    ],
    "2": [("国产剧", "14"), ("欧美剧", "15"), ("港台剧", "16"), ("日韩剧", "62"), ("其他剧", "68")],
    "3": [("国产综艺", "69"), ("港台综艺", "70"), ("日韩综艺", "72"), ("欧美综艺", "73")],
    "4": [("国产动漫", "75"), ("日韩动漫", "76"), ("欧美动漫", "77")],
}
CLASS_OPTIONS = {
    "1": ["爱情", "动作", "喜剧", "战争", "科幻", "剧情", "武侠", "冒险", "枪战", "恐怖", "其他"],
    "2": ["古装", "战争", "喜剧", "家庭", "犯罪", "动作", "奇幻", "剧情", "历史", "短片", "其他"],
    "3": ["真人秀", "音乐", "脱口秀"],
    "4": ["喜剧", "科幻", "热血", "冒险", "动作", "运动", "战争", "动画"],
}
AREA_OPTIONS = {
    "1": ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国", "印度", "泰国", "英国", "法国", "其他"],
    "2": ["中国大陆", "中国香港", "中国台湾", "日本", "韩国", "美国", "泰国", "其他"],
    "3": ["中国大陆", "中国香港", "中国台湾", "日本", "韩国", "美国", "其他"],
    "4": ["中国大陆", "日本", "美国", "其他"],
}
LANG_OPTIONS = {
    "1": ["国语", "英语", "粤语", "韩语", "日语", "其他"],
    "2": ["国语", "英语", "粤语", "韩语", "日语", "泰语", "其他"],
    "3": ["国语", "英语", "粤语", "韩语", "日语", "其他"],
    "4": ["国语", "英语", "日语", "其他"],
}
YEAR_OPTIONS = {
    "1": [str(y) for y in range(2026, 2009, -1)] + ["2009~2000"],
    "2": [str(y) for y in range(2026, 2009, -1)],
    "3": [str(y) for y in range(2026, 2019, -1)],
    "4": [str(y) for y in range(2026, 2009, -1)],
}



def _json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _text(value, default=""):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _first(obj, names, default=""):
    if not isinstance(obj, dict):
        return default
    for name in names:
        value = obj.get(name)
        if value not in (None, "", [], {}):
            return value
    return default


def _option_group(key, name, values):
    return {
        "key": key,
        "name": name,
        "value": [{"n": "全部", "v": ""}] + [{"n": str(v), "v": str(v)} for v in values],
    }


def _filters(type_id):
    """Mirror the filter keys and values in the source jpyy.js."""
    type_id = str(type_id)
    type_values = [
        {"n": name, "v": value}
        for name, value in TYPE_OPTIONS.get(type_id, [])
    ]
    return [
        {"key": "type", "name": "类型", "value": [{"n": "全部", "v": ""}] + type_values},
        _option_group("class", "剧情", CLASS_OPTIONS.get(type_id, [])),
        _option_group("area", "地区", AREA_OPTIONS.get(type_id, [])),
        _option_group("year", "年份", YEAR_OPTIONS.get(type_id, [])),
        _option_group("lang", "语言", LANG_OPTIONS.get(type_id, [])),
        {"key": "sort", "name": "排序", "value": [
            {"n": "最近更新", "v": "2"},
            {"n": "人气高低", "v": "3"},
            {"n": "评分高低", "v": "4"},
        ]},
    ]



def _format_score(value):
    value = _clean_display_value(value)
    if not value:
        return ""
    try:
        return "%.1f" % float(value)
    except Exception:
        return value


def _map_vod(item):
    """Map original list/search API fields, omitting blank/unknown values."""
    item = item if isinstance(item, dict) else {}
    video_id = _clean_display_value(_first(item, ("vodId", "vod_id", "videoId", "video_id", "id")))
    name = _clean_display_value(_first(item, ("vodName", "vod_name", "name", "title")))
    pic = _clean_display_value(_first(item, ("vodPic", "vod_pic", "pic", "cover", "coverUrl")))
    score = _format_score(_first(item, ("vodDoubanScore", "vod_douban_score", "score", "rating")))
    remarks = _clean_display_value(_first(item, ("vodRemarks", "vod_remarks", "remarks")))
    # Original JS: vodRemarks.replace(/\|.*/, '') || vodVersion
    duration_or_remark = _clean_display_value(remarks.split("|", 1)[0])
    if not duration_or_remark:
        duration_or_remark = _clean_display_value(_first(item, ("vodVersion", "vod_version", "version")))
    pubdate = _clean_display_value(_first(item, ("vodPubdate", "vod_pubdate", "pubdate", "releaseDate", "year")))

    result = {"vod_id": _text(video_id)}
    if name:
        result["vod_name"] = name
    if pic:
        result["vod_pic"] = pic
    if score:
        # The original source puts the Douban rating in vod_remarks.
        result["vod_remarks"] = score
    if duration_or_remark:
        result["vod_duration"] = duration_or_remark
    if pubdate:
        # Keep the original API value and provide the conventional year field
        # when a 4-digit year is present, without inventing a missing value.
        result["vod_pubdate"] = pubdate
        year_match = re.search(r"(?:19|20)\d{2}", pubdate)
        if year_match:
            result["vod_year"] = year_match.group(0)
    return result


def _unwrap_payload(data):
    if isinstance(data, dict) and "data" in data and data.get("data") is not None:
        return data.get("data")
    return data


def _get_ci(obj, names, default=None):
    """Read an object key without depending on camelCase/snake_case casing."""
    if not isinstance(obj, dict):
        return default
    wanted = {str(name).casefold() for name in names}
    for key, value in obj.items():
        if str(key).casefold() in wanted and value not in (None, "", [], {}):
            return value
    return default


def _decode_episode_payload(value):
    """Normalize the detail API's episodellist value to Python objects."""
    if isinstance(value, str):
        raw = html.unescape(value).strip()
        if not raw:
            return []
        for candidate in (raw, raw.replace(r'\"', '"').replace(r"\/", "/")):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, (list, dict)):
                    return parsed
            except Exception:
                pass
        # Some deployments return a JS-style serialized array. Reuse the
        # parser against a synthetic episodeList assignment.
        parsed = _extract_episode_list('episodeList:' + raw)
        return parsed
    return value


def _flatten_episode_rows(value):
    """Flatten episode arrays/groups while keeping only entries with a nid."""
    value = _decode_episode_payload(value)
    output = []
    seen = set()
    container_keys = (
        "episodelist", "episodeList", "episode_list", "episodes", "list",
        "tracks", "children", "items", "data", "videos", "videoList",
        "playList", "playlist", "sourceList", "lineList",
    )

    def walk(node):
        if isinstance(node, str):
            decoded = _decode_episode_payload(node)
            if decoded is not node and isinstance(decoded, (list, dict)):
                walk(decoded)
            return
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return

        nid = _get_ci(node, ("nid", "episodeId", "episode_id", "id"))
        name = _get_ci(node, ("name", "title", "episodeName", "episode_name"))
        if nid not in (None, "") and name not in (None, ""):
            marker = (str(nid), str(name))
            if marker not in seen:
                seen.add(marker)
                output.append(node)
            return

        # Prefer known grouping fields; if a site build changes the group key,
        # inspect remaining nested objects/arrays as a defensive fallback.
        visited = set()
        for key in container_keys:
            child = _get_ci(node, (key,))
            if child is not None:
                visited.add(key.casefold())
                walk(child)
        for key, child in node.items():
            if str(key).casefold() not in visited and isinstance(child, (dict, list)):
                walk(child)

    walk(value)
    return output


def _episodes_from_detail_payload(data):
    """Read lowercase episodelist (legacy API) or camelCase episodeList."""
    root = _unwrap_payload(data)
    # Some API builds wrap the video object one more time.
    if isinstance(root, dict):
        nested = _get_ci(root, ("video", "detail", "item"))
        if isinstance(nested, dict):
            root = nested
    episode_value = _get_ci(root, ("episodelist", "episodeList", "episode_list"))
    return _flatten_episode_rows(episode_value), root if isinstance(root, dict) else {}


def _rows_and_total(data):
    root = _unwrap_payload(data)
    if isinstance(root, list):
        return root, len(root), 1
    if not isinstance(root, dict):
        return [], 0, 1
    rows = _first(root, ("list", "records", "items", "content", "rows"), [])
    if not isinstance(rows, list):
        rows = []
    total = _first(root, ("total", "totalCount", "totalElements", "count"), len(rows))
    pages = _first(root, ("totalPage", "totalPages", "pageCount", "pages"), 0)
    try:
        total = int(total)
    except Exception:
        total = len(rows)
    try:
        pages = int(pages)
    except Exception:
        pages = 0
    return rows, total, pages


def _home_aggregate_rows(data):
    """Extract movie rows from the site's v1/home/all/list response.

    A known public implementation iterates data.values() and extends each
    group's ``list``. This parser follows that response shape, while also
    accepting a directly returned list and common wrapper variants.
    """
    root = _unwrap_payload(data)
    rows = []

    def add_group(group):
        if isinstance(group, list):
            rows.extend(item for item in group if isinstance(item, dict))
            return
        if not isinstance(group, dict):
            return
        group_rows = _get_ci(group, ("list", "records", "items", "content", "rows"))
        if isinstance(group_rows, list):
            rows.extend(item for item in group_rows if isinstance(item, dict))
            return
        # Some builds may expose one card directly rather than a group object.
        if _first(group, ("vodId", "vod_id", "videoId", "video_id", "id")) not in (None, ""):
            rows.append(group)

    if isinstance(root, list):
        for entry in root:
            add_group(entry)
    elif isinstance(root, dict):
        # Some wrappers put the aggregate result under a nested list/data key.
        direct = _get_ci(root, ("list", "records", "items", "content", "rows"))
        if isinstance(direct, list):
            rows.extend(item for item in direct if isinstance(item, dict))
        else:
            for group in root.values():
                add_group(group)

    return rows


def _safe_page(value):
    try:
        return max(1, int(value))
    except Exception:
        return 1


def _extract_episode_list(page_html):
    """Extract the episodeList array from the mobile detail page.

    The first strategy mirrors the original XPTV jpyy.js parser. Extra passes
    handle HTML entities and one or more layers of JSON/JS string escaping.
    """
    raw = str(page_html or "")
    if not raw:
        return []

    sources = []
    current = raw
    for _ in range(4):
        current = html.unescape(current)
        current = current.replace(r"\/", "/")
        current = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda m: chr(int(m.group(1), 16)),
            current,
        )
        sources.append(current)
        # Unwrap common escaped JSON/JS string layers. Repeat because some
        # server builds serialize an already escaped state object.
        unescaped = current.replace(r'\\"', '"').replace(r'\"', '"')
        unescaped = unescaped.replace(r"\\/", "/")
        if unescaped == current:
            break
        current = unescaped

    def _parse_array(candidate):
        candidate = candidate.strip()
        candidates = [candidate, re.sub(r",\s*([}\]])", r"\1", candidate)]
        for text_candidate in candidates:
            try:
                value = json.loads(text_candidate)
                if isinstance(value, list):
                    return value
            except Exception:
                pass

        # Common JavaScript literal form: single quotes and unquoted keys.
        js_candidate = candidate.replace("'", '"')
        js_candidate = re.sub(
            r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:", r'\1"\2":', js_candidate
        )
        js_candidate = re.sub(r",\s*([}\]])", r"\1", js_candidate)
        js_candidate = re.sub(r"\bundefined\b", "null", js_candidate)
        try:
            value = json.loads(js_candidate)
            return value if isinstance(value, list) else []
        except Exception:
            return []

    # Match the exact fragment form used by the original XPTV implementation.
    for source in sources:
        original_match = re.search(
            r"episodeList[\s\S]*?\[[\s\S]*?\}\]\}", source, flags=re.I
        )
        if original_match:
            fragment = '{"' + original_match.group(0)
            fragment = fragment.replace(r'\\"', '"').replace(r'\"', '"')
            try:
                parsed = json.loads(fragment)
                episodes = parsed.get("episodeList") if isinstance(parsed, dict) else None
                if isinstance(episodes, list):
                    return episodes
            except Exception:
                pass

    # Balanced-array fallback. Search each marker occurrence because pages can
    # contain an unrelated template marker before the real hydrated state.
    for source in sources:
        for marker in re.finditer(r"episodeList", source, flags=re.I):
            start = source.find("[", marker.end())
            if start < 0:
                continue
            depth = 0
            in_string = False
            quote_char = ""
            escaped = False
            for pos in range(start, len(source)):
                char = source[pos]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote_char:
                        in_string = False
                        quote_char = ""
                    continue
                if char in ('"', "'"):
                    in_string = True
                    quote_char = char
                elif char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                    if depth == 0:
                        parsed = _parse_array(source[start:pos + 1])
                        if parsed:
                            return parsed
                        break
    return []


def _page_title(page_html, fallback=""):
    source = str(page_html or "")
    match = re.search(r"<title[^>]*>([\s\S]*?)</title>", source, flags=re.I)
    if match:
        title = re.sub(r"<[^>]+>", " ", match.group(1))
        title = re.sub(r"\s+", " ", html.unescape(title)).strip()
        title = re.split(r"\s*[-_|｜]\s*金牌影院", title, maxsplit=1)[0].strip()
        if title:
            return title
    # Meta attributes can occur in either order (property before content or
    # content before property), so parse each tag rather than assuming order.
    for tag in re.findall(r"<meta\b[^>]*>", source, flags=re.I):
        name = re.search(r"(?:property|name)=[\"'](?:og:title|title)[\"']", tag, flags=re.I)
        content = re.search(r"content=[\"']([^\"']+)", tag, flags=re.I)
        if name and content:
            return html.unescape(content.group(1)).strip()
    return fallback


def _clean_display_value(value):
    """Return an empty string for blank or placeholder metadata values."""
    value = _text(value).strip()
    if not value:
        return ""

    normalized = re.sub(r"\s+", "", value).casefold()
    placeholders = {
        "none", "null", "undefined", "nan", "n/a", "na", "nil",
        "未知", "暂无", "暂无数据", "无", "不详", "未填写", "未提供",
        "未录入", "空", "-", "--", "—", "－", "/",
    }
    if normalized in placeholders:
        return ""

    # Common site placeholders such as “未知年份” or “暂无评分”.
    if re.fullmatch(
        r"(?:未知|暂无|未提供|未填写|未录入)(?:信息|数据|年份|类型|地区|评分|片长|导演|演员|简介)?",
        value,
        flags=re.I,
    ):
        return ""
    return value




class Spider(BaseSpider):
    """CatVod-compatible Python spider for Yingxia on supported platforms."""

    def getName(self):
        return "金牌影院"

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

        self.base = _text(self.extend.get("site") or self.extend.get("base") or BASE).rstrip("/")
        if not self.base.startswith(("http://", "https://")):
            self.base = BASE
        self.mobile = re.sub(r"^https?://www\.", "https://m.", self.base, flags=re.I)
        self.session = requests.Session()
        self.session.headers.update(JSON_HEADERS)
        # Keep exact list/search API rows so detailContent can display the
        # fields returned by the original list API without guessing a detail API.
        self.video_cache = _VIDEO_CACHE

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|m4v|mpd|flv|ts)(?:\?|$)", str(url or ""), re.I))

    def manualVideoCheck(self):
        return False

    # ----------------------------- HTTP / signing -----------------------------

    @staticmethod
    def _query_string(params):
        # Keep insertion order and raw values for the original site signature.
        return "&".join("%s=%s" % (key, _text(value)) for key, value in params.items())

    @classmethod
    def _signature_headers(cls, params):
        timestamp = str(int(time.time() * 1000))
        sign_source = cls._query_string(params)
        if sign_source:
            sign_source += "&"
        sign_source += "key=" + SIGN_KEY + "&t=" + timestamp
        md5_hex = hashlib.md5(sign_source.encode("utf-8")).hexdigest()
        sign = hashlib.sha1(md5_hex.encode("ascii")).hexdigest()
        headers = dict(JSON_HEADERS)
        headers.update({
            "deviceId": str(uuid.uuid4()),
            "t": timestamp,
            "sign": sign,
        })
        return headers

    def _request_json(self, url, params_for_sign):
        response = self.session.get(
            url,
            headers=self._signature_headers(params_for_sign),
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = json.loads(response.text)
        if not isinstance(data, (dict, list)):
            raise RuntimeError("接口返回格式不正确")
        return data

    def _request_html(self, url, referer=None):
        # The original jpyy.js detail request sends only its browser User-Agent.
        # Use a clean request rather than inheriting JSON API Origin/Accept
        # headers from self.session; those headers can trigger a different
        # mobile-page response on some deployments.
        headers = {"User-Agent": UA}
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() in ("iso-8859-1", "ascii"):
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text or ""

    @staticmethod
    def _failure(message):
        return _json({"list": [], "msg": _text(message, "金牌影院请求失败")})

    # ---------------------------------- 首页 ----------------------------------

    def homeContent(self, filter):
        # Keep only the four original top-level content categories.
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
        ]
        filters = {str(index): _filters(str(index)) for index in range(1, 5)} if filter else {}
        return _json({"class": classes, "filters": filters})

    def homeVideoContent(self):
        """Use the first 30 valid unique items from the site's aggregate homepage feed.

        Preserve the endpoint's shelf and item order. Do not re-rank the feed or
        synthesize a separate recommendation score; only discard unusable,
        preview, and duplicate cards before applying the 30-item limit.
        """
        try:
            url = self.base + "/api/mw-movie/anonymous/v1/home/all/list"
            # The known site implementation signs this endpoint with no query
            # parameters; keep the request consistent with that contract.
            data = self._request_json(url, {})
            rows = _home_aggregate_rows(data)

            vods = []
            seen = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                vod = _map_vod(row)
                video_id = vod.get("vod_id", "")
                if not video_id or not vod.get("vod_name"):
                    continue
                if "预告" in vod.get("vod_name", ""):
                    continue
                if video_id in seen:
                    continue
                seen.add(video_id)
                self.video_cache[video_id] = row
                vods.append(vod)
                if len(vods) >= 30:
                    break

            return _json({"list": vods})
        except Exception as exc:
            return self._failure(exc)

    # -------------------------------- 分类列表 --------------------------------

    def categoryContent(self, tid, pg, filter, extend):
        try:
            ext = extend if isinstance(extend, dict) else {}
            if isinstance(extend, str) and extend.strip():
                try:
                    ext = json.loads(extend)
                except Exception:
                    ext = {}
            ext = ext if isinstance(ext, dict) else {}
            page = _safe_page(pg)
            params = {
                "area": _text(ext.get("area")),
                "filterStatus": "1",
                "lang": _text(ext.get("lang")),
                "pageNum": str(page),
                "pageSize": str(PAGE_SIZE),
                "sort": _text(ext.get("sort") or "1"),
                "sortBy": "1",
                "type": _text(ext.get("type")),
                "type1": _text(tid),
                "v_class": _text(ext.get("v_class") or ext.get("class")),
                "year": _text(ext.get("year")),
            }
            # Match the original JS toQueryString(): omit empty filters before
            # both building the request URL and signing its query parameters.
            query_params = {key: value for key, value in params.items() if value not in (None, "")}
            url = self.base + "/api/mw-movie/anonymous/video/list?" + urlencode(query_params, doseq=True)
            data = self._request_json(url, query_params)
            rows, total, page_count = _rows_and_total(data)
            rows = [row for row in rows if isinstance(row, dict) and "预告" not in _text(row.get("vodName"))]
            vods = []
            for row in rows:
                vod = _map_vod(row)
                if vod.get("vod_id") and vod.get("vod_name"):
                    self.video_cache[vod["vod_id"]] = row
                    vods.append(vod)
            calculated_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            return _json({
                "page": page,
                "pagecount": page_count or calculated_pages,
                "limit": PAGE_SIZE,
                "total": total,
                "list": vods,
            })
        except Exception as exc:
            return self._failure(exc)

    # ---------------------------------- 详情 ----------------------------------

    def detailContent(self, ids):
        try:
            if isinstance(ids, (list, tuple)):
                video_id = _text(ids[0]) if ids else ""
            elif isinstance(ids, dict):
                video_id = _text(_first(ids, ("vod_id", "id", "vodId")))
            else:
                video_id = _text(ids)
                # Some wrappers serialize the ID argument as a one-item JSON list.
                if video_id.startswith("["):
                    try:
                        decoded_ids = json.loads(video_id)
                        if isinstance(decoded_ids, list) and decoded_ids:
                            video_id = _text(decoded_ids[0])
                    except Exception:
                        pass
            if not video_id:
                raise RuntimeError("详情缺少影片 ID")

            episodes = []
            api_item = {}
            api_error = ""

            # Some records do not expose the same episodeList shape in HTML.
            # The site's detail JSON API returns the playlist as lowercase
            # `episodelist` with each entry carrying `name` + `nid`. This is
            # therefore the primary source; the original XPTV mobile-page
            # parser remains as a fallback for records where the API is empty.
            detail_params = {"id": video_id}
            detail_url = self.base + "/api/mw-movie/anonymous/video/detail?" + urlencode(detail_params)
            try:
                detail_data = self._request_json(detail_url, detail_params)
                episodes, api_item = _episodes_from_detail_payload(detail_data)
            except Exception as exc:
                api_error = _text(exc)

            page_html = ""
            if not episodes:
                detail_urls = [
                    (self.mobile + "/detail/" + quote(video_id, safe=""), self.mobile + "/"),
                    (self.base + "/detail/" + quote(video_id, safe=""), self.base + "/"),
                ]
                for page_url, referer in detail_urls:
                    try:
                        candidate_html = self._request_html(page_url, referer=referer)
                        if candidate_html:
                            page_html = candidate_html
                            episodes = _flatten_episode_rows(_extract_episode_list(candidate_html))
                        if episodes:
                            break
                    except Exception:
                        continue

            # Prefer the richer detail API object. If it is unavailable, use
            # the list/search row cache, then take the title from page HTML.
            cached_item = getattr(self, "video_cache", {}).get(video_id, {})
            source_item = api_item if api_item else cached_item
            vod = _map_vod(source_item)
            if not vod.get("vod_name"):
                title = _clean_display_value(
                    _first(source_item, ("vodName", "vod_name", "name", "title"))
                )
                if title:
                    vod["vod_name"] = title
            if not vod.get("vod_pic"):
                pic = _clean_display_value(_first(source_item, ("vodPic", "vod_pic", "pic", "cover")))
                if pic:
                    vod["vod_pic"] = pic
            if not vod.get("vod_remarks"):
                score = _format_score(_first(source_item, ("vodDoubanScore", "vod_douban_score", "score", "rating")))
                if score:
                    vod["vod_remarks"] = score
            if not vod.get("vod_name"):
                page_name = _clean_display_value(_page_title(page_html, ""))
                if page_name:
                    vod["vod_name"] = page_name
            vod["vod_id"] = video_id

            play_items = []
            for index, episode in enumerate(episodes):
                if not isinstance(episode, dict):
                    continue
                episode_id = _get_ci(episode, ("nid", "episodeId", "episode_id", "id"))
                if episode_id in (None, ""):
                    continue
                default_label = "第%d集" % (index + 1)
                label = _text(_get_ci(episode, ("name", "title", "episodeName", "episode_name"), default_label))
                label = re.sub(r"[$#\r\n]+", " ", label).strip() or default_label
                play_items.append(label + "$" + video_id + "|" + _text(episode_id))

            if play_items:
                vod.update({
                    "vod_play_from": "金牌影院",
                    "vod_play_url": "#".join(play_items),
                })
            # Return the detail object even when no track is found, so Yingxia
            # can still show available metadata. No fake playlist is generated.
            return _json({"list": [vod]})
        except Exception as exc:
            return self._failure(exc)

    # ---------------------------------- 搜索 ----------------------------------

    def searchContent(self, key, quick, pg="1"):
        try:
            keyword = _text(key).strip()
            if not keyword:
                return _json({"list": []})
            page = _safe_page(pg)
            params = {
                "keyword": keyword,
                "pageNum": str(page),
                "pageSize": str(SEARCH_PAGE_SIZE),
                "type": "false",
            }
            url = (self.base + "/api/mw-movie/anonymous/video/searchByWordPageable?"
                   + "keyword=" + quote(keyword, safe="")
                   + "&pageNum=" + str(page)
                   + "&pageSize=" + str(SEARCH_PAGE_SIZE)
                   + "&type=false")
            data = self._request_json(url, params)
            rows, total, page_count = _rows_and_total(data)
            vods = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                vod = _map_vod(row)
                if vod.get("vod_id") and vod.get("vod_name"):
                    self.video_cache[vod["vod_id"]] = row
                    vods.append(vod)
            calculated_pages = max(1, (total + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE)
            return _json({
                "page": page,
                "pagecount": page_count or calculated_pages,
                "limit": SEARCH_PAGE_SIZE,
                "total": total,
                "list": vods,
            })
        except Exception as exc:
            return self._failure(exc)

    # ---------------------------------- 播放 ----------------------------------

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = _text(id).split("|", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise RuntimeError("播放参数缺少影片 ID 或集数 ID")
            params = {"id": parts[0], "nid": parts[1]}
            url = self.base + "/api/mw-movie/anonymous/v2/video/episode/url?" + urlencode(params)
            data = self._request_json(url, params)
            root = _unwrap_payload(data)
            rows = root.get("list", []) if isinstance(root, dict) else []
            play_url = ""
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and row.get("url"):
                        play_url = _text(row.get("url"))
                        break
            if not play_url and isinstance(root, dict):
                play_url = _text(root.get("url"))
            if not play_url:
                raise RuntimeError("播放接口没有返回有效地址")
            return _json({"parse": 0, "url": play_url, "header": PLAY_HEADERS})
        except Exception as exc:
            return self._failure(exc)


# Metadata is supplied for convenient copying into a TVBox/Yingxia subscription.
# It does not self-register when the .py file is loaded.
TVBOX_SOURCE_CONFIG = {
    "sites": [{
        "key": "jpyy",
        "name": "金牌影院",
        "type": 3,
        "api": "./jpyy.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "changeable": 1,
        "timeout": 30,
        "ext": "",
    }]
}
TVBOX_SOURCE_CONFIG_JSON = _json(TVBOX_SOURCE_CONFIG)
