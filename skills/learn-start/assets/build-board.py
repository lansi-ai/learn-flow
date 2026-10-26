#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
learn-flow 学习看板生成器
读 docs/board.yaml，生成单文件离线 HTML 看板 docs/board-html/index.html

用法：
    python scripts/build-board.py            # 生成看板
    python scripts/build-board.py --check    # 只校验，不生成
    python scripts/build-board.py -f a.yaml -o out.html

依赖：PyYAML
设计原则：内容由 Python 生成，JS 只负责视图切换与筛选（JS 挂了也不白屏）。
"""

import argparse
import html
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("缺少依赖：pip install pyyaml")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STATUS_LABEL = {"todo": "待开始", "doing": "进行中", "blocked": "阻塞", "done": "已完成"}
STATUS_ORDER = ["todo", "doing", "blocked", "done"]
TYPE_LABEL = {"学": "输入", "练": "练习", "产": "产出", "复": "复习"}
MASTERY_LABEL = {0: "未接触", 1: "能认", 2: "能复述", 3: "能独立做", 4: "能教别人"}


def dstr(v):
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def esc(v):
    return html.escape(dstr(v))


# ---------------------------------------------------------------- 数据加载与校验

def load(path):
    if not path.exists():
        sys.exit(f"找不到 {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        sys.exit("board.yaml 顶层必须是映射（key: value）")
    return data


def iter_tasks(data):
    for d in data.get("domains") or []:
        for u in d.get("units") or []:
            for t in u.get("tasks") or []:
                yield d, u, t


def validate(data):
    warns = []
    seen_ids = {}
    for d, u, t in iter_tasks(data):
        tid = dstr(t.get("id"))
        title = dstr(t.get("title"))
        status = dstr(t.get("status")) or "todo"
        if not tid:
            warns.append(f"任务缺 id：{title or '(无标题)'}")
        elif tid in seen_ids:
            warns.append(f"任务 id 重复：{tid}")
        else:
            seen_ids[tid] = t
        if not title:
            warns.append(f"任务 {tid} 缺 title")
        if status not in STATUS_LABEL:
            warns.append(f"任务 {tid} 的 status 非法：{status}")
        if status == "done" and not dstr(t.get("evidence")).strip():
            warns.append(f"任务 {tid}「{title}」已完成但没有 evidence（完成无证据）")
        if not dstr(t.get("created")).strip():
            warns.append(f"任务 {tid}「{title}」缺 created（趋势统计会失真）")
    if not data.get("domains"):
        warns.append("没有 domains，看板是空的")
    return warns


# ---------------------------------------------------------------- 统计

def collect_stats(data):
    s = {
        "total": 0, "by_status": {k: 0 for k in STATUS_ORDER},
        "by_type": {k: 0 for k in TYPE_LABEL},
        "done_hollow": 0, "overdue": [], "with_data": [],
    }
    today = date.today().isoformat()
    for d, u, t in iter_tasks(data):
        s["total"] += 1
        st = dstr(t.get("status")) or "todo"
        if st in s["by_status"]:
            s["by_status"][st] += 1
        ty = dstr(t.get("type"))
        if ty in s["by_type"]:
            s["by_type"][ty] += 1
        m = t.get("mastery")
        if st == "done" and isinstance(m, int) and m <= 1:
            s["done_hollow"] += 1
        rd = dstr(t.get("review_due"))
        if rd and rd <= today:
            s["overdue"].append((d, u, t))
        if t.get("data"):
            s["with_data"].append((d, u, t))
    s["done_rate"] = round(s["by_status"]["done"] / s["total"] * 100) if s["total"] else 0
    s["study_ratio"] = round(s["by_type"].get("学", 0) / s["total"] * 100) if s["total"] else 0
    return s


def domain_mastery(d):
    vals = [u.get("mastery") for u in (d.get("units") or []) if isinstance(u.get("mastery"), int)]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


# ---------------------------------------------------------------- HTML 片段

def stat_card(label, value, hint="", tone=""):
    return (
        f'<div class="stat {tone}">'
        f'<div class="stat-v">{esc(value)}</div>'
        f'<div class="stat-l">{esc(label)}</div>'
        f'<div class="stat-h">{esc(hint)}</div></div>'
    )


def bar(label, value, maxv, note="", tone="blue"):
    pct = round(value / maxv * 100) if maxv else 0
    return (
        f'<div class="bar-row"><div class="bar-label">{esc(label)}</div>'
        f'<div class="bar-track"><div class="bar-fill {tone}" style="width:{pct}%"></div></div>'
        f'<div class="bar-num">{esc(note or value)}</div></div>'
    )


def task_card(d, u, t):
    st = dstr(t.get("status")) or "todo"
    ty = dstr(t.get("type"))
    m = t.get("mastery")
    hollow = st == "done" and isinstance(m, int) and m <= 1
    badges = [f'<span class="tag t-type">{esc(TYPE_LABEL.get(ty, ty or "—"))}</span>']
    if isinstance(m, int):
        badges.append(f'<span class="tag t-m">掌握 {m}</span>')
    if dstr(t.get("review_due")):
        badges.append(f'<span class="tag t-rev">复习 {esc(dstr(t.get("review_due")))}</span>')
    if dstr(t.get("evidence")):
        badges.append('<span class="tag t-evd">有证据</span>')
    if t.get("data"):
        if isinstance(t["data"], dict):
            pairs = " · ".join(f"{k} {v}" for k, v in t["data"].items())
        else:
            pairs = dstr(t["data"])
        badges.append(f'<span class="tag t-data">{esc(pairs)}</span>')
    dep = t.get("dep") or []
    if dep:
        badges.append(f'<span class="tag t-dep">依赖 {esc(", ".join(dstr(x) for x in dep))}</span>')
    node = ""
    if dstr(t.get("note")):
        node = f'<div class="card-note">{esc(t.get("note"))}</div>'
    return (
        f'<div class="card {"hollow" if hollow else ""}" '
        f'data-domain="{esc(d.get("id"))}" data-status="{esc(st)}" data-type="{esc(ty)}">'
        f'<div class="card-top"><span class="st-dot st-{esc(st)}"></span>'
        f'<span class="card-id">{esc(t.get("id"))}</span></div>'
        f'<div class="card-title">{esc(t.get("title"))}</div>'
        f'<div class="card-path">{esc(d.get("name"))} / {esc(u.get("name"))}</div>'
        f'<div class="card-tags">{"".join(badges)}</div>'
        f'{node}</div>'
    )


def render_overview(data, s):
    out = []
    out.append('<div class="grid4">')
    out.append(stat_card("任务总数", s["total"], f'完成 {s["by_status"]["done"]} 项'))
    out.append(stat_card("完成率", f'{s["done_rate"]}%', "按任务数计"))
    out.append(stat_card("完成但未掌握", s["done_hollow"], "done 且掌握度 ≤1",
                         "warn" if s["done_hollow"] else ""))
    out.append(stat_card("复习到期", len(s["overdue"]), "今天及更早应复习",
                         "danger" if s["overdue"] else ""))
    out.append("</div>")

    if s["study_ratio"] > 50:
        out.append(
            f'<div class="alert">⚠ 输入类任务占比 {s["study_ratio"]}%，已超过一半。'
            f'这是在囤积输入，不是在练能力——把一部分「学」改成「练」或「产」。</div>'
        )

    out.append('<h2>各能力域掌握度</h2><div class="panel">')
    for d in data.get("domains") or []:
        mv = domain_mastery(d)
        units = len(d.get("units") or [])
        note = f"{mv} / 4" if mv is not None else "未评级"
        tone = "blue" if mv is None or mv < 2 else ("green" if mv < 3.5 else "amber")
        out.append(bar(dstr(d.get("name")), mv or 0, 4, note, tone))
    out.append(f'<div class="panel-foot">共 {len(data.get("domains") or [])} 个能力域 · 掌握度取域内单元均值</div></div>')

    out.append('<h2>任务类型分布</h2><div class="panel">')
    for k, cn in TYPE_LABEL.items():
        v = s["by_type"].get(k, 0)
        out.append(bar(cn, v, max(1, s["total"]), str(v), "blue"))
    out.append('<div class="panel-foot">建议比例：学 ≤30% · 练 ≥40% · 产 ≥20% · 复按曲线</div></div>')

    out.append('<h2>今天该复习</h2><div class="panel">')
    if s["overdue"]:
        for d, u, t in s["overdue"]:
            out.append(
                f'<div class="rev-row"><span class="rev-date">{esc(dstr(t.get("review_due")))}</span>'
                f'<span class="rev-title">{esc(t.get("title"))}</span>'
                f'<span class="rev-path">{esc(d.get("name"))} / {esc(u.get("name"))}</span></div>'
            )
    else:
        out.append('<div class="empty">没有到期的复习。注意：新学的单元按 1/3/7/15/30 天排复习才会出现在这里。</div>')
    out.append("</div>")

    if s["with_data"]:
        out.append('<h2>已回填的外部反馈</h2><div class="panel">')
        for d, u, t in s["with_data"]:
            data_v = t["data"]
            txt = " · ".join(f"{k} {v}" for k, v in data_v.items()) if isinstance(data_v, dict) else dstr(data_v)
            out.append(
                f'<div class="rev-row"><span class="rev-date">{esc(dstr(t.get("date")))}</span>'
                f'<span class="rev-title">{esc(t.get("title"))}</span>'
                f'<span class="rev-path">{esc(txt)}</span></div>'
            )
        out.append("</div>")
    return "".join(out)


def render_board(data):
    out = ['<div class="board">']
    for st in STATUS_ORDER:
        cards = [task_card(d, u, t) for d, u, t in iter_tasks(data)
                 if (dstr(t.get("status")) or "todo") == st]
        out.append(
            f'<div class="col"><div class="col-head"><span class="st-dot st-{st}"></span>'
            f'{STATUS_LABEL[st]}<span class="col-count">{len(cards)}</span></div>'
            f'<div class="col-body">{"".join(cards) or "<div class=\'empty\'>暂无</div>"}</div></div>'
        )
    out.append("</div>")
    return "".join(out)


def render_tree(data):
    out = ['<div class="tree">']
    for d in data.get("domains") or []:
        mv = domain_mastery(d)
        mvt = f"掌握度 {mv}" if mv is not None else "未评级"
        out.append(
            f'<details open><summary><span class="tree-d">{esc(d.get("name"))}</span>'
            f'<span class="tree-meta">{esc(d.get("priority") or "")} · {mvt} · '
            f'{len(d.get("units") or [])} 单元</span></summary><div class="tree-body">'
        )
        for u in d.get("units") or []:
            um = u.get("mastery")
            umt = f"掌握 {um}" if isinstance(um, int) else "未评级"
            out.append(
                f'<div class="unit"><div class="unit-head"><span class="unit-name">{esc(u.get("name"))}</span>'
                f'<span class="unit-id">{esc(u.get("id"))}</span><span class="unit-m">{esc(umt)}</span></div>'
            )
            cards = [task_card(d, u, t) for t in (u.get("tasks") or [])]
            out.append('<div class="unit-tasks">' + ("".join(cards) or '<div class="empty">该单元还没有任务</div>') + '</div></div>')
        out.append("</div></details>")
    out.append("</div>")
    return "".join(out)


def render_matrix(data):
    out = ['<table class="mx"><thead><tr><th>能力域</th>']
    for i in range(5):
        out.append(f'<th>{i} {MASTERY_LABEL[i]}</th>')
    out.append('<th>未评级</th></tr></thead><tbody>')
    for d in data.get("domains") or []:
        counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, None: 0}
        for u in d.get("units") or []:
            m = u.get("mastery")
            counts[m if isinstance(m, int) and 0 <= m <= 4 else None] += 1
        out.append(f'<tr><td class="mx-d">{esc(d.get("name"))}</td>')
        for i in range(5):
            v = counts[i]
            cls = "mx-on" if v else "mx-off"
            out.append(f'<td class="{cls}">{v or "·"}</td>')
        out.append(f'<td class="mx-off">{counts[None] or "·"}</td></tr>')
    out.append("</tbody></table>")
    out.append('<div class="panel-foot">单元格 = 处于该掌握度的单元数。整行偏左说明这个域还没真正开始；'
               '整行偏右但 <code>done</code> 很多，检查是不是自评放水。</div>')
    return "".join(out)


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#FAF9F6;color:#2C2C2A;font-size:14px;line-height:1.6;padding:28px 20px 60px}
.wrap{max-width:1180px;margin:0 auto}
header h1{font-size:22px;font-weight:600;letter-spacing:-.2px}
.goal{color:#5F5E5A;font-size:14px;margin-top:6px}
.meta{color:#888780;font-size:12px;margin-top:4px}
.alert{margin:16px 0;padding:12px 14px;background:#FAEEDA;border-left:3px solid #854F0B;color:#633806;border-radius:4px;font-size:13px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0 8px}
.stat{background:#FFF;border:1px solid #E5E3DC;border-radius:10px;padding:14px 16px}
.stat.warn{border-color:#EF9F27;background:#FFFBF2}
.stat.danger{border-color:#E24B4A;background:#FFF7F7}
.stat-v{font-size:26px;font-weight:600;line-height:1.2}
.stat-l{font-size:13px;color:#2C2C2A;margin-top:2px}
.stat-h{font-size:11px;color:#888780;margin-top:2px}
h2{font-size:15px;font-weight:600;margin:26px 0 10px}
.panel{background:#FFF;border:1px solid #E5E3DC;border-radius:10px;padding:16px}
.panel-foot{font-size:12px;color:#888780;margin-top:12px;padding-top:10px;border-top:1px dashed #E5E3DC}
.bar-row{display:flex;align-items:center;gap:10px;margin:8px 0}
.bar-label{width:120px;font-size:13px;flex:none}
.bar-track{flex:1;height:8px;background:#F1EFE8;border-radius:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px}
.bar-fill.blue{background:#378ADD}
.bar-fill.green{background:#639922}
.bar-fill.amber{background:#BA7517}
.bar-num{width:64px;text-align:right;font-size:12px;color:#5F5E5A;flex:none}
.rev-row{display:flex;gap:12px;align-items:baseline;padding:7px 0;border-bottom:1px solid #F1EFE8;font-size:13px}
.rev-row:last-child{border-bottom:none}
.rev-date{font-size:12px;color:#854F0B;width:88px;flex:none;font-variant-numeric:tabular-nums}
.rev-title{flex:1}
.rev-path{font-size:12px;color:#888780}
.empty{color:#888780;font-size:13px;padding:10px 0}
.tabs{display:flex;gap:4px;margin:22px 0 0;border-bottom:1px solid #E5E3DC}
.tab{background:none;border:none;padding:9px 16px;font-size:14px;color:#5F5E5A;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit}
.tab.active{color:#185FA5;border-bottom-color:#185FA5;font-weight:500}
.filters{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}
.filters select{font-family:inherit;font-size:13px;padding:5px 8px;border:1px solid #D3D1C7;border-radius:6px;background:#FFF;color:#2C2C2A}
section{display:none}section.active{display:block}
.board{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;align-items:start}
.col{background:#F5F4EF;border-radius:10px;padding:10px;min-height:120px}
.col-head{font-size:13px;font-weight:500;display:flex;align-items:center;gap:6px;padding:4px 4px 10px}
.col-count{margin-left:auto;font-size:11px;color:#888780;background:#E5E3DC;border-radius:9px;padding:1px 7px}
.col-body{max-height:70vh;overflow-y:auto;display:flex;flex-direction:column;gap:8px}
.card{background:#FFF;border:1px solid #E5E3DC;border-radius:8px;padding:10px 11px}
.card.hollow{border-left:3px solid #EF9F27}
.card-top{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.card-id{font-size:11px;color:#888780;font-variant-numeric:tabular-nums}
.card-title{font-size:13px;font-weight:500;line-height:1.45}
.card-path{font-size:11px;color:#888780;margin-top:3px}
.card-tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:7px}
.card-note{font-size:11px;color:#5F5E5A;margin-top:6px;padding-top:6px;border-top:1px dashed #E5E3DC}
.tag{font-size:10px;padding:1px 6px;border-radius:3px;background:#F1EFE8;color:#5F5E5A}
.tag.t-m{background:#E6F1FB;color:#185FA5}
.tag.t-evd{background:#EAF3DE;color:#3B6D11}
.tag.t-rev{background:#FAEEDA;color:#854F0B}
.tag.t-data{background:#FBEAF0;color:#993556}
.tag.t-dep{background:#EEEDFE;color:#534AB7}
.st-dot{width:7px;height:7px;border-radius:50%;display:inline-block;flex:none}
.st-todo{background:#B4B2A9}.st-doing{background:#378ADD}
.st-blocked{background:#E24B4A}.st-done{background:#639922}
.tree details{background:#FFF;border:1px solid #E5E3DC;border-radius:10px;margin-bottom:10px;padding:2px 14px}
.tree summary{cursor:pointer;padding:12px 0;display:flex;gap:10px;align-items:baseline}
.tree-d{font-size:15px;font-weight:500}
.tree-meta{font-size:12px;color:#888780}
.tree-body{padding:0 0 12px 8px;border-top:1px dashed #E5E3DC}
.unit{margin-top:12px}
.unit-head{display:flex;gap:10px;align-items:baseline;margin-bottom:6px}
.unit-name{font-size:13px;font-weight:500}
.unit-id{font-size:11px;color:#888780}
.unit-m{font-size:11px;color:#185FA5;margin-left:auto}
.unit-tasks{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px}
.mx{width:100%;border-collapse:collapse;background:#FFF;border:1px solid #E5E3DC;border-radius:10px;overflow:hidden;font-size:13px}
.mx th{background:#F5F4EF;font-weight:500;font-size:12px;padding:9px 8px;text-align:center;border-bottom:1px solid #E5E3DC}
.mx td{padding:8px;text-align:center;border-bottom:1px solid #F1EFE8;font-variant-numeric:tabular-nums}
.mx-d{text-align:left;font-weight:500}
.mx-on{color:#185FA5;font-weight:500;background:#F5FAFF}
.mx-off{color:#C9C7BE}
.warns{margin:16px 0;padding:12px 14px;background:#FFF7F7;border-left:3px solid #A32D2D;border-radius:4px;font-size:12px;color:#791F1F}
.warns ul{margin-left:18px}
"""

