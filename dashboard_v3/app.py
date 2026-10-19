"""보안 관제 현황 — 한 화면 대시보드 (dashboard_v3).

실행 (저장소 최상위에서):
    .venv/Scripts/python.exe -m streamlit run dashboard_v3/app.py
"""
import base64
import time
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import data

st.set_page_config(page_title="보안 관제 현황", layout="wide", initial_sidebar_state="collapsed")


@st.cache_data
def load():
    return data.load()


D = load()
LOGO = "data:image/png;base64," + base64.b64encode(
    (Path(__file__).parent / "assets" / "sesac_security_logo.png").read_bytes()).decode()
DAYS = D["days"]

RED, AMBER, BLUE, NAVY, NAVY2 = "#FF4B4B", "#F5B740", "#67BAF4", "#1E466B", "#2C5F8E"
MUTE, DIM, GRAY = "#A0A7B1", "#636A74", "#3A3F47"
LOGC = {"Sysmon": "#67BAF4", "NGINX": "#2C7BB8", "SSHD": "#1E466B", "Audit": "#A9D6F8"}
TAC = {"Initial Access": "초기 침투", "Reconnaissance": "정찰", "Execution": "실행", "Persistence": "지속",
       "Command and Control": "원격 제어", "Credential Access": "계정 정보 접근", "Collection": "수집",
       "Exfiltration": "유출", "Defense Evasion": "탐지 회피", "Discovery": "탐색",
       "Lateral Movement": "내부 이동", "Impact": "파괴·변경"}
SES_TYPE = {"web_only": "웹", "server_only": "서버", "server+web": "서버+웹"}
ROLE = {"application": "앱", "bastion": "접속 관문", "operations": "운영", "web": "웹"}
SEV = {r["id"]: r["sev"] for r in D["rules"]}
NAME = {r["id"]: r["name"] for r in D["rules"]}

