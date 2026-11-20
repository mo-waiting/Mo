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
if (typeof globalThis.navigator === 'undefined') { try { Object.defineProperty(globalThis, 'navigator', { value: { userAgent: 'Mozilla/5.0' }, configurable: true }); } catch (_) {} }
(()=>{if(typeof global!=="undefined"){}else if(typeof window!=="undefined"){window.global=window}else if(typeof self!=="undefined"){self.global=self}else{throw new Error("cannot export Go (neither global, window nor self is defined)");}const enosys=()=>{const err=new Error("not implemented");err.code="ENOSYS";return err};if(!global.fs){let outputBuf="";global.fs={constants:{O_WRONLY:-1,O_RDWR:-1,O_CREAT:-1,O_TRUNC:-1,O_APPEND:-1,O_EXCL:-1},writeSync(fd,buf){outputBuf+=decoder.decode(buf);const nl=outputBuf.lastIndexOf("\n");if(nl!=-1){console.log(outputBuf.substr(0,nl));outputBuf=outputBuf.substr(nl+1)}return buf.length},write(fd,buf,offset,length,position,callback){if(offset!==0||length!==buf.length||position!==null){callback(enosys());return}const n=this.writeSync(fd,buf);callback(null,n)},chmod(path,mode,callback){callback(enosys())},chown(path,uid,gid,callback){callback(enosys())},close(fd,callback){callback(enosys())},fchmod(fd,mode,callback){callback(enosys())},fchown(fd,uid,gid,callback){callback(enosys())},fstat(fd,callback){callback(enosys())},fsync(fd,callback){callback(null)},ftruncate(fd,length,callback){callback(enosys())},lchown(path,uid,gid,callback){callback(enosys())},link(path,link,callback){callback(enosys())},lstat(path,callback){callback(enosys())},mkdir(path,perm,callback){callback(enosys())},open(path,flags,mode,callback){callback(enosys())},read(fd,buffer,offset,length,position,callback){callback(enosys())},readdir(path,callback){callback(enosys())},readlink(path,callback){callback(enosys())},rename(from,to,callback){callback(enosys())},rmdir(path,callback){callback(enosys())},stat(path,callback){callback(enosys())},symlink(path,link,callback){callback(enosys())},truncate(path,length,callback){callback(enosys())},unlink(path,callback){callback(enosys())},utimes(path,atime,mtime,callback){callback(enosys())}}}if(!global.process){global.process={getuid(){return-1},getgid(){return-1},geteuid(){return-1},getegid(){return-1},getgroups(){throw enosys();},pid:-1,ppid:-1,umask(){throw enosys();},cwd(){throw enosys();},chdir(){throw enosys();},exit(code){throw new Error("Go WASM exited with code "+code)}}}if(!global.crypto){global.crypto={getRandomValues(b){for(let i=0;i<b.length;i++){b[i]=Math.floor(Math.random()*256)}return b}}}if(!global.performance){global.performance={now(){return Date.now()}}}if(!global.TextEncoder){global.TextEncoder=class{encode(value){const s=encodeURIComponent(String(value));const bytes=[];for(let i=0;i<s.length;){if(s.charAt(i)==="%"){bytes.push(parseInt(s.slice(i+1,i+3),16));i+=3}else{bytes.push(s.charCodeAt(i++))}}return new Uint8Array(bytes)}}}if(!global.TextDecoder){global.TextDecoder=class{constructor(label,options){this.fatal=!!(options&&options.fatal)}decode(input){if(input==null)return "";let bytes;if(input instanceof ArrayBuffer)bytes=new Uint8Array(input);else if(ArrayBuffer.isView(input))bytes=new Uint8Array(input.buffer,input.byteOffset,input.byteLength);else bytes=new Uint8Array(input);let encoded="";for(let i=0;i<bytes.length;i++)encoded+="%"+bytes[i].toString(16).padStart(2,"0");try{return decodeURIComponent(encoded)}catch(e){if(this.fatal)throw e;let out="";for(let j=0;j<bytes.length;j++)out+=String.fromCharCode(bytes[j]);return out}}}}const encoder=new TextEncoder("utf-8");const decoder=new TextDecoder("utf-8");var logLine=[];global.Go=class{constructor(){this._callbackTimeouts=new Map();this._nextCallbackTimeoutID=1;const mem=()=>{return new DataView(this._inst.exports.memory.buffer)};const setInt64=(addr,v)=>{mem().setUint32(addr+0,v,true);mem().setUint32(addr+4,Math.floor(v/4294967296),true)};const getInt64=(addr)=>{const low=mem().getUint32(addr+0,true);const high=mem().getInt32(addr+4,true);return low+high*4294967296};const loadValue=(addr)=>{const f=mem().getFloat64(addr,true);if(f===0){return undefined}if(!isNaN(f)){return f}const id=mem().getUint32(addr,true);return this._values[id]};const storeValue=(addr,v)=>{const nanHead=0x7ff80000;if(typeof v==="number"){if(isNaN(v)){mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,0,true);return}if(v===0){mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,1,true);return}mem().setFloat64(addr,v,true);return}switch(v){case undefined:mem().setFloat64(addr,0,true);return;case null:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,2,true);return;case true:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,3,true);return;case false:mem().setUint32(addr+4,nanHead,true);mem().setUint32(addr,4,true);return}let id=this._ids.get(v);if(id===undefined){id=this._idPool.pop();if(id===undefined){id=this._values.length}this._values[id]=v;this._goRefCounts[id]=0;this._ids.set(v,id)}this._goRefCounts[id]++;let typeFlag=1;switch(typeof v){case"string":typeFlag=2;break;case"symbol":typeFlag=3;break;case"function":typeFlag=4;break}mem().setUint32(addr+4,nanHead|typeFlag,true);mem().setUint32(addr,id,true)};const loadSlice=(array,len,cap)=>{return new Uint8Array(this._inst.exports.memory.buffer,array,len)};const loadSliceOfValues=(array,len,cap)=>{const a=new Array(len);for(let i=0;i<len;i++){a[i]=loadValue(array+i*8)}return a};const loadString=(ptr,len)=>{return decoder.decode(new DataView(this._inst.exports.memory.buffer,ptr,len))};const timeOrigin=Date.now()-performance.now();this.importObject={wasi_snapshot_preview1:{fd_write:function(fd,iovs_ptr,iovs_len,nwritten_ptr){let nwritten=0;if(fd==1){for(let iovs_i=0;iovs_i<iovs_len;iovs_i++){let iov_ptr=iovs_ptr+iovs_i*8;let ptr=mem().getUint32(iov_ptr+0,true);let len=mem().getUint32(iov_ptr+4,true);for(let i=0;i<len;i++){let c=mem().getUint8(ptr+i);if(c==13){}else if(c==10){let line=decoder.decode(new Uint8Array(logLine));logLine=[];console.log(line)}else{logLine.push(c)}}}}else{console.error("invalid file descriptor:",fd)}mem().setUint32(nwritten_ptr,nwritten,true);return 0},proc_exit:(code)=>{if(global.process){process.exit(code)}else{throw"trying to exit with code "+code;}}},env:{"runtime.ticks":()=>{return timeOrigin+performance.now()},"runtime.sleepTicks":(timeout)=>{setTimeout(this._inst.exports.go_scheduler,timeout)},"syscall/js.finalizeRef":(sp)=>{console.error("syscall/js.finalizeRef not implemented")},"syscall/js.stringVal":(ret_ptr,value_ptr,value_len)=>{const s=loadString(value_ptr,value_len);storeValue(ret_ptr,s)},"syscall/js.valueGet":(retval,v_addr,p_ptr,p_len)=>{let prop=loadString(p_ptr,p_len);let value=loadValue(v_addr);let result=Reflect.get(value,prop);storeValue(retval,result)},"syscall/js.valueSet":(v_addr,p_ptr,p_len,x_addr)=>{const v=loadValue(v_addr);const p=loadString(p_ptr,p_len);const x=loadValue(x_addr);Reflect.set(v,p,x)},"syscall/js.valueDelete":(v_addr,p_ptr,p_len)=>{const v=loadValue(v_addr);const p=loadString(p_ptr,p_len);Reflect.deleteProperty(v,p)},"syscall/js.valueIndex":(ret_addr,v_addr,i)=>{storeValue(ret_addr,Reflect.get(loadValue(v_addr),i))},"syscall/js.valueSetIndex":(v_addr,i,x_addr)=>{Reflect.set(loadValue(v_addr),i,loadValue(x_addr))},"syscall/js.valueCall":(ret_addr,v_addr,m_ptr,m_len,args_ptr,args_len,args_cap)=>{const v=loadValue(v_addr);const name=loadString(m_ptr,m_len);const args=loadSliceOfValues(args_ptr,args_len,args_cap);try{const m=Reflect.get(v,name);storeValue(ret_addr,Reflect.apply(m,v,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueInvoke":(ret_addr,v_addr,args_ptr,args_len,args_cap)=>{try{const v=loadValue(v_addr);const args=loadSliceOfValues(args_ptr,args_len,args_cap);storeValue(ret_addr,Reflect.apply(v,undefined,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueNew":(ret_addr,v_addr,args_ptr,args_len,args_cap)=>{const v=loadValue(v_addr);const args=loadSliceOfValues(args_ptr,args_len,args_cap);try{storeValue(ret_addr,Reflect.construct(v,args));mem().setUint8(ret_addr+8,1)}catch(err){storeValue(ret_addr,err);mem().setUint8(ret_addr+8,0)}},"syscall/js.valueLength":(v_addr)=>{return loadValue(v_addr).length},"syscall/js.valuePrepareString":(ret_addr,v_addr)=>{const s=String(loadValue(v_addr));const str=encoder.encode(s);storeValue(ret_addr,str);setInt64(ret_addr+8,str.length)},"syscall/js.valueLoadString":(v_addr,slice_ptr,slice_len,slice_cap)=>{const str=loadValue(v_addr);loadSlice(slice_ptr,slice_len,slice_cap).set(str)},"syscall/js.valueInstanceOf":(v_addr,t_addr)=>{return loadValue(v_addr)instanceof loadValue(t_addr)},"syscall/js.copyBytesToGo":(ret_addr,dest_addr,dest_len,dest_cap,source_addr)=>{let num_bytes_copied_addr=ret_addr;let returned_status_addr=ret_addr+4;const dst=loadSlice(dest_addr,dest_len);const src=loadValue(source_addr);if(!(src instanceof Uint8Array)){mem().setUint8(returned_status_addr,0);return}const toCopy=src.subarray(0,dst.length);dst.set(toCopy);setInt64(num_bytes_copied_addr,toCopy.length);mem().setUint8(returned_status_addr,1)},"syscall/js.copyBytesToJS":(ret_addr,dest_addr,source_addr,source_len,source_cap)=>{let num_bytes_copied_addr=ret_addr;let returned_status_addr=ret_addr+4;const dst=loadValue(dest_addr);const src=loadSlice(source_addr,source_len);if(!(dst instanceof Uint8Array)){mem().setUint8(returned_status_addr,0);return}const toCopy=src.subarray(0,dst.length);dst.set(toCopy);setInt64(num_bytes_copied_addr,toCopy.length);mem().setUint8(returned_status_addr,1)}}}}async run(instance){this._inst=instance;this._values=[NaN,0,null,true,false,global,this];this._goRefCounts=[];this._ids=new Map();this._idPool=[];this.exited=false;const mem=new DataView(this._inst.exports.memory.buffer);while(true){const callbackPromise=new Promise((resolve)=>{this._resolveCallbackPromise=()=>{if(this.exited){throw new Error("bad callback: Go program has already exited");}setTimeout(resolve,0)}});this._inst.exports._start();if(this.exited){break}await callbackPromise}}_resume(){if(this.exited){throw new Error("Go program has already exited");}this._inst.exports.resume();if(this.exited){this._resolveExitPromise()}}_makeFuncWrapper(id){const go=this;return function(){const event={id:id,this:this,args:arguments};go._pendingEvent=event;go._resume();return event.result}}};})();

