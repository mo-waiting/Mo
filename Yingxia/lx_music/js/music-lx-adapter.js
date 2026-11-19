/*
 * Yingxia Music Adapter for pdone/lx-music-source
 * Adapter protocol: the uploaded Yingxia music resolver module (default.init/play).
 *
 * IMPORTANT:
 * - Loads the repository's latest.js scripts on first use from raw GitHub (proxy fallback).
 * - Runs each script in a compatibility scope that provides globalThis.lx.
 * - This is not an offline bundle. The host must permit Function() and HTTP requests to GitHub/proxy.
 * - Only scripts with an actual musicUrl handler are activated. ChangQing, Fish and LX
 *   are listed in the accompanying README as not executable from their current latest.js.
 */

const SOURCE_BASE = "https://raw.githubusercontent.com/pdone/lx-music-source/main/";
const SOURCE_PROXIES = [
  "https://gh-proxy.org/raw.githubusercontent.com/pdone/lx-music-source/main/",
  "https://ghproxy.net/https://raw.githubusercontent.com/pdone/lx-music-source/main/"
];
const LOAD_TIMEOUT = 12000;
const PLAY_TIMEOUT = 18000;
const USER_AGENT = "Yingxia-LX-Music-Adapter/1.0";

const SOURCE_DEFS = {
  feichangdao: { file: "feichangdao/latest.js", name: "非常刀", platforms: ["netease", "qq", "kuwo", "kugou", "migu", "qishui"] },
  helloworld:  { file: "helloworld/latest.js",  name: "HelloWorld", platforms: ["qq", "netease", "kuwo", "kugou", "migu"] },
  huanyin:     { file: "huanyin/latest.js",     name: "幻音", platforms: ["qq", "netease", "kuwo", "migu"] },
  hyw:         { file: "hyw/latest.js",         name: "HYW", platforms: ["qq", "netease", "kuwo", "kugou", "migu", "qishui", "bilibili", "youtube", "ximalaya"] },
  jiexiang:    { file: "jiexiang/latest.js",    name: "杰翔聚合", platforms: ["qq", "netease", "kuwo", "kugou", "migu"] },
  qdy:         { file: "qdy/latest.js",         name: "全豆要聚合", platforms: ["qq", "netease", "kuwo", "kugou", "migu", "qishui"] },
  qingliang:   { file: "qingliang/latest.js",   name: "轻量", platforms: ["qq", "netease", "kuwo", "kugou"] },
  suyin:       { file: "suyin/latest.js",       name: "溯音", platforms: ["qq", "netease", "kuwo", "migu"] },
  xinghai:     { file: "xinghai/latest.js",     name: "星海", platforms: ["qq", "netease", "kuwo", "kugou", "migu", "qishui"] },
  xinglan:     { file: "xinglan/latest.js",     name: "星澜", platforms: ["qq", "netease", "kuwo", "kugou", "migu", "qishui"] }
};

const PLATFORM_TO_LX = {
  qq: "tx",
  netease: "wy",
  kuwo: "kw",
  kugou: "kg",
  migu: "mg",
  qishui: "qs",
  bilibili: "bili",
  youtube: "ytb",
  ximalaya: "xm"
};

class ChannelError extends Error {
  constructor(code, detail = "") {
    super(detail || code);
    this.code = code;
    this.detail = detail;
  }
}

function toBytes(value) {
  const s = String(value ?? "");
  if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(s);
  const encoded = unescape(encodeURIComponent(s));
  const out = new Uint8Array(encoded.length);
  for (let i = 0; i < encoded.length; i++) out[i] = encoded.charCodeAt(i);
  return out;
}

function bytesToUtf8(bytes) {
  if (typeof TextDecoder !== "undefined") return new TextDecoder("utf-8").decode(bytes);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += "%" + bytes[i].toString(16).padStart(2, "0");
  return decodeURIComponent(binary);
}

