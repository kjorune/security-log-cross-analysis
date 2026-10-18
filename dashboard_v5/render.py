"""사용자 위험 대시보드 v5의 화면 HTML을 만든다.

- 시안: teiren_siem/output/dashboard_mockup/make_monitor_mockup_v2style.py (2026-10-18 확정본)를 옮겼다.
- 디자인: v2 색·글꼴·카드·표, 이글루 모니터링 화면 구조, 경보 빨강·위험 노랑
- 데이터: 저장소 최상위 data/ 의 분석 결과 CSV를 읽기만 한다. 탐지·점수·경보는 다시 계산하지 않는다.
- 결과: CSS, USER_HTML(사용자 위험 현황), SYS_HTML(시스템 배경 활동), JS(사용자 클릭 전환)
"""
import html
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data"

# v2 색 (dashboard_v2/theme.py TOKENS, components.py)
NAVY, SKY, INK = "#d03b3b", "#fab219", "#0b1b33"   # 2026-10-18 요청: 경보 = 빨강(v2 STATUS critical), 위험 = 노랑(v2 STATUS warning)
TITLE, BLUE = "#062a7a", "#0b5be0"                  # 제목·점수 = v2 navy, 띠·링크 = v2 blue
PANEL, PAGE, STRIP = "#ffffff", "#f3f7fc", "#eaf1fb"  # 카드, 페이지, 표 머리
TINT = "#eaf1fb"
LINE = "#d6e1f0"
MUTED = "#5a6b85"
RED, RED_BG = "#d03b3b", "#fdeeee"                  # v2 STATUS critical (경보 배지)
GRID = "#e6edf6"
NONE_FILL = "#dfe6f0"          # 6: 신호 없는 세션은 옅게 (v2 DEEMPH보다 밝게)
ALERT_SCORE, ALERT_TACTICS = 100, 3
e = html.escape


def read(rel):
    return pd.read_csv(DATA / rel, encoding="utf-8-sig", dtype=str)


# ---------------------------------------------------------------- 데이터 (가이드 4절과 같은 규칙)
sr = read("10_risk/session_risk.csv")
ev = read("10_risk/risk_events.csv")
rules = read("09_detections/detection_rules.csv").set_index("id")
sessions = read("07_sessions/sessions.csv")
base = read("08_baseline/session_baseline.csv").set_index("work_session_id")
sr["risk_score"] = sr["risk_score"].astype(float)
sr["tactic_count"] = sr["tactic_count"].astype(int)
sr["alert"] = sr["alert"].eq("true")
sr["start_kst"] = pd.to_datetime(sr["start_utc"]) + pd.Timedelta(hours=9)
ev["signal_score"] = ev["signal_score"].astype(float)

sig = (ev.groupby(["work_session_id", "detection_type"], as_index=False)["signal_score"].max()
         .merge(sr[["work_session_id", "person_candidate", "alert"]], on="work_session_id"))
sig["name"] = sig["detection_type"].map(rules["name"])
sig["method"] = sig["detection_type"].map(rules["method"])

users = []
for person, g in sr.groupby("person_candidate"):
    g = g.sort_values(["risk_score", "start_kst"], ascending=[False, False])
    top = g.iloc[0]
    scored = g[g["risk_score"] > 0]
    alerts = sorted(g.loc[g["alert"], "work_session_id"])
    users.append(dict(person=person, max=top["risk_score"], total=g["risk_score"].sum(), alerts=alerts,
                      group="alert" if alerts else ("silent" if len(scored) else "none"),
                      top_sid=top["work_session_id"], tactics=int(top["tactic_count"]),
                      types=int(top["signal_types"]),
                      signal_sessions=sorted(scored["work_session_id"]),
                      last=scored["start_kst"].max() if len(scored) else None))
users = pd.DataFrame(users)
alert_u = users[users["group"] == "alert"].sort_values("max", ascending=False)
silent_u = users[users["group"] == "silent"].sort_values(["total", "person"], ascending=[False, True])
silent_names = list(silent_u["person"])
n_all = sessions["person_candidate"].nunique()
n_none = int((users["group"] == "none").sum())
none_names = ", ".join(users.loc[users["group"] == "none", "person"])


# ---------------------------------------------------------------- 공통 조각
def panel(title, body, cls="", note=""):
    note_html = f'<span class="pnote">{e(note)}</span>' if note else ""
    return (f'<section class="panel {cls}"><div class="ph"><span class="pt"><i class="mk"></i>{e(title)}</span>{note_html}</div>'
            f'<div class="pb">{body}</div></section>')


def legend(items):
    return '<div class="lg">' + "".join(f'<span><i style="background:{c}"></i>{e(t)}</span>' for c, t in items) + "</div>"


# 1. 위험 사용자 요약
summary = f"""
<div class="kpiwrap"><div class="kcards">
  <div class="kc alert"><div class="kl">경보 사용자 (명)</div><div class="kn">{len(alert_u)}</div><div class="ks">경보 세션 {int(sr['alert'].sum())}개</div></div>
  <div class="kc risk"><div class="kl">위험: 안 울린 경보 (명)</div><div class="kn"><span>{len(silent_u)}</span></div><div class="ks">위험 신호는 있고 경보는 없음</div></div>
  <div class="kc"><div class="kl">전체 사용자 (명)</div><div class="kn">{n_all}</div><div class="ks">신호 없음 {n_none}명({e(none_names)})</div></div>
</div>
<p class="rule-note">경보 기준: 세션 {ALERT_SCORE}점 이상 또는 ATT&amp;CK 전술 {ALERT_TACTICS}개 이상</p></div>"""


