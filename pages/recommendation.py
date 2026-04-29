"""추천 종목 입력 페이지"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database import get_influencers, add_recommendation, get_recommendations


def render():
    st.header("추천 종목 입력")

    influencers = get_influencers()
    if not influencers:
        st.warning("먼저 '인플루언서 관리'에서 인플루언서를 등록해주세요.")
        return

    # === 입력 폼 ===
    st.subheader("새 추천 종목 등록")
    with st.form("add_rec", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            inf_names = {inf["name"]: inf["id"] for inf in influencers}
            selected_inf = st.selectbox("인플루언서 *", list(inf_names.keys()))
            stock_name = st.text_input("종목명 *", placeholder="예: 삼성전자")
            stock_code = st.text_input("종목코드", placeholder="예: 005930 (모르면 비워두세요)")
            recommended_date = st.date_input("추천일 *", value=date.today())

        with col2:
            recommended_price = st.number_input("추천 시점 주가 (원) *", min_value=0, step=100)
            target_price = st.number_input("목표가 (원)", min_value=0, step=100, value=0,
                                           help="인플루언서가 제시한 목표가 (없으면 0)")
            stop_loss_price = st.number_input("손절가 (원)", min_value=0, step=100, value=0,
                                              help="인플루언서가 제시한 손절가 (없으면 0)")
            memo = st.text_input("메모", placeholder="추천 사유, 영상 제목 등")

        if st.form_submit_button("등록"):
            if not stock_name:
                st.error("종목명을 입력해주세요")
            elif recommended_price <= 0:
                st.error("추천 시점 주가를 입력해주세요")
            else:
                add_recommendation(
                    influencer_id=inf_names[selected_inf],
                    stock_name=stock_name.strip(),
                    stock_code=stock_code.strip() if stock_code else "",
                    recommended_date=recommended_date.isoformat(),
                    recommended_price=recommended_price,
                    target_price=target_price if target_price > 0 else None,
                    stop_loss_price=stop_loss_price if stop_loss_price > 0 else None,
                    memo=memo
                )
                st.success(f"'{selected_inf}'의 추천 종목 '{stock_name}' 등록 완료!")
                st.rerun()

    # === 최근 등록 내역 ===
    st.subheader("최근 등록된 추천 종목")
    recs = get_recommendations()

    if not recs:
        st.info("등록된 추천 종목이 없습니다.")
        return

    df = pd.DataFrame(recs)
    display_cols = {
        "influencer_name": "인플루언서",
        "stock_name": "종목명",
        "stock_code": "종목코드",
        "recommended_date": "추천일",
        "recommended_price": "추천가",
        "target_price": "목표가",
        "stop_loss_price": "손절가",
        "status": "상태",
        "memo": "메모"
    }
    df_display = df[list(display_cols.keys())].rename(columns=display_cols)
    df_display["추천가"] = df_display["추천가"].apply(lambda x: f"{x:,.0f}" if x else "")
    df_display["목표가"] = df_display["목표가"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x else "")
    df_display["손절가"] = df_display["손절가"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x else "")
    df_display["상태"] = df_display["상태"].map({"active": "추적중", "completed": "완료"})

    st.dataframe(df_display, use_container_width=True, hide_index=True)
