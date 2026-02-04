# 🏫 학급 출결 관리 통합 시스템 (Attendance Management System)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-ff4b4b?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Sheets API](https://img.shields.io/badge/Google%20Sheets-API-green?logo=google-sheets&logoColor=white)](https://developers.google.com/sheets/api)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **구글 스프레드시트(Google Sheets)**에 입력된 실시간 출결 데이터를 기반으로, **나이스(NEIS) 업로드용 리포트, 생활기록 달력, 각종 통계 자료**를 자동으로 생성하는 교무 업무 자동화 솔루션입니다.
>
> **✨ 2026학년도 버전 업데이트 완료:** 연도별 자동 시트 전환 및 UI 모듈화 적용.

---

## ✨ 주요 기능 (Key Features)

이 시스템은 다음과 같은 기능을 제공합니다:

### 1. 📄 기본 리포트 생성
* **🗓️ 생활기록 달력**: 월별 학생들의 출결 및 특이사항이 기록된 달력 HTML 생성.
* **📊 월별/학급별 리포트**: 나이스 업로드용 상세 내역 및 학급 통계표 생성.
* **📑 주간 요약**: 주 단위 출결 현황 요약 리포트.
* **✅ 증빙서류 체크리스트**: 결석계 등 서류 제출 현황 관리 및 미제출자 체크리스트 생성.

### 2. 📊 통계 및 규정 관리
* **🚌 교외체험학습 통계**: 연간 사용 일수(국내/국외) 및 연속 사용 일수 규정 위반 자동 체크.
* **🩸 생리인정결석 체크**: 월별 사용 횟수, 공휴일/주말 연계 사용 등 규정 위반 패턴 감지.
* **📉 장기결석 경고**: 질병/미인정 결석의 장기화 추세 분석 및 경고 리포트.

### 3. 📅 학사일정 및 자동화
* **🔄 학사일정 동기화**: 학교 전체 학사일정(Google Sheets)을 파싱하여 시스템 휴일 데이터(`holidays_202X.json`) 자동 업데이트.
* **🔔 알림 센터**: 텔레그램 봇과 연동하여 오늘의 출결 현황 브리핑 및 공지사항 발송.
* **⚙️ 자동 연도 전환**: `config.json` 설정에 따라 연도별 스프레드시트 자동 연결.

### 4. 🖥 사용자 인터페이스 (Dual Mode)
* **🅰️ CLI 모드 (`main_controller.py`)**: 
    * 터미널 환경에서 빠르고 간편하게 메뉴 선택.
    * 자동화 스크립트 실행 및 대량 작업에 최적화.
* **🅱️ Web 모드 (`app.py`)**: 
    * **Streamlit** 기반의 직관적인 GUI 대시보드.
    * 결과물(HTML) 즉시 미리보기 및 다운로드 지원.

---

## 📦 설치 및 환경 설정

### 1. 필수 요구 사항
* Python 3.9 이상
* Google Cloud Platform (GCP) 서비스 계정 키 (`service_key.json`)
* Telegram Bot Token (알림 기능 사용 시)

### 2. 라이브러리 설치
필요한 Python 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

### 3. 설정 파일 (Configuration)
`config.json`을 통해 연도별 스프레드시트 ID와 학교 정보를 관리합니다.
(Streamlit Cloud 사용 시 `secrets.toml`에 `[app_config]` 섹션으로 등록 가능)

```json
{
    "target_year": 2026,
    "spreadsheets": {
        "2025": "https://docs.google.com/spreadsheets/d/ID_FOR_2025...",
        "2026": "https://docs.google.com/spreadsheets/d/ID_FOR_2026..."
    }
}
```

---

## 🚀 실행 방법

### 방법 1: CLI (터미널) 모드
터미널에서 메뉴를 선택하여 원하는 작업을 수행합니다.

```bash
python main_controller.py
```

* **메뉴 구성**:
    * `1`: 리포트 세트 생성 (달력/월별/주간/체크리스트)
    * `2~4`: 통계 분석 (체험학습/생리결석/장기결석)
    * `5`: 학사일정 업데이트 (구글 시트 연동)
    * `7`: 아침 브리핑 발송
    * `10`: 캐시 데이터 삭제

### 방법 2: Web (Streamlit) 모드
웹 브라우저에서 시각적인 대시보드를 사용합니다.

```bash
streamlit run app.py
```

---

## 📂 프로젝트 구조

```text
Attendance-sheet/
├── app.py                  # [WEB] Streamlit 메인 진입점 (Router)
├── main_controller.py      # [CLI] 터미널 메인 컨트롤러
├── config.json             # (User) 연도별 설정 및 시트 URL 관리
├── service_key.json        # (Secret) GCP 인증 키
├── src/
│   ├── components/         # [Logic] 핵심 기능 구현 (리포트 생성, 통계 로직)
│   │   ├── universal_monthly_report_batch.py
│   │   ├── school_schedule_manager.py
│   │   └── ...
│   ├── services/           # [Service] 데이터 로더, 설정 관리
│   │   ├── data_loader.py
│   │   └── config_manager.py
│   ├── ui/                 # [UI] Streamlit 화면 구성 (Page Pattern)
│   │   ├── dashboard.py
│   │   ├── weekly_calendar.py
│   │   └── ...
│   ├── utils/              # [Util] 공통 유틸리티 (날짜 계산 등)
│   ├── templates/          # [View] HTML 보고서 템플릿
│   └── paths.py            # [Config] 경로 상수 정의
└── reports/                # [Output] 결과물 저장소
    ├── calendar/           # 생활기록 달력
    ├── monthly/            # 월별/학급별 리포트
    ├── stats/              # 각종 통계 리포트
    └── ...
```

---

## 📝 개발 이력 및 참고
* **v2.1 (2026.02)**: UI 코드를 `src/ui`로 모듈화(Page Router 패턴), 연도별 시트 자동 전환 기능 추가, 학사일정 매니저 통합.
* **캐시 시스템**: `pickle`을 사용하여 API 호출을 최소화합니다. 데이터 갱신이 안 될 경우 `캐시 삭제` 기능을 이용하세요.
* **복원 기능**: HTML 리포트 내용을 역파싱하여 시트로 복구하는 기능은 템플릿 구조 변경 시 오작동할 수 있습니다.

---
Developed for efficient school administration.