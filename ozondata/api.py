# -*- coding: utf-8 -*-
"""ozon-market-data HTTP 客户端 —— 只用标准库，一个文件就能读明白。

和 `client.py`（读本地 JSON）的关系：**同一份数据，两种拿法**。
探索阶段打接口，要全量就 `clone` 仓库读文件，字段一模一样（schema `ozon-market-data/v1`）。

三条口径决定了这个库的形状（详见 PROTOCOL.md）：

1. **`null` ≠ 0。** 字段没取到就是 `None`，不是 `0`。
   `item.gmv is None` 是「这个数我们没抓到」，`gmv == 0` 才是「真的一件没卖」。

2. **每个响应都带 `updated_at`。** 三十天前的榜和昨天的榜不能平起平坐。

3. **服务不可用就是不可用。** 数据没就绪抛 `NotReady`，不返回空列表
   —— 空列表会被读成「这个类目没有商品」。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "Client", "Item", "CategoryStats", "LibraryStats",
    "MarketError", "BadRequest", "NotFound", "RateLimited", "NotReady", "ServerError",
    "DEFAULT_BASE", "SORTABLE",
]

DEFAULT_BASE = "https://yunlinghanyin.cn"
USER_AGENT = "ozondata-python/0.1"
SORTABLE = ("gmv", "sales", "growth_pct", "reviews", "rating", "conv_pct", "drr_pct")
MAX_N = 200


# ── 异常 ────────────────────────────────────────────────────────────────

class MarketError(Exception):
    """所有异常的基类。`status` 是 HTTP 状态码；网络层失败时为 None。"""
    status: Optional[int] = None

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class BadRequest(MarketError):
    """400：参数不合法（比如 by 传了不认识的指标）。"""


class NotFound(MarketError):
    """404：没有这个类目 / SKU —— **不是零，是没抓**。"""


class RateLimited(MarketError):
    """429：超过每分钟 60 次。"""


class NotReady(MarketError):
    """503：服务端数据文件还没就绪。"""


class ServerError(MarketError):
    """5xx 或返回结构异常。"""


_STATUS = {400: BadRequest, 404: NotFound, 429: RateLimited, 503: NotReady}


# ── 数据对象 ────────────────────────────────────────────────────────────

@dataclass
class Item:
    sku: str
    name: str = ""
    brand: str = ""
    category_id: str = ""
    gmv: Optional[float] = None
    sales: Optional[float] = None
    growth_pct: Optional[float] = None
    price_avg: Optional[float] = None
    price_min: Optional[float] = None
    rank_bin: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[float] = None
    conv_pct: Optional[float] = None
    drr_pct: Optional[float] = None
    promo_days: Optional[float] = None
    scheme: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Item":
        keys = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in keys})

    @property
    def has_sales(self) -> bool:
        """有没有销量数据。False 不代表卖不动，只代表这一类目没拿到销量。"""
        return self.sales is not None


@dataclass
class CategoryStats:
    category: str
    n: int
    gmv_total: Optional[float] = None
    sales_total: Optional[int] = None
    price_median: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    drr_median: Optional[float] = None
    growth_median: Optional[float] = None
    concentration: Optional[float] = None
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class LibraryStats:
    schema: Optional[str]
    updated_at: Optional[str]
    period: Optional[str]
    categories: int
    items: int
    category_list: List[Dict[str, str]] = field(default_factory=list)


# ── 客户端 ──────────────────────────────────────────────────────────────

class Client:
    """市场数据接口的客户端。

        from ozondata.api import Client
        c = Client()
        c.stats()                              # 库状态
        c.top("93443", n=10, by="sales")       # 腮红销量前十
        c.stats_by_category("93443")           # GMV / 价格带 / ДРР 中位
    """

    def __init__(self, base: str = DEFAULT_BASE, timeout: float = 20.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    # -- 底层 ----------------------------------------------------------
    def _get(self, path: str, **params) -> Dict[str, Any]:
        q = {k: v for k, v in params.items() if v is not None}
        url = self.base + path + (("?" + urllib.parse.urlencode(q)) if q else "")
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = json.loads(e.read().decode("utf-8")).get("detail") or ""
            except Exception:
                pass
            cls = _STATUS.get(e.code, ServerError)
            raise cls("HTTP %d%s" % (e.code, ("：" + body) if body else ""), e.code)
        except urllib.error.URLError as e:
            raise MarketError("连不上 %s（%s）" % (self.base, e.reason))
        except json.JSONDecodeError as e:
            raise ServerError("返回不是 JSON：%s" % e)

    # -- 接口 ----------------------------------------------------------
    def stats(self) -> LibraryStats:
        d = self._get("/api/market/stats")
        return LibraryStats(schema=d.get("schema"), updated_at=d.get("updated_at"),
                            period=d.get("period"), categories=d.get("categories", 0),
                            items=d.get("items", 0),
                            category_list=d.get("category_list") or [])

    def categories(self) -> List[Dict[str, Any]]:
        return self._get("/api/market/categories").get("categories") or []

    def top(self, category: Optional[str] = None, n: int = 20,
            by: str = "gmv") -> List[Item]:
        """按某个指标取前 n。`by` 只认 SORTABLE 里那几个。"""
        if by not in SORTABLE:
            raise ValueError("by 只认 %s，收到 %r" % ("/".join(SORTABLE), by))
        d = self._get("/api/market/top", category=category, n=min(max(1, n), MAX_N), by=by)
        return [Item.from_dict(x) for x in (d.get("items") or [])]

    def stats_by_category(self, category: str) -> CategoryStats:
        d = self._get("/api/market/stats_by_category", category=category)
        return CategoryStats(
            category=str(d.get("category")), n=d.get("n", 0),
            gmv_total=d.get("gmv_total"), sales_total=d.get("sales_total"),
            price_median=d.get("price_median"), price_min=d.get("price_min"),
            price_max=d.get("price_max"), drr_median=d.get("drr_median"),
            growth_median=d.get("growth_median"), concentration=d.get("concentration"),
            updated_at=d.get("updated_at"), raw=d)

    def item(self, sku: str) -> Item:
        """单个商品。没有这个 SKU 抛 NotFound（不是返回 None）。"""
        return Item.from_dict(self._get("/api/market/item", sku=sku).get("item") or {})