// Small synchronous MD5 implementation required by some repository sources (Fish/EAPI signatures).
function md5Hex(value) {
  const input = toBytes(value);
  const bitLen = input.length * 8;
  const paddedLen = Math.ceil((input.length + 9) / 64) * 64;
  const msg = new Uint8Array(paddedLen);
  msg.set(input);
  msg[input.length] = 0x80;
  for (let i = 0; i < 8; i++) msg[paddedLen - 8 + i] = Math.floor(bitLen / Math.pow(256, i)) & 255;
  let a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;
  const shifts = [7,12,17,22,7,12,17,22,7,12,17,22,7,12,17,22,5,9,14,20,5,9,14,20,5,9,14,20,5,9,14,20,4,11,16,23,4,11,16,23,4,11,16,23,4,11,16,23,6,10,15,21,6,10,15,21,6,10,15,21,6,10,15,21];
  const k = new Array(64);
  for (let i = 0; i < 64; i++) k[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296) >>> 0;
  const rotl = (x, n) => (x << n) | (x >>> (32 - n));
  for (let offset = 0; offset < paddedLen; offset += 64) {
    const m = new Uint32Array(16);
    for (let i = 0; i < 16; i++) {
      const p = offset + i * 4;
      m[i] = (msg[p] | (msg[p + 1] << 8) | (msg[p + 2] << 16) | (msg[p + 3] << 24)) >>> 0;
    }
    let a = a0, b = b0, c = c0, d = d0;
    for (let i = 0; i < 64; i++) {
      let f, g;
      if (i < 16) { f = (b & c) | (~b & d); g = i; }
      else if (i < 32) { f = (d & b) | (~d & c); g = (5 * i + 1) % 16; }
      else if (i < 48) { f = b ^ c ^ d; g = (3 * i + 5) % 16; }
      else { f = c ^ (b | ~d); g = (7 * i) % 16; }
      const sum = (a + f + k[i] + m[g]) >>> 0;
      const nextB = (b + rotl(sum, shifts[i])) >>> 0;
      a = d; d = c; c = b; b = nextB;
    }
    a0 = (a0 + a) >>> 0; b0 = (b0 + b) >>> 0; c0 = (c0 + c) >>> 0; d0 = (d0 + d) >>> 0;
  }
  const words = [a0, b0, c0, d0];
  return words.map(w => [w & 255, (w >>> 8) & 255, (w >>> 16) & 255, (w >>> 24) & 255].map(x => x.toString(16).padStart(2, "0")).join("")).join("");
}

// AES-128-ECB/PKCS7 implementation used only by the EAPI fallback routes in JieXiang/XingLan.
function aes128Ecb(data, keyText) {
  const keyIn = toBytes(keyText);
  if (keyIn.length !== 16) throw new Error("AES-128 key must be 16 bytes");
  const sbox = new Uint8Array(256);
  const gfMul = (a, b) => {
    let p = 0;
    for (let i = 0; i < 8; i++) {
      if (b & 1) p ^= a;
      const hi = a & 0x80;
      a = (a << 1) & 255;
      if (hi) a ^= 0x1b;
      b >>>= 1;
    }
    return p;
  };
  const gfPow = (a, n) => { let r = 1; while (n) { if (n & 1) r = gfMul(r, a); a = gfMul(a, a); n >>>= 1; } return r; };
  const rot8 = (x, n) => ((x << n) | (x >>> (8 - n))) & 255;
  for (let i = 0; i < 256; i++) {
    const inv = i === 0 ? 0 : gfPow(i, 254);
    sbox[i] = (inv ^ rot8(inv, 1) ^ rot8(inv, 2) ^ rot8(inv, 3) ^ rot8(inv, 4) ^ 0x63) & 255;
  }
  const expanded = new Uint8Array(176);
  expanded.set(keyIn);
  const rcon = [0,1,2,4,8,16,32,64,128,27,54];
  let generated = 16, r = 1;
  const temp = new Uint8Array(4);
  while (generated < 176) {
    for (let i = 0; i < 4; i++) temp[i] = expanded[generated - 4 + i];
    if (generated % 16 === 0) {
      const t = temp[0]; temp[0] = sbox[temp[1]] ^ rcon[r++]; temp[1] = sbox[temp[2]]; temp[2] = sbox[temp[3]]; temp[3] = sbox[t];
    }
    for (let i = 0; i < 4; i++) { expanded[generated] = expanded[generated - 16] ^ temp[i]; generated++; }
  }
  const bytes = toBytes(data);
  const pad = 16 - (bytes.length % 16);
  const padded = new Uint8Array(bytes.length + pad);
  padded.set(bytes);
  padded.fill(pad, bytes.length);
  const out = new Uint8Array(padded.length);
  const addKey = (state, round) => { const start = round * 16; for (let i = 0; i < 16; i++) state[i] ^= expanded[start + i]; };
  const subBytes = state => { for (let i = 0; i < 16; i++) state[i] = sbox[state[i]]; };
  const shiftRows = s => {
    let t;
    t=s[1];s[1]=s[5];s[5]=s[9];s[9]=s[13];s[13]=t;
    t=s[2];let u=s[6];s[2]=s[10];s[6]=s[14];s[10]=t;s[14]=u;
    t=s[3];u=s[7];let v=s[11];s[3]=s[15];s[7]=t;s[11]=u;s[15]=v;
  };
  const mixColumns = s => {
    for (let c = 0; c < 4; c++) {
      const i = c * 4, a=s[i], b=s[i+1], d=s[i+2], e=s[i+3], all=a^b^d^e;
      s[i] ^= all ^ gfMul(a ^ b, 2);
      s[i+1] ^= all ^ gfMul(b ^ d, 2);
      s[i+2] ^= all ^ gfMul(d ^ e, 2);
      s[i+3] ^= all ^ gfMul(e ^ a, 2);
    }
  };
  for (let block = 0; block < padded.length; block += 16) {
    const state = padded.slice(block, block + 16);
    addKey(state, 0);
    for (let round = 1; round < 10; round++) { subBytes(state); shiftRows(state); mixColumns(state); addKey(state, round); }
    subBytes(state); shiftRows(state); addKey(state, 10);
    out.set(state, block);
  }
  return out;
}

