# 사용자 위험 대시보드 v5

2026-10-18 확정한 시안(`teiren_siem/output/dashboard_mockup/user_risk_monitor_mockup_v2style.html`)을 Streamlit 앱으로 옮겼다. 분석 결과 CSV를 읽기만 하며, `dashboard_v2`·`v3`·`v4`와 저장소 최상위 `.streamlit/config.toml`은 고치지 않았다.

## 실행

저장소 최상위에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard_v5/app.py
```

`.venv`가 없으면 먼저 만든다.

```powershell
uv venv .venv --python 3.13
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

## 화면

왼쪽 탭은 두 개다. 사이드바는 v2와 같은 남색 바탕과 육각 무늬이고, 맨 위에 v2 로고(`assets/`)가 있다.

| 탭 | 내용 |
| --- | --- |
| 사용자 위험 현황 | 요약 카드(경보 사용자 4, 위험 3, 전체 사용자 8), 날짜별 세션 수, 위험 사용자 현황 표, 안 울린 경보의 평소와 다른 정도, 점수가 있는 세션, 안 울린 경보 사용자의 위험행위, 경보 판정 기준(규칙 기반 14개, 행동 기반 9개) |
| 시스템 배경 활동 | 시스템 계정 자동 활동(root, www-data, syslog), 설정 위험(MFA 없는 최상위 계정 로그인), 외부 로그인 시도 |

- 경보는 빨강(`#d03b3b`), 위험(안 울린 경보)은 노랑(`#fab219`)이다. 숫자 카드는 아래 음영으로 구분한다.
- 표의 사용자 이름이나 '세션 보기', 그래프의 사용자 이름을 누르면 '점수가 있는 세션' 그래프가 그 사용자의 위험행위 세션으로 바뀐다. '전체 보기'로 돌아간다. 주소에 `#user=analyst01`처럼 남아 새로고침해도 유지된다.
- 화면 폭이 1760px보다 좁으면 패널이 위아래로 쌓인다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `app.py` | 페이지 설정, 로고, 사이드바, 두 페이지 연결 |
| `render.py` | 분석 결과 CSV로 두 페이지의 HTML과 CSS, 클릭 스크립트를 만든다 (시안 스크립트를 옮긴 것) |
| `shared.py` | `render.py` 결과를 캐시하고(결과 파일 수정 시각이 바뀌면 다시 만듦), 사이드바 CSS와 차트 SVG 넣기를 맡는다 |
| `app_pages/user_risk.py`, `app_pages/system.py` | 각 페이지를 그린다 |
| `.streamlit/config.toml` | v5 전용 테마 (앱 파일 옆 설정이라 저장소 최상위 설정보다 먼저 적용) |

## 구현할 때 확인한 점 (Streamlit 1.62)

- `st.html`은 넣은 HTML에서 `<svg>`를 지운다. 그래서 차트 SVG를 base64로 자리표에 담고, 화면이 뜬 뒤 스크립트가 원래 SVG를 넣는다(`shared.html_with_svgs`). 이 때문에 두 페이지 모두 `unsafe_allow_javascript=True`를 쓴다. 넣는 HTML은 분석 결과 CSV로만 만든다.
- 스크립트 안에 SVG 문자열을 그대로 넣으면 스크립트째 지워진다. base64로 넣는 이유다.
- `shared.py`, `render.py`를 고치면 Streamlit이 다시 읽지 않을 수 있다. 서버를 다시 시작한다.

## 검증

```powershell
.\.venv\Scripts\python.exe scripts\101_verify_dashboard_v5.py
```

두 페이지가 오류 없이 실행되는지, 요약 숫자(4, 3, 8), 표 순서, 경보·위험 배지 수, 사용자별 그래프 7개, 판정 기준 표(14, 9), 시스템 카드(20, 10, 24, 4,079), 외부 시도 카드(3, 161, 5, 0)를 확인한다. 2026-10-18 결과: 15/15 통과.

화면 안의 스크립트(차트 표시, 사용자 클릭 전환)는 AppTest로 확인할 수 없어 브라우저에서 따로 확인했다(1920px, 1440px). 차트 18개가 모두 보이고, analyst01을 누르면 표의 행이 칠해지며 그래프가 S132·S053의 위험행위로 바뀌었다.

## 아직 없는 것

- 사용자 상세 페이지. 표의 '세션 보기'는 같은 화면의 그래프를 바꾼다.
- 판단 문서 7.1의 추가 사항 중 동일인 후보 근거, 원문 보기, 판정 기록.
