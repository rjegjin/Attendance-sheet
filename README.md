# 🏫 학급 출결 관리 통합 시스템 (Attendance Management System)

구글 스프레드시트(Google Sheets)에 입력된 출결 데이터를 기반으로, 나이스(NEIS) 업로드용 리포트, 생활기록 달력, 각종 통계 자료를 자동으로 생성하는 Python 프로젝트입니다.

## ✨ 주요 기능

이 시스템은 다음과 같은 기능을 제공합니다:

1.  **📄 기본 리포트 생성**
    *   **생활기록 달력**: 월별 학생들의 출결 및 특이사항이 기록된 달력 HTML 생성
    *   **월별/학급별 리포트**: 나이스 업로드용 상세 내역 및 학급 통계표 생성
    *   **주간 요약**: 주 단위 출결 현황 요약
    *   **증빙서류 체크리스트**: 결석계 등 서류 제출 현황 관리 및 체크리스트 생성

2.  **📊 통계 및 규정 관리**
    *   **교외체험학습 통계**: 연간 사용 일수(국내/국외) 및 연속 사용 일수 규정 위반 체크
    *   **생리인정결석 체크**: 월별 사용 횟수 및 기타 결석과의 중복 사용 등 규정 위반 체크
    *   **장기결석 경고**: 질병/미인정 결석의 장기화 경고 리포트

3.  **🛠 유틸리티**
    *   **데이터 복원**: 생성된 HTML 리포트 데이터를 역파싱하여 구글 시트로 복구 (`restore_from_html_to_gsheet.py`)
    *   **통합 인덱스**: 생성된 모든 월별 리포트를 쉽게 탐색할 수 있는 네비게이션 페이지 생성
    *   **OneDrive 연동**: `setup.py`를 통해 로컬 데이터 폴더와 OneDrive 폴더 동기화 (Windows Junction)

4.  **🖥 사용자 인터페이스**
    *   **CLI 모드**: `main_controller.py`를 통한 터미널 메뉴 방식
    *   **Web 모드**: `app.py`를 통한 Streamlit 대시보드 방식

## 📦 설치 및 환경 설정

### 1. 필수 요구 사항
*   Python 3.8 이상
*   Google Cloud Platform 서비스 계정 키 (`service_key.json`)

### 2. 라이브러리 설치
필요한 Python 라이브러리를 설치합니다.

```bash
pip install pandas jinja2 streamlit gspread oauth2client beautifulsoup4
```

### 3. 구글 시트 연동 설정
프로젝트 루트 경로에 GCP 서비스 계정 키 파일(`service_key.json`)이 필요합니다.
*   Streamlit 사용 시 `.streamlit/secrets.toml`에 설정을 저장하면 `app.py` 실행 시 자동으로 파일을 생성합니다.

### 4. 폴더 연결 (선택 사항)
OneDrive 등을 사용하여 데이터를 동기화하는 경우, 아래 스크립트를 실행하여 폴더 바로가기(Junction)를 생성할 수 있습니다. (Windows 전용)

```bash
python setup.py
```

## 🚀 실행 방법

### 방법 1: CLI (터미널) 모드
가장 기본적인 실행 방법으로, 메뉴를 선택하여 원하는 작업을 수행합니다.

```bash
python main_controller.py
```

*   **주요 메뉴**:
    *   `1`: 기본 리포트 세트 생성 (달력, 월별, 주간, 체크리스트)
    *   `2~4`: 각종 통계 분석
    *   `5`: HTML 리포트 내용을 구글 시트로 복원
    *   `6`: 전체 작업 일괄 수행
    *   `9`: 체크리스트 업데이트 파일 반영

### 방법 2: Web (Streamlit) 모드
웹 브라우저에서 시각적인 대시보드를 통해 작업을 수행하고 결과를 미리볼 수 있습니다.

```bash
streamlit run app.py
```

## 📂 프로젝트 구조

```
Attendance-sheet/
├── app.py                  # Streamlit 웹 애플리케이션 진입점
├── main_controller.py      # CLI 메인 컨트롤러
├── setup.py                # 폴더 연동 설정 스크립트
├── service_key.json        # (생성 필요) GCP 인증 키
├── src/
│   ├── components/         # 핵심 기능 모듈 (리포트 생성, 통계 등)
│   │   ├── universal_monthly_report_batch.py
│   │   ├── universal_calendar_batch.py
│   │   ├── generate_checklist.py
│   │   └── ...
│   ├── services/           # 데이터 로딩 및 공통 서비스
│   │   └── data_loader.py
│   ├── templates/          # Jinja2 HTML 템플릿 파일
│   └── paths.py            # 경로 상수 정의
└── reports/                # (자동 생성) 결과물 저장 폴더
    ├── calendar/           # 생활기록 달력
    ├── monthly/            # 월별/학급별 리포트
    ├── weekly/             # 주간 요약
    ├── checklist/          # 증빙서류 체크리스트
    ├── stats/              # 각종 통계 리포트
    └── index/              # 통합 네비게이션 인덱스
```

## 📝 참고 사항

*   **캐시 관리**: 데이터 로딩 속도를 위해 캐시를 사용합니다. 데이터가 갱신되지 않을 경우 메뉴에서 '캐시 삭제'를 수행하세요.
*   **복원 기능**: `restore_from_html_to_gsheet.py`는 HTML 구조에 의존하므로, 템플릿이 변경되면 동작하지 않을 수 있습니다.

---
Developed for efficient school administration.