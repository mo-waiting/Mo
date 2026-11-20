# AGE 动漫 Yingxia iOS 纯 JavaScript 播放版 v11

## 文件

- `age_wuzhou_yingxia.js`：Spider 主文件。
- `age_wuzhou_js_subscription.json`：映匣订阅配置。

## v11 主要改动

1. **移除了五洲派 Go/WASM 运行时**：不再下载 `jx.wuzhoupai.com.wasm`，不再调用 `WebAssembly.instantiate()`，也不再依赖 `Go` 运行时。
2. **纯 JavaScript 实现 `hxm_encrypt()` / `hxm_decrypt()`**：从原版 Go/WASM 中确认算法为 AES-128-CBC、PKCS7，使用相同的 16 字节 ASCII key/IV `ni po jie ni ** `，十六进制输入/输出。
3. **MD5 与 Code=10 AES-CBC 统一走内置 CryptoJS 4.1.1**：不再依赖映匣宿主是否提供 `md5X` 或 `nativeCrypto`。
4. **保留移动版 API 与全部现有线路**：分类、筛选、搜索、详情、线路映射、集数 ID、二级播放器处理均以 v10 为基础保留。
5. **保留 iOS 请求标记**：五洲派请求参数仍强制 `ios=1`、`wap=1`。

## 导入

将 ZIP 解压后，把 `age_wuzhou_js_subscription.json` 导入映匣。订阅配置引用的 Spider 文件名为 `age_wuzhou_yingxia.js`，请保持文件名不变。

## 网络

仍需要根据实际网络环境为以下域名配置可用代理：

- `agedm.io`（包括 `api.agedm.io`、`m.agedm.io`）
- `wuzhoupai.com`（包括 `jx.wuzhoupai.com:8443`）

v11 不再下载 WASM，因此正常播放解析不再需要 `cdn.xmfxgjzx.com` 的 WASM 文件。实际媒体 CDN 是否需要代理，应根据播放时真实请求域名判断。

## 本地验证

已完成的离线验证：

- `node --check` 语法检查。
- 将 `WebAssembly` 显式设为 `undefined` 后，Spider 仍可导入并运行首页方法。
- 纯 JS HXM 实现与之前从原版 WASM 实际采集的输出逐项匹配：空字符串、英文、UTF-8 中文、五洲派 JSON 请求参数。
- 对此前保存的真实 Code=10 样本执行 MD5、AES-CBC/PKCS7 解密，再通过纯 JS `hxm_decrypt()` 得到与旧版 resolver 记录完全一致的 MP4 地址。
- 完整 Spider 模拟请求返回单一播放地址，且未发起任何 WASM 下载请求；`ios=1`、`wap=1` 参数正确。

## 实机验证边界

这些检查是在本地 Node 环境中完成，并通过禁用 `WebAssembly` 验证不再需要 WASM；它们不等同于在用户设备的 iOS QuickJS 版本上完成实机播放。若仍无法播放，下一步应以 Spider 的返回对象或 Yingxia 播放器实际拿到的 `url` 为准，继续区分解析失败与媒体 CDN 请求失败。
