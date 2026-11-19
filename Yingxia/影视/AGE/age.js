// Go/WASM compatibility prelude for Yingxia's JavaScript Spider VM.
// The WASM runtime runs in this Spider's own JS process; no subprocess is created.
globalThis.global = globalThis;
globalThis.window = globalThis;
globalThis.self = globalThis;
globalThis.performance = globalThis.performance || { now: () => Date.now() };
globalThis.Domain = 'jx.wuzhoupai.com';
globalThis.location = globalThis.location || {
  hostname: 'jx.wuzhoupai.com',
  host: 'jx.wuzhoupai.com:8443',
  href: 'https://jx.wuzhoupai.com:8443/vip/'
};
globalThis.navigator = globalThis.navigator || { userAgent: 'Mozilla/5.0' };
(()=>{if(typeof global!=="undefined"){}else if(typeof window!=="undefined"){window.global=window}else if(typeof self!=="undefined"){self.global=self}else{throw new Error("cannot export Go (neither global, window nor self is defined)");}if(!global.require&&typeof require!=="undefined"){global.require=require}if(!global.fs&&global.require){global.fs=require("fs")}const enosys=()=>{const err=new Error("not implemented");err.code="ENOSYS";return err};if(!global.fs){let outputBuf="";global.fs={constants:{O_WRONLY:-1,O_RDWR:-1,O_CREAT:-1,O_TRUNC:-1,O_APPEND:-1,O_EXCL:-1},writeSync(fd,buf){outputBuf+=decoder.decode(buf);const nl=outputBuf.lastIndexOf("\n");if(nl!=-1){console.log(outputBuf.substr(0,nl));outputBuf=outputBuf.substr(nl+1)}return buf.length},write(fd,buf,offset,length,position,callback){if(offset!==0||length!==buf.length||position!==null){callback(enosys());return}const n=this.writeSync(fd,buf);callback(null,n)},chmod(path,mode,callback){callback(enosys())},chown(path,uid,gid,callback){callback(enosys())},close(fd,callback){callback(enosys())},fchmod(fd,mode,callback){callback(enosys())},fchown(fd,uid,gid,callback){callback(enosys())},fstat(fd,callback){callback(enosys())},fsync(fd,callback){callback(null)},ftruncate(fd,length,callback){callback(enosys())},lchown(path,uid,gid,callback){callback(enosys())},link(path,link,callback){callback(enosys())},lstat(path,callback){callback(enosys())},mkdir(path,perm,callback){callback(enosys())},open(path,flags,mode,callback){callback(enosys())},read(fd,buffer,offset,length,position,callback){callback(enosys())},readdir(path,callback){callback(enosys())},readlink(path,callback){callback(enosys())},rename(from,to,callback){callback(enosys())},rmdir(path,callback){callback(enosys())},stat(path,callback){callback(enosys())},symlink(path,link,callback){callback(enosys())},truncate(path,length,callback){callback(enosys())},unlink(path,callback){callback(enosys())},utimes(path,atime,mtime,callback){callback(enosys())}}}if(!global.process){global.process={getuid(){return-1},getgid(){return-1},geteuid(){return-1},getegid(){return-1},getgroups(){throw enosys();},pid:-1,ppid:-1,umask(){throw enosys();},cwd(){throw enosys();},chdir(){throw enosys();}}}if(!global.crypto){const nodeCrypto=require("crypto");global.crypto={getRandomValues(b){nodeCrypto.randomFillSync(b)}}}if(!global.performance){global.performance={now(){const[sec,nsec]=process.hrtime();return sec*1000+nsec/1000000}}}if(!global.TextEncoder){global.TextEncoder=require("util").TextEncoder}if(!global.TextDecoder){global.TextDecoder=require("util").TextDecoder}const encoder=new TextEncoder("utf-8");const decoder=new TextDecoder("utf-8");var logLine=[];global.Go=class{constructor(){this._callbackTimeouts=new Map();this._nextCallbackTimeoutID=1;const mem=()=>{return new DataView(this._inst.exports.memory.buffer)};const setInt64=(addr,v)=>{mem().setUint32(addr+0,v,true);mem().setUint32(addr+4,Math.floor(v/4294967296),true)};const getInt64=(addr)=>{const low=mem().getUint32(addr+0,true);const high=mem().getInt32(addr+4,true);return low+high*4294967296};const loadValue=(addr)=>{const f=mem().getFloat64(addr,true);if(f===0){return undefined}if(!isNaN(f)){return f}const id=mem().getUint32(addr,true);return this._values[id]};const storeValue=(addr,v)=>{const nanHead=0x7ff80000;if(typeof v==="number"){if(isNaN(v)){mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,0,true);return}if(v===0){mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,1,true);return}mem().setFloat64(addr,v,true);return}switch(v){case undefined:mem().setFloat64(addr,0,true);return;case null:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,2,true);return;case true:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,3,true);return;case false:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,4,true);return}let id=this._ids.get(v);if(id===undefined){id=this._idPool.pop();if(id===undefined){id=this._values.length}this._values[id]=v;this._goRefCounts[id]=0;this._ids.set(v,id)}this._goRefCounts[id]++;let typeFlag=1;switch(typeof v){case"string":typeFlag=2;break;case"symbol":typeFlag=3;break;case"function":typeFlag=4;break}mem().setUint32(addr+4,nanHead|typeFlag,true);mem().setUint32(addr,id,true)};const loadSlice=(array,len,cap)=>{return new Uint8Array(this._inst.exports.memory.buffer,array,len)};const loadSliceOfValues=(array,len,cap)=>{const a=new Array(len);for(let i=0;i<len;i++){a[i]=loadValue(array+i*8)}return a};const loadString=(ptr,len)=>{return decoder.decode(new DataView(this._inst.exports.memory.buffer,ptr,len))};const timeOrigin=Date.now()-performance.now();this.importObject={wasi_snapshot_preview1:{fd_write:function(fd,iovs_ptr,iovs_len,nwritten_ptr){let nwritten=0;if(fd==1){for(let iovs_i=0;iovs_i<iovs_len;iovs_i++){let iov_ptr=iovs_ptr+iovs_i*8;let ptr=mem().getUint32(iov_ptr+0,true);let len=mem().getUint32(iov_ptr+4,true);for(let i=0;i<len;i++){let c=mem().getUint8(ptr+i);if(c==13){}else if(c==10){let line=decoder.decode(new Uint8Array(logLine));logLine=[];console.log(line)}else{logLine.push(c)}}}}else{console.error("invalid file descriptor:",fd)}mem().setUint32(nwritten_ptr,nwritten,true);return 0},proc_exit:(code)=>{if(global.process){process.exit(code)}else{throw"trying to exit with code "+code;}}},env:{"runtime.ticks":()=>{return timeOrigin+performance.now()},"runtime.sleepTicks":(timeout)=>{setTimeout(this._inst.exports.go_scheduler,timeout)},"syscall/js.finalizeRef":(sp)=>{console.error("syscall/js.finalizeRef not implemented")},"syscall/js.stringVal":(ret_ptr,value_ptr,value_len)=>{const s=loadString(value_ptr,value_len);storeValue(ret_ptr,s)},"syscall/js.valueGet":(retval,v_addr,p_ptr,p_len)=>{let prop=loadString(p_ptr,p_len);let value=loadValue(v_addr);let result=Reflect.get(value,prop);storeValue(retval,result)},"syscall/js.valueSet":(v_addr,p_ptr,p_len,x_addr)=>{const v=loadValue(v_addr);const p=loadString(p_ptr,p_len);const x=loadValue(x_addr);Reflect.set(v,p,x)},"syscall/js.valueDelete":(v_addr,p_ptr,p_len)=>{const v=loadValue(v_addr);const p=loadString(p_ptr,p_len);Reflect.deleteProperty(v,p)},"syscall/js.valueIndex":(ret_addr,v_addr,i)=>{storeValue(ret_addr,Reflect.get(loadValue(v_addr),i))},"syscall/js.valueSetIndex":(v_addr,i,x_addr)=>{Reflect.set(loadValue(v_addr),i,loadValue(x_addr))},"syscall/js.valueCall":(ret_addr,v_addr,m_ptr,m_len,args_ptr,args_len,args_cap)=>{const v=loadValue(v_addr);const name=loadString(m_ptr,m_len);const args=loadSliceOfValues(args_ptr,args_len,args_cap);try{const m=Reflect.get(v,name);storeValue(ret_addr,Reflect.apply(m,v,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueInvoke":(ret_addr,v_addr,args_ptr,args_len,args_cap)=>{try{const v=loadValue(v_addr);const args=loadSliceOfValues(args_ptr,args_len,args_cap);storeValue(ret_addr,Reflect.apply(v,undefined,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueNew":(ret_addr,v_addr,args_ptr,args_len,args_cap)=>{const v=loadValue(v_addr);const args=loadSliceOfValues(args_ptr,args_len,args_cap);try{storeValue(ret_addr,Reflect.construct(v,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueLength":(v_addr)=>{return loadValue(v_addr).length},"syscall/js.valuePrepareString":(ret_addr,v_addr)=>{const s=String(loadValue(v_addr));const str=encoder.encode(s);storeValue(ret_addr,str);setInt64(ret_addr+8,str.length)},"syscall/js.valueLoadString":(v_addr,slice_ptr,slice_len,slice_cap)=>{const str=loadValue(v_addr);loadSlice(slice_ptr,slice_len,slice_cap).set(str)},"syscall/js.valueInstanceOf":(v_addr,t_addr)=>{return loadValue(v_addr)instanceof loadValue(t_addr)},"syscall/js.copyBytesToGo":(ret_addr,dest_addr,dest_len,dest_cap,source_addr)=>{let num_bytes_copied_addr=ret_addr;let returned_status_addr=ret_addr+4;const dst=loadSlice(dest_addr,dest_len);const src=loadValue(source_addr);if(!(src instanceof Uint8Array)){mem().setUint8(returned_status_addr,0);return}const toCopy=src.subarray(0,dst.length);dst.set(toCopy);setInt64(num_bytes_copied_addr,toCopy.length);mem().setUint8(returned_status_addr,1)},"syscall/js.copyBytesToJS":(ret_addr,dest_addr,source_addr,source_len,source_cap)=>{let num_bytes_copied_addr=ret_addr;let returned_status_addr=ret_addr+4;const dst=loadValue(dest_addr);const src=loadSlice(source_addr,source_len);if(!(dst instanceof Uint8Array)){mem().setUint8(returned_status_addr,0);return}const toCopy=src.subarray(0,dst.length);dst.set(toCopy);setInt64(num_bytes_copied_addr,toCopy.length);mem().setUint8(returned_status_addr,1)}}}}async run(instance){this._inst=instance;this._values=[NaN,0,null,true,false,global,this];this._goRefCounts=[];this._ids=new Map();this._idPool=[];this.exited=false;const mem=new DataView(this._inst.exports.memory.buffer);while(true){const callbackPromise=new Promise((resolve)=>{this._resolveCallbackPromise=()=>{if(this.exited){throw new Error("bad callback: Go program has already exited");}setTimeout(resolve,0)}});this._inst.exports._start();if(this.exited){break}await callbackPromise}}_resume(){if(this.exited){throw new Error("Go program has already exited");}this._inst.exports.resume();if(this.exited){this._resolveExitPromise()}}_makeFuncWrapper(id){const go=this;return function(){const event={id:id,this:this,args:arguments};go._pendingEvent=event;go._resume();return event.result}}};if(global.require&&global.require.main===module&&global.process&&global.process.versions&&!global.process.versions.electron){if(process.argv.length!=3){console.error("usage: go_js_wasm_exec [wasm binary] [arguments]");process.exit(1)}const go=new Go();WebAssembly.instantiate(fs.readFileSync(process.argv[2]),go.importObject).then((result)=>{return go.run(result.instance)}).catch((err)=>{console.error(err);process.exit(1)})}})();

const SITE = 'https://www.agedm.io/';
const DEFAULT_API = 'https://jx.wuzhoupai.com:8443/vip';
const DEFAULT_HOST = 'jx.wuzhoupai.com';
const DEFAULT_VERSION = 'V3.2';
const DEFAULT_DOMAIN = 'jx.wuzhoupai.com';
const WASM_URL = 'https://cdn.xmfxgjzx.com/jx/20230723ver/Play/jx.wuzhoupai.com.wasm?v=20260512';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

let wasmReady = false;
let wasmPromise = null;
let lastError = '';
const cookies = new Map();

function log(...args) {
  try { console.log('[AGE]', ...args); } catch (_) {}
}
function fail(message) {
  lastError = String(message || 'Unknown AGE resolver error');
  try { console.error('[AGE_PLAY_ERROR]', lastError); } catch (_) {}
  return JSON.stringify({
    parse: 1, jx: 0, url: '',
    error: lastError,
    header: { 'User-Agent': UA }
  });
}
function absolute(url, base = SITE) {
  try { return new URL(String(url || '').trim(), base).href; }
  catch (_) { return String(url || '').trim(); }
}
function cookieHeader() {
  return Array.from(cookies.entries()).map(([k, v]) => k + '=' + v).join('; ');
}
function absorbCookies(headers) {
  if (!headers) return;
  let values = headers['set-cookie'] || headers['Set-Cookie'];
  if (!values) return;
  if (!Array.isArray(values)) values = [values];
  for (const item of values) {
    const pair = String(item).split(';', 1)[0];
    const at = pair.indexOf('=');
    if (at > 0) cookies.set(pair.slice(0, at).trim(), pair.slice(at + 1).trim());
  }
}
function request(url, options = {}) {
  const headers = Object.assign({ 'User-Agent': UA }, options.headers || {});
  const cookie = cookieHeader();
  if (cookie && !Object.keys(headers).some(k => k.toLowerCase() === 'cookie')) headers.Cookie = cookie;
  const result = req(url, Object.assign({ timeout: 20000 }, options, { headers }));
  if (!result || typeof result !== 'object') throw new Error('Yingxia req() 返回值格式异常');
  absorbCookies(result.headers);
  const code = Number(result.code || 0);
  if (code < 200 || code >= 300) {
    throw new Error('HTTP ' + (code || 'network error') + ' ' + url + (result.content ? ': ' + String(result.content).slice(0, 160) : ''));
  }
  return result;
}
function textOf(fragment, selector) {
  try { return pdfh(String(fragment || ''), selector + '&&Text').trim(); }
  catch (_) { return ''; }
}
function attrOf(fragment, selector, attr) {
  try { return pdfh(String(fragment || ''), selector + '&&' + attr).trim(); }
  catch (_) { return ''; }
}
function manyOf(fragment, selector) {
  try { return pdfa(String(fragment || ''), selector) || []; }
  catch (_) { return []; }
}
function cardFromHtml(fragment, base) {
  const href = attrOf(fragment, 'a[href]', 'href') || attrOf(fragment, 'a', 'href');
  const title = attrOf(fragment, 'img', 'alt') || textOf(fragment, 'a') || textOf(fragment, 'h3') || textOf(fragment, 'h4');
  const pic = attrOf(fragment, 'img', 'data-original') || attrOf(fragment, 'img', 'data-src') || attrOf(fragment, 'img', 'src');
  const note = textOf(fragment, 'span') || textOf(fragment, '.video_item--info');
  if (!href || !title) return null;
  return {
    vod_id: absolute(href, base),
    vod_name: title,
    vod_pic: pic ? absolute(pic, base) : '',
    vod_remarks: note
  };
}
function cardsFromHtml(html, selector, base) {
  const out = [], seen = new Set();
  for (const fragment of manyOf(html, selector)) {
    const item = cardFromHtml(fragment, base);
    if (item && !seen.has(item.vod_id)) { seen.add(item.vod_id); out.push(item); }
  }
  return out;
}
function escapeRegExp(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function readAssigned(html, name) {
  const n = escapeRegExp(name);
  const reString = new RegExp('(?:\\b(?:var|let|const)\\s+)?(?:window\\s*\\.\\s*)?' + n + '\\s*=\\s*([\\\'\"])([\\s\\S]*?)\\1');
  const m = String(html || '').match(reString);
  if (m) return m[2].replace(/\\x([0-9a-f]{2})/gi, (_, h) => String.fromCharCode(parseInt(h, 16))).replace(/\\u([0-9a-f]{4})/gi, (_, h) => String.fromCharCode(parseInt(h, 16)));
  if (name === 'Time') {
    const numeric = String(html || '').match(/(?:\\b(?:var|let|const)\\s+)?(?:window\\s*\\.\\s*)?Time\\s*=\\s*(\\d{10,13})\\b/);
    if (numeric) return numeric[1];
  }
  return '';
}
function readFlag(html, name, fallback) {
  const m = String(html || '').match(new RegExp('(?:\\b(?:var|let|const)\\s+)?(?:window\\s*\\.\\s*)?' + escapeRegExp(name) + '\\s*=\\s*(true|false|!0|!1|[01])\\b', 'i'));
  if (!m) return fallback;
  return /^(?:true|!0|1)$/i.test(m[1]) ? '1' : '0';
}
function readMetaId(html, selector, attrName) {
  const viaCheerio = attrOf(html, selector, attrName || 'id');
  if (viaCheerio) return viaCheerio;
  const tagPattern = selector.includes('Content-Type')
    ? /<meta\b(?=[^>]*\bhttp-equiv\s*=\s*['"]?Content-Type['"]?)[^>]*>/i
    : /<meta\b(?=[^>]*\bname\s*=\s*['"]?viewport['"]?)[^>]*>/i;
  const tag = String(html || '').match(tagPattern);
  if (!tag) return '';
  const id = tag[0].match(/\bid\s*=\s*(['"])(.*?)\1/i);
  return id ? id[2] : '';
}
function uuidV4() {
  const b = new Uint8Array(16);
  if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === 'function') globalThis.crypto.getRandomValues(b);
  else for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, x => x.toString(16).padStart(2, '0').toUpperCase());
  // Match the player's UUID() layout: 8-4-4-4-12 hex characters.
  return h.slice(0, 4).join('') + '-' +
    h.slice(4, 6).join('') + '-' +
    h.slice(6, 8).join('') + '-' +
    h.slice(8, 10).join('') + '-' +
    h.slice(10, 16).join('');
}
async function ensureWasm(domain = DEFAULT_DOMAIN) {
  if (wasmReady && typeof globalThis.hxm_encrypt === 'function' && typeof globalThis.hxm_decrypt === 'function') {
    globalThis.Domain = domain;
    if (globalThis.location) { globalThis.location.hostname = domain; globalThis.location.host = domain + ':8443'; }
    return;
  }
  if (wasmPromise) return wasmPromise;
  wasmPromise = (async () => {
    if (typeof WebAssembly === 'undefined') throw new Error('当前 JS 运行环境不支持 WebAssembly');
    globalThis.Domain = domain;
    globalThis.window = globalThis;
    globalThis.self = globalThis;
    globalThis.global = globalThis;
    globalThis.performance = globalThis.performance || { now: () => Date.now() };
    globalThis.location = globalThis.location || { hostname: domain, host: domain + ':8443', href: 'https://' + domain + ':8443/vip/' };
    globalThis.location.hostname = domain;
    globalThis.location.host = domain + ':8443';
    if (typeof globalThis.Go !== 'function') throw new Error('Go/WASM 运行时没有加载');
    const wasmRes = request(WASM_URL, { buffer: 1, timeout: 30000, headers: { 'Accept': '*/*' } });
    const wasmBytes = new Uint8Array(wasmRes.content || []);
    if (wasmBytes.length < 10000 || wasmBytes[0] !== 0 || wasmBytes[1] !== 97 || wasmBytes[2] !== 115 || wasmBytes[3] !== 109) {
      throw new Error('下载的五洲派 WASM 文件无效');
    }
    const go = new globalThis.Go();
    // The Wuzhou page suppresses this optional Go runtime hook as well.
    if (go.importObject && go.importObject.env && go.importObject.env['syscall/js.finalizeRef']) {
      go.importObject.env['syscall/js.finalizeRef'] = () => {};
    }
    const loaded = await WebAssembly.instantiate(wasmBytes, go.importObject);
    go.run(loaded.instance).catch(e => { try { console.error('[AGE_WASM_RUNTIME]', e && e.stack || e); } catch (_) {} });
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) {
      if (typeof globalThis.hxm_encrypt === 'function' && typeof globalThis.hxm_decrypt === 'function') break;
      await new Promise(resolve => setTimeout(resolve, 25));
    }
    if (typeof globalThis.hxm_encrypt !== 'function' || typeof globalThis.hxm_decrypt !== 'function') {
      throw new Error('五洲派 WASM 已实例化，但没有注册 hxm_encrypt/hxm_decrypt');
    }
    wasmReady = true;
    log('Wuzhou WASM ready', 'bytes=' + wasmBytes.length, 'domain=' + domain);
  })().catch(e => {
    wasmPromise = null;
    throw e;
  });
  return wasmPromise;
}
function md5Hex(text) {
  if (typeof globalThis.md5X === 'function') return globalThis.md5X(String(text)).toLowerCase();
  throw new Error('当前 Yingxia JS 宿主没有提供 md5X');
}
function aesCbcDecrypt(dataHex, seed) {
  const digest = md5Hex(seed);
  if (typeof globalThis.nativeCrypto !== 'function') throw new Error('当前 Yingxia JS 宿主没有提供 nativeCrypto');
  const result = globalThis.nativeCrypto({
    op: 'aes', encrypt: false, mode: 'CBC',
    keyText: digest.slice(0, 16), ivText: digest.slice(16, 32),
    dataHex: String(dataHex || ''), output: 'text'
  });
  if (!result || typeof result.text !== 'string') throw new Error('AES-CBC 解密没有返回文本');
  return JSON.parse(result.text);
}
function parseWuzhouConfig(playerHtml, playerUrl) {
  const url = new URL(playerUrl);
  const contentId = readMetaId(playerHtml, 'meta[http-equiv="Content-Type"]', 'id');
  const viewportId = readMetaId(playerHtml, 'meta[name="viewport"]', 'id');
  const vurl = readAssigned(playerHtml, 'Vurl');
  if (!contentId || !viewportId) throw new Error('五洲派播放器页面缺少 Code=10 所需 Meta ID');
  if (!vurl) throw new Error('没有从五洲派播放器 HTML 中提取 Vurl；该变量可能由页面脚本动态计算');
  const timeText = readAssigned(playerHtml, 'Time') || String(Math.floor(Date.now() / 1000));
  return {
    metaContentId: contentId,
    metaViewportId: viewportId,
    vurl,
    time: timeText,
    host: readAssigned(playerHtml, 'Host') || url.hostname,
    referer: readAssigned(playerHtml, 'Ref'),
    version: readAssigned(playerHtml, 'Version') || DEFAULT_VERSION,
    api: readAssigned(playerHtml, 'Api') || DEFAULT_API,
    wap: readFlag(playerHtml, 'Iswap', '0'),
    ios: readFlag(playerHtml, 'Isios', '0')
  };
}
function parseApiResponse(apiResponse, config, domain) {
  if (String(apiResponse.Status) !== '1') throw new Error('五洲派 API Status=' + apiResponse.Status + ': ' + String(apiResponse.Data || '').slice(0, 120));
  const code = String(apiResponse.Code || '');
  const appkey = String(apiResponse.Appkey || '');
  const version = String(apiResponse.Version || config.version || DEFAULT_VERSION);
  const data = String(apiResponse.Data || '');
  const joinedMeta = (config.metaContentId + config.metaViewportId).replace('viewport', '');
  const seed = code === '10' ? code + joinedMeta + appkey + version : code + appkey + version;
  const info = aesCbcDecrypt(data, seed);
  let mediaUrl = String(info.url || '');
  if (!mediaUrl) throw new Error('五洲派 API 解密 JSON 没有 url 字段');
  if (code === '10') {
    globalThis.Domain = domain;
    const encoded = globalThis.hxm_decrypt(mediaUrl);
    mediaUrl = decodeURIComponent(String(encoded));
  } else {
    mediaUrl = decodeURIComponent(mediaUrl);
  }
  if (!/^https?:\/\//i.test(mediaUrl)) throw new Error('Wuzhou 解密结果不是 HTTP(S) 地址: ' + mediaUrl.slice(0, 100));
  info.url = mediaUrl;
  info.api_code = code;
  return info;
}
function resolveApi(config, playerUrl) {
  const apiBase = String(config.api || DEFAULT_API).replace(/\/$/, '');
  const apiUrl = apiBase + '/Api.php';
  const uuid = uuidV4();
  const payload = {
    url: config.vurl,
    wap: config.wap || '0',
    ios: config.ios || '0',
    host: config.host || DEFAULT_HOST,
    referer: config.referer || '',
    time: String(config.time)
  };
  const params = globalThis.hxm_encrypt(JSON.stringify(payload)).toUpperCase();
  const signPlain = payload.host + ' | ' + uuid + ' | ' + payload.time + ' | ' + config.version + ' | ' + params;
  const sign = globalThis.hxm_encrypt(signPlain).toUpperCase();
  const origin = new URL(apiBase).origin;
  const headers = {
    'User-Agent': UA,
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': origin,
    'Referer': playerUrl,
    'Video-Parse-Uuid': uuid,
    'Video-Parse-Time': payload.time,
    'Video-Parse-Version': config.version,
    'Video-Parse-Sign': sign
  };
  const body = 'Params=' + encodeURIComponent(params);
  const response = request(apiUrl, { method: 'POST', headers, body, timeout: 25000 });
  let json;
  try { json = JSON.parse(response.content); }
  catch (_) { throw new Error('五洲派 Api.php 没有返回 JSON: ' + String(response.content || '').slice(0, 200)); }
  const info = parseApiResponse(json, config, config.host || DEFAULT_DOMAIN);
  info.requestTime = payload.time;
  info.timeFallback = !readAssigned(config.__html || '', 'Time');
  return info;
}

function spiderErrorResult(error) {
  const message = String(error && error.message || error || '未知播放错误');
  lastError = message;
  try { console.error('[AGE_PLAY_ERROR]', message); } catch (_) {}
  return JSON.stringify({ parse: 1, jx: 0, url: '', error: message, header: { 'User-Agent': UA } });
}

const spider = {
  async init(ext) {
    this.ext = ext || {};
    this.lastError = '';
    this.name = 'AGE动漫';
    log('Spider initialized');
    return true;
  },

  async home(filter) {
    return JSON.stringify({ class: [{ type_id: 'update', type_name: '最近更新' }] });
  },

  async homeVod() {
    const url = SITE;
    const page = request(url, { headers: { 'Referer': SITE } });
    const list = cardsFromHtml(page.content, 'div.video_list_box.recommend_list > div.video_list_box--bd > div > div', page.url || url);
    return JSON.stringify({ list });
  },

  async category(tid, pg, filter, extend) {
    const pageNo = Math.max(1, Number(pg || 1) || 1);
    if (String(tid) !== 'update') return JSON.stringify({ list: [], page: pageNo, pagecount: 1, limit: 24, total: 0 });
    let url = SITE + 'update';
    if (pageNo > 1) url += '?page=' + pageNo;
    const page = request(url, { headers: { 'Referer': SITE } });
    let fragments = manyOf(page.content, '.video_item');
    if (!fragments.length) fragments = manyOf(page.content, 'div.video_list_box.recent_update .video_item');
    const list = fragments.map(fragment => cardFromHtml(fragment, page.url || url)).filter(Boolean);
    return JSON.stringify({ list, page: pageNo, pagecount: pageNo + (list.length >= 24 ? 1 : 0), limit: 24, total: (pageNo - 1) * 24 + list.length });
  },

  async search(key, quick, pg) {
    const pageNo = Math.max(1, Number(pg || 1) || 1);
    let url = SITE + 'search?query=' + encodeURIComponent(String(key || ''));
    if (pageNo > 1) url += '&page=' + pageNo;
    const page = request(url, { headers: { 'Referer': SITE } });
    const list = cardsFromHtml(page.content, 'div.row > div > div', page.url || url);
    return JSON.stringify({ list, page: pageNo, pagecount: pageNo + (list.length >= 20 ? 1 : 0), limit: 20, total: (pageNo - 1) * 20 + list.length });
  },

  async detail(id) {
    const detailUrl = absolute(id, SITE);
    const page = request(detailUrl, { headers: { 'Referer': SITE } });
    const h = page.content;
    const name = textOf(h, 'section > div > div.video_detail_right.ps-3.flex-grow-1 > h2') || textOf(h, 'h2') || textOf(h, 'h1');
    const desc = textOf(h, 'div.video_detail_right.ps-3.flex-grow-1 > div.video_detail_desc.py-2');
    const pic = attrOf(h, 'section > div > div.video_detail_left > div.video_detail_cover > img', 'data-original') ||
      attrOf(h, 'section > div > div.video_detail_left > div.video_detail_cover > img', 'data-src') ||
      attrOf(h, 'section > div > div.video_detail_left > div.video_detail_cover > img', 'src') || attrOf(h, 'img', 'src');
    const typeName = textOf(h, 'div.video_detail_box.detail_baseinfo.my-2 > div > div > div > ul > li:nth-child(9) > span:nth-child(2)');
    const routeTitles = manyOf(h, 'div.video_detail_playlist_wrapper.pt-4 > ul > li');
    const routeContainers = manyOf(h, 'div.video_detail_playlist_wrapper.pt-4 > div.tab-content > div');
    const playFrom = [], playUrl = [];
    for (let i = 0; i < routeContainers.length; i++) {
      const routeTitle = textOf(routeTitles[i] || '', 'body') || (routeTitles[i] ? textOf(routeTitles[i], 'li') : '') || ('线路' + (i + 1));
      const episodes = [];
      const lis = manyOf(routeContainers[i], 'ul > li');
      for (let j = 0; j < lis.length; j++) {
        const href = attrOf(lis[j], 'a[href]', 'href');
        const epName = textOf(lis[j], 'a') || ('第' + (j + 1) + '集');
        if (href) episodes.push(epName + '$' + absolute(href, page.url || detailUrl));
      }
      if (episodes.length) {
        playFrom.push(routeTitle || ('线路' + (i + 1)));
        playUrl.push(episodes.join('#'));
      }
    }
    if (!playUrl.length) {
      const links = manyOf(h, 'div.video_detail_playlist_wrapper a[href]');
      const episodes = [];
      for (let i = 0; i < links.length; i++) {
        const href = attrOf(links[i], 'a[href]', 'href');
        const epName = textOf(links[i], 'a') || ('第' + (i + 1) + '集');
        if (href) episodes.push(epName + '$' + absolute(href, page.url || detailUrl));
      }
      if (episodes.length) { playFrom.push('线路1'); playUrl.push(episodes.join('#')); }
    }
    const vod = {
      vod_id: detailUrl, vod_name: name, vod_pic: pic ? absolute(pic, page.url || detailUrl) : '',
      vod_actor: '', vod_director: '', vod_remarks: '', vod_content: desc,
      type_name: typeName, vod_play_from: playFrom.join('$$$'), vod_play_url: playUrl.join('$$$')
    };
    return JSON.stringify({ list: [vod] });
  },

  async play(flag, id, flags) {
    try {
      const playPageUrl = absolute(id, SITE);
      const u = new URL(playPageUrl);
      if (!['www.agedm.io', 'agedm.io'].includes(u.hostname)) throw new Error('播放 ID 不是 AGE 动漫单集页面: ' + playPageUrl);
      const agePage = request(playPageUrl, { headers: { 'Referer': SITE } });
      const playerSrc = attrOf(agePage.content, 'iframe#iframeForVideo', 'src');
      if (!playerSrc) throw new Error('AGE 单集页面没有找到 iframe#iframeForVideo[src]');
      const playerUrl = absolute(playerSrc, agePage.url || playPageUrl);
      const pu = new URL(playerUrl);
      if (pu.hostname !== 'jx.wuzhoupai.com') throw new Error('AGE iframe 不是已分析的五洲派播放器: ' + pu.hostname);
      const playerPage = request(playerUrl, { headers: { 'Referer': playPageUrl, 'Accept': 'text/html,*/*;q=0.8' } });
      const config = parseWuzhouConfig(playerPage.content, playerPage.url || playerUrl);
      const hostname = new URL(playerUrl).hostname;
      globalThis.Domain = hostname;
      await ensureWasm(hostname);
      config.__html = playerPage.content;
      const info = resolveApi(config, playerUrl);
      if (String(info.type || '').toLowerCase() === 'url') {
        throw new Error('五洲派 API 返回的是二级播放器页面，不是单一媒体地址: ' + info.url);
      }
      const mediaUrl = String(info.url || '');
      if (!/^https?:\/\//i.test(mediaUrl)) throw new Error('五洲派没有返回有效媒体 URL');
      lastError = '';
      log('Resolved media', info.type || 'unknown', new URL(mediaUrl).hostname);
      return JSON.stringify({
        parse: 0, jx: 0, url: mediaUrl,
        format: String(info.type || '').toLowerCase(),
        header: { 'User-Agent': UA, 'Referer': playerUrl }
      });
    } catch (e) {
      return spiderErrorResult(e);
    }
  }
};

export default spider;
