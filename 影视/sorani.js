/*
 * Sorani adapter for tvbox-silicon / Yingxia (type 3 JavaScript spider).
 * This revision intentionally contains NO ES class declarations.
 * The exported constructor is an ordinary function that works both as
 * createSoraniSpider() and as new createSoraniSpider().
 *
 * API endpoints used by this adapter:
 *   GET /sorani-cms/api/video?page=&size=&keyword=&enabled=&sortMode=&sortDesc=
 *   GET /sorani-cms/api/video/{videoId}
 *   GET /sorani-cms/api/video/episode/{episodeId}/play
 *
 * Login note: this adapter does not bypass Sorani's interactive slider CAPTCHA.
 * After the native macOS web-login bridge has saved a session in Keychain, the
 * host injects ext.soraniCookiesByDomain into this Spider at runtime.
 */

const WEB = "https://www.sorani.net";
const API = "https://api.sorani.cc/sorani-cms/api";
const PAGE_SIZE = 24;

function asText(value, fallback) {
  if (fallback === undefined) fallback = "";
  return value === undefined || value === null ? fallback : String(value);
}

function firstValue(obj, keys, fallback) {
  if (fallback === undefined) fallback = "";
  for (let i = 0; i < keys.length; i++) {
    const value = obj && obj[keys[i]];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
}

function unwrap(value) {
  let current = value;
  for (let i = 0; i < 2; i++) {
    if (current && !Array.isArray(current) && typeof current === "object" && current.data !== undefined) {
      current = current.data;
    } else {
      break;
    }
  }
  return current;
}

function normalizeImage(value) {
  const raw = asText(value).trim();
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.indexOf("//") === 0) return "https:" + raw;
  try { return new URL(raw, WEB + "/").href; } catch (_) { return raw; }
}

function videoCard(item) {
  const id = firstValue(item, ["id", "videoId", "malId", "sourceId"]);
  const name = firstValue(item, ["title", "name", "videoName", "animeTitle"], "未命名");
  const image = firstValue(item, ["cover", "coverUrl", "coverImage", "imageUrl", "image", "poster", "pic"]);
  const remarks = firstValue(item, ["remarks", "latestEpisode", "episodeLabel", "updateInfo", "status"]);
  const year = firstValue(item, ["year", "releaseYear"]);
  const category = firstValue(item, ["categoryName", "typeName", "category"]);
  const intro = firstValue(item, ["description", "summary", "synopsis", "intro"]);
  return {
    vod_id: asText(id),
    vod_name: asText(name),
    vod_pic: normalizeImage(image),
    vod_remarks: asText(remarks),
    vod_year: asText(year),
    type_name: asText(category),
    vod_content: asText(intro)
  };
}

function jsonResult(value) {
  return JSON.stringify(value);
}

// Ordinary function constructor: callable without `new` and constructible with `new`.
function createSoraniSpider() {
  if (!(this instanceof createSoraniSpider)) return new createSoraniSpider();
  this.ext = {};
  this.cookie = "";
  this.authorization = "";
}

createSoraniSpider.prototype.init = function (ext) {
  let parsed = ext;
  // CatVod-compatible hosts may wrap the actual extension in { stype, skey, ext }.
  if (parsed && typeof parsed === "object" && parsed.ext !== undefined) parsed = parsed.ext;
  if (typeof parsed === "string" && parsed.trim()) {
    try { parsed = JSON.parse(parsed); } catch (_) { parsed = {}; }
  }
  this.ext = parsed && typeof parsed === "object" ? parsed : {};
  this.cookie = asText(
    this.ext.soraniCookie || this.ext.cookie || this.ext.Cookie
  ).trim();
  this.authorization = asText(
    this.ext.soraniAuthorization || this.ext.authorization || this.ext.Authorization
  ).trim();

  let cookieMap = this.ext.soraniCookiesByDomain || {};
  if (typeof cookieMap === "string" && cookieMap.trim()) {
    try { cookieMap = JSON.parse(cookieMap); } catch (_) { cookieMap = {}; }
  }
  this.soraniCookiesByDomain = cookieMap && typeof cookieMap === "object"
    ? cookieMap : {};
};

