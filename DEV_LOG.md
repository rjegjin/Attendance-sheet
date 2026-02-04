📚 Development Log & Memory
🛠️ 환경 설정 및 장애 복구 (2026-02-04)
[Issue-04] MCP 서버 Discovery 실패 (Invalid Configuration)
현상: filesystem 서버 실행 시 missing command 에러 발생. github/search 서버 Connection closed 에러 발생.
원인: 1. filesystem 등록 시 실행 명령어(npx ...)가 누락되고 경로만 전달됨.
2. stdio 전송 방식에서 실행 환경(Node.js)의 경로 인식 문제.
해결: 1. gemini mcp remove로 기존 설정 초기화.
2. gemini mcp add <name> "<command>" 형식을 준수하여 재등록.
3. filesystem의 경우 실행 커맨드 내부에 작업 디렉토리 경로를 명시적으로 포함함.
💡 주요 해결 이력 (Solved Issues)
[2026-02-04] GEMINI.md 업데이트 (v2.1): 'Code-First Analysis' 규칙 강화 및 filesystem MCP 활용 강조.
[2026-02-04] MCP 서버 수동 재설정 및 연결 성공.
[2026-02-04] MCP 서버 상태 확인 (gemini mcp list) 완료.
[2026-02-04] DateCalculator.py 분석 완료 (src.paths 미사용 및 Type Hinting 부재 확인).
[2026-02-04] DateCalculator.py 리팩토링 완료 (src.paths 적용, Type Hinting 추가).
[2026-02-04] src/utils 내 유틸리티 사용처 전수 조사 완료.
[2026-02-04] TemplateManager, universal_calendar_batch, daily_alert_system 리팩토링 완료 (src.paths 적용).
[2026-02-04] school_schedule_manager.py 리팩토링 및 src/components 이동 완료.
[2026-02-04] app.py(Streamlit) 및 main_controller.py(CLI)에 학사일정 관리 기능 통합 완료.
[2026-02-04] [Bug-Fix] SchoolScheduleManager의 월간 롤오버(Row-span) 오류 수정 (31일 이후 1일 감지 시 월 자동 증가).
[2026-02-04] [Hot-Fix] app.py '주간 요약 & 달력' 섹션 코드 누락 복구 (탭 반복 루프 소실 복원).
[2026-02-04] [Refactor] app.py 모듈화 (Page Router 패턴 적용) 완료.
  - UI 코드를 `src/ui/` 패키지로 분리.
  - `app.py`는 라우팅 및 상태 관리만 담당.
[2026-02-04] [Fix] app.py 사이드바 '전체 선택/해제' 버튼 기능 추가.
[2026-02-04] [Fix] main_controller.py 5번 메뉴(학사일정) 들여쓰기 오류 및 무한 루프 증상 해결.
[2026-02-04] [Policy] PowerShell 환경 호환성을 위해 쉘 명령어 실행 시 `&&` 사용 금지 원칙 수립.

📌 다음 작업 예약 (To-Do)
[ ] 리팩토링된 모듈들의 통합 테스트.
[ ] 구글 시트 API 연결 테스트 (실제 서비스 키 필요).