# 2. 날짜별 세션 수
def day_chart(w=880, h=112):
    s = sr.copy()
    s["day"] = s["start_kst"].dt.date
    s["kind"] = "none"
    s.loc[(s["risk_score"] > 0) & (~s["alert"]), "kind"] = "silent"
    s.loc[s["alert"], "kind"] = "alert"
    d = s.pivot_table(index="day", columns="kind", values="work_session_id", aggfunc="count", fill_value=0)
    d["all"] = d.sum(axis=1)
    left, bottom, top = 28, 20, 14
    ph = h - bottom - top
    step = (w - left - 4) / len(d)
    bw = step * 0.56
    mx = 16
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for v in (0, 5, 10, 15):
        y = top + ph - v / mx * ph
        out.append(f'<line x1="{left}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
                   f'<text x="{left - 6}" y="{y + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i, (day, r) in enumerate(d.iterrows()):
        x = left + i * step + (step - bw) / 2
        y = top + ph
        for k, c in (("alert", NAVY), ("silent", SKY), ("none", NONE_FILL)):
            v = int(r.get(k, 0))
            if v:
                hh = v / mx * ph
                out.append(f'<rect x="{x:.1f}" y="{y - hh + 1:.1f}" width="{bw:.1f}" height="{hh - 1:.1f}" fill="{c}"/>')
                y -= hh
        out.append(f'<text x="{x + bw / 2:.1f}" y="{y - 4:.1f}" class="val mut" text-anchor="middle">{int(r["all"])}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{h - 5}" class="ax" text-anchor="middle">{day.month}/{day.day}</text>')
    out.append("</svg>")
    return "".join(out)


trend = day_chart() + legend([(NAVY, "경보 세션"), (SKY, "안 울린 경보 세션"), (NONE_FILL, "신호 없는 세션")])


# 3. 위험 사용자 현황 표
def score_bar(v, alert, w=80, mx=450):
    fill = NAVY if alert else SKY
    t = ALERT_SCORE / mx * w
    return (f'<svg width="{w}" height="10" class="sbar"><rect x="0" y="2" width="{w}" height="6" fill="{STRIP}"/>'
            f'<rect x="0" y="2" width="{max(v / mx * w, 2):.1f}" height="6" fill="{fill}"/>'
            f'<line x1="{t:.1f}" x2="{t:.1f}" y1="0" y2="10" stroke="{INK}" stroke-width="1"/></svg>')


def acts_cell(u):
    """1: 행위 이름과 가산점을 두 줄로. 2: 안 울린 경보는 둘째 줄에 경보가 안 된 이유."""
    if u["group"] == "alert":
        s = sig[sig["work_session_id"] == u["top_sid"]].sort_values(["signal_score", "detection_type"],
                                                                   ascending=[False, True])
        lines = [f'{e(r.name)} <b>+{r.signal_score:g}</b>' for r in s.head(2).itertuples()]
        if len(s) > 2:
            lines[-1] += f' <span class="mut">외 {len(s) - 2}종</span>'
        return "<br>".join(lines)
    g = (sig[sig["person_candidate"] == u["person"]].groupby("name", as_index=False)
         .agg(n=("work_session_id", "size"), pts=("signal_score", "max")))
    first = ", ".join(f'{e(r.name)}{" ×" + str(r.n) if r.n > 1 else ""} <b>+{r.pts:g}</b>' for r in g.itertuples())
    reason = (f"경보 안 됨: 최고 세션 {u['max']:g}점 &lt; {ALERT_SCORE}점, "
              f"전술 {u['tactics']}개 &lt; {ALERT_TACTICS}개")
    return f'{first}<br><span class="mut">{reason}</span>'


rows = []
for i, (_, u) in enumerate(pd.concat([alert_u, silent_u]).iterrows(), start=1):
    alert = u["group"] == "alert"
    kind = '<span class="pill red">▲ 경보</span>' if alert else '<span class="pill yel">◆ 위험</span>'
    rows.append(
        f'<tr data-user="{e(u["person"])}"><td class="c">{i}</td>'
        f'<td class="b"><a href="#" class="ulink" data-pick="{e(u["person"])}">{e(u["person"])}</a></td><td>{kind}</td>'
        f'<td><span class="sv{" navy" if alert else ""}">{u["max"]:g}</span>{score_bar(u["max"], alert)}</td>'
        f'<td class="acts">{acts_cell(u)}</td><td class="r">{u["tactics"]}</td>'
        f'<td>{u["last"]:%m-%d %H:%M}</td><td><a href="#" data-pick="{e(u["person"])}">세션 보기</a></td></tr>')
table = f"""
<table class="tb">
<thead><tr><th class="c">순위</th><th>사용자</th><th>구분</th><th>최고 세션 점수 <span class="th-note">세로선 = 기준 {ALERT_SCORE}</span></th>
<th>주요 위험행위와 가산점</th><th class="r">전술</th><th>최근 신호 (KST)</th><th></th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="foot">사용자 이름이나 '세션 보기'를 누르면 아래 그래프가 그 사용자의 위험행위 세션으로 바뀝니다. 설정 위험(R16 MFA 없는 최상위 계정 로그인) admin01@lab.internal 23건은 점수에 넣지 않아 이 표에 없습니다.</p>"""


# 4. 평소와 다른 정도 (안 울린 경보 사용자의 신호 세션)
def hour_strip(now, lo, hi, w=150):
    """0~24시 띠에 평소 시작 시각 범위(옅은 칠)와 이번 시작 시각(점)을 표시한다."""
    x = lambda h: 4 + h / 24 * (w - 8)
    out = [f'<svg width="{w}" height="22" class="hs">',
           f'<line x1="{x(0):.1f}" x2="{x(24):.1f}" y1="11" y2="11" stroke="{LINE}"/>',
           f'<rect x="{x(lo):.1f}" y="6" width="{x(hi) - x(lo):.1f}" height="10" fill="{TINT}" stroke="{SKY}"/>',
           f'<circle cx="{x(now):.1f}" cy="11" r="4" fill="{TITLE}"/>']
    for h in (0, 12, 24):
        out.append(f'<text x="{x(h):.1f}" y="22" class="tick" text-anchor="middle">{h}</text>')
    out.append("</svg>")
    return "".join(out)


dev_items = []
for u in silent_u.itertuples():
    for sid in u.signal_sessions:
        b = base.loc[sid]
        who = "본인" if b["baseline_level"] == "person" else "비슷한 사용자"
        for r in sig[sig["work_session_id"] == sid].itertuples():
            if r.detection_type == "B01":
                now, lo, hi = int(b["start_hour_kst"]), int(b["hist_hour_min"]), int(b["hist_hour_max"])
                what = f"시작 {now}시, 평소 {lo}~{hi}시"
                vis = hour_strip(now, lo, hi)
            else:  # B08: 과거 최댓값을 넘은 양 (session_baseline의 _above_max)
                over = [c for c in ("process_count", "non_get_count") if b[f"{c}_above_max"] == "true"]
                label = {"process_count": "실행한 프로세스", "non_get_count": "GET 외 웹 요청"}
                what = ", ".join(f"{label[c]} {b[c]}개" for c in over) + ", 과거 최대보다 많음"
                vis = ""
            dev_items.append(
                f'<div class="dvi"><div><div><b>{e(u.person)}</b> {sid} '
                f'<span class="mut">{r.detection_type}</span> {e(r.name)}</div>'
                f'<div>{e(what)}</div><div class="mut">비교: {who}의 과거 세션 {b["baseline_n"]}개</div></div>'
                f'<div>{vis}</div></div>')
deviation = ('<div class="dvl">' + "".join(dev_items) + '</div>'
             '<p class="foot">평소는 이 세션보다 먼저 끝난 과거 세션입니다. '
             '띠의 옅은 칸은 평소 시작 시각, 점은 이번 시작 시각입니다.</p>')


# 5·6. 가로 막대
def hbars(items, w=640, mx=None, fmt=lambda v: f"{v:g}", n=5, label_w=250, tail=200):
    """items: (탐지 ID, 이름, 값, 색, 덧붙일 글). 이름을 줄이지 않고 왼쪽에 쓴다."""
    row_h, bar_h, top = 27, 14, 4
    h = top + n * row_h
    mx = mx or max(it[2] for it in items) * 1.2
    unit = (w - label_w - tail) / mx
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for i, (did, name, v, col, extra) in enumerate(items):
        y = top + i * row_h
        cy = y + bar_h / 2 + 4
        out.append(f'<text x="0" y="{cy:.1f}" class="ax"><tspan class="b">{e(did)}</tspan>  {e(name)}</text>')
        out.append(f'<rect x="{label_w}" y="{y:.1f}" width="{v * unit:.1f}" height="{bar_h}" fill="{col}"/>')
        out.append(f'<text x="{label_w + v * unit + 6:.1f}" y="{cy:.1f}" class="val"><tspan class="b">{fmt(v)}</tspan>'
                   f'<tspan class="mutt">{("  " + e(extra)) if extra else ""}</tspan></text>')
    out.append(f'<line x1="{label_w}" x2="{label_w}" y1="0" y2="{h}" stroke="{LINE}"/>')
    out.append("</svg>")
    return "".join(out)


# 2026-10-18: '경보 세션 위험행위 점수 Top5'를 빼고 '점수가 있는 세션' 막대그래프를 넣는다.
# 전체 보기(기본)와 사용자별 보기(표에서 사용자를 누르면)를 미리 그려 두고 스크립트로 바꿔 보여준다.
def scored_all(w=880):
    rows = sr[sr["risk_score"] > 0].sort_values(["risk_score", "work_session_id"], ascending=[False, True])
    label_w, row_h, bar_h, top, bottom = 132, 21, 13, 6, 22
    h = top + len(rows) * row_h + bottom
    mx = 450
    unit = (w - label_w - 40) / mx
    x100 = label_w + 100 * unit
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for v in (0, 100, 200, 300, 400):
        x = label_w + v * unit
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 2}" y2="{h - bottom}" stroke="{GRID}"/>'
                   f'<text x="{x:.1f}" y="{h - 6}" class="tick2" text-anchor="middle">{v}</text>')
    for i, r in enumerate(rows.itertuples()):
        y = top + i * row_h
        cy = y + bar_h / 2 + 4
        col = NAVY if r.alert else SKY
        out.append(f'<text x="{label_w - 8}" y="{cy:.1f}" class="ax pick" text-anchor="end" data-pick="{e(r.person_candidate)}">'
                   f'<tspan class="b">{r.work_session_id}</tspan> {e(r.person_candidate)}</text>')
        out.append(f'<rect x="{label_w}" y="{y:.1f}" width="{max(r.risk_score * unit, 2):.1f}" height="{bar_h}" fill="{col}"/>')
        out.append(f'<text x="{label_w + r.risk_score * unit + 6:.1f}" y="{cy:.1f}" class="val b">{r.risk_score:g}</text>')
    out.append(f'<line x1="{x100:.1f}" x2="{x100:.1f}" y1="{top - 4}" y2="{h - bottom}" stroke="{INK}" stroke-dasharray="3 3"/>'
               f'<text x="{x100 + 4:.1f}" y="{h - bottom - 4}" class="tick2">경보 기준 100</text>')
    out.append("</svg>")
    return "".join(out)


