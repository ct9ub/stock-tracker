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
    ["대시보드", "인플루언서 관리", "추천 종목 입력", "추천 종목 추적", "매매 일지", "주가 업데이트"]
)

if page == "대시보드":
    from pages import dashboard
    dashboard.render()
elif page == "인플루언서 관리":
    from pages import influencer
    influencer.render()
elif page == "추천 종목 입력":
    from pages import recommendation
    recommendation.render()
elif page == "추천 종목 추적":
    from pages import tracking
    tracking.render()
elif page == "매매 일지":
    from pages import journal
    journal.render()
elif page == "주가 업데이트":
    from pages import updater
    updater.render()
