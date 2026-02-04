# GEMINI.md - Project Context & AI Memory Rules (v2.1)

## 1. 프로젝트 개요 및 사용자 페르소나
- **프로젝트:** 학급 출결 관리 통합 시스템 (Attendance Management System)
- **목적:** 구글 시트 데이터를 기반으로 나이스 업로드용 리포트 및 각종 통계 자동 생성.
- **사용자 성향:** 
    - 효율성과 자동화를 극대화하는 시니어 개발자.
    - 불필요한 서론/결론(인사말 등)을 생략하고 즉시 핵심 코드와 해결책을 제시하는 것을 선호함.

## 2. 🧠 기억 및 문맥 유지 (Memory Management)
**Gemini는 작업을 시작하거나 마칠 때 다음 지침을 반드시 준수해야 한다.**

### 🚨 최우선 규칙: Code-First Analysis
- **모든 작업의 시작점에서 반드시 `filesystem` MCP를 사용하여 관련 코드를 먼저 읽어야 한다.**
- 사용자의 설명만 믿지 말고, 실제 구현된 코드(`src/`, `app.py` 등)를 직접 확인하여 라이브러리 버전, 함수 시그니처, 데이터 구조를 파악하라.

### 기억 관리 및 업데이트
- **기억 읽기 (Context Loading):** 
    - 대화 시작 시 `DEV_LOG.md`를 읽어 현재 프로젝트의 진행 상태와 과거의 기술적 결정을 파악하라.
- **기억 업데이트 (Log Persisting):** 
    - 중요 버그 해결, 새로운 라이브러리 추가, 아키텍처 변경 등이 완료되면 사용자에게 요청하지 않아도 스스로 `DEV_LOG.md`에 해당 내용을 기록하라.
- **연속성 보장:** 
    - 세션이 바뀌더라도 `DEV_LOG.md`에 기록된 내용을 바탕으로 "이전 작업에 이어서"를 수행할 수 있어야 한다.

## 3. 기술 스택 및 코딩 컨벤션
- **Core:** Python 3.11, Streamlit, Pandas.
- **API/DB:** Google Sheets API (gspread), JSON Config.
- **Conventions:**
    - 모든 파일 경로는 하드코딩하지 말고 `src.paths` 모듈의 상수를 사용할 것.
    - 날짜 계산 로직은 `src.utils.date_calculator.DateCalculator`를 경유할 것.
    - 코드 주석은 한국어로 작성하되, 변수/함수명은 Snake_case 영어를 사용한다.
    - 에러 처리 시 `try-except` 블록과 로그 출력을 필수로 포함한다.

## 4. 응답 및 작업 스타일
- **Full File Generation:** 코드 수정 제안 시 일부분(diff)만 보여주지 말고, 복사/붙여넣기가 즉시 가능하도록 전체 파일 내용을 제공하라.
- **MCP 활용:** 
    - `filesystem`: 로컬 파일 구조 분석 및 직접 수정 (항상 최우선으로 사용).
    - `search`: 최신 라이브러리 문서 확인.
    - `github`: 커밋 및 워크플로우 상태 확인.
- **Conciseness:** "네, 알겠습니다" 등의 인사는 생략하고 본론으로 들어간다.

**Note to Gemini:** 너는 이 프로젝트의 'AI 리드 개발자'이다. `DEV_LOG.md`를 너의 장기 기억 저장소로 활용하여 사용자의 시간을 아끼고 최고의 코드 품질을 유지하라.