def scored_user(person, w=880):
    """한 사용자의 점수가 있는 세션마다 세션 줄 하나와 그 세션의 위험행위 막대를 그린다."""
    ss_ = sr[(sr["person_candidate"] == person) & (sr["risk_score"] > 0)].sort_values("risk_score", ascending=False)
    label_w, head_h, row_h, bar_h, top = 300, 24, 18, 11, 4
    n_rows = sum(len(sig[sig["work_session_id"] == r.work_session_id]) for r in ss_.itertuples())
    h = top + len(ss_) * head_h + n_rows * row_h + 6
    mx = 95
    unit = (w - label_w - 60) / mx
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    y = top
    for r in ss_.itertuples():
        col = NAVY if r.alert else SKY
        state = "경보" if r.alert else "경보 아님"
        out.append(f'<rect x="0" y="{y + 5}" width="4" height="13" fill="{col}"/>'
                   f'<text x="10" y="{y + 16}" class="ax"><tspan class="b">{r.work_session_id}</tspan>'
                   f'  {r.risk_score:g}점, {state}, 전술 {r.tactic_count}개, {r.start_kst:%m-%d %H:%M} KST</text>')
        y += head_h
        b = sig[sig["work_session_id"] == r.work_session_id].sort_values(["signal_score", "detection_type"],
                                                                        ascending=[False, True])
        for x_ in b.itertuples():
            cy = y + bar_h / 2 + 4
            out.append(f'<text x="18" y="{cy:.1f}" class="ax"><tspan class="b">{x_.detection_type}</tspan> {e(x_.name)}</text>')
            out.append(f'<rect x="{label_w}" y="{y:.1f}" width="{x_.signal_score * unit:.1f}" height="{bar_h}" fill="{col}"/>')
            out.append(f'<text x="{label_w + x_.signal_score * unit + 6:.1f}" y="{cy:.1f}" class="val">+{x_.signal_score:g}</text>')
            y += row_h
    out.append("</svg>")
    return "".join(out)


views = ['<div class="sv-view" data-view="all">' + scored_all()
         + legend([(NAVY, "경보 세션"), (SKY, "위험 세션 (경보 아님)")]) + '</div>']
for person in pd.concat([alert_u, silent_u])["person"]:
    views.append(f'<div class="sv-view" data-view="{e(person)}" hidden>' + scored_user(person) + '</div>')
scored_panel = (
    '<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i><span id="sv-title">점수가 있는 세션</span></span>'
    '<span class="pnote"><span id="sv-hint">표나 막대의 사용자를 누르면 그 사용자의 위험행위 세션을 봅니다</span>'
    '<a href="#" id="sv-reset" data-pick="all" hidden>전체 보기</a></span></div>'
    '<div class="pb scroll">' + "".join(views) + '</div></section>')


# 3: 안 울린 경보 사용자의 신호만 센다 (요약의 3명과 같은 범위)
ss = sig[sig["person_candidate"].isin(silent_names)]
cnt = (ss.groupby(["detection_type", "name"]).agg(n=("work_session_id", "size")).reset_index()
         .sort_values(["n", "detection_type"], ascending=[False, True]))
by_user = ss.groupby(["detection_type", "person_candidate"]).size()
p_silent = hbars([(r.detection_type, r.name, r.n, SKY,
                   ", ".join(f"{p} {by_user[(r.detection_type, p)]}" for p in silent_names
                             if (r.detection_type, p) in by_user.index))
                  for r in cnt.itertuples()], mx=5, fmt=lambda v: f"{v:g}건", n=len(cnt) + 1, w=440, label_w=170, tail=150)
other = sig[(~sig["alert"]) & (~sig["person_candidate"].isin(silent_names))].sort_values("work_session_id")
p_silent += (f'<p class="foot">이 {len(cnt)}종뿐입니다. 경보 사용자의 경보 아닌 세션 신호 {len(other)}건'
             f'({", ".join(f"{r.work_session_id} {r.person_candidate} {r.detection_type}" for r in other.itertuples())})은 '
             f'상세에서 봅니다.</p>')


# 2026-10-18: 경보 세션에서 걸린 규칙 기반·행동 기반 탐지의 조건과 임계값
BASE_SCORE = {"high": 60, "medium": 30, "low": 10}


def pct(note, key):
    """threshold_note('≥2h:4.8%; ...')에서 key의 비율을 찾아 '약 5%'로 반올림한다."""
    for part in str(note).split(";"):
        k, _, v = part.strip().partition(":")
        if k.strip() == key:
            return f"약 {round(float(v.strip().rstrip('%')))}%"
    return "알 수 없음"


