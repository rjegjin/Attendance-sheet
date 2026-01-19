import streamlit as st
import sys
import os
import glob
import shutil
import webbrowser
import datetime
import json

# --------------------------------------------------------------------------
# 1. PATH CONFIGURATION & SECRETS SETUP (CRITICAL)
# 프로젝트 루트 경로 설정 및 필수 설정 파일(Key, Config) 자동 생성
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def create_file_from_secrets(filename, secret_key):
    """
    Streamlit Secrets에서 데이터를 읽어 로컬 json 파일을 생성하는 헬퍼 함수.
    이 함수가 있어야 서버에서 service_key.json과 config.json을 인식할 수 있습니다.
    """
    file_path = os.path.join(BASE_DIR, filename)
    
    # 파일이 이미 존재하면 굳이 다시 만들지 않음 (로컬 개발 환경 보호)
    if not os.path.exists(file_path):
        if secret_key in st.secrets:
            try:
                # Secrets 데이터를 딕셔너리로 가져옴
                data = dict(st.secrets[secret_key])
                
                # private_key의 줄바꿈 문자(\\n)가 문자열로 들어왔을 경우 실제 줄바꿈(\n)으로 치환
                # (service_key.json의 포맷 유지를 위해 필수)
                if 'private_key' in data:
                    data['private_key'] = data['private_key'].replace('\\n', '\n')
                
                # JSON 파일 생성 (한글 깨짐 방지 ensure_ascii=False)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                print(f"✅ [System] {filename} 파일이 Secrets로부터 생성되었습니다.")
            except Exception as e:
                print(f"❌ [Error] {filename} 생성 실패: {e}")
        else:
            # Secrets에 해당 섹션이 없는 경우
            print(f"⚠️ [Warning] Secrets에 '{secret_key}' 섹션이 없습니다. {filename}을 생성할 수 없습니다.")

# (1) 인증 키 파일 생성 (Secrets의 [gcp_service_account] 섹션 사용)
create_file_from_secrets('service_key.json', 'gcp_service_account')

# (2) 설정 파일 생성 (Secrets의 [app_config] 섹션 사용)
# "명렬표를 불러오지 못했습니다" 에러를 해결하기 위해 필수입니다.
create_file_from_secrets('config.json', 'app_config')

# --------------------------------------------------------------------------
# 2. IMPORT CUSTOM MODULES
# --------------------------------------------------------------------------
try:
    from src.services import data_loader
    from src.paths import REPORTS_DIR, CACHE_DIR
    
    # 리포트 생성기들 (Components)
    from src.components import universal_monthly_report_batch as monthly_gen
    from src.components import universal_fieldtrip_stats as fieldtrip_gen
    from src.components import universal_menstrual_stats as menstrual_gen
    from src.components import universal_long_term_absence as absence_gen
    from src.components import generate_checklist as checklist_gen
    from src.components import universal_weekly_summary_batch as weekly_gen
    from src.components import universal_calendar_batch as calendar_gen
    
except ImportError as e:
    st.error(f"❌ 모듈을 불러오는 중 오류가 발생했습니다: {e}")
    st.info("프로젝트 루트 폴더(app.py가 있는 위치)에서 실행했는지 확인해주세요.")
    st.stop()

# --------------------------------------------------------------------------
# 3. SETTINGS & PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="학급 출결 관리 시스템",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------------------------
# 4. HELPER FUNCTIONS
# --------------------------------------------------------------------------
def clear_cache_data():
    """캐시 폴더를 비우고 세션 상태를 초기화합니다."""
    if os.path.exists(CACHE_DIR):
        try:
            for filename in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            st.toast("🧹 캐시 데이터가 삭제되었습니다. 최신 데이터를 받아옵니다.", icon="✅")
        except Exception as e:
            st.error(f"캐시 삭제 실패: {e}")
    else:
        st.toast("캐시 폴더가 이미 비어있습니다.", icon="ℹ️")

