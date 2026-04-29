"""주가 업데이트 페이지"""
import streamlit as st
from database import get_recommendations
from price_updater import update_prices, search_stock


def render():
    st.header("주가 업데이트")

    st.markdown("""
    추천 종목의 주가를 **PyKRX**에서 자동으로 가져옵니다.
    - 활성 상태(추적중)인 추천 종목만 업데이트됩니다
    - 추천일부터 오늘까지의 일별 종가를 수집합니다
    - 모니터링 기간(30영업일) 초과 시 자동으로 '완료' 처리됩니다
    """)

    # 현재 활성 종목 수
    active_recs = get_recommendations(status="active")
    st.info(f"현재 추적중인 종목: **{len(active_recs)}개**")

    if active_recs:
        with st.expander("추적중인 종목 목록"):
            for rec in active_recs:
                code_info = f" ({rec['stock_code']})" if rec['stock_code'] else ""
                st.write(f"- [{rec['influencer_name']}] {rec['stock_name']}{code_info} "
                         f"(추천일: {rec['recommended_date']}, 추천가: {rec['recommended_price']:,.0f}원)")

    # 업데이트 실행
    st.subheader("수동 업데이트")
    if st.button("주가 업데이트 실행", type="primary"):
        if not active_recs:
            st.warning("추적중인 종목이 없습니다.")
        else:
            with st.spinner("주가 데이터를 가져오는 중... (종목당 약 1~2초 소요)"):
                updated, msg = update_prices()
            st.success(msg)
            st.rerun()

    # 종목 검색 도우미
    st.subheader("종목코드 검색")
    st.caption("추천 종목 입력 시 종목코드를 모르면 여기서 검색하세요.")
    keyword = st.text_input("종목명 검색", placeholder="예: 삼성")
    if keyword and len(keyword) >= 2:
        with st.spinner("검색 중..."):
            results = search_stock(keyword)
        if results:
            for r in results:
                st.write(f"**{r['name']}** - `{r['code']}`")
        else:
            st.info("검색 결과가 없습니다.")