CSS = """
<style>
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],footer{display:none!important}
.block-container,[data-testid="stMainBlockContainer"]{padding:8px 14px 6px!important;max-width:100%!important}
[data-testid="stVerticalBlock"]{gap:10px}
[data-testid="stHorizontalBlock"]{gap:10px!important}
.stApp{font-variant-numeric:tabular-nums}
[data-testid="stHtml"]{line-height:1.35}
[data-testid="stElementContainer"],[data-testid="stHtml"]{overflow:visible!important}

/* 패널 */
[class*="st-key-pn_"]{background:#141519;border:1px solid #272A31;border-radius:6px;padding:9px 12px 10px;gap:6px!important}
.st-key-row2 [data-testid="stColumn"]>div,.st-key-row3 [data-testid="stColumn"]>div{height:100%}
.st-key-row2 [class*="st-key-pn_"],.st-key-row3 [class*="st-key-pn_"]{flex:1 1 auto}
.ph{display:flex;align-items:center;gap:7px;min-height:22px}
.ph h2{font-size:13px;margin:0;padding:0;font-weight:700;color:#FAFAFA;line-height:1.3}
.ph h2 .n{margin-left:5px;font-weight:800}
.ph .tools{margin-left:auto;display:flex;gap:10px;align-items:center;color:#636A74;font-size:11.5px}
.red{color:#FF4B4B}.amber{color:#F5B740}.blue{color:#67BAF4}.mu{color:#A0A7B1}.dim{color:#636A74}
.mono{font-family:Consolas,"D2Coding",monospace;font-size:12px}

/* 물음표·말풍선 */
.q{position:relative;width:15px;height:15px;border-radius:50%;border:1px solid #33373F;color:#636A74;font-size:10px;font-weight:700;display:inline-grid;place-items:center;cursor:help;flex:none;line-height:1}
.q:hover{color:#FAFAFA;border-color:#A0A7B1}
.q:hover::after,.tt:hover::after{content:attr(data-tip);position:absolute;z-index:1000;white-space:pre-line;width:max-content;max-width:260px;background:#22252B;border:1px solid #33373F;border-radius:5px;padding:7px 9px;font-size:12px;font-weight:400;color:#FAFAFA;line-height:1.5;text-align:left;box-shadow:0 6px 18px rgba(0,0,0,.55);pointer-events:none;letter-spacing:0}
.q:hover::after{left:-6px;top:20px}
.q.r:hover::after{left:auto;right:-6px}
.tt{position:relative;cursor:default}
.tt:hover::after{left:40px;top:100%}

/* 진입 효과 */
@keyframes fin{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
@keyframes grow{from{width:0}}
@keyframes up{from{transform:scaleY(0)}}
@keyframes sh{from{background-position:100% 0}to{background-position:-200% 0}}
.fx{animation:fin .4s ease-out both}
.sk{display:flex;flex-direction:column;gap:9px;padding:4px 0}
.sk i{display:block;height:11px;border-radius:2px;background:linear-gradient(90deg,#1C1E23 0%,#2A2D34 40%,#1C1E23 80%);background-size:300% 100%;animation:sh 1.1s linear infinite}
.sk i:first-child{width:34%;height:13px}.sk i:nth-child(3n){width:72%}.sk i:nth-child(4n){width:48%}.sk i:nth-child(5n){width:86%}
.pbar{height:2px;background:#67BAF4;transition:width .2s;margin:-10px -14px 8px}

/* 상단 */
.top{display:flex;align-items:center;gap:14px;border-bottom:1px solid #272A31;padding:2px 0 9px}
.logo{display:flex;align-items:center}
.logo img{height:30px;width:auto;display:block}
.top h1{font-size:16px;margin:0 0 0 4px;padding:0;font-weight:700}
.top .meta{margin-left:auto;display:flex;gap:16px;align-items:center;color:#A0A7B1;font-size:12.5px}
.top .meta b{color:#FAFAFA;font-weight:600}
.st-key-reload button{min-height:30px;padding:2px 10px;background:#1B1D22;border-color:#33373F;color:#A0A7B1;margin-top:1px}

/* 요약 */
.kpis{display:grid;grid-template-columns:1.25fr 1.1fr 1fr 1fr 1fr .9fr;gap:10px}
.kpi{background:#141519;border:1px solid #272A31;border-radius:6px;padding:9px 12px 8px;position:relative;display:flex;flex-direction:column;gap:2px;height:90px}
.kpi .lb{display:flex;align-items:center;gap:6px;color:#A0A7B1;font-size:12px}
.kpi .mid{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;flex:1}
.kpi .v{font-size:30px;font-weight:800;line-height:1;white-space:nowrap}
.kpi .v small{font-size:13px;font-weight:600;color:#A0A7B1;margin-left:3px}
.kpi .sub{color:#A0A7B1;font-size:12px;white-space:nowrap}
.kpi .sub b{color:#FAFAFA;font-weight:600}
.kpi .sp{display:flex;align-items:flex-end;gap:1.5px;height:28px;width:96px;flex:none;margin-bottom:2px}
.kpi .sp i{flex:1;background:#25282E;transform-origin:bottom;animation:up .6s cubic-bezier(.2,.7,.2,1) both}
.kpi.crit{border-color:rgba(255,75,75,.55);background:#1C1415}
.kpi.crit::before{content:"";position:absolute;left:-1px;top:-1px;bottom:-1px;width:3px;background:#FF4B4B;border-radius:6px 0 0 6px}
.kpi.crit .v{color:#FF4B4B;font-size:34px}
.kpi.warn{border-color:rgba(245,183,64,.42)}.kpi.warn .v{color:#F5B740}
.kpi.info .v{color:#67BAF4}
.kpi.ref .v{color:#A0A7B1;font-weight:700}

/* 표 */
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{font-size:11.5px;font-weight:600;color:#636A74;text-align:left;padding:5px 6px;border-bottom:1px solid #272A31;white-space:nowrap;background:none}
.tbl td{padding:4px 6px;border-bottom:1px solid #1E2025;white-space:nowrap;color:#FAFAFA;background:none}
.tbl tr.sel td{background:rgba(103,186,244,.07)}
.tbl tr.sel td:first-child{box-shadow:inset 2px 0 #67BAF4}
.tbl .user{font-weight:700}
.sc{display:flex;align-items:center;gap:8px}
.sc b{color:#FF4B4B;font-weight:800;font-size:14px;width:30px;text-align:right}
.track{height:6px;background:#22252B;border-radius:1px;flex:1;min-width:50px;position:relative}
.fill{height:100%;border-radius:1px;animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.track .th{position:absolute;top:-3px;bottom:-3px;width:1px;background:#A0A7B1;opacity:.7}
.dots{display:inline-flex;gap:2px;vertical-align:middle;margin-left:5px}
.dots i{width:5px;height:9px;background:#2A2D33}.dots i.on{background:#FF4B4B}
.tag{display:inline-block;padding:0 6px;border-radius:3px;font-size:11px;font-weight:700;line-height:17px}
.t-red{background:rgba(255,75,75,.15);color:#FF4B4B}.t-amber{background:rgba(245,183,64,.13);color:#F5B740}
.t-blue{background:rgba(103,186,244,.13);color:#67BAF4}.t-gray{background:#23262C;color:#A0A7B1}
.chip{font-family:Consolas,monospace;font-size:10.5px;padding:1px 5px;border-radius:2px;background:#24272D;color:#A0A7B1}
.chip.h{background:rgba(255,75,75,.14);color:#FF8A8A}

/* 경보 선택 */
.st-key-sel_alert [data-testid="stWidgetLabel"]{display:none}
.st-key-sel_alert button{min-height:28px;padding:2px 10px;font-size:12px}
.detail{display:grid;grid-template-columns:1.25fr 1fr;gap:16px}
.dh{grid-column:1/3;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.dh .id{color:#A0A7B1}.dh .who{font-size:15px;font-weight:800}.dh .pt{font-size:15px;font-weight:800;color:#FF4B4B}
.chain{display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-left:auto}
.chain span{background:#1F2228;border:1px solid #33373F;padding:3px 7px;border-radius:3px;font-weight:600;font-size:12px}
.chain em{color:#636A74;font-style:normal;font-size:11px}
.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 12px;align-content:start;padding-top:2px}
.fact{display:flex;gap:7px;align-items:baseline;min-width:0}
.fact .k{color:#636A74;font-size:11.5px;flex:none;width:54px}
.fact .v{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fact .v.hot{color:#FF4B4B}.fact .v.warm{color:#F5B740}
.sigs .cap{display:flex;justify-content:space-between;color:#636A74;font-size:11.5px;margin-bottom:3px}
.sigs .cap span{display:inline-flex;align-items:center;gap:5px}
.sigs .s{display:grid;grid-template-columns:30px 1fr 20px 64px 28px;gap:7px;align-items:center;padding:2px 0}
.sigs .x{color:#A0A7B1;font-size:11px;text-align:right}
.sigs .i{font-family:Consolas,monospace;font-size:11px;color:#A0A7B1}
.sigs .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sigs .pv{text-align:right;font-weight:700}
.sigs .more{color:#636A74;font-size:11.5px;padding-top:2px}
.evs td{font-size:12px;padding:4px 6px;vertical-align:top}
.evs .cmd{font-family:Consolas,monospace;font-size:11.5px;white-space:normal;word-break:break-all;color:#D8DCE1}

/* 토글 */
[data-testid="stCheckbox"] label p,[class*="st-key-tg_"] label p{font-size:12.5px;color:#A0A7B1}

/* 사용자 */
.ubar{display:grid;grid-template-columns:70px 1fr 38px;gap:9px;align-items:center;padding:2.5px 0}
.ubar .nm{font-weight:600}.ubar .nm.zero{color:#636A74;font-weight:500}
.ubar .val{text-align:right;font-weight:800}
.ubar .track{height:12px}
.axis{display:grid;grid-template-columns:70px 1fr 38px;gap:9px;color:#636A74;font-size:11px;margin-top:2px}
.axis div{position:relative;height:13px}.axis div span{position:absolute;transform:translateX(-50%);white-space:nowrap}
.axis div span:first-child{transform:none}
.lg{display:inline-flex;align-items:center;gap:5px;color:#A0A7B1;font-size:11.5px}
.lg i{width:9px;height:9px;border-radius:2px;display:inline-block}

/* 서버 */
.hosts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.host{background:#1B1D22;border:1px solid #272A31;border-radius:5px;padding:8px 10px;display:grid;grid-template-columns:1fr auto;gap:2px 8px}
.host .hn{font-weight:700}.host .hr{color:#636A74;font-size:11.5px}
.host .hs{grid-row:1/3;grid-column:2;font-size:22px;font-weight:800;text-align:right;line-height:1}
.host .hs small{display:block;font-size:10.5px;color:#636A74;font-weight:500;margin-top:3px}
.host .chips{grid-column:1/3;display:flex;flex-wrap:wrap;gap:3px;margin-top:4px}

/* 신호 유형 */
.seg{display:flex;height:10px;border-radius:2px;overflow:hidden;margin:2px 0 6px;gap:2px;animation:grow .8s both}
.segl{display:flex;gap:10px;flex-wrap:wrap;font-size:11.5px;color:#A0A7B1;margin-bottom:6px}
.segl b{color:#FAFAFA}.segl i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}
.trow{display:grid;grid-template-columns:30px 1fr 80px 24px;gap:7px;align-items:center;padding:2.5px 0}
.trow .i{font-family:Consolas,monospace;font-size:11px;color:#636A74}
.trow .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trow .val{text-align:right;font-weight:700}.trow .track{height:8px}

/* 외부 시도 */
.ext-top{display:flex;gap:18px;margin-bottom:6px;align-items:baseline}
.ext-top .big{font-size:22px;font-weight:800}.ext-top .k{color:#636A74;font-size:11.5px;margin-left:3px}
.iprow{padding:4px 0;border-top:1px solid #1E2025}
.iprow .l1{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;gap:8px}
.iprow .ip{font-family:Consolas,monospace;font-weight:700}
.iprow .l1 .when{color:#636A74;font-size:11.5px;margin-left:auto}
.stack{display:flex;height:9px;gap:1px;animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.stack div{height:100%}

/* 판정 기준 */
.cc-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.cc{background:#1B1D22;border:1px solid #272A31;border-radius:5px;padding:8px 10px}
.cc .k{color:#636A74;font-size:11.5px}.cc .v{font-size:14px;font-weight:700;margin-top:2px}
.rules td{font-size:12px;padding:4px 6px}

@media (max-width:1180px){.kpis{grid-template-columns:repeat(3,1fr)}.cc-row{grid-template-columns:1fr}}
@media (max-width:640px){.kpis{grid-template-columns:1fr 1fr}.detail{grid-template-columns:1fr}.dh{grid-column:1}
  .facts{grid-template-columns:1fr}.top{flex-wrap:wrap}.top .meta{margin-left:0;flex-wrap:wrap;gap:8px}}
</style>
"""

