# 映匣洛雪音乐源适配包

## 本包做什么

本包以用户提供的映匣音乐解析模块（`default.init / default.play`）为接口基准，将 `pdone/lx-music-source` 中健康报告标记为“可用”、且当前 `latest.js` 确实带有 `musicUrl` 事件处理器的音源，适配为映匣 `yingxiaMusic` 播放渠道。

## 文件

- `js/music-lx-adapter.js`：映匣统一音乐解析入口。
- `yingxiaMusic-config.json`：为了可以添加加入了哔哩哔哩，含 `yingxiaMusic` 属性，供合并到你现有的订阅 JSON。

## 接入步骤

你此前的订阅地址是 `https://bright-harbor.pages.dev/v1/tvbox.json`。按这个目录结构部署：

```text
/v1/
  tvbox.json                 # 你原来的订阅 JSON，保留现有 sites/lives
  /js/
    music-lx-adapter.js      # 本包提供的适配器
```

`yingxiaMusic-config.json` 中的 API 路径为：

```json
"api": "./js/music-lx-adapter.js"
```

因此订阅在 `/v1/tvbox.json` 时，会指向 `/v1/js/music-lx-adapter.js`。

把 `yingxiaMusic-config.json` 中的整个 `yingxiaMusic` 对象合并到你现有 `tvbox.json` 根节点，替换旧的 `yingxiaMusic` 对象即可。不要用 `subscription-sample.json` 覆盖现有订阅，否则示例中的空 `sites` 会替换你的影视源列表。

## 已适配并注册的 10 个渠道

| 渠道 ID | 名称 | 脚本中声明的平台 |
|---|---|---|
| `feichangdao` | 非常刀 | 网易云、QQ、酷我、酷狗、咪咕、汽水 |
| `helloworld` | HelloWorld | QQ、网易云、酷我、酷狗、咪咕 |
| `huanyin` | 幻音 | QQ、网易云、酷我、咪咕 |
| `hyw` | HYW 公益版 | QQ、网易云、酷我、酷狗、咪咕、汽水、B站、YouTube、喜马拉雅 |
| `jiexiang` | 杰翔聚合 | QQ、网易云、酷我、酷狗、咪咕 |
| `qdy` | 全豆要聚合 | QQ、网易云、酷我、酷狗、咪咕、汽水 |
| `qingliang` | 轻量 | QQ、网易云、酷我、酷狗 |
| `suyin` | 溯音 | QQ、网易云、酷我、咪咕 |
| `xinghai` | 星海（洛雪版） | QQ、网易云、酷我、酷狗、咪咕、汽水 |
| `xinglan` | 星澜 | QQ、网易云、酷我、酷狗、咪咕、汽水 |

`order` 前 6 条为主要渠道，后续条目作为备用次序。可在 `yingxiaMusic-config.json` 中调整渠道优先级。


健康报告的“可用”只表示探测到上游主机 HTTP 可达，不代表每个平台、每首歌、每种音质都验证过播放。详见 `source-availability.json`。

## 运行方式与重要限制

1. 适配器在每个渠道首次播放时，从 `raw.githubusercontent.com` 下载对应 `latest.js`；直连失败时尝试 `gh-proxy.org`、`ghproxy.net`。模块在当前运行会话中缓存已加载脚本。
2. 所以本包不是离线包。播放设备必须能够访问 GitHub Raw 或至少一个加速站。
3. 适配器用兼容层提供洛雪脚本所需的 `globalThis.lx`、`EVENT_NAMES`、`on/send`、回调式 `request`、MD5、AES-128-ECB 和 Buffer 工具。
4. 适配器需要映匣运行环境提供 `globalThis.req`，并允许 `Function()` 动态执行远程音源 JS。若映匣禁用动态执行，脚本无法加载。
5. 你上传的原版解析模块使用同步 `globalThis.req`（通过直接读取 `reply.code/content`）。因此洛雪脚本声明的并发/竞速请求在此适配层中可能被主机请求机制串行化，可能影响速度和个别源的超时表现。
6. 目前只适配歌曲播放取链 `musicUrl`，不把洛雪的搜索、歌词、封面、音源配置界面移植到映匣。
7. 洛雪源脚本会访问各自的第三方服务。其 API、鉴权、限流和可播放性均受上游变化影响。

## 测试结果

本包已执行：

- JavaScript 语法检查；
- 10 个渠道的模拟加载、平台映射和 URL 返回测试；
- 回调式 request 兼容测试；
- MD5 与 AES-128-ECB 已知向量测试；
- JSON 结构及 `order` 对渠道 ID / 平台的引用检查。

这些测试通过，但并不等于映匣客户端真实播放验证。本执行环境无法直连 GitHub Raw 和音乐上游，因此没有声称完成真实歌曲播放联调。首次导入后请用一首 QQ、一首网易云、一首酷我分别验证；若有错误，把映匣返回的错误文本发回即可定位。

## 来源

- https://github.com/pdone/lx-music-source
- 健康状态：`https://raw.githubusercontent.com/pdone/lx-music-source/health-status/health-state.json`
