"""주가 업데이트 페이지"""
import os
import streamlit as st
from database import get_recommendations
from price_updater import update_prices, search_stock, refresh_stock_list, STOCK_LIST_PATH


def render():
    st.header("주가 업데이트")

    st.markdown("""
    추천 종목의 주가를 **네이버 금융**에서 자동으로 가져옵니다.
    - 활성 상태(추적중)인 추천 종목만 업데이트됩니다
    - 추천일부터 오늘까지의 일별 종가를 수집합니다
    - 모니터링 기간(30영업일) 초과 시 자동으로 '완료' 처리됩니다
    """)

    # 종목 리스트 상태
    st.subheader("종목 리스트 관리")
    if os.path.exists(STOCK_LIST_PATH):
        import json
        with open(STOCK_LIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.info(f"종목 리스트: **{data['count']}개** (최종 업데이트: {data['updated_at'][:16]})")
    else:
        st.warning("종목 리스트가 없습니다. 아래 버튼으로 가져와주세요.")

    if st.button("종목 리스트 갱신 (코스피+코스닥)"):
        with st.spinner("네이버 금융에서 전 종목 리스트를 가져오는 중... (약 30초~1분 소요)"):
            count = refresh_stock_list()
        st.success(f"총 {count}개 종목 리스트 갱신 완료!")
        st.rerun()

    st.markdown("---")

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
    st.subheader("주가 업데이트")
    if st.button("주가 업데이트 실행", type="primary"):
        if not active_recs:
            st.warning("추적중인 종목이 없습니다.")
        else:
            with st.spinner("네이버 금융에서 주가 데이터를 가져오는 중... (종목당 약 2~3초 소요)"):
                updated, msg = update_prices()
            st.success(msg)
            st.rerun()

    st.markdown("---")

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
            st.info("검색 결과가 없습니다. 종목 리스트를 갱신해보세요.")