# ── 공통 조각 ───────────────────────────────────────────


def fmt(n):
    return f"{n:,}"


def q(tip, right=False):
    return f'<span class="q{" r" if right else ""}" data-tip="{escape(tip)}">?</span>'


def ph(title, n=None, n_cls="", tip=None, tools="", right=False):
    num = f'<span class="n {n_cls}">{n}</span>' if n is not None else ""
    return (f'<div class="ph"><h2>{title}{num}</h2>{q(tip, right) if tip else ""}'
            f'<div class="tools">{tools}</div></div>')


def skel(rows=5):
    return f'<div class="sk">{"<i></i>" * rows}</div>'


def bar(pct, color, th=None):
    t = f'<span class="th" style="left:{th:.1f}%"></span>' if th is not None else ""
    return f'<div class="track"><div class="fill" style="width:{pct:.1f}%;background:{color}"></div>{t}</div>'


def sev_color(sid, sev):
    if sev == "high":
        return RED
    if sev == "medium":
        return "#C9575A"
    if sid == "R16":
        return GRAY
    return NAVY2


def chip(sid):
    return f'<span class="chip{" h" if SEV.get(sid) == "high" else ""}">{sid}</span>'


def sev_tag(sev):
    if not sev:
        return '<span class="dim">-</span>'
    cls = {"high": "t-red", "medium": "t-amber"}.get(sev, "t-gray")
    return f'<span class="tag {cls}">{sev}</span>'


