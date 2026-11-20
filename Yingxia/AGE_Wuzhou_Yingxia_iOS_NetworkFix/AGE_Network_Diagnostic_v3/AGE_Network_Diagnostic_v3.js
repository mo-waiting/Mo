// Yingxia JS Spider network diagnostic v3 for AGE connectivity.
// Pure JS, QuickJS-compatible; uses only Yingxia's native http() API.

const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const HEADERS = {
  'User-Agent': UA,
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.7',
  'Cache-Control': 'no-cache'
};

// Notes:
// - www.agefans.tv is not the same host as agefans.com.
// - m.agedm.io is included as a separate hostname.
// - HTTP tests are diagnostic only; do not use them for normal browsing.
const TARGETS = [
  { name: 'Baseline Example HTTPS', url: 'https://example.com/', redirect: 1, group: 'baseline' },
  { name: 'Baseline Baidu HTTPS', url: 'https://www.baidu.com/', redirect: 1, group: 'baseline' },

  { name: 'AGE www HTTPS', url: 'https://www.agedm.io/update', redirect: 0, group: 'primary' },
  { name: 'AGE apex HTTPS', url: 'https://agedm.io/update', redirect: 0, group: 'primary' },
  { name: 'AGE mobile host HTTPS', url: 'https://m.agedm.io/update', redirect: 0, group: 'mobile' },
  { name: 'AGE mobile host HTTPS follow', url: 'https://m.agedm.io/update', redirect: 1, group: 'mobile' },

  { name: 'AGE www.age.tv no redirect', url: 'https://www.age.tv/update', redirect: 0, group: 'alias' },
  { name: 'AGE www.age.tv follow', url: 'https://www.age.tv/update', redirect: 1, group: 'alias' },
  { name: 'AGE www.agefans.tv no redirect', url: 'https://www.agefans.tv/update', redirect: 0, group: 'alias' },
  { name: 'AGE www.agefans.tv follow', url: 'https://www.agefans.tv/update', redirect: 1, group: 'alias' },

  { name: 'AGE www HTTP no redirect', url: 'http://www.agedm.io/update', redirect: 0, group: 'http' },
  { name: 'AGE www HTTP follow', url: 'http://www.agedm.io/update', redirect: 1, group: 'http' }
];

function safeText(v, max) {
  try { return String(v == null ? '' : v).replace(/[\r\n\t]+/g, ' ').slice(0, max || 700); }
  catch (_) { return '[unprintable]'; }
}
function byteLength(v) {
  if (v == null) return 0;
  if (typeof v === 'string') return v.length;
  if (Array.isArray(v) || typeof v.length === 'number') return v.length;
  return -1;
}
function getHeader(headers, wanted) {
  if (!headers || typeof headers !== 'object') return '';
  const keys = Object.keys(headers);
  for (let i = 0; i < keys.length; i++) {
    if (keys[i].toLowerCase() === wanted.toLowerCase()) return safeText(headers[keys[i]], 700);
  }
  return '';
}

const spider = {
  async init(ext) { this.ext = ext || {}; return true; },
  async home() {
    return JSON.stringify({ class: [{ type_id: 'network', type_name: 'AGE网络诊断 v3' }] });
  },
  async homeVod() { return JSON.stringify({ list: [] }); },
  async category(tid) {
    if (String(tid) !== 'network') return JSON.stringify({ list: [] });
    const list = [{
      vod_id: 'api', vod_name: 'Yingxia HTTP API', vod_pic: '',
      vod_remarks: 'http=' + (typeof http === 'function') + ' / req=' + (typeof req === 'function'),
      vod_content: '诊断使用 Yingxia 内置 http(url, options)，不使用 fetch、require 或 Node 模块。'
    }];
    if (typeof http !== 'function') {
      list.push({ vod_id: 'missing-http', vod_name: '缺少 http() 接口', vod_pic: '', vod_remarks: 'FAILED', vod_content: '当前宿主未注入 http()。' });
      return JSON.stringify({ list });
    }
    for (let i = 0; i < TARGETS.length; i++) {
      const t = TARGETS[i];
      const started = Date.now();
      try {
        const r = await http(t.url, {
          method: 'get', timeout: 15000, redirect: t.redirect,
          headers: HEADERS
        });
        const code = r && r.code != null && r.code !== '' ? safeText(r.code, 30) : 'empty';
        const content = r && r.content;
        const len = byteLength(content);
        const finalUrl = r && r.url ? r.url : t.url;
        const location = getHeader(r && r.headers, 'location');
        const server = getHeader(r && r.headers, 'server');
        const body = typeof content === 'string' ? content.replace(/\s+/g, ' ').slice(0, 260) : '[non-text body]';
        list.push({
          vod_id: 'test-' + i,
          vod_name: t.name,
          vod_pic: '',
          vod_remarks: 'code=' + code + ' | bytes=' + len + ' | ' + (Date.now() - started) + 'ms',
          vod_content: 'group=' + t.group + '\nrequested=' + t.url + '\nredirect=' + t.redirect +
            '\nfinal=' + safeText(finalUrl, 800) + '\nlocation=' + location +
            '\nserver=' + server + '\nbody=' + body
        });
      } catch (e) {
        list.push({
          vod_id: 'test-' + i,
          vod_name: t.name,
          vod_pic: '',
          vod_remarks: 'REQUEST ERROR | ' + (Date.now() - started) + 'ms',
          vod_content: 'group=' + t.group + '\nrequested=' + t.url + '\nredirect=' + t.redirect +
            '\nerror=' + safeText(e && (e.message || e), 1200)
        });
      }
    }
    return JSON.stringify({ list, page: 1, pagecount: 1, limit: list.length, total: list.length });
  }
};

export default spider;