function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  if (typeof btoa === "function") return btoa(binary);
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let out = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i], b = i + 1 < bytes.length ? bytes[i + 1] : 0, c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    const n = (a << 16) | (b << 8) | c;
    out += chars[(n >> 18) & 63] + chars[(n >> 12) & 63] + (i + 1 < bytes.length ? chars[(n >> 6) & 63] : "=") + (i + 2 < bytes.length ? chars[n & 63] : "=");
  }
  return out;
}

function decodeBase64(text) {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const clean = String(text).replace(/[^A-Za-z0-9+/]/g, "");
  let bits = 0, count = 0, out = "";
  for (const ch of clean) {
    bits = (bits << 6) | chars.indexOf(ch); count += 6;
    if (count >= 8) { count -= 8; out += String.fromCharCode((bits >> count) & 255); }
  }
  return out;
}

const bufferUtils = {
  from(value, encoding = "utf-8") {
    if (value instanceof BufferShim) return value;
    if (typeof value === "number") return new BufferShim(value);
    if (value instanceof ArrayBuffer) return new BufferShim(new Uint8Array(value));
    if (value instanceof Uint8Array) return new BufferShim(value);
    if (encoding === "base64") {
      const binary = typeof atob === "function" ? atob(String(value)) : decodeBase64(String(value));
      return new BufferShim(Uint8Array.from(binary, c => c.charCodeAt(0)));
    }
    if (encoding === "hex") {
      const s = String(value).replace(/[^0-9a-f]/gi, "");
      const out = new Uint8Array(Math.floor(s.length / 2));
      for (let i = 0; i < out.length; i++) out[i] = parseInt(s.slice(i * 2, i * 2 + 2), 16);
      return new BufferShim(out);
    }
    return new BufferShim(toBytes(value));
  },
  bufToString(value, encoding = "utf-8") {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value || []);
    if (encoding === "hex") return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    if (encoding === "base64") return bytesToBase64(bytes);
    return bytesToUtf8(bytes);
  }
};

const cryptoUtils = {
  md5: md5Hex,
  aesEncrypt(data, mode, key, iv) {
    const normalized = String(mode || "").toLowerCase();
    if (normalized !== "ecb" && normalized !== "aes-128-ecb") throw new Error("当前适配器只实现 AES-128-ECB");
    return new BufferShim(aes128Ecb(data, key));
  }
};

const BufferShim = class BufferShim extends Uint8Array {
  static from(value, encoding = "utf-8") { return bufferUtils.from(value, encoding); }
  static isBuffer(value) { return value instanceof BufferShim; }
  static alloc(size, fill = 0) { const b = new BufferShim(size); b.fill(fill); return b; }
  static concat(list, totalLength) {
    const arrays = list.map(item => item instanceof Uint8Array ? item : bufferUtils.from(item));
    const length = totalLength == null ? arrays.reduce((n, item) => n + item.length, 0) : totalLength;
    const out = new BufferShim(length); let offset = 0;
    for (const item of arrays) { const count = Math.min(item.length, length - offset); if (count <= 0) break; out.set(item.subarray(0, count), offset); offset += count; }
    return out;
  }
  toString(encoding = "utf-8") { return bufferUtils.bufToString(this, encoding); }
};

