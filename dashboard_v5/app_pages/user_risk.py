"""사용자 위험 현황: 요약 카드 → 날짜별 세션 → 위험 사용자 현황·평소와 다른 정도 → 점수가 있는 세션 → 경보 판정 기준.

표나 막대의 사용자를 누르면 '점수가 있는 세션' 그래프가 그 사용자의 위험행위 세션으로 바뀐다.
이 전환은 화면 안의 짧은 스크립트가 하므로 서버를 다시 부르지 않는다.
"""
import streamlit as st

import shared

R = shared.render()
st.html(shared.html_with_svgs(R.USER_HTML, R.JS), unsafe_allow_javascript=True)
