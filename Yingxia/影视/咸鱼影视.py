# Yingxia-compatible CatVod Python spider for jxw888.cn
import html
import json
import re
import urllib.parse

import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def getCache(self, key):
            return None

        def setCache(self, key, value):
            return "fail"

        def delCache(self, key):
            return "fail"


def format_remarks(meta=""):
    """Normalize remarks without adding any third-party branding."""
    clean_meta = str(meta or "").strip()
    return re.sub(r"[\r\n\t]+", " ", clean_meta).strip()


class Spider(BaseSpider):
    def __init__(self):
        super(Spider, self).__init__()
        self.siteUrl = "https://www.jxw888.cn"
        self.siteName = "咸鱼影视"
        self._ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.options = {}
        # Yingxia's Python host explicitly provides requests. Keep one session
        # per spider so cookies obtained while browsing can be reused for play.
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self._ua,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.classes = [
            ("1", "电影片"), ("2", "连续剧"), ("3", "综艺片"), ("4", "动漫片"),
            ("35", "电影解说"), ("36", "体育"), ("46", "短剧"),
        ]
        self.sub_map = {
            "1": [
                ("6", "动作片"), ("7", "喜剧片"), ("8", "爱情片"), ("9", "科幻片"),
                ("10", "恐怖片"), ("11", "剧情片"), ("12", "战争片"), ("20", "记录片"),
                ("45", "预告片"),
            ],
            "2": [
                ("13", "国产剧"), ("14", "香港剧"), ("15", "韩国剧"), ("16", "欧美剧"),
                ("21", "台湾剧"), ("22", "日本剧"), ("23", "海外剧"), ("24", "泰国剧"),
            ],
            "3": [
                ("25", "大陆综艺"), ("26", "港台综艺"), ("27", "日韩综艺"), ("28", "欧美综艺"),
            ],
            "4": [
                ("29", "国产动漫"), ("30", "日韩动漫"), ("31", "欧美动漫"), ("32", "港台动漫"),
                ("33", "海外动漫"),
            ],
            "36": [
                ("37", "足球"), ("38", "篮球"), ("39", "网球"), ("40", "斯诺克"),
            ],
        }
        self.all_years = ["2028", "2027", "2026", "2025", "2024", "2023", "2022",
                          "2021", "2020", "2019", "2018", "2017", "2016", "2015",
                          "2014", "2013", "2012", "2011", "2010", "2009", "2008",
                          "2007", "2006", "2005", "2003", "2002", "2000", "1998",
                          "1996", "1995", "1989", "1978", "1973", "1942"]
        self.all_areas = ["中国大陆", "中国香港", "中国台湾", "美国", "日本", "韩国",
                          "英国", "法国", "德国", "俄罗斯", "印度", "泰国", "加拿大",
                          "澳大利亚", "意大利", "西班牙", "巴西", "新加坡"]
        self.card_style = {"type": "rect", "ratio": 0.67}

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
        return self.siteName

    def isVideoFormat(self, url):
        low = (url or "").lower()
        return any(k in low for k in (".m3u8", ".mp4", ".flv", ".mkv", ".avi", ".ts", ".mpd"))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self.options = {}
        try:
            self.session.close()
        except Exception:
            pass

    def _fetch(self, target_url, referer=""):
        if not target_url:
            return {"code": 0, "text": "", "err": "empty url", "final_url": ""}
        target_url = urllib.parse.urljoin(self.siteUrl + "/", str(target_url).strip())
        headers = {
            "Referer": referer or (self.siteUrl + "/"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        last_err = ""
        for attempt in range(2):
            try:
                # TLS verification is intentionally left enabled. requests also
                # handles gzip/deflate and maintains the session cookie jar.
                response = self.session.get(
                    target_url,
                    headers=headers,
                    timeout=(4, 8),
                    allow_redirects=True,
                    verify=True,
                )
                content = response.content or b""
                try:
                    text = content.decode("utf-8-sig")
                except Exception:
                    text = content.decode("gb18030", errors="replace")
                if response.status_code in (429, 502, 503, 504) and attempt == 0:
                    last_err = "HTTP %s" % response.status_code
                    continue
                return {
                    "code": response.status_code,
                    "text": text,
                    "err": "" if response.ok else ("HTTP %s" % response.status_code),
                    "final_url": response.url or target_url,
                }
            except requests.RequestException as e:
                last_err = str(e)
                if attempt == 0:
                    continue
                return {"code": -1, "text": "", "err": last_err, "final_url": target_url}
            except Exception as e:
                last_err = str(e)
                return {"code": -1, "text": "", "err": last_err, "final_url": target_url}
        return {"code": -1, "text": "", "err": last_err, "final_url": target_url}

    def _absolute_media_url(self, media_url, base_url=""):
        media_url = html.unescape(str(media_url or "").strip())
        if not media_url:
            return ""
        return urllib.parse.urljoin(base_url or (self.siteUrl + "/"), media_url)

    def _player_headers(self, referer=""):
        headers = {
            "User-Agent": self._ua,
            "Referer": referer or (self.siteUrl + "/"),
        }
        try:
            cookie_items = [
                "%s=%s" % (cookie.name, cookie.value)
                for cookie in self.session.cookies
                if cookie.name and cookie.value is not None
            ]
            if cookie_items:
                headers["Cookie"] = "; ".join(cookie_items)
        except Exception:
            pass
        return headers

    def _decode_pic(self, src):
        if not src:
            return ""
        src = html.unescape(src.strip())
        if src.startswith("/pic.php?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
            vals = qs.get("u") or []
            if vals:
                return urllib.parse.unquote(vals[0])
            return ""
        if src.startswith("//"):
            return "https:" + src
        if src.startswith("/"):
            return self.siteUrl + src
        return src

    def _parse_cards(self, page_html):
        cards = []
        pat = re.compile(
            r'<a class="card" href="/detail/(\d+)\.html">'
            r'[\s\S]*?<img[^>]+src="([^"]+)"'
            r'(?:[\s\S]*?<b>([^<]*)</b>)?'
            r'[\s\S]*?<div class="nm">(.*?)</div>'
            r'[\s\S]*?<div class="rm">(.*?)</div>',
            re.S)
        for m in pat.finditer(page_html or ""):
            vid = m.group(1)
            pic = self._decode_pic(m.group(2))
            status = html.unescape(m.group(3) or "").strip()
            name = html.unescape(re.sub(r"<[^>]+>", "", m.group(4))).strip()
            rm = html.unescape(re.sub(r"<[^>]+>", "", m.group(5))).strip()
            meta = rm
            if status:
                meta = (rm + " · " + status) if rm else status
            cards.append({
                "vod_id": "vod/" + vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": format_remarks(meta),
                "style": dict(self.card_style),
            })
        return cards

    def _extract_vod(self, page_html):
        if not page_html:
            return None
        marker = "const VOD ="
        i = page_html.find(marker)
        if i < 0:
            return None
        j = page_html.find("{", i + len(marker))
        if j < 0:
            return None
        try:
            obj, _ = json.JSONDecoder().raw_decode(page_html[j:])
            return obj if isinstance(obj, dict) else None
        except (TypeError, ValueError):
            return None

    def _primary_line_index(self, lines):
        best = 0
        best_n = -1
        for idx, line in enumerate(lines or []):
            if not isinstance(line, dict):
                continue
            cnt = len(line.get("eps") or [])
            if cnt > best_n:
                best_n = cnt
                best = idx
        return best

    def _clean_ep_name(self, name):
        name = str(name or "").strip()
        name = name.replace("$", "").replace("#", "").strip()
        return name if name else "正片"

    def _line_episodes(self, vid, line_idx, line):
        eps = line.get("eps") or []
        out = []
        single = len(eps) <= 1
        for pos, ep in enumerate(eps):
            if not isinstance(ep, dict):
                continue
            if single:
                ep_name = self._clean_ep_name(ep.get("t"))
            else:
                ep_name = "第%d集" % (pos + 1)
            out.append("%s$play:%s:%d:%d" % (ep_name, vid, line_idx, pos + 1))
        return "#".join(out)

    def _vod_play_url(self, vid, vod):
        lines = vod.get("lines") or []
        if not isinstance(lines, list) or not lines:
            return [], []
        play_from = []
        play_url = []
        # Do not reorder: VOD.lines is the site's own route order, and the
        # line index in each play ID must continue to point to that same entry.
        for line_idx, line in enumerate(lines):
            if not isinstance(line, (dict, str)):
                continue
            episodes = self._line_episodes(vid, line_idx, line) if isinstance(line, dict) else ""
            if not episodes:
                continue
            # Display routes in order as 线路1、线路2... while keeping
            # the original VOD.lines index in each play ID for playback.
            play_from.append("线路%d" % (len(play_from) + 1))
            play_url.append(episodes)
        return play_from, play_url

    def _related_episodes(self, detail_html):
        rel = []
        if not detail_html:
            return rel
        pat = re.compile(
            r'<a class="relcard" href="/detail/(\d+)\.html"[^>]*>'
            r'[\s\S]*?<div class="t">(.*?)</div>',
            re.S)
        seen = set()
        for m in pat.finditer(detail_html):
            rid = m.group(1)
            title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            if not rid or rid in seen or not title:
                continue
            seen.add(rid)
            title = self._clean_ep_name(title)
            url = "%s/detail/%s-1-0.html" % (self.siteUrl, rid)
            rel.append("%s$%s@@@%s" % (title, url, title))
        return rel

    def homeContent(self, filter):
        result = {
            "class": [{"type_id": tid, "type_name": name} for tid, name in self.classes],
        }
        if filter:
            year_filter = {
                "key": "y", "name": "年份", "init": "",
                "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.all_years],
            }
            area_filter = {
                "key": "area", "name": "地区", "init": "",
                "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.all_areas],
            }
            filters = {}
            for tid, _ in self.classes:
                if tid == "latest":
                    continue
                dim_list = []
                subs = self.sub_map.get(tid)
                if subs:
                    dim_list.append({
                        "key": "sub", "name": "子分类", "init": "",
                        "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": i} for i, n in subs],
                    })
                if tid in ("1", "2", "3", "4", "35", "46"):
                    dim_list.append(area_filter)
                    dim_list.append(year_filter)
                if dim_list:
                    filters[tid] = dim_list
            result["filters"] = filters
        return result

    def homeVideoContent(self):
        """Return real homepage video cards for Yingxia's Watch Now > Recommendations.

        The homepage is the source's existing front page (the same route that
        previously backed the hidden latest-updates category).  Keeping this
        separate from ``self.classes`` means the app gets a populated,
        clickable recommendation shelf without exposing a 最近更新 category.
        Each card has a real vod_id, so Yingxia can open detailContent directly.
        """
        res = self._fetch(self.siteUrl + "/")
        cards = self._parse_cards(res.get("text", "")) if res.get("code") == 200 else []
        return {"list": cards}

    def _normalize_extend(self, extend):
        """Accept both CatVod dict parameters and hosts that serialize extend."""
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str) and extend.strip():
            try:
                value = json.loads(extend)
                return value if isinstance(value, dict) else {}
            except Exception:
                return {}
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        tid = str(tid or "").strip()
        extend = self._normalize_extend(extend)
        sub = str(extend.get("sub") or "").strip()
        if sub and sub != "全部":
            tid = sub
        y = str(extend.get("y") or "").strip()
        area = str(extend.get("area") or "").strip()
        if y == "全部":
            y = ""
        if area == "全部":
            area = ""
        query = ""
        if y or area:
            parts = []
            if y:
                parts.append("y=" + urllib.parse.quote(y))
            if area:
                parts.append("area=" + urllib.parse.quote(area))
            query = "?" + "&".join(parts)
        # homeContent() exposes the website's native category IDs.  Movie,
        # series, variety, animation, sports, etc. therefore map directly to
        # /list/<type_id>.html and remain independently clickable in Yingxia.
        if tid == "latest":
            url = "%s/?pg=%d" % (self.siteUrl, page)
        elif page == 1 and not query:
            url = "%s/list/%s.html" % (self.siteUrl, tid)
        else:
            url = "%s/list/%s-%d.html%s" % (self.siteUrl, tid, page, query)
        res = self._fetch(url)
        cards = self._parse_cards(res.get("text", "")) if res.get("code") == 200 else []
        if len(cards) >= 21:
            pagecount = page + 1
            total = page * 21 + 100
        else:
            pagecount = page if cards else 1
            total = (page - 1) * 21 + len(cards)
        return {"list": cards, "page": int(page), "pagecount": int(pagecount), "limit": 21, "total": int(total)}

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        vid = str(raw_id).replace("vod/", "").strip()
        detail_url = "%s/detail/%s.html" % (self.siteUrl, vid)
        dres = self._fetch(detail_url)
        dhtml = dres.get("text", "") if dres.get("code") == 200 else ""
        pres = self._fetch("%s/detail/%s-1-0.html" % (self.siteUrl, vid), referer=detail_url)
        vod = self._extract_vod(pres.get("text", "")) if pres.get("code") == 200 else None
        if vod:
            name = vod.get("name") or ""
            pic = vod.get("pic") or ""
            remarks = vod.get("remarks") or ""
            desc = vod.get("content") or ""
            actor = vod.get("actor") or ""
            director = vod.get("director") or ""
            type_name = vod.get("type_name") or vod.get("class") or ""
        else:
            name = ""
            pic = ""
            remarks = ""
            desc = ""
            actor = ""
            director = ""
            type_name = ""
            m = re.search(r"<h1[^>]*>(.*?)</h1>", dhtml, re.S)
            if m:
                name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
            m = re.search(r'<img[^>]+src="([^"]+)"', dhtml)
            if m:
                pic = self._decode_pic(m.group(1))
            m = re.search(r'<meta name="description" content="([^"]*)"', dhtml)
            if m:
                full = html.unescape(m.group(1))
                if "剧情简介：" in full:
                    desc = full.split("剧情简介：", 1)[1].strip()
        if not pic:
            m = re.search(r'<img[^>]+src="([^"]+)"', dhtml)
            if m:
                pic = self._decode_pic(m.group(1))
        vod_actor = actor
        if desc:
            vod_content = str(desc).strip()
        else:
            related_titles = []
            for ep in self._related_episodes(dhtml):
                nm = ep.split("$", 1)[0]
                if nm:
                    related_titles.append(nm)
            vod_content = (
                "标题：%s\n分类：%s\n编号：%s\n相关推荐：%s"
                % (name, type_name, vid, "、".join(related_titles[:6]))
            )
        if vod:
            play_from, play_url = self._vod_play_url(vid, vod)
        else:
            play_from = []
            eps = []
            for m in re.finditer(r"/detail/%s-(\d+)-0\.html" % re.escape(vid), dhtml):
                ep_no = int(m.group(1))
                eps.append("第%d集$play:%s:0:%d" % (ep_no, vid, ep_no))
            seen_ep = set()
            uniq = []
            for e in eps:
                if e not in seen_ep:
                    seen_ep.add(e)
                    uniq.append(e)
            play_url = ["#".join(uniq)] if uniq else []
            if uniq:
                play_from = ["线路1"]
        related = self._related_episodes(dhtml)
        if related:
            play_from = play_from + ["相关推荐"]
            play_url = play_url + ["#".join(related)]
        vod_item = {
            "vod_id": "vod/" + vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_bg": pic,
            "vod_background": pic,
            "vod_banner": pic,
            "vod_actor": vod_actor,
            "vod_director": director,
            "vod_remarks": format_remarks(remarks),
            "vod_content": vod_content,
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }
        return {"list": [vod_item]}

    def _resolve_play_page(self, play_url):
        res = self._fetch(play_url)
        if res.get("code") != 200:
            return ""
        vod = self._extract_vod(res.get("text", ""))
        if not vod:
            return ""
        lines = vod.get("lines") or []
        if not lines:
            return ""
        primary = self._primary_line_index(lines)
        if not (0 <= primary < len(lines)) or not isinstance(lines[primary], dict):
            return ""
        eps = lines[primary].get("eps") or []
        if not eps or not isinstance(eps[0], dict):
            return ""
        return self._absolute_media_url(eps[0].get("u"), res.get("final_url") or play_url)

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        media_url = ""
        media_referer = self.siteUrl + "/"

        if "@@@" in raw:
            play_page = raw.split("@@@", 1)[0].strip()
            media_referer = play_page
            media_url = self._resolve_play_page(play_page)
        elif raw.startswith("play:"):
            parts = raw.split(":")
            if len(parts) == 4:
                vid = parts[1]
                try:
                    line_idx = int(parts[2])
                    ep_no = int(parts[3])
                except Exception:
                    line_idx, ep_no = -1, -1
                play_page = "%s/detail/%s-%d-%d.html" % (
                    self.siteUrl, vid, ep_no, line_idx
                )
                media_referer = play_page
                res = self._fetch(
                    play_page,
                    referer="%s/detail/%s.html" % (self.siteUrl, vid),
                )
                if res.get("code") == 200:
                    vod = self._extract_vod(res.get("text", ""))
                    if vod:
                        lines = vod.get("lines") or []
                        if 0 <= line_idx < len(lines) and isinstance(lines[line_idx], dict):
                            eps = lines[line_idx].get("eps") or []
                            if 0 < ep_no <= len(eps) and isinstance(eps[ep_no - 1], dict):
                                media_url = self._absolute_media_url(
                                    eps[ep_no - 1].get("u"),
                                    res.get("final_url") or play_page,
                                )
        elif raw.startswith(("http://", "https://", "//")):
            if "/detail/" in raw:
                media_referer = raw
                media_url = self._resolve_play_page(raw)
            else:
                media_url = self._absolute_media_url(raw)
        else:
            media_url = self._absolute_media_url(raw)

        # Yingxia's player consumes the standard CatVod {parse, jx, url, header}
        # response. Include the source session cookie and the actual play-page
        # Referer because AVPlayer performs the subsequent media/HLS requests.
        return {
            "parse": 0,
            "jx": 0,
            "url": media_url,
            "header": self._player_headers(media_referer),
        }

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page != 1:
            return {"list": [], "page": int(page), "pagecount": 1, "limit": 21, "total": 0}
        url = "%s/?wd=%s" % (self.siteUrl, urllib.parse.quote(str(key)))
        res = self._fetch(url)
        cards = self._parse_cards(res.get("text", "")) if res.get("code") == 200 else []
        return {"list": cards, "page": 1, "pagecount": 1, "limit": 21, "total": len(cards)}

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Proxy not configured"]