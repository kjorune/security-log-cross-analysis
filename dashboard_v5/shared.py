"""두 페이지가 같이 쓰는 화면 조각과 사이드바 꾸밈.

- render.py가 분석 결과 CSV를 읽어 HTML을 만든다. 결과 파일이 바뀌면 다시 만든다(수정 시각을 캐시 키로 씀).
- 파일이 없거나 읽지 못하면 오류를 보여주고 멈춘다. 0건으로 바꿔 그리지 않는다.
"""
import base64
import importlib
import re
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def _data_signature() -> tuple:
    return tuple(sorted((str(p.relative_to(DATA)), p.stat().st_mtime_ns) for p in DATA.rglob("*.csv")))


@st.cache_resource(max_entries=4, show_spinner="분석 결과를 읽는 중")
def _load(signature: tuple):
    import render
    return importlib.reload(render)


def render():
    try:
        return _load(_data_signature())
    except (FileNotFoundError, KeyError, ValueError) as err:
        st.error(f"분석 결과를 읽지 못했습니다: {err}")
        st.stop()


_SVG = re.compile(r"<svg[\s\S]*?</svg>")


def html_with_svgs(body: str, extra_js: str = "") -> str:
    """st.html은 넣은 HTML에서 <svg>를 지운다(1.62에서 확인). 차트 SVG를 빈 자리표로 바꾸고,
    화면이 뜬 뒤 스크립트가 원래 SVG를 다시 넣는다. 그래서 차트의 CSS와 누를 수 있는 이름표가 그대로 남는다."""
    # SVG 문자를 스크립트 안에 그대로 넣으면 스크립트째 지워져서, 자리표의 data 속성에 base64로 담는다
    body = _SVG.sub(lambda m: '<span class="svgslot" data-svg="'
                    + base64.b64encode(m.group(0).encode("utf-8")).decode() + '"></span>', body)
    js = ("document.querySelectorAll('.svgslot').forEach(el => {\n"
          "  const bytes = Uint8Array.from(atob(el.dataset.svg), c => c.charCodeAt(0));\n"
          "  el.outerHTML = new TextDecoder('utf-8').decode(bytes);\n"
          "});\n")
    return body + "<script>" + js + extra_js + "</script>"


def sidebar_css(hex_bg: str) -> str:
    """v2와 같은 남색 사이드바와 육각 무늬. 그라데이션은 쓰지 않는다."""
    return f"""
[data-testid="stSidebar"] {{ background:#061c52 url("{hex_bg}") !important; border-right:1px solid #1b3f8f; }}
[data-testid="stSidebarNav"] a {{ border-radius:8px; }}
[data-testid="stSidebarNav"] a span {{ color:rgba(230,241,255,0.86); font-weight:600; }}
[data-testid="stSidebarNav"] a:hover {{ background:rgba(47,224,247,0.08); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background:rgba(47,224,247,0.16); box-shadow:inset 3px 0 0 #35d6f5; }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color:#ffffff; font-weight:800; }}
.side-meta {{ margin-top:6px; padding:12px 4px 0; border-top:1px solid rgba(255,255,255,0.14); font-size:12px;
  color:rgba(220,236,255,0.72); line-height:1.6; }}
.side-meta b {{ color:#ffffff; font-weight:600; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.stMainBlockContainer {{ max-width:1500px; padding-top:1.6rem; }}
"""