def changed(key, init=None):
    """위젯 값이 직전 실행과 달라졌는지. 처음 실행이면 False."""
    cur = st.session_state.get(key, init)
    pk = f"_prev_{key}"
    first = pk not in st.session_state
    prev = st.session_state.get(pk)
    st.session_state[pk] = cur
    return (not first) and prev != cur


def show_loading(slot, rows, sec=0.4):
    slot.html(skel(rows))
    time.sleep(sec)


# ── 화면 조각 ───────────────────────────────────────────


TIP_SAVED = "분석 결과 CSV로 만든 화면\n실시간 수집 아님"
TIP_SCORE = "신호 점수 합\n신호 점수 = 기본점수 × 서버 중요도 × 확신도\n세로선 = 경보 기준 100"
TIP_MAX = "같은 세션·같은 유형 신호는\n가장 높은 점수 1개만 반영\n×2 = 같은 유형 신호 2건"
TIP_BASIS = "관측: 세션에 직접 속한 원본 이벤트로 확인\n추정: 같은 서버·시간대로 이어 붙임"


def html_top():
    p = D["period"]
    return (f'<div class="top fx"><div class="logo"><img src="{LOGO}" alt="SeSAC Security"></div><h1>보안 관제 현황</h1>'
            f'<div class="meta"><span>기간 <b>{p["from"]} ~ {p["to"][5:]}</b> KST</span>'
            f'<span>마지막 로그 <b>{p["last"]}</b></span>'
            f'<span>저장 데이터 {q(TIP_SAVED, right=True)}</span></div></div>')


def spark(vals, color, hi=None):
    mx = max(max(vals), 1)
    out = []
    for i, v in enumerate(vals):
        h = max(v / mx * 100, 6 if v else 3)
        c = (hi[i] if hi and hi[i] else color) if v else "#25282E"
        out.append(f'<i style="height:{h:.0f}%;background:{c};animation-delay:{i * 18}ms"></i>')
    return f'<div class="sp">{"".join(out)}</div>'


def html_kpis():
    a, det, ex, mfa = D["alerts"], D["detections"], D["external"], D["mfa"]
    top = max(x["score"] for x in a)
    log_sum = [sum(D["logs"][k][i] for k in D["logs"]) for i in range(len(DAYS))]
    det_hi = [RED if D["alertDaily"][i] else None for i in range(len(DAYS))]
    cards = [
        ("crit", "경보 세션", "세션 점수 100 이상\n또는 ATT&CK 전술 3개 이상", len(a), "건",
         f'사용자 <b>{len({x["user"] for x in a})}명</b> · 최고 <b class="red">{top}점</b>', spark(D["alertDaily"], RED)),
        ("warn", "주의 세션", "점수는 있지만 경보 기준 미달\n행동 신호 1개 (20점)", len(D["watch"]), "건",
         "모두 <b>20점</b> · 오탐 후보", ""),
        ("info", "탐지 신호", f"룰·행동 탐지가 남긴 신호\n점수 반영 {det['scored']}건", det["total"], "건",
         f'high <b class="red">{det["high"]}</b> · 룰 <b>{det["rule"]}</b> · 행동 <b>{det["behavior"]}</b>',
         spark(det["daily"], BLUE, det_hi)),
        ("", "외부 로그인 시도", "세션 없는 외부 IP의 SSH 시도\n모두 없는 계정 이름", ex["total"], "회",
         f'IP <b>{len(ex["ips"])}개</b> · 성공 <b>{ex["success"]}</b>', spark(ex["daily"], "#2C7BB8")),
        ("", "MFA 없는 root 로그인", "계정 설정 위험\n행동 이상 아님 · 점수 제외", mfa["n"], "회",
         f'<b>{mfa["account"]}</b> · {mfa["first"]}~{mfa["last"]} 매일', spark(mfa["daily"], "#2C7BB8")),
        ("ref", "수집 로그", "로그 4종 정규화 행 수", D["logAll"], "행",
         f'4종 · 세션 <b>{D["sessionsAll"]}</b>', spark(log_sum, NAVY)),
    ]
    body = "".join(
        f'<div class="kpi {c} fx" style="animation-delay:{i * 60}ms"><div class="lb">{lb}{q(tip, right=i == 5)}</div>'
        f'<div class="mid"><div class="v">{fmt(v)}<small>{u}</small></div>{sp}</div><div class="sub">{sub}</div></div>'
        for i, (c, lb, tip, v, u, sub, sp) in enumerate(cards))
    return f'<div class="kpis">{body}</div>'


def html_alert_table(sel):
    mx = max(450, max(a["score"] for a in D["alerts"]))
    rows = []
    for i, a in enumerate(D["alerts"]):
        zone = '<span class="tag t-red">외부</span>' if a["zone"] == "external" else '<span class="tag t-gray">내부</span>'
        attr = '<span class="tag t-blue">관측</span>' if a["attr"] == "관측" else '<span class="tag t-amber">추정</span>'
        dots = "".join(f'<i class="{"on" if k <= a["tactics"] else ""}"></i>' for k in range(1, 6))
        rows.append(
            f'<tr class="{"sel" if a["id"] == sel else ""}"><td class="dim">{i + 1}</td><td class="mono">{a["id"]}</td>'
            f'<td class="user">{a["user"]}</td>'
            f'<td style="width:25%"><div class="sc"><b>{a["score"]}</b>{bar(a["score"] / mx * 100, RED, 100 / mx * 100)}</div></td>'
            f'<td><b>{a["tactics"]}</b><span class="dots">{dots}</span></td><td>{a["start"]}</td>'
            f'<td><span class="mono">{a["ip"]}</span> {zone}</td><td class="mu">{", ".join(a["hosts"]) or "-"}</td><td>{attr}</td></tr>')
    head = ("<tr><th></th><th>세션</th><th>사용자</th>"
            f'<th>점수 {q(TIP_SCORE)}</th>'
            "<th>전술</th><th>시작</th><th>접속 IP</th><th>서버</th>"
            f'<th>근거 {q(TIP_BASIS, right=True)}</th></tr>')
    return f'<table class="tbl fx"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table>'