_n = rules["threshold_note"]
# 행동 기반 조건을 쉬운 문장으로 (원래 조건식은 아래에 작게 남긴다)
BEH_COND = {
    "B01": "세션 시작 시각이 과거 시작 시각 범위에서 2시간 이상 벗어남",
    "B02": "과거에 쓴 적 없는 IP로 접속",
    "B03": "과거에 한 번도 없던 접속 경로 (서버+웹, 서버만, 웹만)",
    "B04": "과거에 없던 웹 로그인 종류",
    "B05": "과거에 하지 않던 민감 행위",
    "B06": "어떤 사용자도 쓴 적 없는 명령",
    "B07": "로그인 직전에 실패가 있었고, 과거에는 실패한 적이 없음",
    "B08": "실행한 프로세스 수나 GET 외 웹 요청 수가 과거 최댓값보다 많음",
    "B09": "어느 서버에서도 본 적 없는 시스템 활동 (서버 기록이 24시간 넘게 쌓인 뒤)",
}
# 임계값 근거: 과거 세션 비율을 반올림해 문장으로
BEH_BASIS = {   # 근거: docs/06_탐지_위험점수.md 5-b '드문 정도 기준 (B01, B08)', 'B09의 24시간 근거'
    "B01": f"과거 세션 중 2시간 이상 벗어난 비율 {pct(_n['B01'], '≥2h')}. "
           f"이 비율이 5% 이하가 되는 가장 작은 값이 2시간이라 기준으로 정했습니다 "
           f"(1시간이면 {pct(_n['B01'], '≥1h')}).",
    "B08": f"과거 최댓값을 넘은 세션이 5% 이하인 항목만 씁니다: 프로세스 수 {pct(_n['B08'], 'process_count')}, "
           f"GET 외 웹 요청 {pct(_n['B08'], 'non_get_count')}. "
           f"세션 길이({pct(_n['B08'], 'duration_min')})와 웹 요청 수({pct(_n['B08'], 'nginx_count')})는 5%를 넘어 뺐습니다.",
    "B09": "정상 반복 작업 중 가장 늦게 처음 나온 것이 서버 기록 시작 뒤 약 12~17시간이었습니다. "
           "하루 주기 작업이 한 번은 나오도록 24시간을 지켜본 뒤부터 신호로 봅니다.",
}
fired = sig[sig["alert"]].groupby("detection_type")["work_session_id"].nunique()


def crit_table(method):
    r = rules[(rules["method"] == method) & (rules.index.isin(fired.index))].copy()
    r = r.loc[sorted(r.index, key=lambda i: (int(i[1:]),))]
    head = ('<tr><th>탐지</th><th>이름</th><th>조건과 임계값</th>'
            + ('<th>심각도 (기본 점수)</th>' if method == "rule" else '<th>임계값을 정한 근거</th>')
            + '<th class="r">경보 세션</th></tr>')
    body = []
    for i, x in r.iterrows():
        if method == "rule":
            extra = f'{e(x["severity"])} ({BASE_SCORE[x["severity"]]}점)'
        else:
            extra = e(BEH_BASIS.get(i, "처음 보는 값이면 신호입니다. 따로 정한 수치 기준은 없습니다."))
        cond = BEH_COND.get(i, x["condition"]) if method == "behavior" else x["condition"]
        code = f'<div class="code">{e(x["condition"])}</div>' if method == "behavior" else ""
        body.append(f'<tr><td class="b">{i}</td><td>{e(x["name"])}</td><td class="cond">{e(cond)}{code}</td>'
                    f'<td class="cond">{extra}</td><td class="r">{int(fired[i])}개</td></tr>')
    return f'<table class="tb crit">{head}{"".join(body)}</table>'


n_rule = int((rules.loc[rules.index.isin(fired.index), "method"] == "rule").sum())
n_beh = int((rules.loc[rules.index.isin(fired.index), "method"] == "behavior").sum())
criteria = f"""
<div class="crit-top">
  <div><b>경보</b> 세션 점수 {ALERT_SCORE}점 이상 또는 ATT&amp;CK 전술 {ALERT_TACTICS}개 이상 (전술은 규칙 기반 탐지에서만 셈)</div>
  <div><b>신호 점수</b> 기본 점수 × 서버 중요도(1.5 또는 1.0) × 연결 신뢰도(직접 1.0, 추정 0.8). 같은 세션의 같은 탐지는 가장 높은 점수 하나만 더함</div>
</div>
<div class="crit-grid">
  <div><p class="crit-h">규칙 기반 {n_rule}개 <span class="mut">경보 세션 4개에서 걸린 규칙</span></p>{crit_table("rule")}</div>
  <div><p class="crit-h">행동 기반 {n_beh}개 <span class="mut">본인·동료의 과거 세션과 비교, 기본 점수 20점</span></p>{crit_table("behavior")}</div>
</div>
<p class="foot">출처: data/09_detections/detection_rules.csv. R09(SSH 무차별 대입)는 이 데이터에서 걸린 적이 없고, R16(MFA 없는 최상위 계정 로그인)은 설정 위험이라 점수에서 빼서 표에 없습니다.</p>"""

# 2026-10-18: 왼쪽 탭의 두 번째 페이지 '시스템 설정·외부 시도' (v2 config_external 화면과 같은 값)
cfg = read("10_risk/config_findings.csv")
r16 = cfg[cfg["rule"] == "R16"].iloc[0]
ext = read("08_baseline/external_profile.csv")
for c in ("attempts", "active_days", "attempts_per_day", "distinct_accounts"):
    ext[c] = ext[c].astype(float)
ext = ext.sort_values("attempts", ascending=False)
tl = pd.read_csv(DATA / "07_sessions" / "timeline_sessions.csv", encoding="utf-8-sig", dtype=str,
                 usecols=["event_time_utc", "bucket", "client_ip"])
tries = tl[tl["bucket"] == "external"].copy()
tries["day"] = (pd.to_datetime(tries["event_time_utc"]) + pd.Timedelta(hours=9)).dt.date
daily = tries.groupby(["day", "client_ip"]).size().unstack(fill_value=0)
kst = lambda t: (pd.to_datetime(t) + pd.Timedelta(hours=9)).strftime("%m-%d %H:%M")
IP_COLORS = ["#2a78d6", "#062a7a", "#1baf7a"]   # v2 SERIES 계열 (주황 대신 남색)


