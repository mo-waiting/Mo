# AGE 动漫 Yingxia iOS 播放修正版 v10

## 文件

- `age_wuzhou_yingxia.js`：iOS 播放修正版 Spider。
- `age_wuzhou_js_subscription.json`：映匣订阅配置。

## 本版修改

1. **iOS 播放标记**：播放器页面的 `Isios`、`Iswap` 由原网页 JavaScript 在浏览器运行时计算；Spider 只下载静态 HTML，无法执行该段检测。本 iOS 专用版本在请求五洲派 API 时明确传入 `ios=1`、`wap=1`。
2. **二级播放器解析**：原版收到 `type=url` 会直接报“不是单一媒体地址”。本版继续尝试解析二级网页中的 `<video>` / `<source>`、JSON 播放配置、iframe、跳转地址以及外部播放器 JS，提取 MP4/M3U8 等直链。
3. **AES/MD5 兼容**：内置来自用户提供的五洲派播放器资源的 CryptoJS 4.1.1 fallback。当映匣宿主没有 `md5X` 或 `nativeCrypto` 时，使用纯 JavaScript 完成 MD5 和 AES-CBC/PKCS7。
4. **保留原功能**：不改移动版目录、筛选、搜索、详情和集数数据结构。

## 导入

将 ZIP 解压后，把 `age_wuzhou_js_subscription.json` 导入映匣；或在订阅管理中指向该配置。Spider 文件名需要保持为 `age_wuzhou_yingxia.js`。

## 网络

继续让以下域名走可用代理策略：

- `agedm.io`
- `wuzhoupai.com`
- `xmfxgjzx.com`

第三个域名提供五洲派 WASM 文件。

## 兼容性边界

五洲派的 `hxm_encrypt` / `hxm_decrypt` 仍来自原版 Go/WASM。本版保留原版 WASM，以避免用未经验证的算法替代它。如果当前 iOS 映匣 JS 宿主没有提供 `WebAssembly` API，Spider 会在五洲派请求前失败；仅靠 Spider JavaScript 无法在缺少 WASM 执行能力的宿主中运行该 Go/WASM。需要映匣 iOS 运行环境提供 WebAssembly，或进一步把这两个函数移植为纯 JavaScript 后才能彻底消除该依赖。

## 本地验证范围

已完成：

- JavaScript 语法检查。
- 使用真实离线 `Code=10` 响应样本验证 MD5 和 AES-CBC/PKCS7 解密。
- 使用原版 WASM 验证 `hxm_encrypt` / `hxm_decrypt` 往返。
- 模拟五洲派 API 请求，确认提交参数包含 `ios=1`、`wap=1`。
- 模拟 `type=url` 的 iframe 和外部 JS 页面，确认能提取单一媒体 URL。
- 完整 Spider 模拟播放流程返回单一 MP4 地址。

这些是本地离线/模拟网络验证，不等同于在实体 iPhone 的映匣版本上完成实机播放验证。
