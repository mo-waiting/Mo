#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""听友听书"""

import re
import json
import html
import unicodedata
import urllib.request
import urllib.parse
import http.cookiejar
import gzip
import zlib
import ssl

try:
    from base.spider import Spider as SpiderBase
except ImportError:
    class SpiderBase(object):
        pass


class Spider(SpiderBase):
    def __init__(self):
        super(Spider, self).__init__()
        self.base = "https://tingyou.fm"
        self.api_hosts = [
            "https://appp.fdhtbz.cn/api/h5/listening",
            "https://tingyou.fm/listening-api",
        ]
        self._ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.ref = "https://tingyou.fm/"
        self.options = {}
        self._web_meta_cache = {}
        self._list_meta_cache = {}
        self._meta_version = "v11-type-cat-author-fallback"

        # 保留原脚本的 TLS 设置，避免改变原有站点连接行为。
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx),
        )

        self.block_kw = (
            "幼女", "幼齿", "萝莉", "未成年", "小学生", "中学生", "儿童色情",
            "强奸", "轮奸", "迷奸", "兽交", "人兽",
        )

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        return True

    def getName(self):
        # Spider 名称采用站点名称，不使用第三方推广品牌。
        return "听友听书"

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv|avi|ts|m4a|mp3|aac)(\?|$)", url, re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.options = {}
        self._web_meta_cache = {}
        self._list_meta_cache = {}

    def _dict(self, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, (str, bytes)):
            try:
                d = json.loads(v)
                return d if isinstance(d, dict) else {}
            except Exception:
                return {}
        return {}

    def _list(self, v):
        if isinstance(v, (list, tuple)):
            return [str(i) for i in v]
        if isinstance(v, (str, bytes)):
            try:
                d = json.loads(v)
                if isinstance(d, (list, tuple)):
                    return [str(i) for i in d]
            except Exception:
                pass
            return [str(v)]
        return []

    def _blocked(self, text):
        if not text:
            return False
        t = str(text).lower()
        return any(k in t for k in self.block_kw)

    _PROMO_RE = re.compile(
        r"蝴蝶影视|蝴蝶影院|蝴蝶听书|@?tvshare23|(?:TG|Telegram)\s*(?:群|频道|交流群)?|"
        r"官方交流群|交流群|QQ群|微信群|粉丝群|加群|进群|入群|扫码(?:进群|加群|关注)?|"
        r"听友听书专线|专线加速|加速播放|极速音质|广告合作|商务合作|推广信息|推广|广告|"
        r"关注公众号|公众号|关注我们|添加客服|客服微信|客服QQ|下载(?:我们的)?APP|"
        r"更多资源|获取资源|资源群|看片群|商务联系",
        re.IGNORECASE,
    )

    def _normalize_source_text(self, value):
        if value is None:
            return ""
        text = unicodedata.normalize("NFKC", html.unescape(str(value)))
        # Remove zero-width and direction-control characters often used to split ad keywords.
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
        text = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", text)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        return text.replace("\r", "\n").replace("\xa0", " ")

    def _person_value(self, value):
        """Extract a person name from flat, nested, or list-shaped API values."""
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("name", "nickname", "nick_name", "username", "uname",
                        "title", "displayName", "value", "text"):
                if value.get(key) not in (None, ""):
                    candidate = self._clean_person_text(value.get(key))
                    if candidate:
                        return candidate
            # Some APIs use {author: {name: ...}} or {artist: [..]}.
            for nested in value.values():
                if isinstance(nested, (dict, list, tuple)):
                    candidate = self._person_value(nested)
                    if candidate:
                        return candidate
            return ""
        if isinstance(value, (list, tuple)):
            names = []
            for item in value:
                name = self._person_value(item)
                if name and name not in names:
                    names.append(name)
            return " / ".join(names)
        return self._clean_person_text(value)

    _UNKNOWN_PERSONS = {"佚名", "匿名", "匿名用户", "未知", "不详", "暂无", "无", "作者佚名", ""}
    _UNKNOWN_GENRES = {"无分类", "未分类", "未知分类", "未知", "暂无", "无", "全部", "其他", "其它", "有声小说", "评书"}

    _TYPE_ID_NAMES = {
        "46": "玄幻奇幻", "11": "武侠小说", "19": "言情通俗",
        "21": "相声小品", "14": "恐怖惊悚", "17": "官场商战",
        "15": "历史军事", "9": "百家讲坛", "16": "刑侦反腐",
        "10": "有声文学", "18": "人物纪实", "36": "广播剧",
        "22": "英文读物", "23": "轻音清心", "31": "二人转",
        "33": "健康养生", "34": "综艺娱乐", "40": "头条",
        "38": "戏曲", "41": "脱口秀", "42": "商业财经",
        "43": "亲子教育", "44": "教育培训", "45": "时尚生活",
        "20": "童话寓言", "47": "未分类",
    }

    _AUTHOR_KEYS = (
        "author", "author_name", "authorName", "original_author", "originalAuthor",
        "book_author", "bookAuthor", "writer", "writer_name", "writerName",
        "authors", "original_author_name", "originalAuthorName", "author_info",
        "authorInfo", "creator", "original_writer", "originalWriter",
    )
    _ARTIST_KEYS = (
        "artist", "teller", "announcer", "broadcaster", "speaker", "anchor",
        "narrator", "performer", "voice_actor", "voiceActor", "播音", "播讲", "主播",
    )
    _GENRE_KEYS = (
        "cat", "category", "category_name", "categoryName", "genre", "genre_name",
        "type_name", "typeName", "novel_type", "novelType", "album_type",
        "albumType", "type", "category_info", "categoryInfo", "class_name", "className",
        "category_id", "categoryId", "genre_id", "genreId", "cat_id", "catId",
        "type_id", "typeId", "分类", "类型",
    )

    def _is_unknown_person(self, value):
        # Empty/missing values must also be considered unknown so the official
        # Tingyou page can fill them. V10 treated None as "known" and skipped fallback.
        cleaned = self._clean_person_text(value).strip()
        return not cleaned or cleaned in self._UNKNOWN_PERSONS

    def _is_unknown_genre(self, value):
        cleaned = self._clean_source_text(value).strip()
        return not cleaned or cleaned in self._UNKNOWN_GENRES

    def _walk_key_values(self, obj, keys, depth=0):
        """Yield values for matching keys throughout nested API/SSR dictionaries."""
        if depth > 8:
            return
        wanted = {str(k).lower() for k in keys}
        if isinstance(obj, dict):
            # Matching keys first, preserving source priority and stable order.
            for key, value in obj.items():
                if str(key).lower() in wanted:
                    yield value
            for value in obj.values():
                if isinstance(value, (dict, list, tuple)):
                    yield from self._walk_key_values(value, keys, depth + 1)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                if isinstance(value, (dict, list, tuple)):
                    yield from self._walk_key_values(value, keys, depth + 1)

    def _first_person(self, records, keys):
        for record in records:
            for raw in self._walk_key_values(record, keys):
                value = self._person_value(raw)
                if value and not self._is_unknown_person(value):
                    return value[:100]
        return ""

    def _walk_strings(self, obj, depth=0):
        if depth > 8:
            return
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for value in obj.values():
                yield from self._walk_strings(value, depth + 1)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                yield from self._walk_strings(value, depth + 1)

    def _broadcast_name(self, album, web_meta=None, extra_records=None):
        """Tingyou displays this as 播音; accept artist plus legacy aliases."""
        records = [album]
        if isinstance(extra_records, (list, tuple)):
            records.extend(extra_records)
        if isinstance(web_meta, dict):
            records.append(web_meta)
        value = self._first_person(records, self._ARTIST_KEYS)
        if value:
            return value
        for record in records:
            for source_text in self._walk_strings(record):
                labelled = self._extract_labeled_meta(source_text)
                candidate = self._clean_person_text(labelled.get("artist"))
                if candidate and not self._is_unknown_person(candidate):
                    return candidate[:100]
        return ""

    def _author_name(self, album, web_meta=None, extra_records=None):
        """Find the genuine original author; ignore default values such as 佚名."""
        records = [album]
        if isinstance(extra_records, (list, tuple)):
            records.extend(extra_records)
        if isinstance(web_meta, dict):
            records.append(web_meta)
        value = self._first_person(records, self._AUTHOR_KEYS)
        if value:
            return self._clean_person_text(value)[:100]

        # Some homepage/list records carry a compact metadata string rather than
        # separate JSON properties (e.g. “分类… 作者… 播音…”).
        for record in records:
            for source_text in self._walk_strings(record):
                labelled = self._extract_labeled_meta(source_text)
                candidate = self._clean_person_text(labelled.get("author"))
                if candidate and not self._is_unknown_person(candidate):
                    return candidate[:100]

        # Some official SSR cards expose labelled text rather than a JSON field.
        for source in records:
            if not isinstance(source, dict):
                continue
            for key in ("title", "synopsis", "description", "intro", "content", "text"):
                text = self._normalize_source_text(source.get(key))
                if not text:
                    continue
                match = re.search(r"(?:原著作者|原著|作者|著者)\s*[:：]\s*([^，,。；;|｜丨\n]{2,40})", text)
                if match:
                    candidate = self._clean_person_text(match.group(1))
                    if candidate and not self._is_unknown_person(candidate):
                        return candidate[:100]
        return ""

    def _genre_value(self, value):
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("name", "title", "label", "category_name", "type_name", "text", "value"):
                if value.get(key) not in (None, ""):
                    candidate = self._clean_source_text(value.get(key))
                    if candidate and not self._is_unknown_genre(candidate):
                        return candidate
            # Category may be nested under info/metadata/data.
            for nested in value.values():
                if isinstance(nested, (dict, list, tuple)):
                    candidate = self._genre_value(nested)
                    if candidate and not self._is_unknown_genre(candidate):
                        return candidate
            return ""
        if isinstance(value, (list, tuple)):
            names = []
            for item in value:
                name = self._genre_value(item)
                if name and not self._is_unknown_genre(name) and name not in names:
                    names.append(name)
            return "/".join(names)
        raw = self._clean_source_text(value)
        if raw in self._TYPE_ID_NAMES:
            return self._TYPE_ID_NAMES[raw]
        # Do not expose opaque numeric IDs as user-facing genres.
        if raw.isdigit() or self._is_unknown_genre(raw):
            return ""
        return raw

    def _genre_from(self, record, web_meta=None, extra_records=None):
        """Read Tingyou's real book category; prefer cat/category over broad type."""
        records = [record]
        if isinstance(extra_records, (list, tuple)):
            records.extend(extra_records)
        if isinstance(web_meta, dict):
            records.append(web_meta)

        # The original Spider read album["type"] and album["cat"]. V10 omitted
        # the generic `type` key, which caused many works to lose their genre.
        # Prefer explicit category/cat fields, then use type as a fallback.
        key_priority = (
            "cat", "category", "category_name", "categoryName", "genre",
            "genre_name", "type_name", "typeName", "novel_type", "novelType",
            "album_type", "albumType", "type", "category_id", "categoryId",
            "genre_id", "genreId", "cat_id", "catId", "type_id", "typeId",
            "分类", "类型",
        )
        names = []
        for source in records:
            for key in key_priority:
                for raw in self._walk_key_values(source, (key,)):
                    value = self._genre_value(raw)
                    if value and not self._is_unknown_genre(value):
                        for part in re.split(r"[/／|｜,，、]", value):
                            part = part.strip()
                            if part and not self._is_unknown_genre(part) and part not in names:
                                names.append(part)
            if not names:
                for source_text in self._walk_strings(source):
                    labelled = self._extract_labeled_meta(source_text)
                    candidate = self._genre_value(labelled.get("category"))
                    if candidate and not self._is_unknown_genre(candidate):
                        names.extend(p.strip() for p in re.split(r"[/／|｜,，、]", candidate)
                                     if p.strip() and not self._is_unknown_genre(p.strip()))
                        break
            if names:
                # Return the best complete metadata from the first useful source.
                break
        return "/".join(dict.fromkeys(names))[:80]

    def _extract_labeled_meta(self, text):
        """Extract the same visible labels that Tingyou renders on its album pages."""
        output = {}
        normalized = re.sub(r"\s+", " ", self._normalize_source_text(text)).strip()
        # Include non-target labels as boundaries. Without these, the final author
        # value could absorb the following page content and be discarded as noisy.
        labels = list(re.finditer(
            r"(分类|作者|播音|状态|更新|频道|博主|作品简介|简介|目录|播放全部|反馈)\s*[:：]",
            normalized
        ))
        field_map = {"分类": "category", "作者": "author", "播音": "artist"}
        for i, match in enumerate(labels):
            field = field_map.get(match.group(1))
            if not field:
                continue
            end = labels[i + 1].start() if i + 1 < len(labels) else len(normalized)
            value = normalized[match.end():end].strip(" |｜·•，,。;；")
            value = re.split(r"(?:作品简介|简介|目录|博主|播放全部|反馈)", value, maxsplit=1)[0].strip()
            # Strip trailing update counters/status text that may sit adjacent to labels.
            value = re.sub(r"(?:\d+\s*期)?\s*(?:已完结|连载中|更新中)?$", "", value).strip()
            if value:
                output[field] = value[:120]
        return output

    def _extract_json_objects(self, raw_html):
        """Collect JSON payloads embedded in script tags (Next/Nuxt/SSR payloads)."""
        objects = []
        script_blocks = re.findall(r"(?is)<script\b[^>]*>(.*?)</script>", raw_html or "")
        candidates = list(script_blocks)
        for block in script_blocks:
            candidates.extend(re.findall(r"(?:__INITIAL_STATE__|__INITIAL_DATA__|__NEXT_DATA__|__NUXT__|__APOLLO_STATE__)\s*=\s*(\{.*?\})\s*;", block, re.S))
        for candidate in candidates:
            candidate = html.unescape(candidate.strip())
            if not candidate:
                continue
            # Parse full JSON and common assignment wrappers.
            for text in (candidate, candidate[candidate.find("{"):] if "{" in candidate else ""):
                if not text:
                    continue
                try:
                    value = json.loads(text)
                    if isinstance(value, (dict, list)):
                        objects.append(value)
                        break
                except Exception:
                    continue
        return objects

    def _fetch_web_meta(self, album_id):
        """Fetch official album-page metadata, including embedded SSR JSON and visible labels."""
        key = str(album_id)
        if key in self._web_meta_cache:
            return self._web_meta_cache[key]

        result = {}
        url = self.base.rstrip("/") + "/albums/" + urllib.parse.quote(key)
        headers = {
            "User-Agent": self._ua,
            "Referer": self.ref,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with self.opener.open(req, timeout=5) as resp:
                if resp.getcode() == 200:
                    raw = resp.read(4 * 1024 * 1024)
                    page = raw.decode("utf-8", errors="ignore")
                    decoded = html.unescape(page)

                    # 1) The site's initial state may contain the full author/category
                    # fields even when the API summary endpoint returns default values.
                    for obj in self._extract_json_objects(decoded):
                        for field, keys in (("author", self._AUTHOR_KEYS),
                                            ("artist", self._ARTIST_KEYS),
                                            ("category", self._GENRE_KEYS)):
                            for raw_value in self._walk_key_values(obj, keys):
                                value = self._person_value(raw_value) if field != "category" else self._genre_value(raw_value)
                                if value and (field == "category" and not self._is_unknown_genre(value)
                                              or field != "category" and not self._is_unknown_person(value)):
                                    result.setdefault(field, value[:120])

                    # 2) Parse rendered SSR text. Keep this independent from script
                    # extraction: do not discard JSON payload before scanning it.
                    visible = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<noscript\b.*?</noscript>", " ", decoded)
                    visible = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", " ", visible)
                    visible = re.sub(r"<[^>]+>", " ", visible)
                    visible = re.sub(r"\s+", " ", visible)
                    labelled = self._extract_labeled_meta(visible)
                    for field, value in labelled.items():
                        if field == "category":
                            if self._is_unknown_genre(result.get(field)) and not self._is_unknown_genre(value):
                                result[field] = value
                        elif self._is_unknown_person(result.get(field)) and not self._is_unknown_person(value):
                            result[field] = self._clean_person_text(value)

                    # 3) Parse meta tags / JSON-LD in case the site publishes structured data.
                    for tag in re.findall(r"(?is)<meta\b[^>]+>", decoded):
                        name = re.search(r"(?:name|property)=[\"']([^\"']+)[\"']", tag, re.I)
                        content = re.search(r"content=[\"']([^\"']*)[\"']", tag, re.I)
                        if not name or not content:
                            continue
                        prop = name.group(1).lower()
                        value = self._clean_source_text(content.group(1))
                        if prop in ("article:author", "author") and value and self._is_unknown_person(result.get("author")):
                            result["author"] = value
                        elif prop in ("article:section", "og:category") and value and self._is_unknown_genre(result.get("category")):
                            result["category"] = value
        except Exception:
            pass

        self._web_meta_cache[key] = result
        return result

    def _remember_list_meta(self, album_id, record):
        """Cache richer metadata returned by homepage/category/search cards for detail lookup."""
        key = str(album_id)
        if not key or not isinstance(record, dict):
            return
        current = self._list_meta_cache.get(key, {})
        # Keep the original nested record so recursive field lookup can find metadata
        # the site's card endpoint may expose under album/info/metadata objects.
        merged = dict(current)
        merged.update(record)
        self._list_meta_cache[key] = merged

    def _clean_person_text(self, value):
        """Clean author/teller metadata; if it is promotional, never display it as a person."""
        text = self._normalize_source_text(value)
        if not text:
            return ""

        # Split common metadata separators so a real name can survive beside an ad suffix.
        chunks = re.split(r"[|｜/／·•;；\n]+", text)
        kept = []
        for chunk in chunks:
            part = chunk.strip(" \t\n,，。:：-—_")
            if not part:
                continue
            promo_match = self._PROMO_RE.search(part)
            if promo_match:
                # A real person's name may appear before an ad suffix, or after a branded prefix.
                prefix = part[:promo_match.start()].strip(" \t\n,，。:：-—_")
                suffix = part[promo_match.end():].strip(" \t\n,，。:：-—_|｜·•")
                prefix = re.sub(r"^[^\w\u4e00-\u9fff]+", "", prefix)
                suffix = re.sub(r"^[^\w\u4e00-\u9fff]+", "", suffix)
                prefix = re.sub(r"^(?:作者|原作者|播讲人|播音|主播|演播|讲述者)\s*[:：]\s*", "", prefix)
                candidate = prefix
                if not candidate or re.match(r"^(?:欢迎|请|马上|点击|扫码|加入|关注|联系|获取|下载|更多|官方)", candidate):
                    candidate = suffix
                if (candidate and not self._PROMO_RE.search(candidate)
                        and not re.match(r"^(?:欢迎|请|马上|点击|扫码|加入|关注|联系|获取|下载|更多|官方|群号)", candidate)
                        and re.search(r"[\w\u4e00-\u9fff]", candidate)):
                    kept.append(candidate)
                continue
            # Common noisy suffixes used by scraped audiobook metadata.
            part = re.sub(r"(?:_?免费听书|免费收听|听书资源)$", "", part, flags=re.I).strip()
            part = re.sub(r"^(?:作者|原作者|播讲人|播音|主播|演播|讲述者)\s*[:：]\s*", "", part)
            if part and not self._PROMO_RE.search(part):
                kept.append(part)
        # Avoid accidentally presenting an unrecognized advertisement as a person's name.
        result = " / ".join(kept)
        if self._PROMO_RE.search(result):
            return ""
        return result.strip(" \t\n/|｜·•,，。:：-—_")

    def _clean_source_text(self, value):
        """Remove promotional clauses/lines while preserving genuine source description text."""
        text = self._normalize_source_text(value)
        if not text:
            return ""

        # Remove bracketed ad blocks first (including emoji-prefixed blocks).
        for _ in range(3):
            text = re.sub(
                r"【[^】]*(?:蝴蝶影视|蝴蝶影院|tvshare23|TG群|Telegram|交流群|QQ群|微信群|"
                r"听友听书专线|专线加速|加速播放|极速音质|推广|广告|公众号|客服)[^】]*】",
                " ", text, flags=re.I,
            )
            text = re.sub(
                r"\[[^\]]*(?:蝴蝶影视|蝴蝶影院|tvshare23|TG群|Telegram|交流群|QQ群|微信群|"
                r"听友听书专线|专线加速|加速播放|极速音质|推广|广告|公众号|客服)[^\]]*\]",
                " ", text, flags=re.I,
            )

        # Split by paragraphs/sentences. Drop the promotional clause from its first marker
        # onward, preserving any meaningful text that precedes an inline ad suffix.
        segments = re.split(r"(?<=[。！？!?；;])|\n+", text)
        kept = []
        for segment in segments:
            part = segment.strip()
            if not part:
                continue
            match = self._PROMO_RE.search(part)
            if match:
                # In a synopsis, drop the whole sentence/line containing a promotion.
                # Keeping its prefix can leave fragments such as “欢迎加入” behind.
                continue
            kept.append(part)

        text = " ".join(kept)
        # Strip residual ad handles/phrases that may not have had normal punctuation.
        residual_patterns = [
            r"@?tvshare23", r"蝴蝶影视", r"蝴蝶影院",
            r"(?:TG|Telegram)\s*(?:群|频道|交流群)?\s*[:：]?\s*@?[\w.-]*",
            r"(?:官方)?交流群\s*[:：]?\s*[^。！？!?；;]*",
            r"(?:QQ群|微信群|粉丝群)\s*[:：]?\s*[^。！？!?；;]*",
            r"听友听书专线(?:加速播放)?", r"专线加速播放", r"专线加速", r"极速音质",
            r"(?:广告合作|商务合作|推广信息|推广|广告)\s*[:：]?\s*[^。！？!?；;]*",
            r"(?:关注公众号|公众号|关注我们|添加客服|客服微信|客服QQ)\s*[:：]?\s*[^。！？!?；;]*",
            r"(?:获取更多资源|更多资源|更多精彩|下载(?:我们的)?APP|扫码关注)\s*[^。！？!?；;]*",
        ]
        for pattern in residual_patterns:
            text = re.sub(pattern, " ", text, flags=re.I)

        # Remove leading display labels and normalize whitespace/punctuation.
        text = re.sub(r"^(?:介绍|简介|内容介绍)\s*[:：]?\s*", "", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\s*([，。；：！？])\s*", r"\1", text)
        text = re.sub(r"[|｜·•]+", " ", text)
        text = text.strip(" \t\n-—:：,，;；")

        # A final guard: if an ad marker survived normalization, discard the affected text
        # instead of leaking third-party promotional information into the UI.
        if self._PROMO_RE.search(text):
            safe = []
            for sentence in re.split(r"(?<=[。！？!?；;])|\n+", text):
                sentence = sentence.strip()
                if sentence and not self._PROMO_RE.search(sentence):
                    safe.append(sentence)
            text = " ".join(safe)
        return text.strip()

    def _pic(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        return url

    @staticmethod
    def _decode_response(resp):
        raw = resp.read()
        enc = getattr(resp, "headers", {}).get("Content-Encoding", "").lower()
        if raw.startswith(b"\x1f\x8b") or enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            try:
                raw = zlib.decompress(raw)
            except Exception:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        text = raw.decode("utf-8", errors="ignore").strip()
        if text and text[0] in "{[":
            return json.loads(text)
        return {}

    def _api_get(self, path, prefer_proxy=False, req_timeout=4):
        hosts = list(self.api_hosts)
        if prefer_proxy:
            hosts = hosts[::-1]

        for host in hosts:
            url = host.rstrip("/") + "/" + path.lstrip("/")
            headers = {
                "User-Agent": self._ua,
                "Referer": self.ref,
                "Origin": self.base,
                "Accept": "application/json, text/plain, */*",
                "Connection": "close",
            }
            try:
                req = urllib.request.Request(url, headers=headers)
                with self.opener.open(req, timeout=req_timeout) as resp:
                    if resp.getcode() != 200:
                        continue
                    return self._decode_response(resp)
            except Exception:
                continue
        return {}

    def _api_post(self, path, body, req_timeout=5):
        data_bytes = json.dumps(body).encode("utf-8")
        for host in self.api_hosts:
            url = host.rstrip("/") + "/" + path.lstrip("/")
            headers = {
                "User-Agent": self._ua,
                "Referer": self.ref,
                "Origin": self.base,
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Connection": "close",
            }
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers)
                with self.opener.open(req, timeout=req_timeout) as resp:
                    if resp.getcode() != 200:
                        continue
                    return self._decode_response(resp)
            except Exception:
                continue
        return {}

    def homeContent(self, filter=False):
        classes = [
            {"type_name": "全部", "type_id": "all"},
            {"type_name": "有声小说", "type_id": "有声小说"},
            {"type_name": "评书", "type_id": "评书"},
        ]

        sort_filter = {
            "key": "sort",
            "name": "排序",
            "value": [
                {"n": "综合排序", "v": "comprehensive"},
                {"n": "播放最多", "v": "popular"},
                {"n": "最近更新", "v": "updated"},
                {"n": "最新发布", "v": "new"},
            ],
        }
        status_filter = {
            "key": "status",
            "name": "状态",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "连载中", "v": "1"},
                {"n": "已完结", "v": "0"},
            ],
        }
        novel_type_values = [
            {"n": "全部类型", "v": ""},
            {"n": "玄幻奇幻", "v": "46"}, {"n": "武侠小说", "v": "11"},
            {"n": "言情通俗", "v": "19"}, {"n": "相声小品", "v": "21"},
            {"n": "恐怖惊悚", "v": "14"}, {"n": "官场商战", "v": "17"},
            {"n": "历史军事", "v": "15"}, {"n": "百家讲坛", "v": "9"},
            {"n": "刑侦反腐", "v": "16"}, {"n": "有声文学", "v": "10"},
            {"n": "人物纪实", "v": "18"}, {"n": "广播剧", "v": "36"},
            {"n": "英文读物", "v": "22"}, {"n": "轻音清心", "v": "23"},
            {"n": "二人转", "v": "31"}, {"n": "健康养生", "v": "33"},
            {"n": "综艺娱乐", "v": "34"}, {"n": "头条", "v": "40"},
            {"n": "戏曲", "v": "38"}, {"n": "脱口秀", "v": "41"},
            {"n": "商业财经", "v": "42"}, {"n": "亲子教育", "v": "43"},
            {"n": "教育培训", "v": "44"}, {"n": "时尚生活", "v": "45"},
            {"n": "童话寓言", "v": "20"}, {"n": "未分类", "v": "47"},
        ]
        pingshu_type_values = [
            {"n": "单田芳", "v": "1"}, {"n": "刘兰芳", "v": "2"},
            {"n": "田连元", "v": "3"}, {"n": "袁阔成", "v": "4"},
            {"n": "连丽如", "v": "5"}, {"n": "孙一", "v": "8"},
            {"n": "王子封臣", "v": "30"}, {"n": "马长辉", "v": "25"},
            {"n": "昊儒书场", "v": "26"}, {"n": "王军", "v": "27"},
            {"n": "王玥波", "v": "28"}, {"n": "石连君", "v": "29"},
            {"n": "粤语评书", "v": "12"}, {"n": "关永超", "v": "35"},
            {"n": "张少佐", "v": "6"}, {"n": "田战义", "v": "7"},
            {"n": "其他评书", "v": "13"},
        ]
        all_type_values = ([{"n": "全部类型", "v": ""}] + novel_type_values[1:]
                           + pingshu_type_values)
        filters = {
            "all": [
                {"key": "type", "name": "类型", "value": all_type_values},
                sort_filter, status_filter,
            ],
            "有声小说": [
                {"key": "type", "name": "类型", "value": novel_type_values},
                sort_filter, status_filter,
            ],
            "评书": [
                {"key": "type", "name": "名家", "value": pingshu_type_values, "init": "1"},
                sort_filter, status_filter,
            ],
        }
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self):
        return self._list_page(cat="", sub_type="", sort="popular", page=1, status="")

    def categoryContent(self, tid, pg, filter=False, extend=None, *args, **kwargs):
        try:
            page_num = max(1, int(str(pg).strip() or 1))
        except Exception:
            page_num = 1

        f = {}
        f.update(self._dict(filter))
        f.update(self._dict(extend))
        for k in ("extend", "ext", "filter"):
            if k in kwargs:
                f.update(self._dict(kwargs.get(k)))

        raw_tid = str(tid).strip()
        cat = "" if raw_tid == "all" else raw_tid
        sub_type = str(f.get("type") or "").strip()
        sort_by = str(f.get("sort") or "comprehensive").strip()
        status_val = str(f.get("status") or "").strip()
        if cat == "评书" and not sub_type:
            sub_type = "1"
        return self._list_page(cat, sub_type, sort_by, page_num, status_val)

    def _filter_genre_label(self, sub_type="", cat=""):
        value = str(sub_type or "").strip()
        if value in self._TYPE_ID_NAMES:
            return self._TYPE_ID_NAMES[value]
        # If the user selected a top-level kind rather than a specific novel genre,
        # show that actual site category instead of a Spider/source brand.
        cat_text = self._clean_source_text(cat)
        return cat_text if cat_text in ("有声小说", "评书") else ""

    def _list_page(self, cat="", sub_type="", sort="comprehensive", page=1, status=""):
        params = {"sort": sort or "comprehensive", "page": str(page)}
        if cat:
            params["cat"] = cat
        if sub_type:
            params["type"] = sub_type
        if status != "" and status is not None:
            params["status"] = str(status)

        data = self._api_get("category?" + urllib.parse.urlencode(params), req_timeout=5)
        items = []
        pagecount = 1
        if isinstance(data, dict):
            try:
                pagecount = int(data.get("pages") or 1)
            except Exception:
                pagecount = 1
            for it in data.get("data") or []:
                if not isinstance(it, dict):
                    continue
                name = self._clean_source_text(it.get("title"))
                if not name or self._blocked(name):
                    continue
                vid = str(it.get("id") or "")
                if not vid:
                    continue
                self._remember_list_meta(vid, it)
                st, cnt = it.get("status"), it.get("count") or 0
                remarks = "连载中" if st == 1 else ("已完结" if st == 0 else "")
                if cnt:
                    remarks = (remarks + " · " if remarks else "") + "%s集" % cnt
                genre = self._genre_from(it) or self._filter_genre_label(sub_type, cat)
                if genre:
                    remarks = (remarks + " · " if remarks else "") + genre
                items.append({
                    "vod_id": vid,
                    "vod_name": name[:80],
                    "vod_pic": self._pic(str(it.get("cover_url") or "")),
                    # 只显示 API 返回的状态和集数，不添加第三方品牌。
                    "vod_remarks": remarks.strip(),
                    "style": {"type": "rect", "ratio": 0.75},
                })

        total_count = int(page * len(items) + 100) if items else 0
        return {
            "page": int(page), "pagecount": max(pagecount, 1),
            "limit": 20, "total": total_count, "list": items,
        }

    def detailContent(self, ids):
        raw_ids = self._list(ids)
        vid = raw_ids[0] if raw_ids else ""
        if not vid:
            return {"list": []}

        album = self._api_get("album/" + vid, req_timeout=3)
        if not isinstance(album, dict) or not album.get("id"):
            album = self._api_get("album/" + vid, prefer_proxy=True, req_timeout=3)
        if not isinstance(album, dict) or not album.get("id"):
            return {"list": []}

        title = self._clean_source_text(album.get("title"))
        if self._blocked(title):
            return {"list": []}

        # `artist` is Tingyou's current published announcer/performer field;
        # older API variants may still return `teller`. Fetch the official page
        # only when an API metadata field is absent/anonymous, so detail loading
        # does not incur an unnecessary extra request for every work.
        # The card/list endpoint may have richer metadata than /album/{id}.
        list_record = self._list_meta_cache.get(str(vid), {})
        extra_records = [list_record] if list_record else []
        api_author = self._author_name(album, extra_records=extra_records)
        api_broadcaster = self._broadcast_name(album, extra_records=extra_records)
        api_genre = self._genre_from(album, extra_records=extra_records)
        # Treat both “佚名” and “无分类/未分类” as missing, not valid values.
        needs_web_meta = (
            not api_author or not api_broadcaster or not api_genre
        )
        web_meta = self._fetch_web_meta(vid) if needs_web_meta else {}
        author = self._author_name(album, web_meta, extra_records)
        broadcaster = api_broadcaster or self._broadcast_name({}, web_meta)
        pic = str(album.get("cover_url") or album.get("artwork") or list_record.get("cover_url") or "")
        synopsis = self._clean_source_text(album.get("synopsis") or album.get("description") or list_record.get("synopsis"))
        type_name = api_genre or self._genre_from({}, web_meta, extra_records)
        cnt = album.get("count") or 0
        try:
            total_count = int(cnt)
        except Exception:
            total_count = 0

        st = album.get("status")
        status_txt = "连载中" if st == 1 else ("已完结" if st == 0 else "")
        chapters = self._fetch_chapters(vid) if total_count <= 400 else []
        play_urls = []
        if chapters:
            for ch in chapters:
                idx = ch.get("index") or 0
                ctitle = self._clean_source_text(ch.get("title") or ("第%s集" % idx))
                clean_ctitle = re.sub(r"[\$\#\r\n\t]+", " ", ctitle).strip()
                if not clean_ctitle:
                    clean_ctitle = "第%s集" % idx
                play_urls.append("%s$%s_%s" % (clean_ctitle, vid, idx))
        else:
            limit_n = min(max(total_count, 1), 5000)
            for idx in range(1, limit_n + 1):
                play_urls.append("第%d集$%s_%d" % (idx, vid, idx))

        # 作者信息放在演员栏；播音/主播信息放在原导演栏位。
        # 标准 CatVod 字段名仍是 vod_director，客户端标签可能仍显示“导演”；
        # 为避免误认，在字段值前明确标注“播音：”。
        author = self._clean_person_text(author)
        broadcaster = self._clean_person_text(broadcaster)
        author_display = ("作者：" + author) if author else ""
        broadcast_display = ("播音：" + broadcaster) if broadcaster else ""
        remarks_meta = (status_txt + (" · %s集" % total_count if total_count else "")).strip(" ·")
        if type_name:
            remarks_meta = (remarks_meta + " · " if remarks_meta else "") + type_name

        # 将作者与播音信息放在简介正文最上方，随后才显示网站原始 synopsis。
        # 同时保留 CatVod 的作者/播音元数据字段，便于支持这些字段的客户端显示。
        intro_lines = []
        if author:
            intro_lines.append("作者：" + author)
        if broadcaster:
            intro_lines.append("播音：" + broadcaster)
        if synopsis:
            intro_lines.append("简介：" + synopsis)
        detail_content = "\n\n".join(intro_lines)

        vod = {
            "vod_id": vid,
            "vod_name": title[:100],
            "vod_pic": self._pic(pic),
            "type_name": type_name[:40],
            "vod_remarks": remarks_meta,
            "vod_actor": author_display[:100],
            "vod_director": broadcast_display[:100],
            "vod_content": detail_content,
            "vod_play_from": "默认线路",
            "vod_play_url": "#".join(play_urls),
        }
        return {"list": [vod]}

    def _fetch_chapters(self, album_id):
        data = self._api_get("chapters/" + str(album_id), prefer_proxy=True, req_timeout=2)
        chs = []
        if isinstance(data, dict):
            for c in data.get("chapters") or []:
                if not isinstance(c, dict):
                    continue
                idx = c.get("index")
                if idx is None:
                    continue
                try:
                    idx = int(idx)
                except Exception:
                    continue
                chs.append({
                    "id": c.get("id"), "index": idx,
                    "title": self._clean_source_text(c.get("title") or ("第%s集" % idx)),
                    "duration": c.get("duration") or 0,
                })
        chs.sort(key=lambda x: x["index"])
        return chs

    def searchContent(self, key, quick, pg="1"):
        try:
            page_num = max(1, int(str(pg).strip() or 1))
        except Exception:
            page_num = 1
        if not key or self._blocked(key):
            return {"list": [], "page": page_num, "pagecount": 1, "limit": 20, "total": 0}

        data = self._api_post("search", {"keyword": key, "page": page_num}, req_timeout=5)
        items, has_more = [], False
        if isinstance(data, dict):
            has_more = bool(data.get("has_more"))
            for it in data.get("results") or data.get("data") or []:
                if not isinstance(it, dict):
                    continue
                name = self._clean_source_text(it.get("title"))
                if not name or self._blocked(name):
                    continue
                vid = str(it.get("id") or "")
                if not vid:
                    continue
                self._remember_list_meta(vid, it)
                st, cnt = it.get("status"), it.get("count") or 0
                remarks = "连载中" if st == 1 else ("已完结" if st == 0 else "")
                if cnt:
                    remarks = (remarks + " · " if remarks else "") + "%s集" % cnt
                genre = self._genre_from(it)
                if genre:
                    remarks = (remarks + " · " if remarks else "") + genre
                items.append({
                    "vod_id": vid,
                    "vod_name": name[:80],
                    "vod_pic": self._pic(str(it.get("cover_url") or "")),
                    "vod_remarks": remarks.strip(),
                    "style": {"type": "rect", "ratio": 0.75},
                })

        pagecount = page_num + 1 if has_more else page_num
        total_items = int(page_num * len(items) + 100) if items else 0
        return {
            "page": int(page_num), "pagecount": int(pagecount),
            "limit": 20, "total": total_items, "list": items,
        }

    def playerContent(self, flag, id, vipFlags):
        parse, url = 0, ""
        try:
            raw_id = str(id).strip()
            parts = raw_id.rsplit("_", 1)
            if len(parts) == 2:
                album_id, chapter_idx = parts[0], int(parts[1])
            else:
                album_id, chapter_idx = raw_id, 1
            data = self._api_post(
                "play", {"album_id": str(album_id), "chapter_idx": int(chapter_idx)},
                req_timeout=6,
            )
            if isinstance(data, dict):
                play_url = str(data.get("play_url") or "").strip()
                if play_url.startswith("http"):
                    url = play_url
                    parse = 0
        except Exception:
            pass

        if not url:
            parse = 1
            url = "%s/listening/album/%s" % (self.base, str(id).split("_")[0])

        headers = {
            "User-Agent": self._ua,
            "Referer": self.ref,
            "Origin": self.base,
        }
        return {"parse": parse, "playUrl": "", "url": url, "header": headers}

    def localProxy(self, param):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]