def ip_lines(w=1380, h=230):
    left, bottom, top, right = 34, 26, 12, 150
    pw, ph = w - left - right, h - top - bottom
    days = list(daily.index)
    mx = max(8, int(daily.values.max()) + 1)
    sx = lambda i: left + i / (len(days) - 1) * pw
    sy = lambda v: top + ph - v / mx * ph
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for v in range(0, mx + 1, 2):
        out.append(f'<line x1="{left}" x2="{left + pw}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="{GRID}"/>'
                   f'<text x="{left - 6}" y="{sy(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i, d in enumerate(days):
        out.append(f'<text x="{sx(i):.1f}" y="{h - 6}" class="ax" text-anchor="middle">{d.month}/{d.day}</text>')
    for ip, col in zip(ext["client_ip"], IP_COLORS):
        vals = [int(daily.loc[d, ip]) if ip in daily.columns else 0 for d in days]
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
        for i, v in enumerate(vals):
            out.append(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="3.5" fill="{col}" stroke="#ffffff" stroke-width="1.5"/>')
        out.append(f'<text x="{left + pw + 10}" y="{sy(vals[-1]) + 4:.1f}" class="ax" fill="{col}"><tspan class="b">{ip}</tspan></text>')
    out.append("</svg>")
    return "".join(out)


ext_rows = "".join(
    f'<tr><td class="b">{r.client_ip}</td><td class="r">{r.attempts:g}</td><td class="r">{r.active_days:g}</td>'
    f'<td class="r">{r.attempts_per_day:g}</td><td class="r">{r.distinct_accounts:g}</td>'
    f'<td>{e(r.accounts.replace("|", ", "))}</td><td>{kst(r.first_seen)}</td><td>{kst(r.last_seen)}</td>'
    f'<td>{"있음" if r.ever_logged_in == "true" else "없음"}</td></tr>' for r in ext.itertuples())
n_success = int((ext["ever_logged_in"] == "true").sum())
accounts = sorted({a.split(":")[0] for x in ext["accounts"] for a in x.split("|")})
ext_page = f"""
<h2 class="sec-h">설정 위험 <span>행동 이상과 따로 고쳐야 할 계정 설정</span></h2>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>시스템 설정 위험</span><span class="pnote">전체 기간 값</span></div>
<div class="pb">
  <div class="pills"><span class="pill">▽ 심각도 low, 행동 이상 아님</span><span class="pill blue">● 근거: 관측</span></div>
  <p class="cfg-main"><b>MFA 없는 최상위 콘솔 계정 로그인</b>, 계정 <code>{e(r16['account'])}</code>, <b>{int(r16['count'])}회</b>
  ({r16['sessions']}개 세션, {kst(r16['first_seen'])} ~ {kst(r16['last_seen'])} KST)</p>
  <ul class="cfg-list">
    <li>테이렌 콘솔의 최상위 계정 로그인입니다. Linux 서버의 <code>root</code> 활동과는 다른 계정 체계입니다.</li>
    <li>행동이 이상한 것이 아니라 계정 설정 문제라서 세션 위험점수에서 빼고 조치 항목 1건으로 보고합니다.</li>
    <li><b>권고 조치:</b> 최상위 계정에 MFA를 적용하고, 일상 업무는 하위 계정으로 나눕니다.</li>
  </ul>
</div></section>
<h2 class="sec-h">외부 로그인 시도 <span>로그인에 성공하지 못한 외부 IP의 반복 시도</span></h2>
<div class="kcards four">
  <div class="kc"><div class="kl">외부 IP (개)</div><div class="kn">{len(ext)}</div><div class="ks">전체 기간</div></div>
  <div class="kc"><div class="kl">로그인 시도 (회)</div><div class="kn">{int(ext['attempts'].sum())}</div><div class="ks">{daily.index.min():%m-%d} ~ {daily.index.max():%m-%d}, 하루 몇 회씩</div></div>
  <div class="kc"><div class="kl">시도한 계정명 (개)</div><div class="kn">{len(accounts)}</div><div class="ks">{e(", ".join(accounts))}</div></div>
  <div class="kc"><div class="kl">로그인 성공 기록 (IP)</div><div class="kn">{n_success}</div><div class="ks">수집된 sshd 범위</div></div>
</div>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>외부 IP 하루 시도 수</span><span class="pnote">발생 시각 기준 (KST)</span></div>
<div class="pb">{ip_lines()}
<p class="foot">세 IP 모두 기간 내내 하루 몇 회씩 천천히 시도했습니다. '같은 IP 1시간 안 실패 5회' 규칙(R09)은 한 번도 걸리지 않았습니다. 느린 반복 시도를 잡는 기준은 개선 과제로 남겼습니다.</p></div></section>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>외부 IP 목록</span><span class="pnote">전체 기간 값</span></div>
<div class="pb"><table class="tb ext"><tr><th>외부 IP</th><th class="r">시도</th><th class="r">기간(일)</th><th class="r">하루 평균</th><th class="r">계정명 수</th><th>시도한 계정명</th><th>처음 (KST)</th><th>마지막 (KST)</th><th>로그인 성공</th></tr>{ext_rows}</table>
<p class="note">이 IP들은 로그인에 성공하지 못해 위험점수가 없습니다. 외부 IP에서 로그인에 성공한 세션(위험 사용자 현황의 경보)과는 다른 집단입니다. IP 국가와 지도는 근거 자료가 없어 표시하지 않습니다.</p></div></section>
"""

# 2026-10-18: '시스템 배경 활동' 탭 — 사람이 로그인하지 않고 서버가 자동으로 실행한 활동의 보안 위협
acc = read("05_enriched/account_inventory.csv").set_index("account")
bg = read("08_baseline/background_baseline.csv")
bgp = read("08_baseline/background_patterns.csv")
bgp["count"] = bgp["count"].astype(int)
det = read("09_detections/detections.csv")
bgd = det[det["bucket"] == "background"].copy()
bgd["t"] = pd.to_datetime(bgd["event_time_utc"]) + pd.Timedelta(hours=9)
sig_patterns = sorted(set(bgd["evidence"].str.extract(r"^(P\d+) 처음 봄")[0].dropna()))
person_of = sr.set_index("work_session_id")["person_candidate"]
alert_of = sr.set_index("work_session_id")["alert"]
events_by_acc = bg.groupby("account").size()
hosts_by_acc = bg.groupby("account")["host"].apply(lambda x: ", ".join(sorted(set(x))))
TYPE_KO = {"system": "시스템 계정", "human": "사람", "nonexistent": "서버에 없는 계정"}

acc_rows = []
for a_ in ["root", "www-data", "syslog", "admin", "admin01"]:
    r = acc.loc[a_]
    t = r["account_type"]
    pill_cls = {"system": "pill navyp", "human": "pill", "nonexistent": "pill"}[t]
    if t == "system":
        where = f'{hosts_by_acc.get(a_, "")}, 자동 실행 {int(events_by_acc.get(a_, 0)):,}건'
    elif t == "nonexistent":
        where = f"외부 IP의 로그인 실패 {int(r['login_fail'])}회 (sshd가 Invalid user로 기록)"
    else:
        where = f"사람 업무 세션 (로그인 성공 {int(r['login_success'])}회), 콘솔 계정은 MFA 설정 위험"
    acc_rows.append(f'<tr><td class="b">{e(a_)}</td><td><span class="{pill_cls}">{TYPE_KO[t]}</span></td>'
                    f'<td>{e(r["type_basis"])}: {e(r["note"])}</td><td>{e(where)}</td></tr>')
acc_table = ('<table class="tb plain"><tr><th>계정</th><th>종류</th><th>판단 근거</th><th>이 데이터에서 한 일</th></tr>'
             + "".join(acc_rows) + "</table>")


def pattern_bars(w=1380, h=210):
    """34개 패턴의 발생 횟수 (로그 눈금). 신호가 걸린 패턴은 빨강."""
    import math
    d = bgp.sort_values(["count", "pattern_id"], ascending=[False, True])
    left, bottom, top = 40, 34, 14
    ph = h - top - bottom
    step = (w - left - 6) / len(d)
    bw = step * 0.62
    ly = lambda v: top + ph - math.log10(v) / math.log10(300) * ph
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for v in (1, 10, 100):
        out.append(f'<line x1="{left}" x2="{w}" y1="{ly(v):.1f}" y2="{ly(v):.1f}" stroke="{GRID}"/>'
                   f'<text x="{left - 6}" y="{ly(v) + 4:.1f}" class="ax" text-anchor="end">{v}</text>')
    for i, r in enumerate(d.itertuples()):
        x = left + i * step + (step - bw) / 2
        y = ly(r.count) if r.count > 1 else top + ph - 3
        col = NAVY if r.pattern_id in sig_patterns else "#c5cfdd"
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{top + ph - y:.1f}" fill="{col}">'
                   f'<title>{r.pattern_id} {e(r.host)} {e(r.account)} {e(r.detail)}: {r.count}회</title></rect>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{y - 4:.1f}" class="tick2" text-anchor="middle">{r.count}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{h - 18}" class="tick2" text-anchor="middle">{r.pattern_id[1:]}</text>')
    out.append(f'<text x="{left}" y="{h - 3}" class="tick2">패턴 번호 (P001~P034), 세로축은 로그 눈금</text>')
    out.append("</svg>")
    return "".join(out)


# 신호가 걸린 시스템 활동: 같은 서버·같은 시각의 신호를 한 줄로
ev_rows = []
for (t, host), g in bgd.groupby(["t", "host"], sort=True):
    b09 = g[g["detection_type"] == "B09"]["evidence"].str.split("): ", n=1, regex=False).str[1].tolist()
    what = " / ".join(b09) if b09 else g["evidence"].iloc[0]
    chips = "".join(f'<span class="dchip">{d_}</span>' for d_ in g["detection_type"])
    sid = g["linked_sessions"].iloc[0].split("(")[0]
    how = g["linked_sessions"].iloc[0].split("(")[1].rstrip(")")
    ses = (f'<span class="pill red">▲ {sid} {e(person_of.get(sid, ""))}</span> <span class="mut">{e(how)}</span>'
           if alert_of.get(sid, False) else f'{sid} {e(person_of.get(sid, ""))}')
    ev_rows.append(f'<tr><td>{t:%m-%d %H:%M:%S}</td><td>{e(host)}</td><td class="b">{e(g["account"].iloc[0])}</td>'
                   f'<td class="what">{e(what)}</td><td>{chips}</td><td>{ses}</td></tr>')
ev_table = ('<table class="tb plain"><tr><th>시각 (KST)</th><th>서버</th><th>계정</th><th>처음 보는 활동</th><th>걸린 탐지</th><th>추정 연결된 세션</th></tr>'
            + "".join(ev_rows) + "</table>")

n_bg = len(bg)
n_repeat = int((~bgp["pattern_id"].isin(sig_patterns)).sum())
rep_rng = bgp.loc[~bgp["pattern_id"].isin(sig_patterns), "count"]
sig_rng = bgp.loc[bgp["pattern_id"].isin(sig_patterns), "count"]
linked = bgd["linked_sessions"].str.split("(").str[0].value_counts()
sys_page = f"""
<div class="wrap">
<header class="top"><h1>시스템 배경 활동</h1>
<span class="meta">시스템 계정의 자동 활동, 계정 설정 위험, 외부 로그인 시도</span></header>
<h2 class="sec-h">시스템 계정 자동 활동 <span>사람이 로그인하지 않고 서버가 자동으로 실행한 활동</span></h2>
<div class="kcards four">
  <div class="kc alert"><div class="kl">시스템 활동 신호 (건)</div><div class="kn">{len(bgd)}</div><div class="ks">경보 세션 {", ".join(f"{k} {v}건" for k, v in linked.items())}에 추정 연결</div></div>
  <div class="kc alert"><div class="kl">처음 보는 활동 (종)</div><div class="kn">{len(sig_patterns)}</div><div class="ks">패턴마다 {sig_rng.min()}~{sig_rng.max()}회, 모두 신호</div></div>
  <div class="kc"><div class="kl">평소 반복 작업 (종)</div><div class="kn">{n_repeat}</div><div class="ks">패턴마다 {rep_rng.min()}~{rep_rng.max()}회 (점검, 웹 서버, 로그 정리)</div></div>
  <div class="kc"><div class="kl">시스템 자동 실행 (건)</div><div class="kn">{n_bg:,}</div><div class="ks">root, www-data, syslog의 Sysmon 기록</div></div>
</div>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>시스템 계정 확인</span><span class="pnote">출처: data/05_enriched/account_inventory.csv</span></div>
<div class="pb">{acc_table}
<p class="foot">root·www-data·syslog만 시스템 계정입니다. admin은 외부에서 로그인을 시도한 이름일 뿐 서버에 없는 계정이고, admin01은 사람(관리자) 계정이라 이 탭에 들어가지 않습니다.</p></div></section>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>패턴별 발생 횟수</span><span class="pnote">서버 + 계정 + 실행 파일 + 명령·연결·파일로 묶은 34종</span></div>
<div class="pb">{pattern_bars()}{legend([("#c5cfdd", "평소 반복 작업"), (NAVY, "처음 보는 활동 (신호)")])}</div></section>
<section class="panel"><div class="ph"><span class="pt"><i class="mk"></i>신호가 걸린 시스템 활동</span><span class="pnote">같은 서버·같은 시각의 신호를 한 줄로 묶음</span></div>
<div class="pb">{ev_table}
<p class="note">시스템 계정의 활동은 사람의 업무 세션에 들어가지 않습니다. 같은 서버·같은 시간대의 사람 세션에 추정으로 연결하고, 점수에는 연결 신뢰도 0.8을 곱합니다. 평소 반복 작업은 수십~수백 회 나오지만, 신호가 걸린 활동은 모두 1~3회만 나온 처음 보는 활동입니다.</p></div></section>
{ext_page}
</div>"""

def _hex_pattern():
    """v2 사이드바와 같은 육각형 무늬. v2보다 조금 더 보이게 선을 진하게 했다."""
    import math
    def pts(cx, cy, r):
        return " ".join(f"{cx + r * math.cos(math.radians(60 * i - 30)):.1f},{cy + r * math.sin(math.radians(60 * i - 30)):.1f}" for i in range(6))
    r = 22
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{r * 0.87 * 2:.0f}' height='{r * 3:.0f}'>"
           f"<polygon points='{pts(r * 0.87, r, r - 1)}' fill='none' stroke='rgba(120,200,255,0.13)'/>"
           f"<polygon points='{pts(r * 0.87 * 2, r * 2.5, r - 1)}' fill='none' stroke='rgba(120,200,255,0.13)'/></svg>")
    return "data:image/svg+xml;utf8," + svg.replace("#", "%23").replace("<", "%3C").replace(">", "%3E")


