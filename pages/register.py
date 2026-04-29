"""종목 등록 - 인플루언서 + 종목을 한 화면에서 등록"""
import streamlit as st
import pandas as pd
from datetime import date
from database import (
    add_influencer, get_influencers, add_recommendation,
    get_recommendations, delete_influencer, update_recommendation_status
)
from price_updater import get_stock_code_by_name, get_current_price


def render():
    st.header("종목 등록")

    # === 간편 등록 (1단계) ===
    st.markdown("인플루언서명과 종목명만 입력하면 됩니다. 나머지는 자동 처리됩니다.")

    col_inf, col_stock, col_btn = st.columns([2, 2, 1])

    with col_inf:
        # 기존 인플루언서 목록 + 신규 입력
        influencers = get_influencers()
        inf_names = [inf["name"] for inf in influencers]
        inf_option = st.selectbox(
            "인플루언서",
            ["-- 직접 입력 (신규) --"] + inf_names,
            key="inf_select"
        )
        if inf_option == "-- 직접 입력 (신규) --":
            new_inf_name = st.text_input("새 인플루언서 이름", key="new_inf")
        else:
            new_inf_name = None

    with col_stock:
        stock_name = st.text_input("종목명", placeholder="예: 삼성전자", key="stock_input")
        rec_date = st.date_input("추천일", value=date.today(), key="rec_date")

    with col_btn:
        st.write("")
        st.write("")
        st.write("")
        register_clicked = st.button("등록", type="primary", use_container_width=True)

    if register_clicked:
        # 인플루언서 결정
        if inf_option == "-- 직접 입력 (신규) --":
            if not new_inf_name:
                st.error("인플루언서 이름을 입력해주세요")
                return
            inf_name = new_inf_name.strip()
            # 신규 등록
            success, msg = add_influencer(inf_name)
            if not success and "이미 등록" not in msg:
                st.error(msg)
                return
            # 등록 후 ID 조회
            influencers = get_influencers()
        else:
            inf_name = inf_option

        if not stock_name:
            st.error("종목명을 입력해주세요")
            return

        # 종목코드 + 현재가 자동 조회
        with st.spinner(f"'{stock_name}' 검색 중..."):
            code = get_stock_code_by_name(stock_name.strip())

        if not code:
            st.error(f"'{stock_name}'을 찾을 수 없습니다. 정확한 종목명을 입력해주세요.")
            return

        price = get_current_price(code)
        if not price:
            st.error("현재가를 가져올 수 없습니다.")
            return

        # 인플루언서 ID 찾기
        influencers = get_influencers()
        inf_id = next((inf["id"] for inf in influencers if inf["name"] == inf_name), None)
        if not inf_id:
            st.error("인플루언서 등록에 실패했습니다.")
            return

        add_recommendation(
            influencer_id=inf_id,
            stock_name=stock_name.strip(),
            stock_code=code,
            recommended_date=rec_date.isoformat(),
            recommended_price=price,
        )
        st.success(f"등록 완료: [{inf_name}] {stock_name} ({code}) - {price:,}원")
        st.rerun()

    # === 현재 등록된 종목 목록 ===
    st.markdown("---")
    st.subheader("등록된 추천 종목")

    recs = get_recommendations()
    if not recs:
        st.info("등록된 추천 종목이 없습니다.")
        return

    # 인플루언서별로 그룹화하여 표시
    df = pd.DataFrame(recs)

    for inf_name in df["influencer_name"].unique():
        inf_recs = df[df["influencer_name"] == inf_name]
        active_count = len(inf_recs[inf_recs["status"] == "active"])
        total_count = len(inf_recs)

        with st.expander(f"**{inf_name}** - 추적중 {active_count}건 / 전체 {total_count}건"):
            for _, rec in inf_recs.iterrows():
                col_info, col_action = st.columns([5, 1])
                with col_info:
                    status_icon = "🟢" if rec["status"] == "active" else "⚪"
                    st.write(f"{status_icon} **{rec['stock_name']}** ({rec['stock_code']}) "
                             f"- 추천가: {rec['recommended_price']:,.0f}원 "
                             f"| 추천일: {rec['recommended_date']}")
                with col_action:
                    if rec["status"] == "active":
                        if st.button("종료", key=f"close_{rec['id']}"):
                            update_recommendation_status(rec["id"], "completed")
                            st.rerun()

    # === 인플루언서 삭제 ===
    st.markdown("---")
    st.subheader("인플루언서 삭제")
    inf_to_delete = st.selectbox("삭제할 인플루언서", ["선택하세요"] + inf_names, key="del_inf")
    if inf_to_delete != "선택하세요":
        st.warning(f"'{inf_to_delete}'를 삭제하면 모든 추천 기록도 삭제됩니다.")
        if st.button("삭제 확인"):
            inf_id = next(inf["id"] for inf in influencers if inf["name"] == inf_to_delete)
            delete_influencer(inf_id)
            st.success(f"'{inf_to_delete}' 삭제 완료")
            st.rerun()
