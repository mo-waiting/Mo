# AGE Network Diagnostic v3

这是临时诊断插件，不是影视源。它用于分辨 AGE 域名连接失败的层次。

## 本版修正

- 使用 `www.agefans.tv`，不再把 `agefans.com` 当作同一个域名。
- 增加 `m.agedm.io`。
- 增加 `http://www.agedm.io/update` 的明文 HTTP 测试，用于辅助判断 TLS 与域名/路由故障。
- 保留 Example 和 Baidu HTTPS 对照组。

## 导入

将 `AGE_Network_Diagnostic_v3.js` 与本 JSON 放在同一目录，确保相对 api 路径可访问；导入 JSON 后打开“AGE网络诊断 v3（临时）”分类。

## 结果解读

- Example/Baidu 200，而 AGE HTTPS 为 code=0：问题局限于 AGE 域名链路，可能是 DNS、IPv4/IPv6 路由、TLS、代理策略或目标网络策略。
- `m.agedm.io` 成功：可以进一步检查移动站是否能承载目录与列表页面，再决定是否作为站点基址。
- `www.agefans.tv` 成功而 `www.age.tv` 失败：可研究该别名，但必须检查重定向后的最终地址。
- HTTP 成功但 HTTPS code=0：重点怀疑 TLS 握手/证书/协议兼容；HTTP 仅作诊断，不建议作为最终站点协议。
- HTTP 和 HTTPS 都 code=0：更偏向 DNS、路由或网络策略问题。

注意：code=0 不会告诉我们具体是哪一种底层错误。此插件不绕过证书验证，也不关闭 TLS 安全检查。
