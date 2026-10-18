"""사용자 위험 대시보드 v5.

실행 (저장소 최상위에서): .venv\\Scripts\\python.exe -m streamlit run dashboard_v5/app.py
- 화면 시안: teiren_siem/output/dashboard_mockup/user_risk_monitor_mockup_v2style.html (2026-10-18)
- 왼쪽 탭 두 개: 사용자 위험 현황, 시스템 배경 활동(설정 위험·외부 시도 포함)
- 분석 결과 CSV를 읽기만 한다. dashboard_v2·v3·v4와 저장소 최상위 .streamlit/config.toml은 고치지 않았다.
"""
from pathlib import Path

import streamlit as st

import shared

HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="사용자 위험 모니터링", layout="wide", initial_sidebar_state="expanded")
st.logo(str(HERE / "assets" / "sesac_security_logo_light.png"), size="large",
        icon_image=str(HERE / "assets" / "sesac_security_mark.png"))

R = shared.render()
st.html("<style>" + R.CSS + shared.sidebar_css(R.HEX_BG) + "</style>")

page = st.navigation(
    [st.Page("app_pages/user_risk.py", title="사용자 위험 현황", default=True),
     st.Page("app_pages/system.py", title="시스템 배경 활동", url_path="system")],
    position="sidebar",
)
lo, hi = R.PERIOD
with st.sidebar:
    st.html(f'<div class="side-meta">시스템 배경 활동 탭에 설정 위험과 외부 시도가 함께 있습니다.<br><br>'
            f'데이터 기간 (KST)<br><b>{lo:%Y-%m-%d} ~ {hi:%Y-%m-%d}</b><br>'
            f'데이터 안의 시각입니다. 실시간 관제가 아닙니다.</div>')
page.run()
