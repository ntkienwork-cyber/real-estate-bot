"""
BDS Dashboard — Flask web server
Phân tích BĐS TP.HCM 3-5 tỷ + hạ tầng tiềm năng (44 dự án)
"""
import json, sys, os
from flask import Flask, render_template_string
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze, AnalysisResult, CREDIT_GROWTH_YOY, MORTGAGE_RATE_CURRENT, MORTGAGE_RATE_TREND, get_macro
from infrastructure import (
    get_infra_score, get_infra_momentum, infra_label as _infra_label,
    INFRA_PROJECTS, Status, InfraType,
)

app = Flask(__name__)

# ── constants ──────────────────────────────────────────────────────
ALL_DISTRICTS = [
    "Quận 1","Quận 3","Quận 4","Quận 5","Quận 6","Quận 7","Quận 8",
    "Quận 10","Quận 11","Quận 12",
    "Bình Thạnh","Gò Vấp","Phú Nhuận","Tân Bình","Tân Phú","Bình Tân",
    "Thủ Đức","Nhà Bè","Hóc Môn","Củ Chi","Bình Chánh","Cần Giờ",
]

_base     = os.path.dirname(__file__)
_scraped  = os.path.join(_base, "data.json")
_sample   = os.path.join(_base, "data_sample.json")
DATA_FILE = _scraped if (os.path.exists(_scraped) and os.path.getsize(_scraped) > 2) else _sample
with open(DATA_FILE, encoding="utf-8") as f:
    PROPS = json.load(f)
RESULTS: list[AnalysisResult] = analyze(PROPS)

# ── helpers ────────────────────────────────────────────────────────
def verdict_color(v):
    return {"BUY": "#22c55e", "HOLD": "#f59e0b", "SKIP": "#ef4444"}.get(v, "#6b7280")

def verdict_bg(v):
    return {"BUY": "#dcfce7", "HOLD": "#fef3c7", "SKIP": "#fee2e2"}.get(v, "#f3f4f6")

def value_badge(v):
    m = {"UNDERVALUED": ("#166534","#bbf7d0"), "OVERVALUED": ("#991b1b","#fee2e2"),
         "FAIR": ("#1e40af","#dbeafe"), "UNKNOWN": ("#374151","#f3f4f6")}
    return m.get(v, ("#374151","#f3f4f6"))

def infra_label(score):
    label, fc, bc = _infra_label(score)
    return label, fc, bc

# ── data helpers ───────────────────────────────────────────────────
def district_summary():
    by_d = defaultdict(list)
    for r in RESULTS:
        by_d[r.property["district"]].append(r)
    rows = []
    for d, res in by_d.items():
        avg_score = sum(r.score for r in res) / len(res)
        ht_sc, _ = get_infra_score(d)
        buy_count = sum(1 for r in res if r.verdict == "BUY")
        rows.append({"district": d, "avg_score": round(avg_score,1),
                     "ht_score": round(ht_sc,1), "buy": buy_count, "total": len(res)})
    rows.sort(key=lambda x: x["avg_score"], reverse=True)
    return rows

def all_districts_infra():
    rows = []
    for d in ALL_DISTRICTS:
        sc, projs = get_infra_score(d)
        label, fc, bc = _infra_label(sc)
        momentum = get_infra_momentum(d)
        macro = get_macro(d)
        rows.append({
            "district": d, "score": round(sc,1),
            "label": label, "fc": fc, "bc": bc,
            "projects": projs, "n": len(projs),
            "momentum": momentum,
            "supply_tightness": macro.get("supply_tightness", 0),
            "absorption_rate": macro.get("absorption_rate", 0),
            "mortgage_growth": macro.get("mortgage_growth_yoy", 0),
        })
    rows.sort(key=lambda x: x["momentum"]["momentum_score"], reverse=True)
    return rows

def active_projects():
    active = [p for p in INFRA_PROJECTS
              if p.status in (Status.UNDER_CONST, Status.APPROVED)]
    return sorted(active, key=lambda x: x.price_impact_pct, reverse=True)

def projects_by_type():
    by_type = defaultdict(list)
    for p in INFRA_PROJECTS:
        by_type[p.infra_type.value].append(p)
    return dict(by_type)

