"""대시보드 메인 페이지"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import (
    get_influencer_stats, get_recommendations, get_trades,
    get_price_tracking, get_influencers
)
from config import MIN_RECOMMENDATIONS


def render():
    st.header("대시보드")

    # === 전체 요약 ===
    influencers = get_influencers()
    all_recs = get_recommendations()
    active_recs = [r for r in all_recs if r["status"] == "active"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("등록 인플루언서", f"{len(influencers)}명")
    with col2:
        st.metric("총 추천 종목", f"{len(all_recs)}건")
    with col3:
        st.metric("현재 추적중", f"{len(active_recs)}건")

    if not all_recs:
        st.info("아직 데이터가 없습니다. '인플루언서 관리'에서 인플루언서를 등록하고, '추천 종목 입력'에서 추천 종목을 등록해주세요.")
        return

    st.markdown("---")

    # === 인플루언서 신뢰도 랭킹 ===
    st.subheader("인플루언서 신뢰도 랭킹")

    stats = get_influencer_stats()
    if stats:
        df_stats = pd.DataFrame(stats)
        df_stats = df_stats[df_stats["total_recs"] > 0]

        if not df_stats.empty:
            df_display = df_stats[["name", "total_recs", "hit_count", "hit_rate",
                                    "avg_return", "max_return", "min_return"]].copy()
            df_display.columns = ["인플루언서", "추천수", "적중수", "적중률(%)",
                                   "평균수익률(%)", "최고수익률(%)", "최저수익률(%)"]

            # 적중률 기준 정렬
            df_display = df_display.sort_values("적중률(%)", ascending=False)

            # 포맷팅
            for col in ["적중률(%)", "평균수익률(%)", "최고수익률(%)", "최저수익률(%)"]:
                df_display[col] = df_display[col].apply(lambda x: f"{x:.1f}")

            # 신뢰도 표시
            df_display.insert(0, "순위", range(1, len(df_display) + 1))

            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # 표본 수 경고
            low_sample = df_stats[df_stats["total_recs"] < MIN_RECOMMENDATIONS]
            if not low_sample.empty:
                names = ", ".join(low_sample["name"].tolist())
                st.caption(f"* {names}: 추천 수가 {MIN_RECOMMENDATIONS}건 미만이라 신뢰도가 낮을 수 있습니다.")
        else:
            st.info("추천 기록이 있는 인플루언서가 없습니다.")

    st.markdown("---")

    # === 현재 추적중인 종목 현황 ===
    st.subheader("추적중인 종목 현황")
    if active_recs:
        results = []
        for rec in active_recs:
            tracking = get_price_tracking(rec["id"])
            current_return = tracking[-1]["change_pct"] if tracking else None
            current_price = tracking[-1]["close_price"] if tracking else None
            days = tracking[-1]["days_since_rec"] if tracking else 0

            results.append({
                "인플루언서": rec["influencer_name"],
                "종목명": rec["stock_name"],
                "추천가": f"{rec['recommended_price']:,.0f}",
                "현재가": f"{current_price:,.0f}" if current_price else "미수집",
                "수익률": f"{current_return:+.2f}%" if current_return is not None else "-",
                "경과일": f"{days}일"
            })

        df_active = pd.DataFrame(results)
        st.dataframe(df_active, use_container_width=True, hide_index=True)
    else:
        st.info("현재 추적중인 종목이 없습니다.")

    st.markdown("---")

    # === 매매 일지 요약 ===
    st.subheader("이번 달 매매 요약")
    from datetime import date
    first_day = date(date.today().year, date.today().month, 1).isoformat()
    today = date.today().isoformat()
    trades = get_trades(first_day, today)

    if trades:
        df_trades = pd.DataFrame(trades)
        buy_total = df_trades[df_trades["action"] == "매수"]["total_amount"].sum()
        sell_total = df_trades[df_trades["action"] == "매도"]["total_amount"].sum()
        tax_total = df_trades["tax"].sum()
        trade_count = len(df_trades)

        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1:
            st.metric("총 매수", f"{buy_total:,.0f}원")
        with tc2:
            st.metric("총 매도", f"{sell_total:,.0f}원")
        with tc3:
            st.metric("거래세 합계", f"{tax_total:,.0f}원")
        with tc4:
            st.metric("거래 횟수", f"{trade_count}건")
    else:
        st.info("이번 달 매매 기록이 없습니다.")