function normaliseBody(options) {
  const out = { ...(options || {}) };
  const body = out.body;
  if (body != null && typeof body === "object" && !(body instanceof Uint8Array) && !(body instanceof ArrayBuffer)) {
    const headers = { ...(out.headers || {}) };
    const contentType = String(headers["Content-Type"] || headers["content-type"] || "").toLowerCase();
    if (contentType.includes("application/x-www-form-urlencoded")) {
      out.body = Object.keys(body).map(k => encodeURIComponent(k) + "=" + encodeURIComponent(body[k])).join("&");
    } else {
      out.body = JSON.stringify(body);
      if (!contentType) headers["Content-Type"] = "application/json";
    }
    out.headers = headers;
  }
  return out;
}

function invokeHostRequest(url, options = {}) {
  if (typeof globalThis.req !== "function") throw new ChannelError("hostUnavailable", "映匣没有提供 globalThis.req");
  return globalThis.req(url, normaliseBody(options));
}

async function fetchSourceText(sourceId) {
  const def = SOURCE_DEFS[sourceId];
  if (!def) throw new ChannelError("unknownChannel", sourceId);
  const urls = [SOURCE_BASE + def.file, ...SOURCE_PROXIES.map(base => base + def.file)];
  let lastError = null;
  for (const url of urls) {
    try {
      const raw = await Promise.resolve(invokeHostRequest(url, {
        method: "GET",
        timeout: LOAD_TIMEOUT,
        headers: { "User-Agent": USER_AGENT, Accept: "text/javascript, application/javascript, */*" }
      }));
      const code = Number(raw?.code ?? raw?.statusCode ?? 0);
      const content = raw?.content ?? raw?.body ?? "";
      if (code >= 200 && code < 300 && typeof content === "string" && content.trim().length > 100) {
        if (!content.includes("EVENT_NAMES") || !content.includes("musicUrl")) {
          throw new ChannelError("sourceNotExecutable", `${sourceId} 没有可识别的 musicUrl 处理逻辑`);
        }
        return content.replace(/^\uFEFF/, "");
      }
      lastError = new Error(`HTTP ${code || "无响应"}`);
    } catch (error) { lastError = error; }
  }
  throw new ChannelError("sourceDownloadFailed", `${sourceId}: ${lastError?.message || "下载失败"}`);
}

function makeLXRequest() {
  return function lxRequest(url, options = {}, callback) {
    let called = false;
    const done = (err, response) => {
      if (called) return;
      called = true;
      if (typeof callback === "function") callback(err || null, response || {}, response?.body);
    };
    let result;
    try { result = invokeHostRequest(url, options); }
    catch (error) {
      done(error);
      return callback ? { abort() {} } : Promise.reject(error);
    }
    const convert = raw => {
      const statusCode = Number(raw?.code ?? raw?.statusCode ?? 0);
      if (!statusCode) throw new Error("网络请求失败或超时");
      return {
        statusCode,
        headers: raw?.headers || {},
        body: raw?.content ?? raw?.body ?? "",
        url: raw?.url || url
      };
    };
    const promise = Promise.resolve(result).then(raw => {
      const response = convert(raw);
      done(null, response);
      return response;
    }).catch(error => {
      done(error);
      throw error;
    });
    // LX scripts commonly call the callback form and may invoke abort() during their own timeout cleanup.
    return callback ? { abort() { /* globalThis.req is host-controlled; no abort handle is exposed */ } } : promise;
  };
}