HEX_BG = _hex_pattern()

lo, hi = sr["start_kst"].min(), sr["start_kst"].max()

# ---------------------------------------------------------------- 화면 조각 (app이 st.html로 그린다)
CSS = f"""
@font-face {{ font-family:"Pretendard"; font-weight:100 900;
  src:url("https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/variable/woff2/PretendardVariable.woff2") format("woff2"); }}
* {{ box-sizing:border-box; }}
.wrap {{ color:{INK}; font-family:Pretendard,"Malgun Gothic",sans-serif; font-size:12.5px; line-height:1.45; }}
.wrap p, .wrap ul {{ margin-bottom:0; }}
.pb svg:not(.sbar):not(.hs) {{ max-width:100%; height:auto; }}
[hidden] {{ display:none !important; }}
.shell {{ display:flex; width:1680px; align-items:flex-start; }}
.side {{ width:240px; flex:none; position:sticky; top:0; height:100vh; padding:18px 14px; display:flex; flex-direction:column; gap:4px;
  background:#061c52 url("{HEX_BG}"); border-right:1px solid #1b3f8f; }}   /* v2 사이드바 색과 육각 무늬, 그라데이션 없음 */
.brand {{ display:flex; gap:10px; align-items:center; font-size:15.5px; font-weight:800; color:#ffffff; margin:0 4px 18px; line-height:1.3; }}
.brand small {{ display:block; font-size:11px; font-weight:500; color:rgba(200,228,255,0.72); margin-top:3px; }}
.logo {{ display:block; width:200px; height:auto; margin:2px 4px 20px; }}
.hexmark {{ width:24px; height:28px; flex:none; background:#35d6f5; clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%); }}
.nav {{ display:block; padding:9px 12px; border-radius:8px; color:rgba(230,241,255,0.86); text-decoration:none; font-weight:600; font-size:13.5px; }}
.nav:hover {{ background:rgba(47,224,247,0.08); }}
.nav.on {{ background:rgba(47,224,247,0.16); color:#ffffff; font-weight:800; box-shadow:inset 3px 0 0 #35d6f5; }}
.side-meta {{ margin-top:22px; padding:12px 4px 0; border-top:1px solid rgba(255,255,255,0.14); font-size:11.5px; color:rgba(220,236,255,0.72); line-height:1.6; }}
.side-meta b {{ color:#ffffff; font-weight:600; }}
main {{ flex:1; min-width:0; }}
.wrap {{ width:100%; max-width:1440px; padding:0 0 18px; display:flex; flex-direction:column; gap:12px; }}
.kcards.four {{ grid-template-columns:repeat(4, 1fr); }}
.kcards.four .kc {{ height:auto; }}
.pills {{ display:flex; gap:8px; margin:2px 0 8px; }}
.pill.blue {{ color:{BLUE}; background:{STRIP}; }}
.cfg-main {{ margin:0 0 6px; font-size:13.5px; }}
.cfg-list {{ margin:0; padding-left:18px; font-size:13px; line-height:1.8; }}
code {{ font-size:12px; background:{STRIP}; padding:1px 5px; border-radius:4px; color:{TITLE}; }}
.tb.ext td {{ height:34px; }}
.tb.ext > tbody > tr:nth-child(n) > td {{ border-bottom:1px solid {LINE}; }}
.tb.ext tr:last-child > td {{ border-bottom:none; }}
.note {{ margin:10px 0 0; padding:10px 12px; background:{STRIP}; border-radius:8px; font-size:12.5px; color:{TITLE}; }}
.tb.plain td {{ height:auto; padding:7px 8px; white-space:normal; vertical-align:top; }}
.tb.plain > tbody > tr:nth-child(n) > td {{ border-bottom:1px solid {LINE}; }}
.tb.plain tr:last-child > td {{ border-bottom:none; }}
.tb.plain td.what {{ font-family:Consolas,monospace; font-size:11.5px; color:{INK}; }}
.pill.navyp {{ color:#ffffff; background:{TITLE}; }}
.dchip {{ display:inline-block; font-size:11px; font-weight:700; color:{TITLE}; background:{STRIP}; padding:1px 6px; border-radius:4px; margin:0 3px 3px 0; }}
.sec-h {{ margin:14px 0 0; padding-top:12px; border-top:1px solid {LINE}; font-size:17px; font-weight:800; color:{TITLE}; }}
.wrap > .top + .sec-h {{ margin-top:0; padding-top:0; border-top:none; }}
.sec-h span {{ font-size:12px; font-weight:500; color:{MUTED}; margin-left:8px; }}
.nav small {{ display:block; font-size:11px; font-weight:500; color:rgba(200,228,255,0.68); margin-top:2px; }}
.code {{ font-size:10.5px; color:{MUTED}; margin-top:2px; font-family:Consolas,monospace; }}
.top {{ height:50px; flex:none; display:flex; align-items:center; justify-content:space-between; padding:0 4px;
  border-bottom:1px solid {LINE}; }}
.top h1 {{ margin:0; font-size:21px; font-weight:800; color:{TITLE}; letter-spacing:-0.3px; }}
.top .meta {{ font-size:12.5px; color:{MUTED}; font-variant-numeric:tabular-nums; }}
.row {{ display:grid; gap:12px; }}
.r1 {{ grid-template-columns:480px 1fr; height:182px; flex:none; }}
.r2 {{ grid-template-columns:1fr 470px; height:432px; flex:none; }}
.r3 {{ grid-template-columns:1.9fr 1fr; height:330px; flex:none; }}
.pb.scroll {{ overflow-y:auto; }}
.r4 {{ grid-template-columns:1fr; }}
.tick2 {{ font-size:10.5px; fill:{MUTED}; }}
.pick, .ulink {{ cursor:pointer; }}
.ulink {{ color:{INK}; text-decoration:none; border-bottom:1px dashed {MUTED}; }}
.tb tr.sel > td {{ background:#eef4fd; }}
#sv-reset {{ color:{BLUE}; font-weight:600; margin-left:10px; }}
.crit-top {{ display:grid; grid-template-columns:1fr 1.6fr; gap:16px; font-size:12.5px; color:{INK};
  background:{STRIP}; border-radius:8px; padding:9px 12px; margin-bottom:10px; }}
.crit-top b {{ color:{TITLE}; margin-right:8px; }}
.crit-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; align-items:start; }}
.crit-h {{ margin:0 0 6px; font-weight:800; color:{TITLE}; font-size:13px; }}
.crit-h .mut {{ font-weight:400; font-size:11.5px; margin-left:6px; }}
.tb.crit td {{ height:auto; padding:5px 6px; white-space:normal; vertical-align:top; font-size:12px; }}
.tb.crit td.cond {{ min-width:120px; }}
.tb.crit > tbody > tr:nth-child(n) > td {{ border-bottom:1px solid {LINE}; }}
.tb.crit td:nth-child(2) {{ min-width:118px; }}
.tb.crit tr:last-child > td {{ border-bottom:none; }}
.panel {{ background:{PANEL}; border:1px solid {LINE}; border-radius:12px; display:flex; flex-direction:column;
  min-width:0; min-height:0; overflow:hidden; }}
.ph {{ height:34px; flex:none; display:flex; align-items:flex-end; justify-content:space-between; padding:0 14px 4px; }}
.pt {{ font-weight:800; font-size:14px; color:{TITLE}; display:flex; align-items:center; gap:7px; }}
.mk {{ width:10px; height:12px; background:{BLUE}; clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%); }}
.pnote {{ font-size:11.5px; color:{MUTED}; }}
.pb {{ padding:6px 14px 10px; flex:1; min-height:0; overflow:hidden; }}
.kpiwrap {{ display:flex; flex-direction:column; }}
.kcards {{ display:grid; grid-template-columns:1fr 1.45fr 1fr; gap:10px; }}
.kc {{ position:relative; background:{PANEL}; border:1px solid {LINE}; border-radius:12px; padding:14px 14px 10px;
  overflow:hidden; height:138px; }}
/* 2026-10-18 요청: 숫자 카드는 위쪽 띠 없이 모두 아래 음영 (번지지 않는 단색) */
.kc {{ box-shadow:0 5px 0 {TITLE}; margin-bottom:5px; }}
.kc.alert {{ box-shadow:0 5px 0 {NAVY}; }}
.kc.risk {{ box-shadow:0 5px 0 {SKY}; }}
.kc.alert .kn {{ color:{NAVY}; }}
.kc.risk .kn span {{ color:{SKY}; }}
.kl {{ font-size:12px; font-weight:600; color:{MUTED}; }}
.kn {{ font-size:40px; font-weight:800; line-height:1.15; color:{TITLE}; font-variant-numeric:tabular-nums; margin-top:6px; }}
.ks {{ font-size:11.5px; color:{MUTED}; margin-top:6px; }}
.rule-note {{ margin:10px 0 0 2px; font-size:11.5px; color:{MUTED}; }}
svg text {{ font-family:inherit; }}
.ax {{ font-size:11.5px; fill:#3d4f6b; }}
.b, .ax .b {{ font-weight:700; }}
.ax .b {{ fill:{INK}; }}
.tick {{ font-size:9px; fill:{MUTED}; }}
.val {{ font-size:11.5px; fill:{INK}; font-variant-numeric:tabular-nums; }}
.val.mut, .mutt {{ fill:{MUTED}; }}
.lg {{ display:flex; gap:18px; justify-content:center; font-size:11.5px; color:#3d4f6b; margin-top:2px; }}
.lg i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:-1px; }}
.tb {{ width:100%; border-collapse:separate; border-spacing:0; font-size:12.5px; border:1px solid {LINE}; border-radius:10px; overflow:hidden; }}
.tb th {{ text-align:left; font-weight:700; font-size:12px; color:{TITLE}; background:{STRIP}; padding:7px 6px;
  border-bottom:1px solid {LINE}; white-space:nowrap; }}
.tb td {{ padding:4px 6px; height:40px; border-bottom:1px solid {LINE}; white-space:nowrap; font-variant-numeric:tabular-nums; }}
.tb > tbody > tr:last-child > td {{ border-bottom:none; }}
.tb > tbody > tr:nth-child({len(alert_u)}) > td {{ border-bottom:1px solid {TITLE}; }}
.tb .c {{ text-align:center; }} .tb .r {{ text-align:right; }}
.tb .acts {{ line-height:1.45; }}
.mut {{ color:{MUTED}; }}
.th-note {{ font-weight:400; color:{MUTED}; font-size:11px; margin-left:4px; }}
.sv {{ display:inline-block; width:34px; text-align:right; font-weight:800; margin-right:8px; }}
.sv.navy {{ color:{NAVY}; }}
.sbar, .hs {{ vertical-align:middle; }}
.hs {{ display:block; margin-top:2px; }}
.pill {{ font-size:11.5px; font-weight:600; padding:2px 9px; border-radius:999px; color:{MUTED}; background:{STRIP}; white-space:nowrap; }}
.pill.red {{ color:#ffffff; background:{NAVY}; font-weight:700; }}
.pill.yel {{ color:{INK}; background:{SKY}; font-weight:700; }}
.tb a {{ color:{BLUE}; text-underline-offset:2px; font-weight:600; }}
.dvl {{ margin-top:0; }}
.dvi {{ display:grid; grid-template-columns:1fr 156px; gap:10px; align-items:center;
  padding:6px 0; border-bottom:1px solid {LINE}; line-height:1.5; }}
.foot {{ margin:6px 0 0; font-size:11.5px; color:{MUTED}; white-space:normal; }}

/* 화면이 좁으면(사이드바 포함 1760px 이하) 패널을 위아래로 쌓는다. 다른 규칙보다 뒤에 둬야 덮어쓴다 */
@media (max-width:1760px) {{
  .r1, .r2, .r3 {{ grid-template-columns:1fr; height:auto; }}
  .pb.scroll {{ max-height:420px; }}
  .kcards.four {{ grid-template-columns:repeat(2, 1fr); }}
  .crit-grid {{ grid-template-columns:1fr; }}
}}
"""