def display_html_report(file_path, height=800):
    """생성된 HTML 파일을 읽어서 Streamlit에 iframe으로 표시합니다."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 다운로드 버튼 제공
        file_name = os.path.basename(file_path)
        st.download_button(
            label=f"📥 {file_name} 다운로드",
            data=html_content,
            file_name=file_name,
            mime="text/html"
        )
        
        # 미리보기 (iframe)
        st.components.v1.html(html_content, height=height, scrolling=True)
    else:
        st.warning(f"⚠️ 리포트 파일이 생성되지 않았거나 찾을 수 없습니다: {file_path}")

# --------------------------------------------------------------------------
# 5. SIDEBAR UI
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("🏫 출결 관리 시스템")
    st.markdown("---")
    
    # 1. 메뉴 선택
    menu = st.radio(
        "작업 선택",
        ["대시보드(Home)", "월별/학급별 리포트", "교외체험학습 통계", "생리인정결석 체크", "장기결석 경고 관리", "증빙서류 체크리스트", "주간 요약 & 달력"]
    )
    
    st.markdown("---")
    
    # 2. 월 선택 (멀티 셀렉트)
    st.write("📅 **분석 대상 월 선택**")
    # data_loader에 ACADEMIC_MONTHS가 있으면 사용, 없으면 기본값 사용
    all_months = getattr(data_loader, 'ACADEMIC_MONTHS', [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2])
    
    current_month = datetime.datetime.now().month
    # 학기 중인 월이 선택되도록 기본값 설정
    default_selection = [current_month] if current_month in all_months else [3]
    
    selected_months = st.multiselect(
        "월을 선택하세요",
        all_months,
        default=default_selection
    )
    
    st.markdown("---")
    
    # 3. 데이터 관리 (캐시 삭제)
    st.subheader("⚙️ 데이터 관리")
    if st.button("🔄 데이터 강제 새로고침 (캐시삭제)", type="primary"):
        clear_cache_data()
        # st.rerun() # Streamlit 버전에 따라 필요 시 주석 해제

# --------------------------------------------------------------------------
# 6. MAIN CONTENT ROUTING
# --------------------------------------------------------------------------

if menu == "대시보드(Home)":
    st.header("👋 환영합니다, 선생님!")
    st.markdown("""
    이 시스템은 **구글 스프레드시트**의 출결 데이터를 기반으로 다양한 통계 리포트를 자동 생성합니다.
    
    ### 👈 왼쪽 사이드바에서 메뉴를 선택해주세요.
    * **월별/학급별 리포트**: 나이스 업로드용 상세 내역 및 통계표
    * **통계 분석**: 체험학습, 생리인정, 장기결석 등 규정 위반 체크
    * **체크리스트**: 증빙서류 제출 현황 관리
    """)
    
    with st.spinner("명렬표 데이터를 확인 중입니다..."):
        try:
            # 여기서 config.json이나 service_key.json이 없으면 에러가 발생할 수 있음
            # 상단의 create_file_from_secrets 함수가 이를 방지함
            roster = data_loader.get_master_roster()
            if roster:
                st.success(f"✅ 명렬표 로드 완료: 총 {len(roster)}명의 학생 데이터가 준비되었습니다.")
            else:
                st.error("❌ 명렬표를 불러오지 못했습니다. 구글 시트 연결을 확인하세요.")
        except Exception as e:
            st.error(f"데이터 로드 중 오류 발생: {e}")
            st.warning("💡 힌트: 'service_key.json' 또는 'config.json' 파일이 생성되지 않았을 수 있습니다. Streamlit Secrets 설정을 확인해주세요.")

elif menu == "월별/학급별 리포트":
    st.subheader("📑 월별 상세 및 학급별 통계 리포트")
    
    if st.button("🚀 리포트 생성 시작"):
        if not selected_months:
            st.warning("월을 하나 이상 선택해주세요.")
        else:
            with st.spinner("데이터 분석 및 리포트 생성 중..."):
                monthly_gen.run_monthly_reports(target_months=selected_months)
            st.success("작업이 완료되었습니다!")
            
            tabs = st.tabs([f"{m}월" for m in selected_months])
            for i, month in enumerate(selected_months):
                with tabs[i]:
                    st.write(f"### {month}월 리포트 미리보기")
                    file_path = os.path.join(REPORTS_DIR, "monthly", f"{month:02d}월_학급별현황.html")
                    display_html_report(file_path)

elif menu == "교외체험학습 통계":
    st.subheader("🚌 교외체험학습 연간 통계")
    if st.button("📊 분석 실행"):
        with st.spinner("분석 중..."):
            fieldtrip_gen.run_fieldtrip_stats()
        st.success("완료!")
        file_path = os.path.join(REPORTS_DIR, "stats", "연간_체크_체험학습통계.html")
        display_html_report(file_path)

elif menu == "생리인정결석 체크":
    st.subheader("🩸 생리인정결석 규정 위반 체크")
    if st.button("🩸 분석 실행"):
        with st.spinner("분석 중..."):
            menstrual_gen.run_menstrual_stats()
        st.success("완료!")
        file_path = os.path.join(REPORTS_DIR, "stats", "생리인정결석_통계.html")
        display_html_report(file_path)

elif menu == "장기결석 경고 관리":
    st.subheader("📉 장기결석(질병/미인정) 경고 리포트")
    if st.button("📉 분석 실행"):
        with st.spinner("분석 중..."):
            absence_gen.run_long_term_absence()
        st.success("완료!")
        file_path = os.path.join(REPORTS_DIR, "stats", "장기결석_경고리포트.html")
        display_html_report(file_path)
        
elif menu == "증빙서류 체크리스트":
    st.subheader("✅ 증빙서류 제출 체크리스트")
    if st.button("📝 생성 실행"):
        with st.spinner("생성 중..."):
            checklist_gen.run_checklists(target_months=selected_months)
        st.success("완료!")
        
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, month in enumerate(selected_months):
            with tabs[i]:
                file_path = os.path.join(REPORTS_DIR, "checklist", f"{month:02d}월_증빙서류_체크리스트.html")
                display_html_report(file_path)

elif menu == "주간 요약 & 달력":
    st.subheader("📅 주간 요약 및 생활기록 달력")
    if st.button("📆 생성 실행"):
        with st.spinner("생성 중..."):
            weekly_gen.run_weekly(target_months=selected_months)
            calendar_gen.run_calendar(target_months=selected_months)
        st.success("완료!")
        st.info("결과 파일은 reports/weekly 및 reports/calendar 폴더에 저장되었습니다.")