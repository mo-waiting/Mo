# AGE 动漫 Yingxia JS：iOS QuickJS 加载兼容修正版

基于 `v1_plus_regions_no_today` 修改。保留现有目录、筛选、详情、搜索和五洲派播放解析逻辑；这次只处理 iOS QuickJS 加载时的 Node.js `require` 依赖。

## 本版修复

- 删除 Go/WASM 兼容层中对 `require('fs')`、`require('crypto')`、`require('util')` 的调用。
- 不再引用 Node.js 的 `module` 入口判断。
- 为没有原生 `TextEncoder` / `TextDecoder` 的 JS 宿主增加轻量 UTF-8 fallback。
- 为 Go/WASM UUID 随机数提供 `crypto.getRandomValues` fallback。
- 保留分类：最新更新、日本、中国、欧美；没有独立“今日推荐”分类。
- 保留 `homeVod()`，供 Yingxia 自带的推荐页使用。

## 本地验证

- `node --check` 语法检查通过。
- 在 `require` 不存在的 ESM 环境中成功导入模块。
- 首页分类返回：`update`、`japan`、`china`、`western`。
- 日本、中国、欧美三组筛选配置存在。
- 使用本地 WASM 文件在 Node 的 WebAssembly 环境中验证 Go/WASM 初始化及 `hxm_encrypt` / `hxm_decrypt` 往返成功。

## iOS 重要限制

本次修复针对用户遇到的 `ReferenceError: require is not defined`，目的是让 JS 插件不再因 Node.js 模块调用而在加载阶段失败。

五洲派播放解密仍依赖 `WebAssembly` 执行 Go WASM。Yingxia 开发文档说明 iOS/tvOS 的 JS Spider 运行在 QuickJS，而 macOS 使用 Node。标准 QuickJS 通常不内置 JavaScript `WebAssembly` API；如果当前 iOS Yingxia 构建没有额外提供该 API，分类、详情可以运行，但五洲派播放解密仍会提示当前环境不支持 WebAssembly。Node 本地测试不等于 iOS 设备播放测试。

若 iOS 日志出现“当前 JS 运行环境不支持 WebAssembly”，需要进一步把 `hxm_encrypt` / `hxm_decrypt` 从 Go WASM 移植为纯 JavaScript（或由宿主提供 WASM 支持），单纯删除 `require` 无法解决这部分兼容性。
