/*
 * Sorani adapter for tvbox-silicon / Yingxia (type 3 JavaScript spider)
 *
 * Confirmed API shape from a public third-party Sorani rule:
 *   GET /sorani-cms/api/video?page=&size=&keyword=&enabled=&sortMode=&sortDesc=
 *   GET /sorani-cms/api/video/{videoId}
 *   response list: data.records[]; detail episodes: data.episodes[]
 *
 * Playback endpoint is implemented from the Sorani episode API route:
 *   GET /sorani-cms/api/video/episode/{episodeId}/play
 *
 * Login UI note:
 *   This script intentionally does not automate or bypass Sorani's drag CAPTCHA.
 *   tvbox-silicon's native source-account UI currently only supports QR sign-in.
 *   ext.cookie / ext.authorization are optional manual session-header overrides.
 */

const WEB = "https://www.sorani.net";
const API = "https://api.sorani.cc/sorani-cms/api";
const PAGE_SIZE = 24;

const asText = (value, fallback = "") => {
  if (value === undefined || value === null) return fallback;
  return String(value);
};

const firstValue = (obj, keys, fallback = "") => {
  for (const key of keys) {
    const value = obj && obj[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
};

const unwrap = (value) => {
  let current = value;
  // The Sorani API normally wraps payloads in `data`; tolerate one extra envelope.
  for (let i = 0; i < 2; i++) {
    if (current && !Array.isArray(current) && typeof current === "object" && current.data !== undefined) {
      current = current.data;
    } else {
      break;
    }
  }
  return current;
};

const normalizeImage = (value) => {
  const raw = asText(value).trim();
  if (!raw) return "";
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith("//")) return "https:" + raw;
  try { return new URL(raw, WEB + "/").href; } catch { return raw; }
};

const videoCard = (item) => {
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
};

export default class SoraniSpider {
  init(ext = "") {
    this.ext = {};
    if (ext && typeof ext === "object") {
      this.ext = ext;
    } else if (typeof ext === "string" && ext.trim()) {
      try { this.ext = JSON.parse(ext); } catch { this.ext = {}; }
    }
    this.cookie = asText(this.ext.cookie || this.ext.Cookie).trim();
    this.authorization = asText(this.ext.authorization || this.ext.Authorization).trim();
  }

  headers(extra = {}) {
    const headers = {
      "Accept": "application/json, text/plain, */*",
      "Referer": WEB + "/",
      "Origin": WEB,
      "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
      ...extra
    };
    if (this.cookie) headers.Cookie = this.cookie;
    if (this.authorization) headers.Authorization = this.authorization;
    return headers;
  }

  requestJson(url, options = {}) {
    const response = req(url, {
      method: options.method || "GET",
      headers: this.headers(options.headers || {}),
      body: options.body,
      timeout: options.timeout || 20000
    });
    const status = Number(response && response.code || 0);
    const body = response && response.content !== undefined ? response.content : "";
    if (status >= 400) {
      throw new Error(`Sorani API HTTP ${status}: ${asText(body).slice(0, 180)}`);
    }
    let parsed;
    try {
      parsed = typeof body === "string" ? JSON.parse(body) : body;
    } catch (error) {
      throw new Error("Sorani API 返回的不是有效 JSON");
    }
    if (parsed && typeof parsed === "object") {
      const code = firstValue(parsed, ["code", "statusCode"]);
      const success = parsed.success;
      if (success === false || (code !== "" && code !== 0 && code !== 200 && code !== "200")) {
        const message = firstValue(parsed, ["message", "msg", "error"], "请求被服务器拒绝");
        throw new Error("Sorani: " + asText(message));
      }
    }
    return parsed;
  }

  listPayload(payload) {
    const root = unwrap(payload);
    if (Array.isArray(root)) return { records: root, total: root.length };
    const records = firstValue(root, ["records", "list", "items", "videos"], []);
    return {
      records: Array.isArray(records) ? records : [],
      total: Number(firstValue(root, ["total", "totalElements", "count"], 0)) || 0
    };
  }

  listUrl(page, keyword = "", sortMode = "latest") {
    const query = new URLSearchParams({
      page: String(page),
      size: String(PAGE_SIZE),
      keyword: String(keyword || ""),
      enabled: "true",
      sortMode: sortMode,
      sortDesc: "false"
    });
    return `${API}/video?${query.toString()}`;
  }

  pagedList(payload, pg) {
    const page = Math.max(1, Number.parseInt(pg, 10) || 1);
    const { records, total } = this.listPayload(payload);
    const list = records.map(videoCard).filter(item => item.vod_id && item.vod_name);
    const pagecount = total > 0 ? Math.max(page, Math.ceil(total / PAGE_SIZE)) : (records.length >= PAGE_SIZE ? page + 1 : page);
    return { list, page, pagecount, limit: PAGE_SIZE, total };
  }

  // Homepage category catalogue. The public catalogue currently exposes a latest-list API;
  // other menu/ranking endpoints are intentionally not guessed here.
  home() {
    return {
      class: [
        { type_id: "latest", type_name: "全部 / 最新更新" }
      ]
    };
  }

  homeVod() {
    const payload = this.requestJson(this.listUrl(1, "", "latest"));
    return this.pagedList(payload, 1);
  }

  category(tid, pg = "1", filter = false, extend = {}) {
    const page = Math.max(1, Number.parseInt(pg, 10) || 1);
    const sortMode = "latest";
    const payload = this.requestJson(this.listUrl(page, "", sortMode));
    return this.pagedList(payload, page);
  }

  search(key, quick = false, pg = "1") {
    const page = Math.max(1, Number.parseInt(pg, 10) || 1);
    const payload = this.requestJson(this.listUrl(page, asText(key), "latest"));
    return this.pagedList(payload, page);
  }

  detail(ids = []) {
    const list = [];
    for (const rawId of (Array.isArray(ids) ? ids : [ids])) {
      const id = asText(rawId).trim();
      if (!id) continue;
      const payload = this.requestJson(`${API}/video/${encodeURIComponent(id)}`);
      const detail = unwrap(payload) || {};
      const base = videoCard(detail);
      const episodes = Array.isArray(detail.episodes) ? detail.episodes
        : (Array.isArray(payload && payload.episodes) ? payload.episodes : []);
      const episodeLines = [];
      for (const episode of episodes) {
        const episodeId = firstValue(episode, ["episodeId", "id", "episodeOrder", "order"]);
        if (episodeId === "") continue;
        const label = firstValue(episode, ["episodeLabel", "name", "title", "episodeName"], `第${episodeId}集`);
        episodeLines.push(`${asText(label).replace(/[#$]/g, " ")}$${encodeURIComponent(asText(episodeId))}`);
      }
      list.push({
        ...base,
        vod_id: id,
        vod_name: asText(firstValue(detail, ["title", "name", "videoName"], base.vod_name)),
        vod_pic: normalizeImage(firstValue(detail, ["cover", "coverUrl", "coverImage", "imageUrl", "image", "poster", "pic"], base.vod_pic)),
        vod_content: asText(firstValue(detail, ["description", "summary", "synopsis", "intro"], base.vod_content)),
        vod_play_from: "Sorani",
        vod_play_url: episodeLines.join("#")
      });
    }
    return { list };
  }

  play(flag, id) {
    const episodeId = decodeURIComponent(asText(id));
    if (!episodeId) throw new Error("Sorani: 缺少集数 ID");
    const payload = this.requestJson(`${API}/video/episode/${encodeURIComponent(episodeId)}/play`);
    const data = unwrap(payload) || {};
    const playUrl = firstValue(data, ["playUrl", "url", "videoUrl", "src"])
      || firstValue(payload, ["playUrl", "url", "videoUrl", "src"]);
    if (!playUrl || !/^https?:\/\//i.test(asText(playUrl))) {
      throw new Error("Sorani 未返回可直接播放的 HTTP 视频地址；可能需要有效登录态或该集暂不可用");
    }
    return {
      parse: 0,
      jx: 0,
      url: asText(playUrl),
      header: this.headers()
    };
  }
}