async function compileLXSource(sourceId, sourceText) {
  const requestHandlers = [];
  let sourceMetadata = {};
  const EVENT_NAMES = {
    request: "request",
    inited: "inited",
    updateAlert: "updateAlert",
    showConfigView: "showConfigView",
    log: "log",
    progress: "progress",
    error: "error"
  };
  const lx = {
    EVENT_NAMES,
    request: makeLXRequest(),
    on(event, handler) {
      if (event === EVENT_NAMES.request && typeof handler === "function") requestHandlers.push(handler);
    },
    send(event, payload) {
      if (event === EVENT_NAMES.inited && payload && payload.sources && typeof payload.sources === "object") {
        sourceMetadata = payload.sources;
      }
    },
    utils: { crypto: cryptoUtils, buffer: bufferUtils },
    env: "yingxia",
    version: "1.0.0",
    currentScriptInfo: { rawScript: sourceText, name: sourceId }
  };
  const sandbox = Object.create(globalThis);
  sandbox.lx = lx;
  sandbox.req = globalThis.req;
  try {
    if (typeof Function !== "function") throw new ChannelError("runtimeUnsupported", "当前运行环境禁用了 Function()，无法运行洛雪音源脚本");
    const execute = new Function("globalThis", "Buffer", `${sourceText}\n;return true;`);
    execute(sandbox, BufferShim);
    await Promise.resolve();
  } catch (error) {
    if (error instanceof ChannelError) throw error;
    throw new ChannelError("sourceInitFailed", `${sourceId}: ${error?.message || String(error)}`);
  }
  if (!requestHandlers.length) throw new ChannelError("sourceNotExecutable", `${sourceId} 没有注册 request 处理器`);
  return { sourceId, handler: requestHandlers[requestHandlers.length - 1], sources: sourceMetadata };
}

const loadedSources = new Map();
async function getLoadedSource(sourceId) {
  if (loadedSources.has(sourceId)) return loadedSources.get(sourceId);
  const task = (async () => {
    const code = await fetchSourceText(sourceId);
    return compileLXSource(sourceId, code);
  })();
  loadedSources.set(sourceId, task);
  try { return await task; }
  catch (error) { loadedSources.delete(sourceId); throw error; }
}

function lxPlatformFor(sourceId, platform) {
  if (sourceId === "qdy" && platform === "qishui") return "qsvip";
  return PLATFORM_TO_LX[platform] || "";
}

function chooseQuality(qualitys, requested) {
  const available = Array.isArray(qualitys) ? qualitys : [];
  const groups = {
    lossless: ["master", "atmos_plus", "atmos", "hires", "flac24bit", "24bit", "flac", "lossless"],
    high: ["320k", "exhigh", "high", "192k", "hq"],
    standard: ["128k", "standard", "lq"]
  };
  const wanted = groups[requested] || groups.lossless;
  for (const q of wanted) if (available.includes(q)) return q;
  if (requested === "lossless") {
    for (const q of groups.high) if (available.includes(q)) return q;
    for (const q of groups.standard) if (available.includes(q)) return q;
  } else if (requested === "high") {
    for (const q of groups.standard) if (available.includes(q)) return q;
  }
  return available[0] || (requested === "standard" ? "128k" : requested === "high" ? "320k" : "flac");
}

function makeMusicInfo(ask, id, lxSource) {
  const input = ask.musicInfo && typeof ask.musicInfo === "object" ? ask.musicInfo : {};
  const musicInfo = { ...input };
  const songId = String(id);
  musicInfo.id = musicInfo.id || songId;
  musicInfo.songmid = musicInfo.songmid || songId;
  musicInfo.mid = musicInfo.mid || songId;
  musicInfo.hash = musicInfo.hash || songId;
  musicInfo.rid = musicInfo.rid || songId;
  musicInfo.songId = musicInfo.songId || songId;
  musicInfo.source = lxSource;
  musicInfo.name = musicInfo.name || musicInfo.songname || musicInfo.songName || musicInfo.title || (ask.name ? String(ask.name) : "");
  musicInfo.singer = musicInfo.singer || musicInfo.singers || musicInfo.artist || (ask.singer || ask.artist ? String(ask.singer || ask.artist) : "");
  musicInfo.artist = musicInfo.artist || musicInfo.singer;
  musicInfo.albumName = musicInfo.albumName || musicInfo.album || "";
  const oldMeta = musicInfo.meta && typeof musicInfo.meta === "object" ? musicInfo.meta : {};
  musicInfo.meta = { ...oldMeta, [lxSource]: { ...(oldMeta[lxSource] || {}), id: songId, songmid: songId, mid: songId, hash: songId, rid: songId, songId } };
  return musicInfo;
}

function extractURL(value, depth = 0) {
  if (depth > 4 || value == null) return "";
  if (typeof value === "string") return /^https?:\/\/[^\s]+/i.test(value) ? value : "";
  if (Array.isArray(value)) {
    for (const item of value) { const u = extractURL(item, depth + 1); if (u) return u; }
    return "";
  }
  if (typeof value === "object") {
    for (const key of ["url", "playUrl", "play_url", "musicUrl", "src", "data", "result"]) {
      if (key in value) { const u = extractURL(value[key], depth + 1); if (u) return u; }
    }
  }
  return "";
}

