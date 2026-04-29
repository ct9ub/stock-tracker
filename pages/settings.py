"""설정 페이지 - 종목 리스트 갱신, 수동 주가 업데이트 등"""
import os
import json
import streamlit as st
from database import get_recommendations
from price_updater import update_prices, refresh_stock_list, search_stock, STOCK_LIST_PATH


def render():
    st.header("설정")

    # === 종목 리스트 관리 ===
    st.subheader("종목 리스트 관리")
    st.caption("종목 검색에 필요한 코스피/코스닥 전 종목 목록입니다. 최초 1회 갱신이 필요합니다.")

    if os.path.exists(STOCK_LIST_PATH):
        with open(STOCK_LIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.info(f"종목 리스트: **{data['count']}개** (최종 업데이트: {data['updated_at'][:16]})")
    else:
        st.warning("종목 리스트가 없습니다. 아래 버튼으로 가져와주세요.")

    if st.button("종목 리스트 갱신 (코스피+코스닥)"):
        with st.spinner("네이버 금융에서 전 종목 리스트를 가져오는 중... (약 30초~1분)"):
            count = refresh_stock_list()
        st.success(f"총 {count}개 종목 리스트 갱신 완료!")
        st.rerun()

    st.markdown("---")

    # === 수동 주가 업데이트 ===
    st.subheader("수동 주가 업데이트")
    st.caption("대시보드 접속 시 자동 업데이트되지만, 수동으로도 실행할 수 있습니다.")

    active_recs = get_recommendations(status="active")
    st.info(f"현재 추적중인 종목: **{len(active_recs)}개**")

    if st.button("주가 업데이트 실행", type="primary"):
        if not active_recs:
            st.warning("추적중인 종목이 없습니다.")
        else:
            with st.spinner("네이버 금융에서 주가 데이터를 가져오는 중..."):
                updated, msg = update_prices()
            st.success(msg)

    st.markdown("---")

    # === 종목코드 검색 ===
    st.subheader("종목코드 검색")
    keyword = st.text_input("종목명 검색", placeholder="예: 삼성")
    if keyword and len(keyword) >= 2:
        results = search_stock(keyword)
        if results:
            for r in results:
                st.write(f"**{r['name']}** - `{r['code']}`")
        else:
            st.info("검색 결과가 없습니다.")
