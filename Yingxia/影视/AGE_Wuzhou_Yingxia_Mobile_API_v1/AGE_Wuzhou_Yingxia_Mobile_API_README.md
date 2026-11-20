# AGE 动漫 Yingxia JS（移动版 API）

本版以此前的 v1 五洲派播放解析源为基础，保留四个分类和五项地区筛选，并将列表、详情切换到用户提供的 AGE 移动版 JSON API。

## 分类

1. 最新更新
2. 日本
3. 中国
4. 欧美

不单独暴露“今日推荐”分类；Yingxia 原生推荐仍由 `homeVod()` 尝试读取原首页推荐区。

## 地区筛选（日本 / 中国 / 欧美）

每个地区分类仅显示五项筛选：

- 类型：全部、TV、剧场版、OVA
- 年份：全部、2026 至 2001、2000以前
- 季度：全部、第一季度、第二季度、第三季度、第四季度
- 状态：全部、连载、完结
- 排序：时间、热度

映射到移动 API：

| UI 筛选 | API 参数 | 值 |
|---|---|---|
| 类型 | `genre` | `all`、`TV`、`剧场版`、`OVA` |
| 年份 | `year` | `all`、年份数字、`2000` |
| 季度 | `season` | `all`、`1`、`2`、`3`、`4` |
| 状态 | `status` | `all`、`连载`、`完结` |
| 排序 | `order` | `time`、`hits` |

其他参数固定为 `label=all`、`letter=all`、`resource=all`。地区由分类决定，分页由 Yingxia 页码决定，每页 `size=10`。

`year=2000` 已根据用户提供的响应样本确认包含 2000 年及以前作品。

## API

- 列表：`https://api.agedm.io/v2/catalog`
- 详情：`https://api.agedm.io/v2/detail/{id}`

“最新更新”使用目录 API 的 `region=all`、`order=time`，不再请求旧版 `/update` HTML。

详情读取 `video` 元数据、`playlists`、`player_label_arr`、`player_vip` 和 `player_jx`。集数播放 ID 将线路 key、VIP/ZJ 模式、解析入口和 AGE 播放 token 一起保存，避免再次请求 AGE 旧版单集 HTML。

## 播放解析

- `player_vip` 中列出的线路，使用 `player_jx.vip`。
- 不在 `player_vip` 中的线路，使用 `player_jx.zj`。
- 播放器页面和 `Api.php` 仍复用原 v1 的五洲派 V3.2、Go WASM、Code=10 AES 解密流程。

此线路映射依据用户提供的 `player_vip` 与 `player_jx` 响应字段实现。完整的不同线路播放仍需在 Yingxia 真机逐条验证，尤其是 `zj`（`/m3u8/`）入口。

## 网络说明

列表和详情请求现在访问 `api.agedm.io`，而不是 `www.agedm.io` 的目录/详情 HTML。若 iOS Yingxia 仍出现 `code=0`，需要检查 Shadowrocket 是否把 `api.agedm.io` 也按 `DOMAIN-SUFFIX,agedm.io` 规则转发。

五洲派播放还会请求：

- `jx.wuzhoupai.com:8443`
- `cdn.xmfxgjzx.com`（WASM）

## 尚未覆盖 / 未实测的部分

- 搜索仍保留 v1 的网页搜索逻辑；目前没有用户提供并验证移动版搜索 API，因此没有猜测 `/v2/search` 等接口。
- Yingxia 原生推荐 `homeVod()` 仍尝试读取原首页推荐 HTML，失败时返回空列表，不会阻止四个主分类加载。
- 已完成本地模拟 API 响应、分类参数、分页、详情字段、播放线路 ID 拼装和 VIP 播放解析流程测试；没有在用户的 iPhone Yingxia 环境中直接访问真实 API 或实播。
