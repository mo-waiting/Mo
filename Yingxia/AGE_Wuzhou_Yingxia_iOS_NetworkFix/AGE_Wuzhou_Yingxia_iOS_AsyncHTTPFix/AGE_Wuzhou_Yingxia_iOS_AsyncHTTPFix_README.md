# AGE 动漫 Yingxia JS — iOS 异步 HTTP 修正版

## 本次修正

- JS Spider 的网页和 API 请求优先使用 `await http(url, options)`，不再默认使用同步 `req()`。
- 当宿主没有提供 `http()` 时，才回退到 `req()`。
- 请求失败且 HTTP `code` 为空时，错误日志会附带原始 code、最终 URL、响应内容长度和响应头字段名称，便于进一步定位。
- 保留四个分类：最新更新、日本、中国、欧美。
- 保留日本、中国、欧美各自的五项筛选：类型、年份、季度、状态、排序。
- 保留详情、集数和五洲派播放解析代码；播放使用的 WASM 请求也改为异步等待。

## 关键点

Yingxia 的 JS Spider 提供 HTTP 能力。当前代码将 `req()` 的同步调用改成优先使用异步 `http()`。这次修正针对日志中出现的空 HTTP 状态码/网络异常路径，不代表已经证明 iOS 真机访问 AGE 成功。

## 本地检查

- `node --check age_wuzhou_yingxia.js` 通过。
- 用模拟的异步 `http()` 返回 200 响应，验证了 `homeVod()`、`category('update')`、`category('japan')` 的请求流程。
- 已确认分类 ID 为 `update,japan,china,western`。

## 若 iOS 仍然报错

请提供新错误全文。新版会尽量在错误文本中显示 `code`、`finalUrl`、`contentLength` 和 `detail`。若 `code` 仍为空，说明原生网络层未获得有效 HTTP 响应，需要结合新日志继续判断 DNS、TLS、代理或服务端连接问题。
