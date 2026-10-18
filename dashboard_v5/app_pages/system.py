"""시스템 배경 활동: 시스템 계정(root, www-data, syslog)의 자동 활동 → 설정 위험 → 외부 로그인 시도."""
import streamlit as st

import shared

R = shared.render()
# 차트 SVG를 다시 넣는 스크립트가 필요해서 unsafe_allow_javascript를 켠다 (화면은 분석 결과로만 만든다)
st.html(shared.html_with_svgs(R.SYS_HTML), unsafe_allow_javascript=True)
