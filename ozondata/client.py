# -*- coding: utf-8 -*-
"""ozon-market-data 的读取端 —— 零依赖，只读本地 JSON。

设计原则（和本项目的其他库一致）：
  · 缺字段就回 None / 空，不兜 0（"没抓到"和"是零"是两件事）
  · 排序必须显式给 by；默认按 GMV，不按评分/评价数——那两个跟销量差了数量级
  · 任何统计都返回样本量 n，让你自己判断这个结论可不可用

用法：
    from ozondata import Library
    lib = Library()                    # 默认读仓库里的 data/latest.json
    lib.categories()                   # 有哪些类目、各多少条
    lib.top("93443", n=10, by="sales") # 该类目销量前十
    lib.search("румяна")               # 按标题模糊搜
    lib.stats("93443")                 # 聚合：GMV 总量/价格中位/ДРР 均值
"""
import json
import os
import statistics

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "latest.json")

BUILTIN = "__builtin__"          # Python 2 时代的老写法，保留提示用


class Library:
    def __init__(self, path=None):
        self.path = path or DEFAULT_PATH
        if not os.path.isfile(self.path):
            raise FileNotFoundError(
                "找不到数据文件 %s —— 仓库里的 data/ 没了，或者你 clone 的是个空壳。" % self.path)
        with open(self.path, encoding="utf-8") as f:
            self.raw = json.load(f)
        self.schema = self.raw.get("schema") or "unknown"
        self.updated_at = self.raw.get("updated_at")
        self._items = self.raw.get("items") or []
        self._cats = self.raw.get("categories") or []

    # ---------------------------------------------------------------- 元信息

    def categories(self):
        """[{id, name, count, gmv_total}] —— 按条数降序。"""
        out = []
        for c in self._cats:
            cid = str(c.get("id"))
            rows = [x for x in self._items if str(x.get("category_id")) == cid]
            out.append({
                "id": cid,
                "name": c.get("name") or "",
                "count": len(rows),
                "gmv_total": _sum(rows, "gmv"),
            })
        out.sort(key=lambda x: x["count"], reverse=True)
        return out

    # ---------------------------------------------------------------- 查询

    def items(self, category=None):
        if category is None:
            return list(self._items)
        cid = str(category)
        return [x for x in self._items if str(x.get("category_id")) == cid]

    def top(self, category=None, n=10, by="gmv"):
        """按某个指标取前 n。by 只认 gmv / sales / growth_pct / reviews / rating。

        ⚠️ 按 rating 或 reviews 排会冒出「只有几十条评价但 5.0 分」的噪声。
           要按口碑排，请自己加 n 的上限并看样本量。
        """
        if by not in ("gmv", "sales", "growth_pct", "reviews", "rating", "conv_pct", "drr_pct"):
            raise ValueError("by 只认 gmv/sales/growth_pct/reviews/rating/conv_pct/drr_pct，收到 %r" % by)
        rows = [x for x in self.items(category) if x.get(by) is not None]
        rows.sort(key=lambda x: x[by], reverse=True)
        return rows[:max(1, int(n))]

    def search(self, text, category=None):
        """标题模糊匹配（大小写不敏感）。空文本返回空列表，不返回全部。"""
        t = (text or "").strip().lower()
        if not t:
            return []
        return [x for x in self.items(category) if t in (x.get("name") or "").lower()]

    # ---------------------------------------------------------------- 聚合

    def stats(self, category=None):
        rows = self.items(category)
        if not rows:
            return {"n": 0}
        prices = [x["price_avg"] for x in rows if x.get("price_avg") is not None]
        drr = [x["drr_pct"] for x in rows if x.get("drr_pct") is not None]
        growth = [x["growth_pct"] for x in rows if x.get("growth_pct") is not None]
        gmv = [x["gmv"] for x in rows if x.get("gmv") is not None]
        sales = [x["sales"] for x in rows if x.get("sales") is not None]
        return {
            "n": len(rows),
            "gmv_total": round(sum(gmv), 2) if gmv else None,
            "sales_total": int(sum(sales)) if sales else None,
            "price_median": round(statistics.median(prices), 2) if prices else None,
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "drr_median": round(statistics.median(drr), 2) if drr else None,
            "growth_median": round(statistics.median(growth), 2) if growth else None,
            "concentration": _concentration(gmv),
        }


def _sum(rows, key):
    vals = [x[key] for x in rows if x.get(key) is not None]
    return round(sum(vals), 2) if vals else None


def _concentration(gmv):
    """前三名 GMV 占比 —— 越高说明类目越被头部锁死，新玩家越难进。"""
    vals = sorted([v for v in gmv if v], reverse=True)
    if not vals:
        return None
    return round(sum(vals[:3]) / sum(vals) * 100, 1)