function classifyError(error) {
  if (error instanceof ChannelError) return error;
  const text = String(error?.message || error || "解析失败");
  if (/timeout|timed out|超时/i.test(text)) return new ChannelError("timeout", text.slice(0, 180));
  if (/401|403|token|密钥|卡密|认证|授权/i.test(text)) return new ChannelError("authRequired", text.slice(0, 180));
  if (/429|频繁|限流|rate.?limit/i.test(text)) return new ChannelError("rateLimited", text.slice(0, 180));
  if (/source.*download|下载.*脚本|GitHub|HTTP 5\d\d/i.test(text)) return new ChannelError("sourceDownloadFailed", text.slice(0, 180));
  return new ChannelError("noResource", text.slice(0, 180));
}

async function withDeadline(promise, deadline, label) {
  const remaining = Math.max(250, Number(deadline || (Date.now() + PLAY_TIMEOUT)) - Date.now());
  let timer;
  try {
    return await Promise.race([
      Promise.resolve(promise),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new ChannelError("timeout", `${label} 超时`)), remaining); })
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function resolveLX(sourceId, ask) {
  const def = SOURCE_DEFS[sourceId];
  if (!def) throw new ChannelError("unknownChannel", sourceId);
  const platform = String(ask.platform || "");
  if (!def.platforms.includes(platform)) throw new ChannelError("unsupportedPlatform", `${def.name} 不支持 ${platform}`);
  const lxSource = lxPlatformFor(sourceId, platform);
  if (!lxSource) throw new ChannelError("unsupportedPlatform", platform);
  const loaded = await getLoadedSource(sourceId);
  const sourceSpec = loaded.sources?.[lxSource];
  if (sourceSpec && Array.isArray(sourceSpec.actions) && !sourceSpec.actions.includes("musicUrl")) {
    throw new ChannelError("unsupportedPlatform", `${def.name}/${lxSource} 未声明 musicUrl`);
  }
  if (!sourceSpec && !(sourceId === "qdy" && lxSource === "qsvip")) {
    // Some scripts send their init metadata asynchronously or omit a source record. The repository's
    // source-level platform list is used only as a fallback; the handler still validates the request.
  }
  const quality = ["standard", "high", "lossless"].includes(ask.quality) ? ask.quality : "lossless";
  const lxQuality = chooseQuality(sourceSpec?.qualitys, quality);
  const id = String(ask.id || "");
  if (!id) throw new ChannelError("noResource", "缺少歌曲 ID");
  const musicInfo = makeMusicInfo(ask, id, lxSource);
  const result = await withDeadline(loaded.handler({
    action: "musicUrl",
    source: lxSource,
    info: { musicInfo, type: lxQuality }
  }), ask.deadline, def.name);
  const url = extractURL(result);
  if (!url) throw new ChannelError("noResource", `${def.name} 未返回可播放 URL`);
  const claimed = (result && typeof result === "object" && (result.quality || result.claimed || result.type)) || lxQuality;
  return { url, claimed: String(claimed), upstream: `lx:${sourceId}` };
}

const channels = {};
for (const [id, def] of Object.entries(SOURCE_DEFS)) {
  channels[id] = {
    platforms: def.platforms.slice(),
    resolve: ask => resolveLX(id, ask)
  };
}

async function play(flag, id) {
  try {
    const asked = JSON.parse(String(flag || "{}"));
    const channelId = String(asked.channel || "");
    const channel = channels[channelId];
    if (!channel) throw new ChannelError("noResource", `未知播放渠道: ${channelId}`);
    const platform = String(asked.platform || "");
    if (!channel.platforms.includes(platform)) throw new ChannelError("unsupportedPlatform", `${channelId} 不支持 ${platform}`);
    const deadline = Date.now() + PLAY_TIMEOUT;
    const result = await channel.resolve({
      platform,
      id: String(id || ""),
      quality: asked.quality || "lossless",
      name: asked.name,
      singer: asked.singer,
      artist: asked.artist,
      musicInfo: asked.musicInfo,
      key: asked.key,
      deadline
    });
    return result;
  } catch (error) {
    const e = classifyError(error);
    return e.detail ? { error: e.code, detail: e.detail } : { error: e.code };
  }
}

const resolve_default = {
  init: (_ext) => {},
  play
};

export { ChannelError, channels, play, md5Hex, aes128Ecb };
export default resolve_default;
