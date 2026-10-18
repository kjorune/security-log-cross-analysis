"""dashboard_v5를 실행해 두 페이지의 화면 내용과 숫자를 확인한다.

실행 (저장소 최상위에서): .venv\\Scripts\\python.exe scripts\\101_verify_dashboard_v5.py
- 화면 코드와 결과 파일은 고치지 않는다. 확인만 한다.
- 사용자 클릭 전환과 차트 표시는 화면 안의 스크립트가 하므로 브라우저에서 따로 확인한다(README 참고).
"""
import io
import logging
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard_v5"
sys.path.insert(0, str(APP))
logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest  # noqa: E402

results = []


def check(cid, title, ok, detail=""):
    results.append((cid, title, bool(ok), detail))


def page_html(at):
    return " ".join(h.proto.body for h in at.get("html"))


with redirect_stderr(io.StringIO()):
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=120).run()
html = page_html(at)
check("U1", "사용자 위험 현황이 오류 없이 실행된다", not at.exception and not at.error,
      "; ".join(str(e.value)[:80] for e in list(at.exception) + list(at.error)))
kn = re.findall(r'<div class="kn">(?:<span>)?([\d,]+)', html)
check("U2", "요약 카드 숫자: 경보 사용자 4, 위험 3, 전체 사용자 8", kn[:3] == ["4", "3", "8"], ", ".join(kn[:3]))
rows = re.findall(r'<tr data-user="([^"]+)"', html)
check("U3", "위험 사용자 현황 표 7명, 순서 analyst01·dev02·ops02·intern01·ops01·admin01·web01",
      rows == ["analyst01", "dev02", "ops02", "intern01", "ops01", "admin01", "web01"], ", ".join(rows))
check("U4", "경보 배지 4개, 위험 배지 3개",
      html.count('<span class="pill red">▲ 경보</span>') == 4 and html.count('<span class="pill yel">◆ 위험</span>') == 3)
views = re.findall(r'class="sv-view" data-view="([^"]+)"', html)
check("U5", "점수가 있는 세션: 전체 보기 1개와 사용자별 보기 7개를 미리 그린다", views == ["all"] + rows, ", ".join(views))
check("U6", "경보 판정 기준 표: 규칙 기반 14개, 행동 기반 9개", "규칙 기반 14개" in html and "행동 기반 9개" in html)
check("U7", "차트 SVG는 자리표로 바뀌어 스크립트가 다시 넣는다", html.count('class="svgslot"') >= 10 and "<svg" not in html,
      f"자리표 {html.count('class=\"svgslot\"')}개")
check("U8", "서버별 위험점수가 없다", "서버별 위험점수" not in html and "node-01 260" not in html)

with redirect_stderr(io.StringIO()):
    at.switch_page("app_pages/system.py").run()
sys_html = page_html(at)
check("S1", "시스템 배경 활동이 오류 없이 실행된다", not at.exception, "; ".join(str(e.value)[:80] for e in at.exception))
for cid, text, title in [("S2", "시스템 계정 자동 활동", "시스템 계정 자동 활동 구역"),
                         ("S3", "설정 위험 <span>", "설정 위험 구역 (합친 탭)"),
                         ("S4", "외부 로그인 시도 <span>", "외부 로그인 시도 구역 (합친 탭)"),
                         ("S5", "서버에 없는 계정", "admin을 서버에 없는 계정으로 표시")]:
    check(cid, title, text in sys_html)
kn = re.findall(r'<div class="kn">([\d,]+)', sys_html)
check("S6", "시스템 카드: 신호 20, 처음 보는 활동 10, 반복 24, 자동 실행 4,079 (위험 신호가 왼쪽)",
      kn[:4] == ["20", "10", "24", "4,079"], ", ".join(kn[:4]))
check("S7", "외부 시도 카드: IP 3, 시도 161, 계정명 5, 성공 0", kn[4:8] == ["3", "161", "5", "0"], ", ".join(kn[4:8]))

fails = 0
for cid, title, ok, detail in results:
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {cid:3} {title}" + (f"  [{detail}]" if detail else ""))
print(f"\n{len(results) - fails}/{len(results)} 통과")
sys.exit(1 if fails else 0)