def facts(a):
    where = "·".join(w for w, ok in (("외부", a["zone"] == "external"), ("처음", a["ipNew"])) if ok)
    f = [("접속", f'{a["ip"]} {where}'.strip(),
          "hot" if a["zone"] == "external" or a["ipNew"] else ""),
         ("시작", f'{a["start"][6:]} · 평소 {a["usual"]}시' + (f' · {a["hourGap"]}시간 벗어남' if a["hourGap"] else ""),
          "warm" if a["hourGap"] >= 3 else ""),
         ("경로", f'{a["type"]} · 평소 {SES_TYPE.get(a["usualType"], a["usualType"])}', "warm" if a["type"] != SES_TYPE.get(a["usualType"]) else ""),
         ("길이", f'{a["dur"]}분 · 이벤트 {a["flowCount"]}', "")]
    if a["failBefore"]:
        f.append(("로그인 전", f'실패 {a["failBefore"]}회', "warm"))
    if a["files"]:
        f.append(("생성 파일", ", ".join(a["files"]), "hot"))
    if a["dests"]:
        f.append(("외부 연결", ", ".join(a["dests"]), "hot"))
    if a["config"]:
        kinds = list(dict.fromkeys(c.split(" ")[0] for c in a["config"]))
        f.append(("설정 변경", f'{len(a["config"])}건 · {", ".join(kinds)}', "hot"))
    if a["concurrent"]:
        f.append(("동시 세션", ", ".join(a["concurrent"]), ""))
    return f


def sig_row(s, smx):
    """점수 구성 한 줄. 같은 유형이 여러 건이면 최고값만 점수로 쓰고 건수를 ×n으로 붙인다."""
    times = f'×{s["n"]}' if s["n"] > 1 else ""
    color = sev_color(s["id"], SEV.get(s["id"], "")) if s["id"][0] == "R" else NAVY2
    return (f'<div class="s"><span class="i">{s["id"]}</span>'
            f'<span class="nm" title="{escape(s["name"])} · {s["n"]}건 중 최고값">{escape(s["name"])}</span>'
            f'<span class="x">{times}</span>{bar(s["score"] / smx * 100, color)}<span class="pv">{s["score"]}</span></div>')


def html_detail(a):
    smx = max(s["score"] for s in a["signals"])
    top, rest = a["signals"][:5], a["signals"][5:]
    chain = "".join(f'{"<em>→</em>" if i else ""}<span class="tt" data-tip="{escape(t)}">{TAC.get(t, t)}</span>'
                    for i, t in enumerate(a["chain"]))
    fx = "".join(f'<div class="fact"><span class="k">{k}</span><span class="v {c}" title="{escape(v)}">{escape(v)}</span></div>'
                 for k, v, c in facts(a))
    sigs = "".join(sig_row(s, smx) for s in top)
    more = f'<div class="more">외 {len(rest)}종 +{sum(s["score"] for s in rest)}점</div>' if rest else ""
    return (f'<div class="detail fx"><div class="dh"><span class="id mono">{a["id"]}</span><span class="who">{a["user"]}</span>'
            f'<span class="pt">{a["score"]}점</span><span class="mu">전술 {a["tactics"]} · {a["verdict"]}</span>'
            f'<div class="chain">{chain}</div></div>'
            f'<div class="facts">{fx}</div>'
            f'<div class="sigs"><div class="cap"><span>점수 구성 {q(TIP_MAX)}</span>'
            f'<span>{len(a["signals"])}종 · 신호 {sum(s["n"] for s in a["signals"])}건</span></div>{sigs}{more}</div></div>')


def html_events(a):
    rows = "".join(
        f'<tr><td class="mono dim">{e["t"]}</td><td class="mu">{e["src"]}</td><td class="mu">{e["host"] or "-"}</td>'
        f'<td class="cmd">{escape(e["text"])}</td>'
        f'<td>{" ".join(chip(t) for t in e["types"])}</td></tr>'
        for e in a["events"])
    return f'<table class="tbl evs fx"><tbody>{rows}</tbody></table>'


def html_users():
    mx = max(450, max(p["max"] for p in D["people"]))
    rows = []
    for p in D["people"]:
        c = RED if p["alert"] else AMBER if p["max"] else GRAY
        vc = RED if p["alert"] else AMBER if p["max"] else DIM
        tip = f'{p["name"]}\n최고 {p["max"]}점 ({p["maxAt"]})\n세션 점수 합계 {p["total"]}점\n세션 {p["sessions"]}개 · 점수 있는 세션 {p["scored"]}개'
        rows.append(f'<div class="ubar tt" data-tip="{escape(tip)}"><span class="nm {"" if p["max"] else "zero"}">{p["name"]}</span>'
                    f'{bar(max(p["max"] / mx * 100, 0.8 if p["max"] else 0), c, 100 / mx * 100)}'
                    f'<span class="val" style="color:{vc}">{p["max"]}</span></div>')
    ax = "".join(f'<span style="left:{v / mx * 100:.1f}%">{lab}</span>'
                 for v, lab in [(0, "0"), (100, "100 경보"), (200, "200"), (400, "400")])
    legend = (f'<span class="lg"><i style="background:{RED}"></i>경보</span><span class="lg"><i style="background:{AMBER}"></i>주의</span>'
              f'<span class="lg"><i style="background:{GRAY}"></i>신호 없음</span>')
    return (ph("사용자별 최고 세션 점수", tip="사용자마다 가장 높은 세션 점수\n이름에 커서 → 16일 합계·세션 수", tools=legend)
            + f'<div class="fx">{"".join(rows)}<div class="axis"><span></span><div>{ax}</div><span></span></div></div>')


