# -*- coding: utf-8 -*-
"""命令行看一眼数据。零依赖。

    python -m ozondata.cli cats
    python -m ozondata.cli top 93443 --n 10 --by sales
    python -m ozondata.cli stats 93443
    python -m ozondata.cli search румяна
"""
import argparse
import json
import sys

from .client import Library


def _fmt(v, unit=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        v = round(v, 2)
    return ("{:,}".format(v) if isinstance(v, (int,)) else str(v)) + unit


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ozondata")
    ap.add_argument("--path", help="数据文件路径（默认仓库里的 data/latest.json）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("cats")
    t = sub.add_parser("top"); t.add_argument("category"); t.add_argument("--n", type=int, default=10)
    t.add_argument("--by", default="gmv")
    s = sub.add_parser("stats"); s.add_argument("category", nargs="?")
    f = sub.add_parser("search"); f.add_argument("text")

    a = ap.parse_args(argv)
    lib = Library(a.path)
    print("数据更新于 %s · schema %s" % (lib.updated_at or "未知", lib.schema))

    if a.cmd == "cats":
        print("%-10s %-14s %6s %14s" % ("类目ID", "名称", "条数", "GMV 合计₽"))
        for c in lib.categories():
            print("%-10s %-14s %6d %14s" % (c["id"], c["name"], c["count"], _fmt(c["gmv_total"])))
    elif a.cmd == "top":
        rows = lib.top(a.category, a.n, a.by)
        print("%-12s %-30s %8s %12s %8s %8s" % ("SKU", "名称", "销量", "GMV₽", "增长%", "ДРР%"))
        for r in rows:
            print("%-12s %-30s %8s %12s %8s %8s" % (
                r.get("sku", ""), (r.get("name") or "")[:28], _fmt(r.get("sales")),
                _fmt(r.get("gmv")), _fmt(r.get("growth_pct")), _fmt(r.get("drr_pct"))))
    elif a.cmd == "stats":
        print(json.dumps(lib.stats(a.category), ensure_ascii=False, indent=2))
    elif a.cmd == "search":
        rows = lib.search(a.text)
        print("命中 %d 条" % len(rows))
        for r in rows[:20]:
            print("  %-12s %-36s %s" % (r.get("sku", ""), (r.get("name") or "")[:34], _fmt(r.get("gmv"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
