"""보안 관제 대시보드에 쓰는 수치.

저장소의 분석 결과 CSV(data/)를 읽어 화면에 쓰는 값을 dict로 만든다.
"""
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
KST = pd.Timedelta("9h")


def read(rel):
    return pd.read_csv(DATA / rel, encoding="utf-8-sig", dtype=str)


def kst(s):
    return pd.to_datetime(s, format="mixed") + KST


def num(v, default=0.0):
    try:
        f = float(v)
        return default if pd.isna(f) else f
    except (TypeError, ValueError):
        return default


def load():
    # ── 원본 ────────────────────────────────────────────────
    tl = read("04_integrated/timeline.csv")
    sr = read("10_risk/session_risk.csv")
    ev = read("10_risk/risk_events.csv")
    det = read("09_detections/detections.csv")
    rules = read("09_detections/detection_rules.csv")
    ent = read("10_risk/entity_risk.csv")
    cfg = read("10_risk/config_findings.csv")
    ext = read("08_baseline/external_profile.csv")
    hosts = read("05_enriched/host_inventory.csv")
    ctx = read("11_investigation/alert_context.csv").set_index("work_session_id")
    tri = read("11_investigation/triage.csv").set_index("work_session_id")
    inc = read("11_investigation/incident_timeline.csv")
    ses = read("07_sessions/sessions.csv").set_index("work_session_id")

    tl["t"] = kst(tl["event_time_utc"])
    tl["day"] = tl["t"].dt.strftime("%m-%d")
    days = sorted(tl["day"].unique())

    SRC = {"sysmon": "Sysmon", "nginx": "NGINX", "sshd": "SSHD", "teiren_audit": "Audit"}
    SES_TYPE = {"web_only": "웹", "server_only": "서버", "server+web": "서버+웹"}


    def per_day(series_days):
        vc = series_days.value_counts()
        return [int(vc.get(d, 0)) for d in days]


    # ── 로그 수집 ───────────────────────────────────────────
    logs = {SRC[k]: per_day(tl.loc[tl.log_source == k, "day"]) for k in SRC}
    log_total = {SRC[k]: int((tl.log_source == k).sum()) for k in SRC}

    # ── 탐지 신호 ───────────────────────────────────────────
    det["t"] = kst(det["event_time_utc"])
    det["day"] = det["t"].dt.strftime("%m-%d")
    sig_types = (
        det.groupby(["detection_type", "name", "method"], dropna=False)
        .size().reset_index(name="n").sort_values(["n", "detection_type"], ascending=[False, True])
    )
    sev = rules.set_index("id")["severity"].to_dict()
    signal_types = [
        {"id": r.detection_type, "name": r.name, "method": r.method, "n": int(r.n),
         "sev": sev.get(r.detection_type) if isinstance(sev.get(r.detection_type), str) else ""}
        for r in sig_types.itertuples()
    ]

    # ── 세션 점수 ───────────────────────────────────────────
    sr["score"] = sr["risk_score"].astype(float)
    sr["t"] = kst(sr["start_utc"])
    alerts_df = sr[sr.alert == "true"].sort_values("score", ascending=False)
    watch_df = sr[(sr.alert != "true") & (sr.score > 0)].sort_values(["score", "t"], ascending=[False, False])

    det_type = det.set_index("detection_id")["detection_type"].to_dict()
    det_name = det.set_index("detection_id")["name"].to_dict()


    def signals_of(sid):
        e = ev[ev.work_session_id == sid].copy()
        e["s"] = e["signal_score"].astype(float)
        g = e.groupby(["detection_type", "name"]).agg(score=("s", "max"), n=("s", "size")).reset_index()
        g = g.sort_values("score", ascending=False)
        return [{"id": r.detection_type, "name": r.name, "score": round(r.score), "n": int(r.n)} for r in g.itertuples()]


    def key_events(sid):
        rows = inc[(inc.incident == sid) & inc.detection_ids.notna()]
        out = []
        for r in rows.itertuples():
            ids = r.detection_ids.split("|")
            types = sorted({det_type.get(i, "") for i in ids})
            out.append({
                "t": r.time_kst[-5:], "src": SRC.get(r.log_source, r.log_source),
                "host": r.host if isinstance(r.host, str) else "",
                "text": r.summary, "types": types,
            })
        return out


    def split_list(v):
        return [x for x in str(v).split("|") if x and x != "nan"]


    alerts = []
    for r in alerts_df.itertuples():
        c, s = ctx.loc[r.work_session_id], ses.loc[r.work_session_id]
        t = tri.loc[r.work_session_id]
        flows = inc[inc.incident == r.work_session_id]
        evs = key_events(r.work_session_id)
        host_set = {h.split(":")[0] for h in split_list(s.hosts)} | {e["host"] for e in evs if e["host"]}
        alerts.append({
            "id": r.work_session_id, "user": r.person_candidate, "score": round(r.score),
            "tactics": int(r.tactic_count),
            "chain": [x.strip() for x in str(c.tactic_chain).split("→")],
            "start": r.t.strftime("%m-%d %H:%M"), "day": r.t.strftime("%m-%d"),
            "usual": c.usual_hours_kst, "hourGap": int(num(c.hour_distance)),
            "ip": r.client_ip, "zone": c.ip_zone, "ipNew": c.ip_first_time_for_person == "true",
            "type": SES_TYPE.get(r.session_type, r.session_type),
            "usualType": str(c.usual_session_types).split(":")[0],
            "hosts": sorted(host_set),
            "dur": round(num(s.duration_min)),
            "failBefore": int(num(c.failed_before_login)),
            "files": split_list(c.files_created),
            "dests": split_list(c.external_destinations),
            "config": split_list(c.config_changes),
            "concurrent": split_list(c.concurrent_sessions_same_host),
            "gaps": int(num(c.data_gaps)),
            "verdict": t.activity_verdict, "attr": t.attribution,
            "signals": signals_of(r.work_session_id),
            "events": evs,
            "flowCount": int(len(flows)),
            "flowBasis": {k: int(v) for k, v in flows.basis.value_counts().items()},
        })

    # 경보 안 된 점수 세션: 신호 이름과 근거 숫자만
    watch = []
    for r in watch_df.itertuples():
        t = tri.loc[r.work_session_id] if r.work_session_id in tri.index else None
        reason = str(t.reason).split("|")[0] if t is not None else ""
        sig = signals_of(r.work_session_id)
        m_hour = re.search(r"시작 (\d+)시, 평소 ([\d~]+)시", reason)
        m_proc = re.search(r"프로세스 (\d+)", reason)
        if m_hour:
            fact = f"시작 {m_hour.group(1)}시 · 평소 {m_hour.group(2)}시"
        elif m_proc:
            fact = f"프로세스 {m_proc.group(1)}개 · 과거 최대 초과"
        else:
            fact = ""
        watch.append({
            "id": r.work_session_id, "user": r.person_candidate, "score": round(r.score),
            "start": r.t.strftime("%m-%d %H:%M"),
            "signal": sig[0]["name"] if sig else "", "sid": sig[0]["id"] if sig else "",
            "fact": fact, "verdict": t.activity_verdict if t is not None else "",
        })

    # ── 사용자·서버 ─────────────────────────────────────────
    people = []
    for r in ent[ent.entity_type == "person"].itertuples():
        srows = sr[sr.person_candidate == r.entity]
        # 최고 세션 점수: 세션 하나의 점수 중 최댓값 (max_24h는 24시간 누적이라 쓰지 않음)
        top = srows.sort_values(["score", "t"], ascending=[False, False]).iloc[0]
        people.append({
            "name": r.entity, "total": round(num(r.total_score)), "max": round(top.score),
            "maxAt": top.work_session_id, "alert": isinstance(r.alert_sessions, str),
            "sessions": int(len(srows)), "scored": int((srows.score > 0).sum()),
        })
    people.sort(key=lambda p: (-p["max"], -p["total"]))

    hinv = hosts.set_index("host")
    host_rows = []
    for r in ent[ent.entity_type == "host"].itertuples():
        h = hinv.loc[r.entity]
        host_rows.append({
            "name": r.entity, "ip": h.ip, "role": h.role, "crit": h.criticality,
            "score": round(num(r.total_score)), "signals": split_list(r.signal_types),
            "logs": {k: int(v) for k, v in (x.split(":") for x in split_list(h.collected_logs))},
        })
    host_rows.sort(key=lambda h: -h["score"])

    # ── 외부 로그인 시도·설정 위험 ──────────────────────────
    ext_ips = list(ext.client_ip)
    ext_rows = tl[tl.src.isin(ext_ips)]
    external = {
        "total": int(len(ext_rows)),
        "success": int((ext.ever_logged_in == "true").sum()),
        "daily": per_day(ext_rows["day"]),
        "ips": [{
            "ip": r.client_ip, "n": int(r.attempts), "days": num(r.active_days),
            "first": kst(pd.Series([r.first_seen]))[0].strftime("%m-%d"),
            "last": kst(pd.Series([r.last_seen]))[0].strftime("%m-%d"),
            "accounts": [{"a": a.split(":")[0], "n": int(a.split(":")[1])} for a in split_list(r.accounts)],
        } for r in ext.sort_values("attempts", key=lambda s: s.astype(int), ascending=False).itertuples()],
    }

    mfa_row = cfg[cfg.rule == "R16"].iloc[0]
    mfa_det = det[det.detection_type == "R16"]
    mfa = {
        "n": int(mfa_row["count"]), "account": mfa_row.account.split("@")[0],
        "daily": per_day(mfa_det["day"]),
        "first": kst(pd.Series([mfa_row.first_seen]))[0].strftime("%m-%d"),
        "last": kst(pd.Series([mfa_row.last_seen]))[0].strftime("%m-%d"),
    }

    # ── 판정 기준 ───────────────────────────────────────────
    rule_rows = [{
        "id": r.id, "method": r.method, "name": r.name, "attck": r.attck if isinstance(r.attck, str) else "",
        "sev": r.severity if isinstance(r.severity, str) else "",
        "src": r.data_source, "hits": int((det.detection_type == r.id).sum()),
    } for r in rules.itertuples()]

    data = {
        "period": {"from": tl["t"].min().strftime("%Y-%m-%d"), "to": tl["t"].max().strftime("%Y-%m-%d"),
                   "last": tl["t"].max().strftime("%m-%d %H:%M")},
        "days": days,
        "logs": logs, "logTotal": log_total, "logAll": int(len(tl)),
        "sessionsAll": int(len(sr)), "scoredAll": int((sr.score > 0).sum()),
        "detections": {"total": int(len(det)), "rule": int((det.method == "rule").sum()),
                       "behavior": int((det.method == "behavior").sum()),
                       "scored": int(ev.detection_id.nunique()),
                       "high": int((det.severity == "high").sum()),
                       "daily": per_day(det["day"]), "types": signal_types},
        "alertDaily": per_day(alerts_df["t"].dt.strftime("%m-%d")),
        "alerts": alerts, "watch": watch, "people": people, "hosts": host_rows,
        "external": external, "mfa": mfa, "rules": rule_rows,
    }

    return data