# ── template ───────────────────────────────────────────────────────
TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BDS Analyzer — TP.HCM 3-5 Tỷ</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
  .header{background:linear-gradient(135deg,#1e3a5f,#0f172a);border-bottom:1px solid #1e40af;padding:18px 32px}
  .header h1{font-size:1.5rem;font-weight:700;color:#fff}
  .header p{color:#94a3b8;font-size:.82rem;margin-top:3px}
  .nav{display:flex;gap:4px;padding:0 32px;background:#0f172a;border-bottom:1px solid #1e293b}
  .nav a{padding:10px 18px;font-size:.82rem;color:#64748b;text-decoration:none;border-bottom:2px solid transparent;cursor:pointer}
  .nav a.active,.nav a:hover{color:#93c5fd;border-bottom-color:#3b82f6}
  .page{max-width:1500px;margin:0 auto;padding:20px 32px}
  .tab{display:none}.tab.active{display:block}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:20px}
  .grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-bottom:20px}
  .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}
  .card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:18px}
  .card h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:#64748b;margin-bottom:14px}
  .stat{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px 20px}
  .stat .val{font-size:1.9rem;font-weight:700}
  .stat .lbl{font-size:.72rem;color:#64748b;margin-top:3px}
  table{width:100%;border-collapse:collapse;font-size:.8rem}
  th{background:#0f172a;color:#64748b;font-weight:600;font-size:.7rem;text-transform:uppercase;
     letter-spacing:.05em;padding:9px 11px;text-align:left;border-bottom:1px solid #334155;white-space:nowrap}
  td{padding:9px 11px;border-bottom:1px solid #1e293b;vertical-align:middle}
  tr:hover td{background:#263548}
  .badge{display:inline-block;padding:2px 7px;border-radius:99px;font-size:.68rem;font-weight:700;letter-spacing:.03em;white-space:nowrap}
  .bar-wrap{display:flex;align-items:center;gap:7px}
  .bar-outer{flex:1;height:6px;background:#334155;border-radius:3px;min-width:50px}
  .bar-inner{height:100%;border-radius:3px}
  .bar-num{font-size:.78rem;font-weight:700;min-width:30px;text-align:right}
  .chart-box{position:relative;height:250px}
  .scrollable{overflow-x:auto}
  a.link{color:#93c5fd;text-decoration:none;font-weight:500}
  a.link:hover{text-decoration:underline}
  .sub{font-size:.7rem;color:#64748b;margin-top:2px}
  ul.reasons{list-style:none}
  ul.reasons li{font-size:.7rem;color:#94a3b8;padding:1px 0}
  ul.reasons li::before{content:"• ";color:#475569}
  .sec{font-size:1rem;font-weight:700;color:#f1f5f9;margin:22px 0 14px;padding-bottom:7px;border-bottom:1px solid #334155}
  /* infra cards */
  .proj-card{background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;margin-bottom:8px}
  .proj-header{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
  .proj-name{font-size:.82rem;font-weight:600;color:#e2e8f0;flex:1}
  .proj-impact{font-size:.8rem;font-weight:700;color:#4ade80;white-space:nowrap}
  .proj-meta{font-size:.7rem;color:#64748b;margin-top:5px;display:flex;gap:10px;flex-wrap:wrap}
  .proj-desc{font-size:.7rem;color:#94a3b8;margin-top:5px;line-height:1.5}
  .proj-districts{font-size:.7rem;color:#93c5fd;margin-top:3px}
  /* district infra panel */
  .dist-infra-row{padding:10px 0;border-bottom:1px solid #1e293b}
  .dist-infra-row:last-child{border-bottom:none}
  .dist-infra-header{display:flex;align-items:center;gap:10px;margin-bottom:6px}
  .dist-infra-name{font-size:.88rem;font-weight:700;width:120px}
  .dist-score-bar{flex:1;height:8px;background:#334155;border-radius:4px}
  .dist-score-fill{height:100%;border-radius:4px}
  .dist-score-num{font-size:.8rem;font-weight:700;width:42px;text-align:right}
  .dist-projects{padding-left:130px}
  .proj-tag{display:inline-block;font-size:.66rem;padding:1px 6px;border-radius:4px;
            background:#1e3a5f;color:#93c5fd;border:1px solid #1e40af;margin:2px 2px 0 0}
</style>
</head>
<body>

<div class="header">
  <h1>BDS Analyzer — TP. Hồ Chí Minh</h1>
  <p>Phân tích BĐS 3–5 tỷ VND · {{ results|length }} listings · {{ n_projects }} dự án hạ tầng · 22 quận/huyện</p>
</div>

<div class="nav">
  <a class="active" onclick="showTab('tab-overview',this)">Tổng quan</a>
  <a onclick="showTab('tab-props',this)">Bảng BĐS</a>
  <a onclick="showTab('tab-districts',this)">Phân tích Quận</a>
  <a onclick="showTab('tab-momentum',this)">Macro & Momentum</a>
  <a onclick="showTab('tab-infra',this)">Hạ tầng ({{ n_projects }})</a>
</div>

<div class="page">

<!-- ═══ TAB OVERVIEW ════════════════════════════════════════════ -->
<div id="tab-overview" class="tab active">

  <div class="grid4">
    <div class="stat"><div class="val" style="color:#22c55e">{{ buy_count }}</div><div class="lbl">NÊN MUA (BUY)</div></div>
    <div class="stat"><div class="val" style="color:#f59e0b">{{ hold_count }}</div><div class="lbl">CHỜ THÊM (HOLD)</div></div>
    <div class="stat"><div class="val" style="color:#ef4444">{{ skip_count }}</div><div class="lbl">BỎ QUA (SKIP)</div></div>
    <div class="stat"><div class="val" style="color:#a78bfa">{{ active_count }}</div><div class="lbl">DỰ ÁN ĐANG THI CÔNG</div></div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>Score phân bố theo quận</h2>
      <div class="chart-box"><canvas id="distChart"></canvas></div>
    </div>
    <div class="card">
      <h2>HT Score vs Avg Score (bong bóng = số listings)</h2>
      <div class="chart-box"><canvas id="htChart"></canvas></div>
    </div>
  </div>

  <!-- Infrastructure News Section -->
  <div class="sec">🔨 Dự Án Hạ Tầng Đang Thi Công — Mua Trước Khi Giá Phản Ánh</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;margin-bottom:24px">
  {% for p in under_const_projs %}
  <div style="background:#1e293b;border:1px solid #334155;border-left:3px solid #f59e0b;border-radius:10px;padding:14px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px">
      <div style="font-size:.84rem;font-weight:700;color:#fbbf24;flex:1">{{ p.name }}</div>
      <div style="font-size:.9rem;font-weight:800;color:#4ade80;white-space:nowrap">+{{ p.price_impact_pct }}%</div>
    </div>
    <div style="font-size:.7rem;color:#94a3b8;line-height:1.55;margin-bottom:8px">{{ p.description }}</div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center">
      <span class="badge" style="color:#f59e0b;background:#0f172a;border:1px solid #f59e0b">🔨 Đang thi công</span>
      <span style="font-size:.7rem;color:#64748b">Xong: {{ p.expected_completion }}</span>
      {% if p.investment_billion_vnd %}<span style="font-size:.7rem;color:#fbbf24;font-weight:600">{{ (p.investment_billion_vnd/1000)|round(1) }}k tỷ VND</span>{% endif %}
    </div>
    <div style="font-size:.7rem;color:#93c5fd;margin-top:6px">Quận hưởng lợi: <strong>{{ p.districts_affected | join(' · ') }}</strong></div>
  </div>
  {% endfor %}
  </div>

  <!-- Approved projects (smaller) -->
  <div class="sec">✅ Dự Án Đã Phê Duyệt — Tiềm Năng Trung Hạn</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:24px">
  {% for p in approved_projs %}
  <div style="background:#1e293b;border:1px solid #334155;border-left:3px solid #3b82f6;border-radius:8px;padding:12px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:6px">
      <div style="font-size:.78rem;font-weight:700;color:#93c5fd;flex:1">{{ p.name }}</div>
      <div style="font-size:.8rem;font-weight:700;color:#4ade80;white-space:nowrap">+{{ p.price_impact_pct }}%</div>
    </div>
    <div style="font-size:.68rem;color:#94a3b8;line-height:1.5;margin-bottom:6px">{{ p.description[:160] }}{% if p.description|length > 160 %}…{% endif %}</div>
    <div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center">
      <span class="badge" style="color:#3b82f6;background:#0f172a;border:1px solid #3b82f6">✅ Đã duyệt</span>
      <span style="font-size:.68rem;color:#64748b">{{ p.expected_completion }}</span>
    </div>
    <div style="font-size:.68rem;color:#93c5fd;margin-top:5px">{{ p.districts_affected | join(' · ') }}</div>
  </div>
  {% endfor %}
  </div>

  <!-- Top BUY summary -->
  <div class="sec">Top BUY — nên mua ngay</div>
  <div class="scrollable"><table>
    <thead><tr>
      <th>#</th><th>Tên BĐS</th><th>Giá</th><th>Diện tích</th><th>Giá/m²</th>
      <th>Quận</th><th>Score</th><th>Verdict</th><th>Định giá</th>
      <th>ROI 5 năm</th><th>Hạ tầng</th>
      <th title="Yield = tiền thuê/năm ÷ giá trị · Hạ tầng = dự án đang/sắp xây gần đó">💡 Gợi ý đầu tư</th>
    </tr></thead>
    <tbody>
    {% for r in buy_list %}
    {% set vc=verdict_color(r.verdict) %}{% set vb=verdict_bg(r.verdict) %}
    {% set vfg,vbg=value_badge(r.value_vs_market) %}
    {% set il,ifc,ibc=infra_label(r.infra_score) %}
    <tr>
      <td style="color:#64748b">{{ loop.index }}</td>
      <td><a class="link" href="{{ r.property.get('url','#') }}" target="_blank">{{ r.property.title[:52] }}</a>
        <div class="sub">{{ r.property.property_type.replace('-',' ').title() }}</div></td>
      <td style="font-weight:700;white-space:nowrap">{{ r.property.price_billion }} tỷ</td>
      <td>{{ r.property.area_m2 or '—' }}{% if r.property.area_m2 %}m²{% endif %}</td>
      <td>{{ r.property.price_per_m2_million or '—' }}{% if r.property.price_per_m2_million %}tr{% endif %}</td>
      <td style="font-size:.75rem;white-space:nowrap">{{ r.property.district }}</td>
      <td>
        <div class="bar-wrap">
          <div class="bar-outer"><div class="bar-inner" style="width:{{ r.score }}%;background:{% if r.score>=75 %}#22c55e{% elif r.score>=55 %}#f59e0b{% else %}#ef4444{% endif %}"></div></div>
          <div class="bar-num" style="color:{% if r.score>=75 %}#22c55e{% elif r.score>=55 %}#f59e0b{% else %}#ef4444{% endif %}">{{ r.score }}</div>
        </div>
      </td>
      <td><span class="badge" style="color:{{ vc }};background:{{ vb }}">{{ r.verdict }}</span></td>
      <td><span class="badge" style="color:{{ vfg }};background:{{ vbg }}">{{ r.value_vs_market }}</span></td>
      <td style="font-weight:700;color:{% if r.roi_5yr and r.roi_5yr>=80 %}#4ade80{% elif r.roi_5yr %}#fbbf24{% else %}#64748b{% endif %}">
        {% if r.roi_5yr %}{{ r.roi_5yr }}%{% else %}—{% endif %}</td>
      <td><span class="badge" style="color:{{ ifc }};background:{{ ibc }}">{{ il }}</span>
        <div class="sub">{{ r.infra_score }}/100</div></td>
      <td>
        <span class="badge" style="color:{{ r.invest_color }};background:{{ r.invest_bg }};font-size:.72rem;padding:3px 8px">{{ r.invest_verdict }}</span>
        {% set detail_lines = r.invest_detail.split('\n') %}
        {% for line in detail_lines %}
        <div class="sub" style="margin-top:2px;font-size:.65rem">{{ line }}</div>
        {% endfor %}
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table></div>
</div>

<!-- ═══ TAB PROPS ════════════════════════════════════════════════ -->
<div id="tab-props" class="tab">
  <div class="sec">Tất cả {{ results|length }} BĐS phân tích</div>
  <div class="scrollable"><table>
    <thead><tr>
      <th>#</th><th>Tên BĐS</th><th>Giá</th><th>DT</th><th>Giá/m²</th>
      <th>Quận</th><th>Score</th><th>Định giá</th>
      <th>ROI 5yr</th><th>Yield</th><th>HT Score</th>
      <th title="Yield = tiền thuê/năm ÷ giá · HT = dự án đang/sắp xây gần đó">💡 Gợi ý đầu tư</th>
      <th>Phân tích</th>
    </tr></thead>
    <tbody>
    {% for r in results %}
    {% set vc=verdict_color(r.verdict) %}{% set vb=verdict_bg(r.verdict) %}
    {% set vfg,vbg=value_badge(r.value_vs_market) %}
    {% set il,ifc,ibc=infra_label(r.infra_score) %}
    <tr>
      <td style="color:#64748b;font-size:.72rem">{{ loop.index }}</td>
      <td style="max-width:200px"><a class="link" href="{{ r.property.get('url','#') }}" target="_blank">{{ r.property.title[:48] }}</a>
        <div class="sub">{{ r.property.get('developer','') }} · {{ r.property.get('building_status','') }}</div></td>
      <td style="font-weight:700;white-space:nowrap">{{ r.property.price_billion }}tỷ</td>
      <td>{{ r.property.area_m2 or '—' }}{% if r.property.area_m2 %}m²{% endif %}</td>
      <td>{{ r.property.price_per_m2_million or '—' }}{% if r.property.price_per_m2_million %}tr{% endif %}</td>
      <td style="font-size:.74rem;white-space:nowrap">{{ r.property.district }}</td>
      <td>
        <div class="bar-wrap">
          <div class="bar-outer"><div class="bar-inner" style="width:{{ r.score }}%;background:{% if r.score>=75 %}#22c55e{% elif r.score>=55 %}#f59e0b{% else %}#ef4444{% endif %}"></div></div>
          <div class="bar-num" style="color:{% if r.score>=75 %}#22c55e{% elif r.score>=55 %}#f59e0b{% else %}#ef4444{% endif %}">{{ r.score }}</div>
        </div>
      </td>
      <td><span class="badge" style="color:{{ vfg }};background:{{ vbg }}">{{ r.value_vs_market }}</span></td>
      <td style="font-weight:700;color:{% if r.roi_5yr and r.roi_5yr>=80 %}#4ade80{% elif r.roi_5yr %}#fbbf24{% else %}#64748b{% endif %}">
        {% if r.roi_5yr %}{{ r.roi_5yr }}%{% else %}—{% endif %}</td>
      <td style="color:#94a3b8">{% if r.rental_yield_est %}{{ r.rental_yield_est }}%{% else %}—{% endif %}</td>
      <td><span class="badge" style="color:{{ ifc }};background:{{ ibc }}">{{ il }}</span>
        <div class="sub">{{ r.infra_score }}/100</div></td>
      <td style="min-width:160px">
        <span class="badge" style="color:{{ r.invest_color }};background:{{ r.invest_bg }};font-size:.72rem;padding:3px 8px;display:block;text-align:center;margin-bottom:3px">{{ r.invest_verdict }}</span>
        {% set detail_lines = r.invest_detail.split('\n') %}
        {% for line in detail_lines %}
        <div style="font-size:.62rem;color:#94a3b8;line-height:1.4">{{ line }}</div>
        {% endfor %}
      </td>
      <td><ul class="reasons">{% for reason in r.reasons[:2] %}<li>{{ reason[:50] }}</li>{% endfor %}</ul></td>
    </tr>
    {% endfor %}
    </tbody>
  </table></div>
</div>

<!-- ═══ TAB DISTRICTS ════════════════════════════════════════════ -->
<div id="tab-districts" class="tab">
  <div class="sec">Phân tích 22 Quận/Huyện TP.HCM — Hạ tầng + Thị trường</div>

  <!-- All districts infra panel -->
  <div class="card">
    <h2>Điểm hạ tầng toàn bộ 22 quận/huyện (44 dự án)</h2>
    {% for row in all_districts %}
    {% set label,fc,bc = row.fc, row.fc, row.bc %}
    <div class="dist-infra-row">
      <div class="dist-infra-header">
        <div class="dist-infra-name">{{ row.district }}</div>
        <div class="dist-score-bar">
          <div class="dist-score-fill" style="width:{{ [row.score,100]|min }}%;background:{% if row.score>=40 %}#8b5cf6{% elif row.score>=22 %}#f59e0b{% elif row.score>=10 %}#3b82f6{% else %}#475569{% endif %}"></div>
        </div>
        <div class="dist-score-num" style="color:{{ row.fc }}">{{ row.score }}</div>
        <span class="badge" style="color:{{ row.fc }};background:{{ row.bc }};margin-left:8px">{{ row.label }}</span>
        <span style="font-size:.7rem;color:#64748b;margin-left:6px">{{ row.n }} dự án</span>
      </div>
      {% if row.projects %}
      <div class="dist-projects">
        {% for proj in row.projects[:4] %}
        <span class="proj-tag">{{ proj[:60] }}</span>
        {% endfor %}
        {% if row.projects|length > 4 %}<span class="proj-tag">+{{ row.projects|length - 4 }} more</span>{% endif %}
      </div>
      {% endif %}
    </div>
    {% endfor %}
  </div>

  <!-- District market table (from analysis) -->
  <div class="sec">Quận có BĐS trong danh sách phân tích</div>
  <div class="card scrollable">
    <table>
      <thead><tr>
        <th>Quận</th><th>Avg Score</th><th>HT Score</th><th>HT Rating</th>
        <th>BUY / Tổng</th><th>Nhận xét</th>
      </tr></thead>
      <tbody>
      {% for row in districts %}
      {% set il,ifc,ibc=infra_label(row.ht_score) %}
      <tr>
        <td style="font-weight:700">{{ row.district }}</td>
        <td>
          <div class="bar-wrap">
            <div class="bar-outer"><div class="bar-inner" style="width:{{ row.avg_score }}%;background:#3b82f6"></div></div>
            <div class="bar-num" style="color:#3b82f6">{{ row.avg_score }}</div>
          </div>
        </td>
        <td>
          <div class="bar-wrap">
            <div class="bar-outer"><div class="bar-inner" style="width:{{ [row.ht_score,100]|min }}%;background:#8b5cf6"></div></div>
            <div class="bar-num" style="color:#8b5cf6">{{ row.ht_score }}</div>
          </div>
        </td>
        <td><span class="badge" style="color:{{ ifc }};background:{{ ibc }}">{{ il }}</span></td>
        <td style="font-weight:700;color:{% if row.buy > 0 %}#22c55e{% else %}#64748b{% endif %}">{{ row.buy }}/{{ row.total }}</td>
        <td style="font-size:.72rem;color:#94a3b8">
          {% if row.ht_score >= 40 %}Hạ tầng bùng nổ — mua mạnh
          {% elif row.ht_score >= 22 %}Hạ tầng tiềm năng — ưu tiên cao
          {% elif row.ht_score >= 10 %}Hạ tầng khởi sắc — theo dõi
          {% else %}Hạ tầng ổn định — chú trọng giá{% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<!-- ═══ TAB MACRO & MOMENTUM ════════════════════════════════════ -->
<div id="tab-momentum" class="tab">
  <div class="sec">Macro Context & Infrastructure Momentum</div>

  <!-- Macro Cards -->
  <div class="grid4" style="margin-bottom:20px">
    <div class="stat">
      <div class="val" style="color:#34d399">{{ credit_growth }}%</div>
      <div class="lbl">Credit Growth / năm</div>
      <div class="sub" style="margin-top:4px;font-size:.7rem;color:#6ee7b7">Tín dụng toàn TP.HCM</div>
    </div>
    <div class="stat">
      <div class="val" style="color:#60a5fa">{{ mortgage_rate }}%</div>
      <div class="lbl">Lãi suất vay mua nhà</div>
      <div class="sub" style="margin-top:4px;font-size:.7rem;color:#93c5fd">{{ mortgage_trend_label }} từ 12% (2023)</div>
    </div>
    <div class="stat">
      <div class="val" style="color:#f59e0b">~72%</div>
      <div class="lbl">Absorption Rate TB</div>
      <div class="sub" style="margin-top:4px;font-size:.7rem;color:#fcd34d">Tỷ lệ hấp thụ toàn TP</div>
    </div>
    <div class="stat">
      <div class="val" style="color:#a78bfa">Phục hồi</div>
      <div class="lbl">Giai đoạn thị trường</div>
      <div class="sub" style="margin-top:4px;font-size:.7rem;color:#c4b5fd">Sau điều chỉnh 2022–2023</div>
    </div>
  </div>

  <div class="card" style="margin-bottom:20px;background:#0f2a1a;border-color:#166534">
    <p style="font-size:.82rem;color:#86efac;line-height:1.6">
      💡 <strong style="color:#4ade80">Nhận định macro:</strong>
      Lãi suất giảm + credit growth <strong>{{ credit_growth }}%</strong> + supply tightness cao ở nội thành
      = <strong>cửa sổ mua thuận lợi</strong>. Thời điểm tốt nhất là trước khi các dự án hạ tầng lớn hoàn thành
      (2026–2027). Mua sau khi hoàn thành thường đã phản ánh hết vào giá.
    </p>
  </div>

  <!-- Infrastructure Momentum Table -->
  <div class="card">
    <h2>Infrastructure Momentum — Xếp hạng theo quận</h2>
    <div class="scrollable">
    <table>
      <thead>
        <tr>
          <th>Quận</th>
          <th>Momentum</th>
          <th>Score</th>
          <th>Đang TC</th>
          <th>Pipeline</th>
          <th>Vốn ĐT</th>
          <th>Impact Giá</th>
          <th>Supply Tightness</th>
          <th>Absorption</th>
          <th>Mortgage Growth</th>
          <th>Sắp xong</th>
          <th>Top Dự án</th>
        </tr>
      </thead>
      <tbody>
      {% for row in all_infra %}
      {% set m = row.momentum %}
      {% set ms = m.momentum_score %}
      {% if ms >= 70 %}{% set mc = "#a78bfa" %}{% elif ms >= 50 %}{% set mc = "#f87171" %}
      {% elif ms >= 30 %}{% set mc = "#fbbf24" %}{% else %}{% set mc = "#64748b" %}{% endif %}
        <tr>
          <td><strong>{{ row.district }}</strong></td>
          <td><span class="badge" style="background:{{ mc }}22;color:{{ mc }}">{{ m.momentum_label }}</span></td>
          <td>
            <div class="bar-wrap">
              <div class="bar-outer"><div class="bar-inner" style="width:{{ ms }}%;background:{{ mc }}"></div></div>
              <span class="bar-num" style="color:{{ mc }}">{{ ms }}</span>
            </div>
          </td>
          <td style="text-align:center;font-weight:700;color:#34d399">{{ m.active_count }}</td>
          <td style="text-align:center;color:#94a3b8">{{ m.pipeline_count }}</td>
          <td style="color:#60a5fa">{{ m.total_investment_t | int }}k tỷ</td>
          <td style="color:#f59e0b;font-weight:700">+{{ m.total_price_impact }}%</td>
          <td>
            <div class="bar-wrap">
              {% set ts = row.supply_tightness %}
              {% if ts >= 8 %}{% set tc = "#34d399" %}{% elif ts >= 6.5 %}{% set tc = "#fbbf24" %}{% else %}{% set tc = "#f87171" %}{% endif %}
              <div class="bar-outer"><div class="bar-inner" style="width:{{ ts * 10 }}%;background:{{ tc }}"></div></div>
              <span class="bar-num" style="color:{{ tc }}">{{ ts }}</span>
            </div>
          </td>
          <td style="color:#94a3b8">{{ (row.absorption_rate * 100) | int }}%</td>
          <td style="color:#a78bfa">+{{ row.mortgage_growth }}%</td>
          <td style="color:#64748b;font-size:.75rem">{{ m.nearest_completion or "—" }}</td>
          <td style="font-size:.7rem;color:#64748b;max-width:220px">
            {% for p in m.top_projects[:2] %}
              <div style="margin-bottom:2px">{{ "🔨" if p.status == "Đang thi công" else "✅" }} {{ p.name[:35] }}… (+{{ p.impact_pct }}%)</div>
            {% endfor %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    </div>
  </div>
</div>

<!-- ═══ TAB INFRA ════════════════════════════════════════════════ -->
<div id="tab-infra" class="tab">
  <div class="sec">{{ n_projects }} Dự án Hạ tầng TP.HCM — Đang triển khai & Quy hoạch</div>

  <!-- Stats by status -->
  <div class="grid4" style="margin-bottom:20px">
    {% for st, color in [("Hoàn thành","#22c55e"),("Đang thi công","#f59e0b"),("Đã duyệt","#3b82f6"),("Quy hoạch","#64748b")] %}
    {% set cnt = infra_by_status[st] %}
    <div class="stat">
      <div class="val" style="color:{{ color }}">{{ cnt }}</div>
      <div class="lbl">{{ st.upper() }}</div>
    </div>
    {% endfor %}
  </div>

  <!-- Filter tabs by type -->
  <div class="grid2">

    <!-- Đang thi công -->
    <div class="card">
      <h2>Đang thi công — MUA TRƯỚC KHI GIÁ PHẢN ÁNH</h2>
      <div style="overflow-y:auto;max-height:620px">
      {% for p in active_projs if p.status.value == "Đang thi công" %}
      {% set sc="#22c55e" %}
      <div class="proj-card">
        <div class="proj-header">
          <div class="proj-name">{{ p.name }}</div>
          <div class="proj-impact">+{{ p.price_impact_pct }}%</div>
        </div>
        <div class="proj-meta">
          <span class="badge" style="color:#22c55e;background:#0f172a;border:1px solid #22c55e">Đang thi công</span>
          <span>Xong: {{ p.expected_completion }}</span>
          {% if p.investment_billion_vnd %}<span style="color:#fbbf24">{{ (p.investment_billion_vnd/1000)|round(0)|int }}k tỷ VND</span>{% endif %}
        </div>
        <div class="proj-districts">Quận hưởng lợi: {{ p.districts_affected | join(' · ') }}</div>
        <div class="proj-desc">{{ p.description[:140] }}</div>
      </div>
      {% endfor %}
      </div>
    </div>

    <!-- Đã duyệt -->
    <div class="card">
      <h2>Đã phê duyệt — TIỀM NĂNG TRUNG HẠN</h2>
      <div style="overflow-y:auto;max-height:300px;margin-bottom:16px">
      {% for p in active_projs if p.status.value == "Đã duyệt" %}
      <div class="proj-card">
        <div class="proj-header">
          <div class="proj-name">{{ p.name }}</div>
          <div class="proj-impact">+{{ p.price_impact_pct }}%</div>
        </div>
        <div class="proj-meta">
          <span class="badge" style="color:#3b82f6;background:#0f172a;border:1px solid #3b82f6">Đã duyệt</span>
          <span>Xong: {{ p.expected_completion }}</span>
        </div>
        <div class="proj-districts">Quận: {{ p.districts_affected | join(' · ') }}</div>
        <div class="proj-desc">{{ p.description[:110] }}</div>
      </div>
      {% endfor %}
      </div>

      <h2 style="margin-top:8px">Đã hoàn thành — GIÁ ĐÃ PHẦN NÀO PHẢN ÁNH</h2>
      <div style="overflow-y:auto;max-height:280px">
      {% for p in INFRA_PROJECTS if p.status.value == "Hoàn thành" %}
      <div class="proj-card" style="opacity:.75">
        <div class="proj-header">
          <div class="proj-name">{{ p.name }}</div>
          <div class="proj-impact" style="color:#94a3b8">+{{ p.price_impact_pct }}%</div>
        </div>
        <div class="proj-meta">
          <span class="badge" style="color:#94a3b8;background:#0f172a;border:1px solid #334155">Hoàn thành {{ p.expected_completion }}</span>
        </div>
        <div class="proj-districts">{{ p.districts_affected | join(' · ') }}</div>
      </div>
      {% endfor %}
      </div>
    </div>

  </div>

  <!-- All projects table -->
  <div class="sec">Bảng tổng hợp tất cả dự án</div>
  <div class="scrollable"><table>
    <thead><tr>
      <th>#</th><th>Tên dự án</th><th>Loại</th><th>Trạng thái</th>
      <th>Hoàn thành</th><th>Tác động giá</th><th>Đầu tư</th>
      <th>Quận hưởng lợi</th>
    </tr></thead>
    <tbody>
    {% for p in INFRA_PROJECTS|sort(attribute='price_impact_pct', reverse=True) %}
    {% set st_colors = {"Hoàn thành":"#22c55e","Đang thi công":"#f59e0b","Đã duyệt":"#3b82f6","Quy hoạch":"#64748b"} %}
    {% set sc = st_colors.get(p.status.value, "#64748b") %}
    <tr>
      <td style="color:#64748b;font-size:.7rem">{{ loop.index }}</td>
      <td style="font-size:.78rem;font-weight:600;max-width:240px">{{ p.name }}</td>
      <td style="font-size:.7rem;color:#94a3b8">{{ p.infra_type.value.replace('_',' ').title() }}</td>
      <td><span class="badge" style="color:{{ sc }};background:#0f172a;border:1px solid {{ sc }}">{{ p.status.value }}</span></td>
      <td style="font-size:.75rem;color:#94a3b8">{{ p.expected_completion }}</td>
      <td style="font-weight:700;color:#4ade80">+{{ p.price_impact_pct }}%</td>
      <td style="font-size:.7rem;color:#fbbf24">
        {% if p.investment_billion_vnd %}{{ (p.investment_billion_vnd/1000)|round(1) }}k tỷ{% else %}—{% endif %}
      </td>
      <td style="font-size:.7rem;color:#93c5fd">{{ p.districts_affected | join(', ') }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table></div>
</div>

</div><!-- /page -->

<script>
// tab switching
function showTab(id, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav a').forEach(a => a.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}

// Chart 1: district bar
const dd = {{ dist_chart | tojson }};
new Chart(document.getElementById('distChart'), {
  type: 'bar',
  data: {
    labels: dd.labels,
    datasets: [
      { label: 'Avg Score', data: dd.scores, backgroundColor: dd.scores.map(s => s>=75?'#22c55e':s>=55?'#f59e0b':'#ef4444'), borderRadius:4 },
      { label: 'HT Score', data: dd.ht, backgroundColor:'#8b5cf680', borderRadius:4 },
    ]
  },
  options: {
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ labels:{ color:'#94a3b8', font:{size:11} } } },
    scales:{
      x:{ ticks:{color:'#94a3b8',font:{size:10}}, grid:{color:'#1e293b'} },
      y:{ min:0, max:110, ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'} }
    }
  }
});

// Chart 2: scatter HT vs Avg
const sd = {{ scatter_data | tojson }};
new Chart(document.getElementById('htChart'), {
  type: 'bubble',
  data: { datasets:[{
    label:'Quận',
    data: sd.points,
    backgroundColor:'#818cf880',
    borderColor:'#818cf8',
  }]},
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{
      legend:{display:false},
      tooltip:{callbacks:{label: ctx => `${sd.labels[ctx.dataIndex]}: Score ${ctx.parsed.y}, HT ${ctx.parsed.x}`}}
    },
    scales:{
      x:{ title:{display:true,text:'HT Score',color:'#64748b'}, ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'}, min:0, max:50 },
      y:{ title:{display:true,text:'Avg Score',color:'#64748b'}, ticks:{color:'#94a3b8'}, grid:{color:'#1e293b'}, min:0, max:110 }
    }
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    buy_list  = [r for r in RESULTS if r.verdict == "BUY"]
    hold_list = [r for r in RESULTS if r.verdict == "HOLD"]
    skip_list = [r for r in RESULTS if r.verdict == "SKIP"]

    districts  = district_summary()
    all_dists  = all_districts_infra()
    active_projs = active_projects()

    # chart data
    dist_chart = {
        "labels": [d["district"] for d in districts],
        "scores": [d["avg_score"] for d in districts],
        "ht":     [d["ht_score"] for d in districts],
    }
    scatter_data = {
        "labels": [d["district"] for d in districts],
        "points": [{"x": d["ht_score"], "y": d["avg_score"],
                    "r": max(6, d["total"] * 6)} for d in districts],
    }

    under_const_projs = sorted(
        [p for p in INFRA_PROJECTS if p.status == Status.UNDER_CONST],
        key=lambda x: x.price_impact_pct, reverse=True
    )
    approved_projs = sorted(
        [p for p in INFRA_PROJECTS if p.status == Status.APPROVED],
        key=lambda x: x.price_impact_pct, reverse=True
    )

    infra_by_status = {
        "Hoàn thành":     sum(1 for p in INFRA_PROJECTS if p.status == Status.COMPLETED),
        "Đang thi công":  sum(1 for p in INFRA_PROJECTS if p.status == Status.UNDER_CONST),
        "Đã duyệt":       sum(1 for p in INFRA_PROJECTS if p.status == Status.APPROVED),
        "Quy hoạch":      sum(1 for p in INFRA_PROJECTS if p.status == Status.PLANNING),
    }

    return render_template_string(
        TEMPLATE,
        results=RESULTS,
        buy_list=buy_list,
        buy_count=len(buy_list),
        hold_count=len(hold_list),
        skip_count=len(skip_list),
        active_count=infra_by_status["Đang thi công"],
        under_const_projs=under_const_projs,
        approved_projs=approved_projs,
        districts=districts,
        all_districts=all_dists,
        all_infra=all_districts_infra(),
        active_projs=active_projs,
        n_projects=len(INFRA_PROJECTS),
        INFRA_PROJECTS=INFRA_PROJECTS,
        infra_by_status=infra_by_status,
        dist_chart=dist_chart,
        scatter_data=scatter_data,
        verdict_color=verdict_color,
        verdict_bg=verdict_bg,
        value_badge=value_badge,
        infra_label=infra_label,
        Status=Status,
        credit_growth=CREDIT_GROWTH_YOY,
        mortgage_rate=MORTGAGE_RATE_CURRENT,
        mortgage_trend_label="Giảm" if MORTGAGE_RATE_TREND == "decreasing" else "Ổn định",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"BDS Dashboard → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