createSoraniSpider.prototype.cookieForURL = function (url) {
  let host = "";
  try { host = new URL(url).hostname.toLowerCase(); } catch (_) {}
  if (!host) return this.cookie;

  // Pick the most-specific saved cookie domain that matches this request host.
  const domains = Object.keys(this.soraniCookiesByDomain || {}).sort(function (a, b) {
    return b.length - a.length;
  });
  for (let i = 0; i < domains.length; i++) {
    const domain = domains[i].replace(/^\./, "").toLowerCase();
    if (host === domain || host.endsWith("." + domain)) {
      const value = asText(this.soraniCookiesByDomain[domains[i]]).trim();
      if (value) return value;
    }
  }

  // Legacy single-cookie fallback is restricted to Sorani hosts only.
  const isSoraniHost = host === "sorani.net" || host.endsWith(".sorani.net")
    || host === "sorani.cc" || host.endsWith(".sorani.cc");
  return isSoraniHost ? this.cookie : "";
};

createSoraniSpider.prototype.headers = function (url, extra) {
  // Keep backward compatibility with callers that used headers(extra).
  if (url && typeof url === "object") {
    extra = url;
    url = "";
  }
  const headers = {
    "Accept": "application/json, text/plain, */*",
    "Referer": WEB + "/",
    "Origin": WEB,
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
  };
  if (extra) Object.keys(extra).forEach(function (key) { headers[key] = extra[key]; });
  const host = url ? (function (value) {
    try { return new URL(value).hostname.toLowerCase(); } catch (_) { return ""; }
  })(url) : "";
  const isSoraniHost = !host || host === "sorani.net" || host.endsWith(".sorani.net")
    || host === "sorani.cc" || host.endsWith(".sorani.cc");
  const cookie = url ? this.cookieForURL(url) : this.cookie;
  if (cookie) headers.Cookie = cookie;
  if (this.authorization && isSoraniHost) headers.Authorization = this.authorization;
  return headers;
};

createSoraniSpider.prototype.requestJson = function (url, options) {
  options = options || {};
  if (typeof req !== "function") throw new Error("当前 Spider 运行环境没有提供 req() HTTP 接口");
  const response = req(url, {
    method: options.method || "GET",
    headers: this.headers(url, options.headers || {}),
    body: options.body,
    timeout: options.timeout || 20000
  });
  const status = Number(response && (response.code || response.status) || 0);
  const body = response && response.content !== undefined ? response.content
    : (response && response.body !== undefined ? response.body : "");
  if (status >= 400) throw new Error("Sorani API HTTP " + status + ": " + asText(body).slice(0, 180));
  let parsed;
  try { parsed = typeof body === "string" ? JSON.parse(body) : body; }
  catch (_) { throw new Error("Sorani API 返回的不是有效 JSON"); }
  if (parsed && typeof parsed === "object") {
    const code = firstValue(parsed, ["code", "statusCode"]);
    if (parsed.success === false || (code !== "" && code !== 0 && code !== 200 && code !== "200")) {
      throw new Error("Sorani: " + asText(firstValue(parsed, ["message", "msg", "error"], "请求被服务器拒绝")));
    }
  }
  return parsed;
};

createSoraniSpider.prototype.listPayload = function (payload) {
  const root = unwrap(payload);
  if (Array.isArray(root)) return { records: root, total: root.length };
  const records = firstValue(root, ["records", "list", "items", "videos"], []);
  return {
    records: Array.isArray(records) ? records : [],
    total: Number(firstValue(root, ["total", "totalElements", "count"], 0)) || 0
  };
};

createSoraniSpider.prototype.listUrl = function (page, keyword, sortMode) {
  const params = [
    "page=" + encodeURIComponent(String(page)),
    "size=" + encodeURIComponent(String(PAGE_SIZE)),
    "keyword=" + encodeURIComponent(String(keyword || "")),
    "enabled=true",
    "sortMode=" + encodeURIComponent(sortMode || "latest"),
    "sortDesc=false"
  ];
  return API + "/video?" + params.join("&");
};