def html_hosts():
    cards = []
    for h in D["hosts"]:
        sc = RED if h["score"] >= 200 else AMBER if h["score"] >= 100 else "#FAFAFA"
        chips = "".join(f'<span class="chip {"h" if SEV.get(s) == "high" else ""}" title="{escape(NAME.get(s, ""))}">{s}</span>'
                        for s in h["signals"])
        cards.append(f'<div class="host"><span class="hn">{h["name"]}</span>'
                     f'<span class="hr">{ROLE.get(h["role"], h["role"])} · <span class="mono">{h["ip"]}</span> · 중요도 '
                     f'<b style="color:{"#FAFAFA" if h["crit"] == "high" else MUTE}">{h["crit"]}</b></span>'
                     f'<span class="hs" style="color:{sc}">{h["score"]}<small>점</small></span><div class="chips">{chips}</div></div>')
    return (ph("서버별 신호 점수", tip="서버에서 나온 신호 점수 합\n빨간 칩 = high 룰", tools="서버 4대", right=True)
            + f'<div class="hosts fx">{"".join(cards)}</div>')


def type_row(t, mx):
    style = "font-weight:700" if t["sev"] == "high" else f"color:{MUTE}" if t["id"] == "R16" else ""
    kind = f'룰 {t["sev"]}' if t["method"] == "rule" else "행동"
    return (f'<div class="trow"><span class="i">{t["id"]}</span><span class="nm" style="{style}" title="{escape(t["name"])} · {kind}">{escape(t["name"])}</span>'
            f'{bar(t["n"] / mx * 100, sev_color(t["id"], t["sev"]))}<span class="val">{t["n"]}</span></div>')


def split_types():
    ty = D["detections"]["types"]
    hi = [t for t in ty if t["sev"] == "high"]
    other = [t for t in ty if t["sev"] != "high"]
    return ty, hi, other[:5], other[5:]


def html_types():
    det = D["detections"]
    ty, hi, top, rest = split_types()
    mx = max(t["n"] for t in ty)
    segs = [("high 룰", sum(t["n"] for t in hi), RED),
            ("medium 룰", sum(t["n"] for t in ty if t["sev"] == "medium"), "#C9575A"),
            ("행동", sum(t["n"] for t in ty if t["method"] == "behavior"), NAVY2),
            ("설정 위험", sum(t["n"] for t in ty if t["id"] == "R16"), GRAY)]
    seg = "".join(f'<div style="flex:{n};background:{c}"></div>' for _, n, c in segs)
    segl = "".join(f'<span><i style="background:{c}"></i>{lab} <b>{n}</b></span>' for lab, n, c in segs)
    return (ph("탐지 신호 유형", tip="R = 룰 탐지 · B = 평소 행동과 비교\nR16은 설정 위험이라 점수 제외",
               tools=f'{len(ty)}종 · {det["total"]}건')
            + f'<div class="fx"><div class="seg">{seg}</div><div class="segl">{segl}</div>'
            + "".join(type_row(t, mx) for t in top) + "</div>")


