"""메인 앱 - Streamlit 진입점"""
import streamlit as st

st.set_page_config(
    page_title="주식 단타 관리 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 초기화
import database  # noqa: F401 (init_db 자동 실행)

st.sidebar.title("주식 단타 관리")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "메뉴",
    ["대시보드", "종목 등록", "매매 일지", "설정"]
)

if page == "대시보드":
    from pages import dashboard
    dashboard.render()
elif page == "종목 등록":
    from pages import register
    register.render()
elif page == "매매 일지":
    from pages import journal
    journal.render()
elif page == "설정":
    from pages import settings
    settings.render()