const SITE = 'https://www.agedm.io/';
const MOBILE_SITE = 'https://m.agedm.io/';
const API_BASE = 'https://api.agedm.io';
const CATALOG_SIZE = 10;
const DEFAULT_API = 'https://jx.wuzhoupai.com:8443/vip';
const DEFAULT_HOST = 'jx.wuzhoupai.com';
const DEFAULT_VERSION = 'V3.2';
const DEFAULT_DOMAIN = 'jx.wuzhoupai.com';
const WASM_URL = 'https://cdn.xmfxgjzx.com/jx/20230723ver/Play/jx.wuzhoupai.com.wasm?v=20260512';
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';

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
async function request(url, options = {}) {
  const headers = Object.assign({
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.7',
    'Cache-Control': 'no-cache'
  }, options.headers || {});
  const cookie = cookieHeader();
  if (cookie && !Object.keys(headers).some(k => k.toLowerCase() === 'cookie')) headers.Cookie = cookie;
  const requestOptions = Object.assign({ timeout: 30000, redirect: 1 }, options, { headers });
  let result;
  let transport = '';
  try {
    // Yingxia exposes both APIs: req() is synchronous, while http() returns a
    // Promise by default. Prefer async http() on iOS QuickJS to avoid blocking
    // the JS host during native networking; keep req() as compatibility fallback.
    if (typeof http === 'function') {
      transport = 'http(async)';
      result = await http(url, requestOptions);
    } else if (typeof req === 'function') {
      transport = 'req(sync-fallback)';
      result = req(url, requestOptions);
    } else {
      throw new Error('Yingxia HTTP host 没有提供 http()/req()');
    }
  } catch (e) {
    const detail = e && (e.message || e.toString()) || String(e);
    log('HTTP request threw', 'transport=' + (transport || 'unselected'), url, detail);
    throw new Error('Yingxia HTTP 请求异常 ' + url + ': ' + detail);
  }
  if (!result || typeof result !== 'object') {
    throw new Error('Yingxia http()/req() 返回值格式异常：' + url + ' (' + typeof result + ')');
  }
  absorbCookies(result.headers);
  const rawCode = result.code;
  const code = rawCode === '' || rawCode === null || rawCode === undefined ? 0 : Number(rawCode);
  if (!code) {
    const detail = result.error || result.message || result.msg || '';
    const finalUrl = result.url || url;
    const bodyLength = result.content == null ? 0 : (typeof result.content === 'string' ? result.content.length : -1);
    const headerNames = result.headers && typeof result.headers === 'object' ? Object.keys(result.headers).join(',') : '';
    log('HTTP no status from host', 'transport=' + (transport || 'unknown'), 'requested=' + url, 'final=' + finalUrl,
      'rawCode=' + JSON.stringify(rawCode), 'contentLength=' + bodyLength,
      'headerNames=' + headerNames, 'detail=' + String(detail).slice(0, 300));
    throw new Error('HTTP network error ' + url + ' [transport=' + (transport || 'unknown') + ', code=' + JSON.stringify(rawCode) +
      ', finalUrl=' + finalUrl + ', contentLength=' + bodyLength +
      (detail ? ', detail=' + String(detail).slice(0, 240) : '') + ']');
  }
  if (code < 200 || code >= 300) {
    const body = result.content ? String(result.content).slice(0, 160) : '';
    throw new Error('HTTP ' + code + ' ' + url + (body ? ': ' + body : ''));
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
    if (typeof WebAssembly === 'undefined') throw new Error('当前 JS 运行环境不支持 WebAssembly；目录、详情可用，但五洲派这条播放线路暂时无法在此环境中解密');
    globalThis.Domain = domain;
    globalThis.window = globalThis;
    globalThis.self = globalThis;
    globalThis.global = globalThis;
    globalThis.performance = globalThis.performance || { now: () => Date.now() };
    globalThis.location = globalThis.location || { hostname: domain, host: domain + ':8443', href: 'https://' + domain + ':8443/vip/' };
    globalThis.location.hostname = domain;
    globalThis.location.host = domain + ':8443';
    if (typeof globalThis.Go !== 'function') throw new Error('Go/WASM 运行时没有加载');
    const wasmRes = await request(WASM_URL, { buffer: 1, timeout: 30000, headers: { 'Accept': '*/*' } });
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
async function resolveApi(config, playerUrl) {
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
  const response = await request(apiUrl, { method: 'POST', headers, body, timeout: 25000 });
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

// AGE catalog filters and list helpers. Kept separate from the v1 detail/play resolver.
const AGE_REGIONS = {
  japan: '日本',
  china: '中国',
  western: '欧美'
};

function ageFilterOptions() {
  const typeValues = [
    { n: '全部', v: 'all' },
    { n: 'TV', v: 'TV' },
    { n: '剧场版', v: '剧场版' },
    { n: 'OVA', v: 'OVA' }
  ];
  const yearValues = [{ n: '全部', v: 'all' }];
  for (let year = 2026; year >= 2001; year--) {
    yearValues.push({ n: String(year), v: String(year) });
  }
  // AGE uses 2000 as the directory value for the "2000以前" option.
  yearValues.push({ n: '2000以前', v: '2000' });
  const quarterValues = [
    { n: '全部', v: 'all' },
    { n: '第一季度', v: '1' },
    { n: '第二季度', v: '2' },
    { n: '第三季度', v: '3' },
    { n: '第四季度', v: '4' }
  ];
  const statusValues = [
    { n: '全部', v: 'all' },
    { n: '连载', v: '连载' },
    { n: '完结', v: '完结' }
  ];
  const sortValues = [
    { n: '时间', v: 'time' },
    { n: '热度', v: 'hits' }
  ];
  return [
    { key: 'type', name: '类型', init: '全部', value: typeValues },
    { key: 'year', name: '年份', init: '全部', value: yearValues },
    { key: 'quarter', name: '季度', init: '全部', value: quarterValues },
    { key: 'status', name: '状态', init: '全部', value: statusValues },
    { key: 'sort', name: '排序', init: '时间', value: sortValues }
  ];
}

function selectedFilter(extend, key, allowed, fallback) {
  const raw = extend && Object.prototype.hasOwnProperty.call(extend, key) ? extend[key] : fallback;
  const value = String(raw == null || raw === '' ? fallback : raw).trim();
  return allowed.includes(value) ? value : fallback;
}

function catalogUrl(region, pageNo, extend) {
  const type = selectedFilter(extend, 'type', ['all', 'TV', '剧场版', 'OVA'], 'all');
  const years = ['all'];
  for (let year = 2026; year >= 2001; year--) years.push(String(year));
  years.push('2000');
  const year = selectedFilter(extend, 'year', years, 'all');
  const quarter = selectedFilter(extend, 'quarter', ['all', '1', '2', '3', '4'], 'all');
  const status = selectedFilter(extend, 'status', ['all', '连载', '完结'], 'all');
  const sort = selectedFilter(extend, 'sort', ['time', 'hits'], 'time');

  // Mobile API parameter mapping confirmed from real Fetch/XHR samples:
  // genre=type, label=theme, letter=initial, order=time|hits, region=area,
  // resource=source, season=quarter, status=status, year=year, page, size.
  // Only five filters are exposed by Yingxia. label/letter/resource remain all.
  const params = [
    ['genre', type],
    ['label', 'all'],
    ['letter', 'all'],
    ['order', sort],
    ['region', region],
    ['resource', 'all'],
    ['season', quarter],
    ['status', status],
    ['year', year],
    ['page', String(pageNo)],
    ['size', String(CATALOG_SIZE)]
  ];
  const query = params.map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)).join('&');
  return API_BASE + '/v2/catalog?' + query;
}

async function requestJson(url, referer = MOBILE_SITE) {
  const response = await request(url, {
    headers: {
      'Accept': 'application/json, text/plain, */*',
      'Referer': referer,
      'Origin': 'https://m.agedm.io',
      'X-Requested-With': 'XMLHttpRequest'
    },
    timeout: 30000
  });
  const raw = response.content == null ? '' : String(response.content);
  try {
    return JSON.parse(raw);
  } catch (e) {
    throw new Error('AGE JSON API 返回内容无法解析：' + url + '；响应开头=' + raw.slice(0, 240));
  }
}

function apiVideoToVod(item, region) {
  const id = item && (item.id != null ? item.id : item.vod_id);
  const name = item && (item.name || item.title || item.vod_name);
  if (id == null || !name) return null;
  const cover = item.cover || item.pic || item.vod_pic || '';
  return {
    vod_id: String(id),
    vod_name: String(name),
    vod_pic: cover ? absolute(cover, API_BASE + '/') : '',
    vod_remarks: String(item.uptodate || item.status || ''),
    vod_year: item.year != null ? String(item.year) : (item.premiere ? String(item.premiere).slice(0, 4) : ''),
    vod_area: String(item.area || region || ''),
    vod_content: String(item.intro_clean || item.intro || '')
  };
}

function catalogListResult(data, pageNo, region = '') {
  const videos = Array.isArray(data && data.videos) ? data.videos : [];
  const list = videos.map(item => apiVideoToVod(item, region)).filter(Boolean);
  const total = Number(data && data.total || 0);
  const pagecount = total > 0 ? Math.max(1, Math.ceil(total / CATALOG_SIZE)) : (list.length >= CATALOG_SIZE ? pageNo + 1 : pageNo);
  return JSON.stringify({ list, page: pageNo, pagecount, limit: CATALOG_SIZE, total });
}

function detailIdFromInput(input) {
  const value = String(input == null ? '' : input).trim();
  const match = value.match(/(?:detail\/)?(\d{6,})(?:\D*)$/) || value.match(/(\d{6,})/);
  return match ? match[1] : '';
}

function makeApiPlayId(routeKey, mode, playerPrefix, token) {
  return 'ageapi::' + String(routeKey) + '::' + String(mode) + '::' +
    encodeURIComponent(String(playerPrefix || '')) + '::' + encodeURIComponent(String(token || ''));
}

function parseApiPlayId(input) {
  const value = String(input || '');
  if (!value.startsWith('ageapi::')) return null;
  const parts = value.split('::');
  if (parts.length !== 5) throw new Error('移动版播放 ID 格式错误');
  return {
    routeKey: parts[1],
    mode: parts[2],
    playerPrefix: decodeURIComponent(parts[3]),
    token: decodeURIComponent(parts[4])
  };
}

function buildMobileDetail(data, detailId) {
  const video = data && (data.video || data.data && data.data.video) || {};
  const playlists = video.playlists || data.playlists || {};
  const labelMap = data.player_label_arr || video.player_label_arr || {};
  const playerVipText = String(data.player_vip || video.player_vip || '');
  const vipSet = new Set(playerVipText.split(',').map(x => x.trim()).filter(Boolean));
  const playerJx = data.player_jx || video.player_jx || {};
  const vipPrefix = String(playerJx.vip || 'https://jx.wuzhoupai.com:8443/vip/?url=');
  const zjPrefix = String(playerJx.zj || 'https://jx.wuzhoupai.com:8443/m3u8/?url=');
  const playFrom = [];
  const playUrl = [];

  for (const routeKey of Object.keys(playlists || {})) {
    const episodes = Array.isArray(playlists[routeKey]) ? playlists[routeKey] : [];
    const useVip = vipSet.has(routeKey);
    const mode = useVip ? 'vip' : 'zj';
    const prefix = useVip ? vipPrefix : zjPrefix;
    const rows = [];
    for (let i = 0; i < episodes.length; i++) {
      const episode = episodes[i];
      if (!Array.isArray(episode) || episode.length < 2) continue;
      const epName = String(episode[0] || ('第' + (i + 1) + '集'));
      const token = String(episode[1] || '');
      if (!token) continue;
      rows.push(epName + '$' + makeApiPlayId(routeKey, mode, prefix, token));
    }
    if (rows.length) {
      playFrom.push(String(labelMap[routeKey] || routeKey));
      playUrl.push(rows.join('#'));
    }
  }

  const name = String(video.name || video.name_other || video.name_original || '');
  const tags = String(video.plot || video.tags || (Array.isArray(video.tags_arr) ? video.tags_arr.join(' ') : ''));
  const type = String(video.type || '');
  const content = String(video.intro_clean || video.intro || video.intro_html || '');
  const company = String(video.company || '');
  const writer = String(video.writer || '');
  const extra = [];
  if (video.name_original) extra.push('原名：' + video.name_original);
  if (video.name_other && video.name_other !== name) extra.push('其他名称：' + video.name_other);
  if (company) extra.push('制作公司：' + company);
  if (video.premiere) extra.push('首播：' + video.premiere);
  const fullContent = [content, extra.join('\n')].filter(Boolean).join('\n\n');
  return {
    vod_id: String(video.id || detailId),
    vod_name: name,
    vod_pic: video.cover ? absolute(video.cover, API_BASE + '/') : '',
    vod_year: video.year != null ? String(video.year) : (video.premiere ? String(video.premiere).slice(0, 4) : ''),
    vod_area: String(video.area || ''),
    vod_remarks: String(video.uptodate || video.status || ''),
    vod_actor: writer,
    vod_director: '',
    vod_content: fullContent,
    type_name: [type, tags].filter(Boolean).join(' / '),
    vod_play_from: playFrom.join('$$$'),
    vod_play_url: playUrl.join('$$$')
  };
}

function pageResult(list, pageNo, limit) {
  return JSON.stringify({
    list,
    page: pageNo,
    pagecount: pageNo + (list.length >= limit ? 1 : 0),
    limit,
    total: (pageNo - 1) * limit + list.length
  });
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
    const classes = [
      { type_id: 'update', type_name: '最新更新' },
      { type_id: 'japan', type_name: '日本' },
      { type_id: 'china', type_name: '中国' },
      { type_id: 'western', type_name: '欧美' }
    ];
    const filters = {};
    for (const id of Object.keys(AGE_REGIONS)) filters[id] = ageFilterOptions();
    return JSON.stringify({ class: classes, filters });
  },

  // Yingxia's native recommendation page uses homeVod(); no duplicate 'today' category is exposed.
  async homeVod() {
    // Recommendation loading is optional in Yingxia. Do not make the whole AGE
    // source fail when the homepage root is blocked or unreachable; categories
    // remain independently requestable.
    const url = SITE;
    try {
      const page = await request(url, { headers: { 'Referer': SITE } });
      const list = cardsFromHtml(page.content, 'div.video_list_box.recommend_list > div.video_list_box--bd > div > div', page.url || url);
      log('Home recommendation cards=' + list.length);
      return JSON.stringify({ list });
    } catch (e) {
      log('Home recommendation unavailable; returning an empty recommendation list', e && e.message || e);
      return JSON.stringify({ list: [] });
    }
  },

  async category(tid, pg, filter, extend) {
    const pageNo = Math.max(1, Number(pg || 1) || 1);
    const categoryId = String(tid || '');

    if (categoryId === 'update') {
      const url = catalogUrl('all', pageNo, {});
      log('Mobile catalog latest updates', url);
      const data = await requestJson(url);
      return catalogListResult(data, pageNo, '');
    }

    if (Object.prototype.hasOwnProperty.call(AGE_REGIONS, categoryId)) {
      const region = AGE_REGIONS[categoryId];
      const url = catalogUrl(region, pageNo, extend || {});
      log('Mobile catalog request', categoryId, url);
      const data = await requestJson(url);
      const result = catalogListResult(data, pageNo, region);
      log('Mobile catalog response', 'region=' + region, 'total=' + String(data && data.total || 0),
        'videos=' + String(Array.isArray(data && data.videos) ? data.videos.length : 0));
      return result;
    }

    return JSON.stringify({ list: [], page: pageNo, pagecount: 1, limit: CATALOG_SIZE, total: 0 });
  },

  async search(key, quick, pg) {
    const pageNo = Math.max(1, Number(pg || 1) || 1);
    let url = SITE + 'search?query=' + encodeURIComponent(String(key || ''));
    if (pageNo > 1) url += '&page=' + pageNo;
    const page = await request(url, { headers: { 'Referer': SITE } });
    const list = cardsFromHtml(page.content, 'div.row > div > div', page.url || url);
    return JSON.stringify({ list, page: pageNo, pagecount: pageNo + (list.length >= 20 ? 1 : 0), limit: 20, total: (pageNo - 1) * 20 + list.length });
  },

  async detail(id) {
    const detailId = detailIdFromInput(id);
    if (!detailId) throw new Error('无法从详情 ID 中提取 AGE 动漫编号：' + String(id));
    const apiUrl = API_BASE + '/v2/detail/' + encodeURIComponent(detailId);
    log('Mobile detail request', apiUrl);
    const data = await requestJson(apiUrl);
    const vod = buildMobileDetail(data, detailId);
    if (!vod.vod_name) throw new Error('AGE 详情 API 没有返回 video.name：' + apiUrl);
    log('Mobile detail parsed', 'id=' + detailId, 'routes=' + (vod.vod_play_from ? vod.vod_play_from.split('$$$').length : 0),
      'playableEpisodes=' + (vod.vod_play_url ? vod.vod_play_url.split('$$$').join('#').split('#').length : 0));
    return JSON.stringify({ list: [vod] });
  },

  async play(flag, id, flags) {
    try {
      let playerUrl = '';
      let referer = MOBILE_SITE;
      const mobilePlay = parseApiPlayId(id);

      if (mobilePlay) {
        if (!mobilePlay.playerPrefix) throw new Error('AGE 详情没有提供五洲派播放器入口');
        playerUrl = mobilePlay.playerPrefix + mobilePlay.token;
        const playerHost = new URL(playerUrl).hostname;
        if (playerHost !== 'jx.wuzhoupai.com') throw new Error('移动版播放入口不是已分析的五洲派域名：' + playerHost);
        log('Mobile playlist play', 'route=' + mobilePlay.routeKey, 'mode=' + mobilePlay.mode);
      } else {
        // Backward compatibility for old HTML episode IDs.
        const playPageUrl = absolute(id, SITE);
        const u = new URL(playPageUrl);
        if (!['www.agedm.io', 'agedm.io', 'm.agedm.io'].includes(u.hostname)) {
          throw new Error('播放 ID 不是 AGE 动漫单集页面或移动版播放 ID：' + playPageUrl);
        }
        const agePage = await request(playPageUrl, { headers: { 'Referer': SITE } });
        const playerSrc = attrOf(agePage.content, 'iframe#iframeForVideo', 'src');
        if (!playerSrc) throw new Error('AGE 单集页面没有找到 iframe#iframeForVideo[src]');
        playerUrl = absolute(playerSrc, agePage.url || playPageUrl);
        referer = playPageUrl;
      }

      const pu = new URL(playerUrl);
      if (pu.hostname !== 'jx.wuzhoupai.com') throw new Error('播放器不是已分析的五洲派域名：' + pu.hostname);
      const playerPage = await request(playerUrl, { headers: { 'Referer': referer, 'Accept': 'text/html,*/*;q=0.8' } });
      const config = parseWuzhouConfig(playerPage.content, playerPage.url || playerUrl);
      const hostname = new URL(playerUrl).hostname;
      globalThis.Domain = hostname;
      await ensureWasm(hostname);
      config.__html = playerPage.content;
      const info = await resolveApi(config, playerUrl);
      if (String(info.type || '').toLowerCase() === 'url') {
        throw new Error('五洲派 API 返回的是二级播放器页面，不是单一媒体地址：' + info.url);
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