JS = """
(function(){
  var tabs=document.querySelectorAll('.tab');
  tabs.forEach(function(t){
    t.addEventListener('click',function(){
      tabs.forEach(function(x){x.classList.remove('active')});
      document.querySelectorAll('section').forEach(function(s){s.classList.remove('active')});
      t.classList.add('active');
      document.getElementById(t.dataset.view).classList.add('active');
    });
  });
  function apply(){
    var d=(document.getElementById('f-domain')||{}).value||'';
    var s=(document.getElementById('f-status')||{}).value||'';
    var ty=(document.getElementById('f-type')||{}).value||'';
    document.querySelectorAll('.card').forEach(function(c){
      var ok=(!d||c.dataset.domain===d)&&(!s||c.dataset.status===s)&&(!ty||c.dataset.type===ty);
      c.style.display=ok?'':'none';
    });
  }
  ['f-domain','f-status','f-type'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.addEventListener('change',apply);
  });
})();
"""


def build_html(data, s, warns, src_path):
    title = dstr(data.get("project")) or "学习看板"
    goal = dstr(data.get("goal"))
    updated = dstr(data.get("updated"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    dom_opts = "".join(f'<option value="{esc(d.get("id"))}">{esc(d.get("name"))}</option>'
                       for d in data.get("domains") or [])
    status_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in STATUS_LABEL.items())
    type_opts = "".join(f'<option value="{k}">{k}（{v}）</option>' for k, v in TYPE_LABEL.items())

    warn_html = ""
    if warns:
        items = "".join(f"<li>{esc(w)}</li>" for w in warns)
        warn_html = f'<div class="warns"><strong>数据校验发现 {len(warns)} 个问题</strong><ul>{items}</ul></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · 学习看板</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<header>
  <h1>{esc(title)}</h1>
  <p class="goal">{esc(goal)}</p>
  <div class="meta">数据更新 {esc(updated)} · 生成于 {now} · 源文件 {esc(str(src_path))}</div>
</header>
{warn_html}
<div class="tabs">
  <button class="tab active" data-view="v-overview">概览</button>
  <button class="tab" data-view="v-board">看板</button>
  <button class="tab" data-view="v-tree">能力树</button>
  <button class="tab" data-view="v-matrix">矩阵</button>
</div>
<div class="filters">
  <select id="f-domain"><option value="">全部能力域</option>{dom_opts}</select>
  <select id="f-status"><option value="">全部状态</option>{status_opts}</select>
  <select id="f-type"><option value="">全部类型</option>{type_opts}</select>
</div>
<main>
  <section id="v-overview" class="active">{render_overview(data, s)}</section>
  <section id="v-board">{render_board(data)}</section>
  <section id="v-tree">{render_tree(data)}</section>
  <section id="v-matrix">{render_matrix(data)}</section>
</main>
</div><script>{JS}</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--file", default=None, help="board.yaml 路径")
    ap.add_argument("-o", "--out", default=None, help="输出 HTML 路径")
    ap.add_argument("--check", action="store_true", help="只校验不生成")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    src = Path(args.file) if args.file else root / "docs" / "board.yaml"
    out = Path(args.out) if args.out else root / "docs" / "board-html" / "index.html"

    data = load(src)
    warns = validate(data)
    s = collect_stats(data)

    print(f"源文件：{src}")
    print(f"任务 {s['total']} 个 · 完成 {s['by_status']['done']} · "
          f"完成率 {s['done_rate']}% · 输入占比 {s['study_ratio']}%")
    if warns:
        print(f"⚠ 校验问题 {len(warns)} 条：")
        for w in warns:
            print("   -", w)
    else:
        print("✓ 校验通过")

    if args.check:
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(data, s, warns, src.name), encoding="utf-8")
    print(f"✓ 看板已生成：{out}")


if __name__ == "__main__":
    main()
