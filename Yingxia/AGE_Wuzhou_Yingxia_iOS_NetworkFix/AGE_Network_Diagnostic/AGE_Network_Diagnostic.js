// Yingxia JS Spider network diagnostic for iOS QuickJS
// This source performs requests through Yingxia's native http() adapter.
// It does not use Node.js modules, fetch(), require(), or WebAssembly.

const TARGETS = [
  { name: 'Example HTTPS', url: 'https://example.com/' },
  { name: 'Baidu HTTPS', url: 'https://www.baidu.com/' },
  { name: 'AGE www / update', url: 'https://www.agedm.io/update' },
  { name: 'AGE bare / update', url: 'https://agedm.io/update' },
  { name: 'AGE www / catalog', url: 'https://www.agedm.io/catalog/TV-2026-all-all-all-time-1-%E6%97%A5%E6%9C%AC-1-%E8%BF%9E%E8%BD%BD' }
];

function contentLength(value) {
  if (value == null) return 0;
  if (typeof value === 'string') return value.length;
  if (Array.isArray(value)) return value.length;
  if (typeof value.length === 'number') return value.length;
  return -1;
}

function safeText(value, max) {
  try { return String(value == null ? '' : value).slice(0, max || 500); }
  catch (_) { return '[unprintable]'; }
}

const spider = {
  async init(ext) {
    this.ext = ext || {};
    return true;
  },

  async home() {
    return JSON.stringify({
      class: [{ type_id: 'network', type_name: '网络连接测试' }]
    });
  },

  async homeVod() {
    return JSON.stringify({ list: [] });
  },

  async category(tid, pg) {
    if (String(tid) !== 'network') return JSON.stringify({ list: [] });
    const list = [];
    const hasHttp = typeof http === 'function';
    const hasReq = typeof req === 'function';

    list.push({
      vod_id: 'runtime',
      vod_name: 'Yingxia HTTP API',
      vod_pic: '',
      vod_remarks: 'http=' + hasHttp + ' / req=' + hasReq,
      vod_content: 'JS runtime network globals. This test uses http() only.'
    });

    if (!hasHttp) {
      list.push({
        vod_id: 'no-http', vod_name: '缺少 http() 接口', vod_pic: '',
        vod_remarks: 'http is not available',
        vod_content: '此宿主没有注入 http()；请确认 Yingxia 版本和 JS Spider 运行环境。'
      });
      return JSON.stringify({ list });
    }

    for (let i = 0; i < TARGETS.length; i++) {
      const target = TARGETS[i];
      const started = Date.now();
      try {
        const result = await http(target.url, {
          timeout: 12000,
          redirect: 1,
          headers: {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.7'
          }
        });
        const rawCode = result && result.code;
        const code = rawCode == null || rawCode === '' ? 'empty' : safeText(rawCode, 30);
        const finalUrl = result && result.url ? result.url : target.url;
        const len = contentLength(result && result.content);
        const headerNames = result && result.headers && typeof result.headers === 'object'
          ? Object.keys(result.headers).join(', ')
          : '(none)';
        const remarks = 'code=' + code + ' | bytes=' + len + ' | ' + (Date.now() - started) + 'ms';
        const bodyPreview = typeof (result && result.content) === 'string'
          ? result.content.replace(/\s+/g, ' ').slice(0, 350)
          : '(body is not text)';
        list.push({
          vod_id: 'target-' + i,
          vod_name: target.name,
          vod_pic: '',
          vod_remarks: remarks,
          vod_content: 'requested=' + target.url + '\nfinal=' + finalUrl + '\nheaders=' + headerNames + '\nbody=' + bodyPreview
        });
      } catch (error) {
        list.push({
          vod_id: 'target-' + i,
          vod_name: target.name,
          vod_pic: '',
          vod_remarks: 'REQUEST ERROR | ' + (Date.now() - started) + 'ms',
          vod_content: 'requested=' + target.url + '\nerror=' + safeText(error && (error.message || error), 1000)
        });
      }
    }

    return JSON.stringify({ list, page: 1, pagecount: 1, limit: list.length, total: list.length });
  }
};

export default spider;