USER_HTML = f"""<div class="wrap">
<header class="top"><h1>사용자 위험 모니터링</h1>
<span class="meta">세션 시작 {lo:%Y-%m-%d} ~ {hi:%Y-%m-%d} KST, 사용자는 동일인 후보(추정)</span></header>
<div class="row r1">
{summary}
{panel("날짜별 세션 수", trend, note="세션 시작일 기준, 보기 전용")}
</div>
<div class="row r2">
{panel("위험 사용자 현황", table, note="경보 사용자는 최고 세션 점수 순, 안 울린 경보는 누적 점수 순")}
{panel("안 울린 경보: 평소와 다른 정도", deviation, note="진짜 위험한지 판단할 근거")}
</div>
<div class="row r3">
{scored_panel}
{panel("안 울린 경보 사용자의 위험행위", p_silent, note="건수, 사용자별 건수")}
</div>
<div class="row r4">
{panel("경보 판정 기준: 경보에 쓰인 조건과 임계값", criteria, note="규칙 기반과 행동 기반")}
</div>
</div>
"""

SYS_HTML = sys_page

JS = f"""
function show(u) {{
  document.querySelectorAll('.sv-view').forEach(v => v.hidden = v.dataset.view !== (u || 'all'));
  document.querySelectorAll('.tb tr[data-user]').forEach(r => r.classList.toggle('sel', r.dataset.user === u));
  document.getElementById('sv-title').textContent = u ? u + '의 위험행위 세션' : '점수가 있는 세션';
  document.getElementById('sv-reset').hidden = !u;
  document.getElementById('sv-hint').hidden = !!u;
}}
if (!window.__v5Click) {{
  window.__v5Click = true;
  document.addEventListener('click', ev => {{
    const a = ev.target.closest('[data-pick]');
    if (!a) return;
    ev.preventDefault();
    const u = a.dataset.pick === 'all' ? null : a.dataset.pick;
    show(u);
    history.replaceState(null, '', u ? '#user=' + encodeURIComponent(u) : location.pathname + location.search);
    if (u && a.closest('table')) document.getElementById('sv-title').scrollIntoView({{behavior: 'smooth', block: 'start'}});
  }});
}}
const m = location.hash.match(/user=([^&]+)/);
show(m ? decodeURIComponent(m[1]) : null);
"""

PERIOD = (lo, hi)