createSoraniSpider.prototype.pagedList = function (payload, pg) {
  const page = Math.max(1, parseInt(pg, 10) || 1);
  const result = this.listPayload(payload);
  const records = result.records;
  const list = records.map(videoCard).filter(function (item) { return item.vod_id && item.vod_name; });
  const pagecount = result.total > 0 ? Math.max(page, Math.ceil(result.total / PAGE_SIZE))
    : (records.length >= PAGE_SIZE ? page + 1 : page);
  return { list: list, page: page, pagecount: pagecount, limit: PAGE_SIZE, total: result.total };
};

createSoraniSpider.prototype.home = function (filter) {
  return jsonResult({ class: [{ type_id: "latest", type_name: "全部 / 最新更新" }] });
};

createSoraniSpider.prototype.homeVod = function () {
  return jsonResult(this.pagedList(this.requestJson(this.listUrl(1, "", "latest")), 1));
};

createSoraniSpider.prototype.category = function (tid, pg, filter, extend) {
  const page = Math.max(1, parseInt(pg, 10) || 1);
  return jsonResult(this.pagedList(this.requestJson(this.listUrl(page, "", "latest")), page));
};

createSoraniSpider.prototype.search = function (key, quick, pg) {
  const page = Math.max(1, parseInt(pg, 10) || 1);
  return jsonResult(this.pagedList(this.requestJson(this.listUrl(page, asText(key), "latest")), page));
};

createSoraniSpider.prototype.detail = function (id) {
  const ids = Array.isArray(id) ? id : [id];
  const list = [];
  for (let i = 0; i < ids.length; i++) {
    const videoId = asText(ids[i]).trim();
    if (!videoId) continue;
    const payload = this.requestJson(API + "/video/" + encodeURIComponent(videoId));
    const detail = unwrap(payload) || {};
    const base = videoCard(detail);
    const episodes = Array.isArray(detail.episodes) ? detail.episodes
      : (Array.isArray(payload && payload.episodes) ? payload.episodes : []);
    const episodeLines = [];
    for (let j = 0; j < episodes.length; j++) {
      const episode = episodes[j];
      const episodeId = firstValue(episode, ["episodeId", "id", "episodeOrder", "order"]);
      if (episodeId === "") continue;
      const label = firstValue(episode, ["episodeLabel", "name", "title", "episodeName"], "第" + episodeId + "集");
      episodeLines.push(asText(label).replace(/[#$]/g, " ") + "$" + encodeURIComponent(asText(episodeId)));
    }
    list.push({
      ...base,
      vod_id: videoId,
      vod_name: asText(firstValue(detail, ["title", "name", "videoName"], base.vod_name)),
      vod_pic: normalizeImage(firstValue(detail, ["cover", "coverUrl", "coverImage", "imageUrl", "image", "poster", "pic"], base.vod_pic)),
      vod_content: asText(firstValue(detail, ["description", "summary", "synopsis", "intro"], base.vod_content)),
      vod_play_from: "Sorani",
      vod_play_url: episodeLines.join("#")
    });
  }
  return jsonResult({ list: list });
};

createSoraniSpider.prototype.play = function (flag, id, flags) {
  let episodeId = asText(id);
  try { episodeId = decodeURIComponent(episodeId); } catch (_) {}
  if (!episodeId) throw new Error("Sorani: 缺少集数 ID");
  const payload = this.requestJson(API + "/video/episode/" + encodeURIComponent(episodeId) + "/play");
  const data = unwrap(payload) || {};
  const playUrl = firstValue(data, ["playUrl", "url", "videoUrl", "src"])
    || firstValue(payload, ["playUrl", "url", "videoUrl", "src"]);
  if (!playUrl || !/^https?:\/\//i.test(asText(playUrl))) {
    throw new Error("Sorani 未返回可直接播放的 HTTP 视频地址；可能需要有效登录态或该集暂不可用");
  }
  return jsonResult({ parse: 0, jx: 0, url: asText(playUrl), header: this.headers(playUrl) });
};

export default createSoraniSpider;
