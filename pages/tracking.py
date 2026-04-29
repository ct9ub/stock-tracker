"""추천 종목 추적 페이지 - 주가 추이 및 수익률 확인"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_recommendations, get_price_tracking, get_influencers


def render():
    st.header("추천 종목 추적")

    recs = get_recommendations()
    if not recs:
        st.info("등록된 추천 종목이 없습니다. '추천 종목 입력'에서 먼저 등록해주세요.")
        return

    # === 필터 ===
    col1, col2 = st.columns(2)
    with col1:
        influencers = get_influencers()
        inf_options = {"전체": None}
        inf_options.update({inf["name"]: inf["id"] for inf in influencers})
        selected_inf = st.selectbox("인플루언서 필터", list(inf_options.keys()))

    with col2:
        status_filter = st.selectbox("상태 필터", ["전체", "추적중", "완료"])

    # 필터 적용
    filtered = recs
    if inf_options[selected_inf]:
        filtered = [r for r in filtered if r["influencer_id"] == inf_options[selected_inf]]
    if status_filter == "추적중":
        filtered = [r for r in filtered if r["status"] == "active"]
    elif status_filter == "완료":
        filtered = [r for r in filtered if r["status"] == "completed"]

    if not filtered:
        st.info("조건에 맞는 추천 종목이 없습니다.")
        return

    # === 종목별 상세 ===
    for rec in filtered:
        tracking = get_price_tracking(rec["id"])

        status_emoji = "🟢" if rec["status"] == "active" else "⚪"
        with st.expander(
            f"{status_emoji} [{rec['influencer_name']}] {rec['stock_name']} "
            f"(추천일: {rec['recommended_date']}, 추천가: {rec['recommended_price']:,.0f}원)",
            expanded=False
        ):
            # 기본 정보
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("추천가", f"{rec['recommended_price']:,.0f}원")
            with info_col2:
                if rec["target_price"]:
                    st.metric("목표가", f"{rec['target_price']:,.0f}원")
                else:
                    st.metric("목표가", "미설정")
            with info_col3:
                if rec["stop_loss_price"]:
                    st.metric("손절가", f"{rec['stop_loss_price']:,.0f}원")
                else:
                    st.metric("손절가", "미설정")

            if not tracking:
                st.warning("아직 주가 데이터가 없습니다. '주가 업데이트'를 실행해주세요.")
                continue

            df_track = pd.DataFrame(tracking)

            # 현재 수익률
            latest = df_track.iloc[-1]
            current_return = latest["change_pct"]
            current_price = latest["close_price"]

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric(
                    "현재가",
                    f"{current_price:,.0f}원",
                    f"{current_return:+.2f}%"
                )
            with col_b:
                max_return = df_track["change_pct"].max()
                st.metric("최고 수익률", f"{max_return:+.2f}%")
            with col_c:
                min_return = df_track["change_pct"].min()
                st.metric("최저 수익률", f"{min_return:+.2f}%")

            # 수익률 차트
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_track["tracking_date"],
                y=df_track["change_pct"],
                mode="lines+markers",
                name="수익률 (%)",
                line=dict(color="royalblue", width=2),
                marker=dict(size=4)
            ))
            # 0% 기준선
            fig.add_hline(y=0, line_dash="dash", line_color="gray")

            # 목표가/손절가 라인
            if rec["target_price"]:
                target_pct = ((rec["target_price"] - rec["recommended_price"]) / rec["recommended_price"]) * 100
                fig.add_hline(y=target_pct, line_dash="dot", line_color="green",
                              annotation_text=f"목표 +{target_pct:.1f}%")
            if rec["stop_loss_price"]:
                sl_pct = ((rec["stop_loss_price"] - rec["recommended_price"]) / rec["recommended_price"]) * 100
                fig.add_hline(y=sl_pct, line_dash="dot", line_color="red",
                              annotation_text=f"손절 {sl_pct:.1f}%")

            fig.update_layout(
                title=f"{rec['stock_name']} 추천 후 수익률 추이",
                xaxis_title="날짜",
                yaxis_title="수익률 (%)",
                height=350,
                margin=dict(t=40, b=30)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 메모
            if rec["memo"]:
                st.caption(f"메모: {rec['memo']}")
