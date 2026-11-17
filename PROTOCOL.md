# 数据结构说明（schema `ozon-market-data/v1`）

数据文件只有一种形状：`data/latest.json`（最新一期）和 `data/snapshots/<日期>.json`（历史快照）。

## 顶层

```json
{
  "schema": "ozon-market-data/v1",
  "updated_at": "2026-11-17T09:47:41+0800",
  "period": "weekly",
  "source": "……",
  "count": 66,
  "categories": [{"id": "93443", "name": "腮红"}],
  "items": [ ... ]
}
```

| 字段 | 含义 |
|---|---|
| `schema` | 结构版本。字段含义有变会升版本号，旧的别硬套。 |
| `updated_at` | 这一期是什么时候抓的（带时区）。 |
| `period` | 统计周期。`weekly` = 周榜，Ozon 后台的口径。 |
| `count` | `items` 的条数。 |
| `categories` | 本期覆盖的类目。 |

## items 的每一项

| 字段 | 类型 | 含义 | 缺省 |
|---|---|---|---|
| `sku` | string | Ozon 商品 SKU，**唯一键** | 必有 |
| `name` | string | 商品标题 | 必有 |
| `brand` | string | 品牌名 | `null` |
| `category_id` | string | 所属类目 ID | 必有 |
| `gmv` | number | 周期内成交额（₽） | `null` |
| `sales` | number | 周期内销量（件） | `null` |
| `growth_pct` | number | 销量动态（%），正数是涨 | `null` |
| `price_avg` | number | 均价（₽） | `null` |
| `price_min` | number | 最低卖家价（₽） | `null` |
| `rank_bin` | string | 排名档：`leader` / `top_10` / `top_50` / 空 | `null` |
| `rating` | number | 评分（0–5） | `null` |
| `reviews` | number | 评价数 | `null` |
| `conv_pct` | number | 曝光→下单转化率（%） | `null` |
| `drr_pct` | number | 广告费率 ДРР（%）：广告花费占成交额比例 | `null` |
| `promo_days` | number | 周期内在促销的天数 | `null` |
| `scheme` | string | 履约方式，常见 `FBO` / `FBS` | `null` |
| `image` | string | 主图 URL（Ozon CDN，可能失效） | `null` |
| `url` | string | 商品页链接 | `null` |

## 三条口径纪律

**1. `null` ≠ 0**

字段是 `null`，意思是**这个值没取到**，不是「等于零」。
把 `null` 当 0 去算平均，会把整体拉低；正确做法是跳过它、并把它计入样本量。

**2. 评价数 ≠ 销量**

两者差一到两个数量级。`reviews` 是历史累计的评价条数，`sales` 是本周期的销量。
拿评价数当销量去估市场规模，会错得离谱。

**3. `growth_pct` 是动态，不是绝对值**

负增长不代表这个品卖不动——可能是去年同期基数太高。看增长要配着 `sales` 的绝对值看。

## 用中文键是什么

原始内部数据是中文键（`销量`/`GMV₽`/`ДРР%`），公开数据统一改成英文键。
对照见仓库根目录 `PROTOCOL.md` 的表格，或者直接看 `ozondata/client.py` 里的 `MAP`（如果还在的话）。

## 版本历史

| schema | 变更 |
|---|---|
| v1 | 初版。 |
