# ozon-market-data

**Ozon 类目市场数据 —— 一个开放的、每天在长的库。**

要知道一个类目「现在卖得好的都是谁、什么价、卖多少、广告压力多大」，
通常得买第三方工具（Seerfar、LinkFox 那类），按积分计费——查得越多越心疼，
最后你会因为舍不得积分而不去扫该扫的类目。

这个库把那部分数据沉淀下来，**每天更新一次，公开、免费、可以直接下载用**。

```bash
git clone https://github.com/Tingxian-Wang/ozon-market-data
cd ozon-market-data
python -m ozondata.cli cats                 # 有哪些类目
python -m ozondata.cli top 93443 --by sales # 腮红类目销量前十
python -m ozondata.cli stats 93443          # 类目聚合：GMV/价格带/ДРР/集中度
python -m ozondata.cli search румяна        # 按标题搜
```

零依赖，只要 Python 3.7+，不联网（数据就在仓库里）。

## 用代码读

```python
from ozondata import Library

lib = Library()
lib.categories()                        # [{id, name, count, gmv_total}]
lib.top("93443", n=10, by="sales")      # 销量前十
lib.stats("93443")                      # 聚合 + 样本量
```

## 里面有什么

每条商品记录带这些字段（完整定义见 [PROTOCOL.md](PROTOCOL.md)）：

| | |
|---|---|
| 规模 | `gmv` 成交额、`sales` 销量 |
| 趋势 | `growth_pct` 销量动态 |
| 价格 | `price_avg` 均价、`price_min` 最低价 |
| 口碑 | `rating` 评分、`reviews` 评价数 |
| **竞争强度** | **`drr_pct` 广告费率**、`conv_pct` 转化率、`promo_days` 促销天数 |
| 其他 | `rank_bin` 排名档、`scheme` 履约方式、`image`、`url` |

**`drr_pct`、`promo_days`、`scheme` 这三项，主流第三方工具都不给**，
而它们恰恰决定一个类目能不能进——ДРР 6% 说明广告压力小，21% 说明是红海。

## 数据从哪来

卖家后台「Ozon 上的商品」周榜 + 买家端商品墙，按 SKU 合并去重。
抓取工具和抓取方式不随本仓库发布——**这里只放数据和读取端**。


## 或者：直接调 API（不用 clone）

同一份数据，我们托管了一份只读接口，**公开、免费、不要令牌**，按 IP 每分钟 60 次。

```bash
# 有哪些类目
curl "https://yunlinghanyin.cn/api/market/categories"

# 腮红类目里销量最高的三个
curl "https://yunlinghanyin.cn/api/market/top?category=93443&n=3&by=sales"

# 类目聚合：GMV / 价格带 / ДРР 中位 / 集中度
curl "https://yunlinghanyin.cn/api/market/stats_by_category?category=93443"
```

| 端点 | 用途 |
|---|---|
| `GET /api/market/stats` | 库状态（schema、更新时间、类目数、商品数） |
| `GET /api/market/categories` | 类目列表 + 条数 + GMV 合计 |
| `GET /api/market/top?category=&n=&by=` | 榜单，`by` 支持 gmv / sales / growth_pct / reviews / rating / conv_pct / drr_pct |
| `GET /api/market/stats_by_category?category=` | 类目聚合 |
| `GET /api/market/item?sku=` | 单个 SKU |

**接口返回的字段和仓库里的 JSON 完全一致**（同一个 schema），所以两种拿法可以混用：
探索阶段打接口，要全量就 clone。

错误约定：`400` 参数非法 / `404` 没有这个类目或 SKU（**不是零，是没抓**）/ `429` 限流 / `503` 数据未就绪。

完整文档：<https://yunlinghanyin.cn/product-api.html>

## 三条口径纪律

1. **`null` ≠ 0。** 字段为空是「没取到」，不是「等于零」，别拿去算平均。
2. **评价数 ≠ 销量。** 差一到两个数量级。
3. **增长是动态不是绝对值。** 负增长可能只是去年同期基数高。

细节见 [PROTOCOL.md](PROTOCOL.md)。

## 目录

```
data/
  latest.json            最新一期（全部类目）
  snapshots/YYYY-MM-DD.json   历史快照，一天一份
ozondata/
  client.py              读取端（零依赖）
  cli.py                 命令行
PROTOCOL.md              字段字典与口径
```

## 关于更新

每天更新一次，`snapshots/` 会一天天攒下去——这就是「不断生长」的部分。
数据在变，`sku` 是稳定键，可以拿它做跨期对比。

## License

MIT。数据来自 Ozon 公开页面与卖家自有账号后台，使用请自行遵守平台条款。