def html_ext():
    ex = D["external"]
    accs = sorted({a["a"] for i in ex["ips"] for a in i["accounts"]})
    pal = ["#67BAF4", "#3F95D3", "#2C6FA5", "#1E466B", "#9FD0F5"]
    ac = {a: pal[i % len(pal)] for i, a in enumerate(accs)}
    mx = max(i["n"] for i in ex["ips"])
    rows = "".join(
        f'<div class="iprow"><div class="l1"><span class="ip">{i["ip"]}</span><span class="when">{i["first"]}~{i["last"]} · 하루 {i["n"] / i["days"]:.1f}회</span><b>{i["n"]}</b></div>'
        f'<div class="stack" style="width:{i["n"] / mx * 100:.1f}%">'
        + "".join(f'<div style="flex:{a["n"]};background:{ac[a["a"]]}" title="{a["a"]} {a["n"]}회"></div>' for a in i["accounts"])
        + "</div></div>" for i in ex["ips"])
    legend = "".join(f'<span class="lg"><i style="background:{ac[a]}"></i>{a}</span>' for a in accs)
    return (ph("외부 IP 로그인 시도", tip="세션 없이 SSH 로그인만 시도한 외부 IP\n없는 계정 이름(invalid_user)\n성공이 없어 점수 없음",
               tools="IP별 · 계정별", right=True)
            + f'<div class="fx"><div class="ext-top"><span><span class="big">{ex["total"]}</span><span class="k">회</span></span>'
              f'<span><span class="big blue">{ex["success"]}</span><span class="k">성공</span></span>'
              f'<span><span class="big">{len(accs)}</span><span class="k">계정 이름</span></span></div>{rows}'
              f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:7px">{legend}</div></div>')


def daily_chart(sources):
    rows = [{"day": d, "src": k, "n": D["logs"][k][i], "o": list(LOGC).index(k)}
            for k in sources for i, d in enumerate(DAYS)]
    df = pd.DataFrame(rows)
    tot = pd.DataFrame({"day": DAYS,
                        "n": [sum(D["logs"][k][i] for k in sources) for i in range(len(DAYS))],
                        "det": D["detections"]["daily"], "alert": D["alertDaily"]})
    tot["lab"] = tot["alert"].map(lambda v: f"경보 {v}" if v else "")
    ymax = tot["n"].max() * 1.28
    x = alt.X("day:O", sort=DAYS, axis=alt.Axis(title=None, labelAngle=0, labelExpr="slice(datum.label, 3)"))
    band = alt.Chart(tot[tot.alert > 0]).mark_rect(color=RED, opacity=0.09).encode(x=x)
    bars = alt.Chart(df).mark_bar(width={"band": 0.62}, cornerRadiusEnd=1).encode(
        x=x,
        y=alt.Y("sum(n):Q", scale=alt.Scale(domain=[0, ymax]), axis=alt.Axis(title=None, tickCount=4, labelExpr="format(datum.value, ',')")),
        color=alt.Color("src:N", scale=alt.Scale(domain=list(LOGC), range=list(LOGC.values())), legend=None),
        order=alt.Order("o:Q", sort="descending"),
        tooltip=[alt.Tooltip("day:N", title="날짜"), alt.Tooltip("src:N", title="로그"),
                 alt.Tooltip("n:Q", title="행 수", format=",")])
    det = alt.Chart(tot).mark_text(dy=-8, fontSize=11, fontWeight=600).encode(
        x=x, y="n:Q", text="det:Q",
        color=alt.condition("datum.alert > 0", alt.value(RED), alt.value(MUTE)),
        tooltip=[alt.Tooltip("day:N", title="날짜"), alt.Tooltip("det:Q", title="탐지 신호"),
                 alt.Tooltip("n:Q", title="로그 합계", format=",")])
    lab = alt.Chart(tot[tot.alert > 0]).mark_text(fontSize=11, fontWeight=700, color=RED, baseline="top").encode(
        x=x, y=alt.value(2), text="lab:N")
    return ((band + bars + det + lab).properties(height=168)
            .configure(background="transparent", font="Pretendard")
            .configure_view(stroke=None)
            .configure_axis(labelColor=MUTE, labelFontSize=11, gridColor="#22252B", domain=False, tickColor="#22252B")
            .configure_axisX(grid=False))


def html_watch():
    rows = "".join(
        f'<tr><td class="mono">{w["id"]}</td><td class="user">{w["user"]}</td><td><b class="amber">{w["score"]}</b></td>'
        f'<td>{w["start"]}</td><td><span class="chip">{w["sid"]}</span> {w["signal"]}</td><td class="mu">{w["fact"]}</td>'
        f'<td><span class="tag t-gray">{w["verdict"]}</span></td></tr>' for w in D["watch"])
    return ('<table class="tbl fx"><thead><tr><th>세션</th><th>사용자</th><th>점수</th><th>시작</th><th>신호</th>'
            f'<th>근거</th><th>판정</th></tr></thead><tbody>{rows}</tbody></table>')


def html_rules():
    def tb(rows):
        body = "".join(
            f'<tr><td class="mono">{r["id"]}</td><td style="{"font-weight:700" if r["sev"] == "high" else ""}">{escape(r["name"])}</td>'
            f'<td>{sev_tag(r["sev"])}</td>'
            f'<td style="text-align:right;{"font-weight:700" if r["hits"] else "color:" + DIM}">{r["hits"]}</td></tr>'
            for r in rows)
        return f'<table class="tbl rules"><thead><tr><th>ID</th><th>이름</th><th>등급</th><th>탐지</th></tr></thead><tbody>{body}</tbody></table>'
    return tb


def html_criteria():
    return ('<div class="cc-row fx">'
            '<div class="cc"><div class="k">경보</div><div class="v">점수 <span class="red">≥ 100</span> 또는 전술 <span class="red">≥ 3</span></div></div>'
            '<div class="cc"><div class="k">신호 점수</div><div class="v">기본 × 서버 중요도 × 확신도</div></div>'
            '<div class="cc"><div class="k">기본점수</div><div class="v">high 60 · medium 30 · 행동 20</div></div></div>')


def html_logs():
    rows = []
    for k, v in D["logs"].items():
        t = D["logTotal"][k]
        mi = v.index(max(v))
        rows.append(f'<tr><td><span class="lg"><i style="background:{LOGC[k]}"></i>{k}</span></td><td><b>{fmt(t)}</b></td>'
                    f'<td style="width:38%">{bar(t / D["logAll"] * 100, LOGC[k])}</td><td>{round(t / len(v))}</td>'
                    f'<td class="mu">{DAYS[mi]} · {v[mi]}</td></tr>')
    return ('<table class="tbl fx"><thead><tr><th>로그</th><th>행 수</th><th>비중</th><th>하루 평균</th><th>최다일</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


# ── 조각별 다시 그리기 (토글·선택 때 그 영역만 다시 불러옴) ────────


@st.fragment
def alert_panel():
    ids = [a["id"] for a in D["alerts"]]
    users = {a["id"]: a["user"] for a in D["alerts"]}
    sel = st.session_state.get("sel_alert") or ids[0]
    table = st.empty()
    table.html(ph("경보 세션", len(ids), "red", tip="세션 점수 100 이상\n또는 ATT&CK 전술 3개 이상",
                  tools="점수순 · 아래에서 세션 선택")
               + html_alert_table(sel))
    sel = st.segmented_control("경보 선택", ids, default=ids[0], key="sel_alert",
                               format_func=lambda i: f"{i} · {users[i]}") or ids[0]
    moved = changed("sel_alert", ids[0])
    if moved:
        table.html(ph("경보 세션", len(ids), "red", tip="세션 점수 100 이상\n또는 ATT&CK 전술 3개 이상",
                      tools="점수순 · 아래에서 세션 선택") + html_alert_table(sel))
    a = next(x for x in D["alerts"] if x["id"] == sel)
    body = st.empty()
    if moved:
        show_loading(body, 6, 0.35)
    with body.container():
        st.html(html_detail(a))
        key = f"tg_ev_{a['id']}"
        on = st.toggle(f"근거 이벤트 {len(a['events'])}건 · 전체 흐름 {a['flowCount']}건 중 신호 붙은 것", key=key)
        opened = changed(key, False)
        if on:
            slot = st.empty()
            if opened:
                show_loading(slot, 5)
            slot.html(html_events(a))


def daily_panel():
    legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{k}</span>' for k, c in LOGC.items())
    st.html(ph("일별 로그 수집 · 탐지", tip="막대 = 하루 로그 행 수 (KST)\n막대 위 숫자 = 그날 탐지 신호 수\n"
                                             "빨간 칸 = 경보 세션 시작일\n막대에 커서 → 로그별 행 수",
               tools=legend))
    st.altair_chart(daily_chart(list(LOGC)), width="stretch", theme=None)


@st.fragment
def types_rest():
    _, hi, _, rest = split_types()
    mx = max(t["n"] for t in D["detections"]["types"])
    on = st.toggle(f"high 룰 {len(hi)}종 {sum(t['n'] for t in hi)}건 · 나머지 {len(rest)}종", key="tg_types")
    opened = changed("tg_types", False)
    if on:
        slot = st.empty()
        if opened:
            show_loading(slot, 6)
        slot.html('<div class="fx">' + "".join(type_row(t, mx) for t in hi + rest) + "</div>")


@st.fragment
def drawers():
    """아래 접는 영역 3개. 켜면 그 내용만 불러오는 모습을 보이고 전체 폭으로 연다."""
    n_rule = sum(r["method"] == "rule" for r in D["rules"])
    items = [("tg_watch", f"주의 세션 {len(D['watch'])}건 · 경보 기준 미달 · 오탐 후보", draw_watch),
             ("tg_rules", f"판정 기준 · 룰 {n_rule} · 행동 {len(D['rules']) - n_rule}", draw_rules),
             ("tg_logs", f"수집 로그 · 4종 · {fmt(D['logAll'])}행", draw_logs)]
    for (key, label, _), col in zip(items, st.columns(3)):
        with col, st.container(key=f"pn_{key}"):
            st.toggle(label, key=key)
    for key, _, render in items:
        opened = changed(key, False)
        if not st.session_state.get(key):
            continue
        with st.container(key=f"pn_body_{key}"):
            body = st.empty()
            if opened:
                show_loading(body, 6)
            with body.container():
                render()


def draw_watch():
    st.html(html_watch())


def draw_rules():
    st.html(html_criteria())
    tb = html_rules()
    c1, c2 = st.columns(2)
    rule = [r for r in D["rules"] if r["method"] == "rule"]
    beh = [r for r in D["rules"] if r["method"] == "behavior"]
    c1.html(f'<div class="mu fx" style="margin-bottom:4px">룰 {len(rule)}개</div>' + tb(rule))
    c2.html(f'<div class="mu fx" style="margin-bottom:4px">행동 {len(beh)}개</div>' + tb(beh))


def draw_logs():
    st.html(html_logs())


# ── 배치 ────────────────────────────────────────────────

st.html(CSS)
first = not st.session_state.get("booted")
slots = []
progress = st.empty()


def slot(fill, rows):
    """처음 들어올 때는 자리표시를 먼저 보이고, 아래에서 차례로 채운다."""
    s = st.empty()
    if first:
        s.html(skel(rows))
        slots.append((s, fill))
    else:
        with s.container():
            fill()


def reload():
    st.session_state["booted"] = False


t1, t2 = st.columns([12, 1], vertical_alignment="center")
with t1:
    st.html(html_top())
with t2:
    st.button("다시 불러오기", key="reload", on_click=reload, width="stretch")

slot(lambda: st.html(html_kpis()), 3)

with st.container(key="row2"):
    c1, c2 = st.columns([1.45, 1])
    with c1:
        with st.container(key="pn_alert"):
            slot(alert_panel, 12)
    with c2:
        with st.container(key="pn_users"):
            slot(lambda: st.html(html_users()), 8)
        with st.container(key="pn_hosts"):
            slot(lambda: st.html(html_hosts()), 5)

with st.container(key="row3"):
    c1, c2, c3 = st.columns([1.55, 1, 1])
    with c1:
        with st.container(key="pn_daily"):
            slot(daily_panel, 9)
    with c2:
        with st.container(key="pn_types"):
            def _types():
                st.html(html_types())
                types_rest()
            slot(_types, 9)
    with c3:
        with st.container(key="pn_ext"):
            slot(lambda: st.html(html_ext()), 9)

with st.container(key="row4"):
    slot(drawers, 1)

if first:
    total = len(slots)
    for i, (s, fill) in enumerate(slots, 1):
        progress.html(f'<div class="pbar" style="width:{i / total * 100:.0f}%"></div>')
        time.sleep(0.11)
        with s.container():
            fill()
    time.sleep(0.15)
    progress.empty()
    st.session_state["booted"] = True
