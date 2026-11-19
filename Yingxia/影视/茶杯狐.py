#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
import ssl
import gzip
import zlib
import http.cookiejar
import urllib.request
import urllib.parse
from urllib.parse import quote, urlsplit

from base.spider import Spider as BaseSpider


def format_remarks(meta=""):
    clean_meta = str(meta or "").strip()
    return re.sub(r"[\r\n\t]+", " ", clean_meta).strip()


class Spider(BaseSpider):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteName = "茶杯狐"
        self.siteUrl = "https://pcupfox.com"
        self.posterRatio = 0.67
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        self.options = {}
        self.orderValues = ["hit", "commend"]
        # 电影分类的筛选项，参数和值依据茶杯狐电影分类页实际链接整理。
        self.movieTypeValues = [
            {"n": "全部", "v": "1"},
            {"n": "动作片", "v": "5"},
            {"n": "爱情片", "v": "6"},
            {"n": "科幻片", "v": "7"},
            {"n": "恐怖片", "v": "8"},
            {"n": "战争片", "v": "9"},
            {"n": "喜剧片", "v": "10"},
            {"n": "纪录片", "v": "11"},
            {"n": "剧情片", "v": "12"}
        ]
        self.moviePlotValues = [
            {"n": "全部", "v": ""},
            {"n": "解密", "v": "解密"},
            {"n": "乡村", "v": "乡村"},
            {"n": "都市", "v": "都市"},
            {"n": "少儿", "v": "少儿"},
            {"n": "对话", "v": "对话"},
            {"n": "搞笑", "v": "搞笑"},
            {"n": "恐怖", "v": "恐怖"},
            {"n": "宫廷", "v": "宫廷"},
            {"n": "剧情", "v": "剧情"},
            {"n": "言情", "v": "言情"},
            {"n": "家庭", "v": "家庭"},
            {"n": "励志", "v": "励志"},
            {"n": "偶像", "v": "偶像"},
            {"n": "时装", "v": "时装"},
            {"n": "年代", "v": "年代"},
            {"n": "悬疑", "v": "悬疑"},
            {"n": "古装", "v": "古装"},
            {"n": "热血", "v": "热血"},
            {"n": "同人", "v": "同人"},
            {"n": "耽美", "v": "耽美"}
        ]
        self.movieYearValues = [{"n": "全部", "v": ""}] + [
            {"n": str(year), "v": str(year)}
            for year in (2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019,
                         2018, 2017, 2016, 2015, 2014, 2013, 2012, 2010)
        ] + [{"n": "更早", "v": "more"}]
        self.movieOrderValues = [
            {"n": "时间排序", "v": "time"},
            {"n": "人气排序", "v": "hit"},
            {"n": "评分排序", "v": "commend"}
        ]
        # 电视剧分类的站点原生类型筛选：全部=2，子类型分别为 13-16。
        self.tvTypeValues = [
            {"n": "全部", "v": "2"},
            {"n": "大陆剧", "v": "13"},
            {"n": "港台剧", "v": "14"},
            {"n": "欧美剧", "v": "15"},
            {"n": "日韩剧", "v": "16"}
        ]
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"}
        ]
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ctx)
        )

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif extend:
            text = str(extend).strip()
            if text.startswith("http"):
                self.options = {"host": text}
            else:
                try:
                    parsed = json.loads(text)
                    self.options = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    self.options = {}
        host = str(self.options.get("host") or "").strip()
        if host.startswith("http"):
            self.siteUrl = host.rstrip("/")
        return True

    def getName(self):
        return self.siteName

    def isVideoFormat(self, url):
        path = urlsplit(str(url or "")).path.lower()
        return path.endswith((".m3u8", ".mpd", ".mp4", ".mkv", ".flv", ".mp3", ".m4a", ".aac"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.options = {}

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return ""
        headers = {
            "User-Agent": self._ua,
            "Referer": referer if referer else (self.siteUrl + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        for attempt in range(2):
            try:
                req = urllib.request.Request(target_url, headers=headers)
                with self.opener.open(req, timeout=8) as resp:
                    raw = resp.read()
                    enc = ""
                    try:
                        enc = resp.headers.get("Content-Encoding", "") or ""
                    except Exception:
                        enc = ""
                    if raw.startswith(b"\x1f\x8b") or enc == "gzip":
                        raw = gzip.decompress(raw)
                    elif enc == "deflate":
                        try:
                            raw = zlib.decompress(raw)
                        except Exception:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    try:
                        return raw.decode("utf-8")
                    except Exception:
                        return raw.decode("utf-8", errors="ignore")
            except Exception:
                if attempt == 0:
                    continue
                return ""
        return ""

    def _decode_entities(self, value):
        text = str(value or "")
        text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        return text

    def _strip_tags(self, value):
        text = re.sub(r"<[^>]+>", "", str(value or ""))
        text = self._decode_entities(text)
        return re.sub(r"\s+", " ", text).strip()

    def _extract_line_names(self, html):
        """按详情页播放线路标签在 HTML 中的先后顺序提取原始线路名。

        茶杯狐页面的线路标签通常位于 class 包含 module-tab-item 的元素中，
        名称优先取内部 span，避免把线路集数等附加文字拼进线路名。
        """
        if not html:
            return []

        names = []
        pattern = re.compile(
            r'<(?P<tag>div|a|li)\b'
            r'(?=[^>]*\bclass\s*=\s*["\'][^"\']*\bmodule-tab-item\b[^"\']*["\'])'
            r'[^>]*>(?P<body>[\s\S]*?)</(?P=tag)\s*>',
            re.I
        )
        for match in pattern.finditer(html):
            block = match.group("body") or ""
            span = re.search(r'<span\b[^>]*>([\s\S]*?)</span\s*>', block, re.I)
            raw_name = span.group(1) if span else block
            name = self._strip_tags(raw_name)
            name = re.sub(r"\s+", " ", name).strip()
            if not name:
                continue
            # 有些模板在标签后附带集数，只保留线路名称部分。
            name = re.sub(r"\s*\d+\s*集.*$", "", name).strip()
            if name and name not in names:
                names.append(name)

        return names

    def _abs_poster(self, raw):
        url = self._decode_entities(str(raw or "").strip())
        if not url:
            return ""
        if url.startswith("http://"):
            url = "https://" + url[7:]
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("/"):
            url = self.siteUrl + url
        if not url.startswith("http"):
            url = "https://" + url
        return url

    def _pick_poster(self, chunk):
        m = re.search(r'data-src="([^"]+)"', chunk, re.I)
        if m and m.group(1):
            return self._abs_poster(m.group(1))
        m = re.search(r'data-original="([^"]+)"', chunk, re.I)
        if m and m.group(1):
            return self._abs_poster(m.group(1))
        m = re.search(r'src="([^"]+)"', chunk, re.I)
        if m and m.group(1) and "loading.png" not in m.group(1) and "load.png" not in m.group(1):
            return self._abs_poster(m.group(1))
        return ""

    def _parse_cards(self, html):
        out = []
        seen = {}
        if not html:
            return out
        pattern = re.compile(r'<a[^>]*href="/movie/index(\d+)\.html"[^>]*>([\s\S]*?)</a>', re.I)
        for m in pattern.finditer(html):
            vid = m.group(1)
            chunk = m.group(0)
            if not vid or vid in seen:
                continue
            if "lazyload" not in chunk:
                continue
            poster = self._pick_poster(chunk)
            if not poster:
                continue
            title = ""
            tm = re.search(r'title="([^"]+)"', chunk, re.I)
            if tm and tm.group(1):
                title = self._decode_entities(tm.group(1)).strip()
            else:
                am = re.search(r'alt="([^"]*)"', chunk, re.I)
                if am and am.group(1):
                    title = self._decode_entities(am.group(1)).strip()
            if not title:
                title = vid
            status = ""
            tail = html[m.end():m.end() + 1500]
            sm = re.search(r'<div class="module-item-text">([^<]*)</div>', tail, re.I)
            if sm and sm.group(1):
                status = sm.group(1).strip()
            else:
                vm = re.search(r'<a[^>]*class="video-serial"[^>]*>([^<]*)</a>', tail, re.I)
                if vm and vm.group(1):
                    status = vm.group(1).strip()
            seen[vid] = True
            out.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": poster,
                "vod_remarks": format_remarks(status),
                "style": {"type": "rect", "ratio": self.posterRatio}
            })
        return out

    def _page_current(self, html):
        html = html or ""
        patterns = (
            r'<span[^>]*class=["\'][^"\']*page-current[^"\']*["\'][^>]*>(\d+)</span>',
            r'<span[^>]*class=["\'][^"\']*page-number[^"\']*["\'][^>]*>(\d+)</span>'
        )
        for pattern in patterns:
            m = re.search(pattern, html, re.I)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
        return 0

    def _page_num(self, pg):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        return page

    def _empty(self, page):
        return {"list": [], "page": page, "pagecount": page if page >= 1 else 1, "limit": 20, "total": 0}

    def _list_result(self, html, page, max_page):
        pc = self._page_current(html)
        if pc != 0 and pc != page:
            return self._empty(page)
        cards = self._parse_cards(html)
        if not cards:
            return self._empty(page)
        pagecount = max_page if max_page >= page else page
        total = pagecount * len(cards)
        return {"list": cards, "page": page, "pagecount": pagecount, "limit": len(cards), "total": total}

    def homeContent(self, filter):
        result = {"class": [dict(item) for item in self.classes]}
        if filter:
            # 电影、电视剧分别使用各自的站点原生类型 ID；两者均支持
            # 按类型、按剧情、按年代和排序四组组合筛选。
            common_order = {
                "key": "order", "name": "排序", "init": "",
                "value": [
                    {"n": "时间排序", "v": ""},
                    {"n": "人气排序", "v": "hit"},
                    {"n": "评分排序", "v": "commend"}
                ]
            }
            filters = {
                "3": [dict(common_order)],
                "4": [dict(common_order)]
            }
            filters["1"] = [
                {"key": "tid", "name": "按类型", "init": "1",
                 "value": [dict(item) for item in self.movieTypeValues]},
                {"key": "jq", "name": "按剧情", "init": "",
                 "value": [dict(item) for item in self.moviePlotValues]},
                {"key": "year", "name": "按时间", "init": "",
                 "value": [dict(item) for item in self.movieYearValues]},
                {"key": "order", "name": "排序", "init": "time",
                 "value": [dict(item) for item in self.movieOrderValues]}
            ]
            filters["2"] = [
                {"key": "tid", "name": "按类型", "init": "2",
                 "value": [dict(item) for item in self.tvTypeValues]},
                {"key": "jq", "name": "按剧情", "init": "",
                 "value": [dict(item) for item in self.moviePlotValues]},
                {"key": "year", "name": "按年代", "init": "",
                 "value": [dict(item) for item in self.movieYearValues]},
                {"key": "order", "name": "排序", "init": "time",
                 "value": [dict(item) for item in self.movieOrderValues]}
            ]
            result["filters"] = filters
        return result

    def homeVideoContent(self):
        html = self._fetch(self.siteUrl + "/")
        if not html:
            return {"list": []}
        cards = []
        start = html.find("正在热播")
        if start != -1:
            end = html.find('<div class="module">', start)
            seg = html[start:end] if end != -1 else html[start:]
            cards = self._parse_cards(seg)
        if not cards:
            cards = self._parse_cards(html)
        return {"list": cards}

    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid or "")
        page = self._page_num(pg)
        known = False
        for item in self.classes:
            if item["type_id"] == tid:
                known = True
                break
        if not known:
            return self._empty(page)
        extend = extend if isinstance(extend, dict) else {}

        if tid in ("1", "2"):
            # 电影和电视剧都走网站高级搜索：tid / jq / year / order。
            # tid=1 是电影全部；tid=2 是电视剧全部；13-16 是电视剧子类型。
            if tid == "1":
                default_genre = "1"
                allowed_genres = {"1", "5", "6", "7", "8", "9", "10", "11", "12"}
            else:
                default_genre = "2"
                allowed_genres = {"2", "13", "14", "15", "16"}

            genre = str(extend.get("tid") or default_genre).strip()
            if genre not in allowed_genres:
                genre = default_genre

            plot = str(extend.get("jq") or "").strip()
            allowed_plots = {item["v"] for item in self.moviePlotValues}
            if plot not in allowed_plots:
                plot = ""

            year = str(extend.get("year") or "").strip()
            allowed_years = {item["v"] for item in self.movieYearValues}
            if year not in allowed_years:
                year = ""

            order = str(extend.get("order") or "time").strip()
            if order not in ("time", "hit", "commend"):
                order = "time"

            params = {
                "page": str(page),
                "searchtype": "5",
                "tid": genre,
                "order": order
            }
            if plot:
                params["jq"] = plot
            if year:
                params["year"] = year
            url = self.siteUrl + "/search.php?" + urllib.parse.urlencode(params)
            html = self._fetch(url)
            if not html:
                return self._empty(page)
            # 高级搜索翻页链接的 page 参数可能不在 URL 的第一个位置。
            pages = [int(x) for x in re.findall(r'[?&]page=(\d+)', html, re.I)]
            return self._list_result(html, page, max(pages) if pages else 0)

        # 综艺和动漫保留原有列表和排序请求方式。
        order = str(extend.get("order") or "")
        if order not in self.orderValues:
            order = ""
        if order:
            url = "%s/search.php?page=%s&searchtype=5&order=%s&tid=%s" % (
                self.siteUrl, page, quote(order, safe=""), quote(tid, safe=""))
        elif page > 1:
            url = "%s/frim/index%s-%s.html" % (self.siteUrl, tid, page)
        else:
            url = "%s/frim/index%s.html" % (self.siteUrl, tid)
        html = self._fetch(url)
        if not html:
            return self._empty(page)
        pages = [int(x) for x in re.findall(r'/frim/index%s-(\d+)\.html' % re.escape(tid), html)]
        return self._list_result(html, page, max(pages) if pages else 0)

    def searchContent(self, key, quick, pg="1"):
        page = self._page_num(pg)
        keyword = str(key or "").strip()
        if not keyword:
            return self._empty(page)
        url = "%s/search.php?page=%s&searchword=%s&searchtype=" % (self.siteUrl, page, quote(keyword, safe=""))
        html = self._fetch(url)
        if not html:
            return self._empty(page)
        pages = [int(x) for x in re.findall(r'search\.php\?page=(\d+)', html)]
        return self._list_result(html, page, max(pages) if pages else 0)

    def _link_texts(self, seg):
        out = []
        for m in re.finditer(r'<a[^>]*>([^<]+)</a>', seg or "", re.I):
            text = m.group(1).strip()
            if text:
                out.append(text)
        return out

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        vid = str(raw or "")
        if not vid:
            return {"list": []}
        detail_url = "%s/movie/index%s.html" % (self.siteUrl, vid)
        html = self._fetch(detail_url)
        if not html:
            return {"list": []}
        own_links = []
        for m in re.finditer(r'/play/([0-9]+)-(\d+)-(\d+)\.html', html, re.I):
            if m.group(1) == vid:
                own_links.append((int(m.group(2)), int(m.group(3))))
        if not own_links:
            return {"list": []}

        # 从详情页线路标签读取真实线路名，再按播放链接中的线路 ID 顺序对应。
        extracted_line_names = self._extract_line_names(html)

        title = vid
        hm = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I)
        if hm and hm.group(1):
            title = hm.group(1).strip()
        cat_name = ""
        tm = re.search(r'<title>([\s\S]*?)</title>', html, re.I)
        if tm and tm.group(1):
            cm = re.search(r'_([^_]+)_茶杯狐', tm.group(1))
            if cm and cm.group(1):
                cat_name = cm.group(1).strip()
        desc = ""
        dm = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html, re.I)
        if not dm:
            dm = re.search(r'<meta[^>]+content="([^"]*)"[^>]+name="description"', html, re.I)
        if dm and dm.group(1):
            desc = self._decode_entities(dm.group(1))
        year = ""
        ym = re.search(r'于(\d{4})年上映', desc)
        if ym and ym.group(1):
            year = ym.group(1)
        synopsis = ""
        si = desc.find("讲述的是")
        if si != -1:
            synopsis = desc[si + 4:].strip()
        elif desc:
            synopsis = re.sub(r'^[^：]*剧情介绍：', "", desc).strip()
        # 从详情页读取网站原始导演、主演，不额外插入第三方品牌信息。
        directors = []
        d_start = html.find("导演：")
        if d_start != -1:
            d_end_candidates = [html.find(label, d_start + len("导演："))
                                for label in ("主演：", "更新：", "类型：", "地区：", "年份：", "备注：")]
            d_end_candidates = [pos for pos in d_end_candidates if pos != -1]
            d_end = min(d_end_candidates) if d_end_candidates else min(len(html), d_start + 4000)
            d_seg = html[d_start:d_end]
            directors = [name for name in self._link_texts(d_seg) if name != "内详"]

        actors = []
        a_start = html.find("主演：")
        if a_start != -1:
            a_end_candidates = [html.find(label, a_start + len("主演："))
                                for label in ("更新：", "类型：", "地区：", "年份：", "备注：")]
            a_end_candidates = [pos for pos in a_end_candidates if pos != -1]
            a_end = min(a_end_candidates) if a_end_candidates else min(len(html), a_start + 4000)
            a_seg = html[a_start:a_end]
            actors = [name for name in self._link_texts(a_seg) if name != "内详"]
        remark = ""
        rk = html.find("备注：")
        if rk != -1:
            rm = re.search(r'<div class="video-info-item">([^<]+)</div>', html[rk:rk + 500])
            if rm and rm.group(1):
                remark = rm.group(1).strip()
        poster = ""
        for pm in re.finditer(r'<img[^>]*class="lazyload"[^>]*>', html, re.I):
            picked = self._pick_poster(pm.group(0))
            if picked:
                poster = picked
                break
        lines_map = {}
        for line_idx, ep_idx in own_links:
            lines_map.setdefault(line_idx, set()).add(ep_idx)
        play_from = []
        play_url = []
        for position, line_idx in enumerate(sorted(lines_map.keys())):
            if position < len(extracted_line_names):
                line_name = extracted_line_names[position]
            else:
                # 线路标签抓取失败时只使用中性编号，不再把 ID 0 写死成品牌线路。
                line_name = "线路%s" % (line_idx + 1)
            eps = []
            for ep_idx in sorted(lines_map[line_idx]):
                ep_name = "第%02d集" % (ep_idx + 1)
                eps.append("%s$%s-%s-%s" % (ep_name, vid, line_idx, ep_idx))
            play_from.append(line_name)
            play_url.append("#".join(eps))
        related = []
        seen_rel = {}
        r_start = html.find("猜你喜欢")
        if r_start != -1:
            r_end = html.find('<div class="module">', r_start)
            r_seg = html[r_start:r_end] if r_end != -1 else html[r_start:r_start + 13000]
            for rm2 in re.finditer(r'/movie/index(\d+)\.html"[^>]*title="([^"]*)"', r_seg, re.I):
                rvid = rm2.group(1)
                rtitle = self._decode_entities(rm2.group(2)).strip()
                if not rvid or rvid == vid or rvid in seen_rel:
                    continue
                seen_rel[rvid] = True
                related.append((rvid, rtitle if rtitle else rvid))
        if related:
            rel_eps = []
            for rvid, rtitle in related:
                clean_title = rtitle.replace("$", "").replace("#", "").strip()
                rel_eps.append("%s$rel:%s" % (clean_title, rvid))
            play_from.append("相关推荐")
            play_url.append("#".join(rel_eps))
        # 简介优先使用网站 description；没有简介时仅保留基础影片信息。
        content_lines = []
        if synopsis:
            content_lines.append(synopsis)
        else:
            content_lines.append("标题：%s" % title)
            if cat_name:
                content_lines.append("分类：%s" % cat_name)
            if related:
                names = [rtitle for _, rtitle in related[:6]]
                content_lines.append("相关推荐：%s" % " / ".join(names))
        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": poster,
            "vod_bg": poster,
            "vod_background": poster,
            "vod_banner": poster,
            "vod_actor": "、".join(actors),
            "vod_director": "、".join(directors),
            "vod_remarks": format_remarks(remark),
            "vod_content": "\n".join(content_lines),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url)
        }
        if cat_name:
            vod["type_name"] = cat_name
            vod["vod_tag"] = cat_name
        if year:
            vod["vod_year"] = year
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        if raw.startswith("rel:"):
            vid = raw[4:]
            line_idx, ep_idx = 0, 0
        else:
            parts = raw.split("-")
            if len(parts) != 3 or not parts[0].isdigit():
                return {"parse": 0, "jx": 0, "url": ""}
            vid = parts[0]
            try:
                line_idx, ep_idx = int(parts[1]), int(parts[2])
            except Exception:
                return {"parse": 0, "jx": 0, "url": ""}
        play_url = "%s/play/%s-%s-%s.html" % (self.siteUrl, vid, line_idx, ep_idx)
        detail_url = "%s/movie/index%s.html" % (self.siteUrl, vid)
        headers = {
            "User-Agent": self._ua,
            "Referer": play_url
        }
        html = self._fetch(play_url, detail_url)
        m = re.search(r'var now="([^"]+)"', html or "")
        if not m or not m.group(1):
            return {"parse": 1, "playUrl": "", "url": play_url, "header": headers}
        url = m.group(1).strip()
        low = url.lower()
        if ".m3u8" in low or ".mp4" in low or ".flv" in low or ".mkv" in low:
            return {"parse": 0, "jx": 0, "url": url, "header": headers}
        if url.startswith("http") and ".html" not in low:
            sep = "&" if "?" in url else "?"
            return {"parse": 0, "jx": 0, "url": url + sep + "format=.m3u8", "header": headers}
        return {"parse": 1, "playUrl": "", "url": url, "header": headers}

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]
