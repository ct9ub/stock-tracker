"""대시보드 - 인플루언서 비교 분석 + 시각화"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from database import (
    get_influencer_stats, get_recommendations, get_trades,
    get_price_tracking, get_influencers
)
from price_updater import update_prices
from config import MIN_RECOMMENDATIONS


def _render_update_button():
    """주가 업데이트 버튼 (수동)"""
    active_recs = get_recommendations(status="active")
    if not active_recs:
        return

    last_update = st.session_state.get("last_price_update")
    if last_update:
        elapsed = (datetime.now() - last_update).seconds // 60
        update_info = f"(마지막 업데이트: {elapsed}분 전)"
    else:
        update_info = "(아직 업데이트하지 않음)"

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("주가 업데이트", type="primary"):
            with st.spinner(f"주가 데이터 업데이트 중... ({len(active_recs)}개 종목)"):
                update_prices()
            st.session_state["last_price_update"] = datetime.now()
            st.rerun()
    with col_info:
        st.caption(update_info)


def _build_comparison_data():
    """인플루언서별 비교 데이터 생성"""
    influencers = get_influencers()
    all_recs = get_recommendations()

    if not all_recs:
        return None, None

    comparison = []
    rec_details = []

    for inf in influencers:
        inf_recs = [r for r in all_recs if r["influencer_id"] == inf["id"]]
        if not inf_recs:
            continue

        returns = []
        for rec in inf_recs:
            tracking = get_price_tracking(rec["id"])
            if tracking:
                latest = tracking[-1]
                ret = latest["change_pct"]
                returns.append(ret)
                rec_details.append({
                    "인플루언서": inf["name"],
                    "종목": rec["stock_name"],
                    "추천가": rec["recommended_price"],
                    "현재가": latest["close_price"],
                    "수익률": ret,
                    "경과일": latest["days_since_rec"],
                    "상태": "추적중" if rec["status"] == "active" else "완료",
                    "추천일": rec["recommended_date"]
                })
            else:
                rec_details.append({
                    "인플루언서": inf["name"],
                    "종목": rec["stock_name"],
                    "추천가": rec["recommended_price"],
                    "현재가": None,
                    "수익률": None,
                    "경과일": 0,
                    "상태": "미수집",
                    "추천일": rec["recommended_date"]
                })

        if returns:
            hits = sum(1 for r in returns if r > 0)
            comparison.append({
                "인플루언서": inf["name"],
                "추천수": len(inf_recs),
                "수집완료": len(returns),
                "적중수": hits,
                "적중률": round(hits / len(returns) * 100, 1) if returns else 0,
                "평균수익률": round(sum(returns) / len(returns), 2),
                "최고수익률": round(max(returns), 2),
                "최저수익률": round(min(returns), 2),
                "총수익률": round(sum(returns), 2)
            })
        else:
            comparison.append({
                "인플루언서": inf["name"],
                "추천수": len(inf_recs),
                "수집완료": 0,
                "적중수": 0,
                "적중률": 0,
                "평균수익률": 0,
                "최고수익률": 0,
                "최저수익률": 0,
                "총수익률": 0
            })

    df_comp = pd.DataFrame(comparison) if comparison else None
    df_detail = pd.DataFrame(rec_details) if rec_details else None
    return df_comp, df_detail


def render():
    st.header("대시보드")

    # 주가 업데이트 버튼
    _render_update_button()

    # 데이터 구축
    df_comp, df_detail = _build_comparison_data()

    if df_comp is None or df_comp.empty:
        st.info("아직 데이터가 없습니다. '종목 등록'에서 인플루언서와 추천 종목을 등록해주세요.")
        return

    # === 상단 요약 ===
    total_inf = len(df_comp)
    total_recs = df_comp["추천수"].sum()
    active_recs = len([r for r in get_recommendations(status="active")])
    avg_return = df_comp["평균수익률"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("인플루언서", f"{total_inf}명")
    with c2:
        st.metric("총 추천종목", f"{total_recs}건")
    with c3:
        st.metric("추적중", f"{active_recs}건")
    with c4:
        st.metric("전체 평균수익률", f"{avg_return:+.2f}%")

    st.markdown("---")

    # === 인플루언서 비교 차트 ===
    st.subheader("인플루언서 비교 분석")

    if len(df_comp) >= 1:
        tab_chart, tab_table = st.tabs(["차트", "테이블"])

        with tab_chart:
            col_left, col_right = st.columns(2)

            with col_left:
                # 적중률 비교 바 차트
                fig_hit = go.Figure()
                colors = ["#2ecc71" if r > 50 else "#e74c3c" if r < 30 else "#f39c12"
                          for r in df_comp["적중률"]]
                fig_hit.add_trace(go.Bar(
                    x=df_comp["인플루언서"],
                    y=df_comp["적중률"],
                    marker_color=colors,
                    text=df_comp["적중률"].apply(lambda x: f"{x:.1f}%"),
                    textposition="outside"
                ))
                fig_hit.add_hline(y=50, line_dash="dash", line_color="gray",
                                  annotation_text="50%")
                fig_hit.update_layout(
                    title="적중률 비교 (%)",
                    yaxis_title="적중률 (%)",
                    yaxis_range=[0, max(df_comp["적중률"].max() * 1.3, 60)],
                    height=400, margin=dict(t=40, b=30)
                )
                st.plotly_chart(fig_hit, use_container_width=True)

            with col_right:
                # 평균수익률 비교 바 차트
                fig_ret = go.Figure()
                colors_ret = ["#2ecc71" if r > 0 else "#e74c3c" for r in df_comp["평균수익률"]]
                fig_ret.add_trace(go.Bar(
                    x=df_comp["인플루언서"],
                    y=df_comp["평균수익률"],
                    marker_color=colors_ret,
                    text=df_comp["평균수익률"].apply(lambda x: f"{x:+.2f}%"),
                    textposition="outside"
                ))
                fig_ret.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_ret.update_layout(
                    title="평균 수익률 비교 (%)",
                    yaxis_title="평균 수익률 (%)",
                    height=400, margin=dict(t=40, b=30)
                )
                st.plotly_chart(fig_ret, use_container_width=True)

            # 수익률 범위 차트 (최고/최저)
            fig_range = go.Figure()
            for _, row in df_comp.iterrows():
                fig_range.add_trace(go.Bar(
                    name=row["인플루언서"],
                    x=[row["인플루언서"]],
                    y=[row["최고수익률"]],
                    marker_color="#2ecc71",
                    showlegend=False
                ))
                fig_range.add_trace(go.Bar(
                    x=[row["인플루언서"]],
                    y=[row["최저수익률"]],
                    marker_color="#e74c3c",
                    showlegend=False
                ))
            fig_range.add_hline(y=0, line_dash="solid", line_color="white", line_width=1)
            fig_range.update_layout(
                title="수익률 범위 (최고 / 최저)",
                yaxis_title="수익률 (%)",
                barmode="relative",
                height=350, margin=dict(t=40, b=30)
            )
            st.plotly_chart(fig_range, use_container_width=True)

        with tab_table:
            # 랭킹 테이블 (적중률 기준 정렬)
            df_rank = df_comp.sort_values("적중률", ascending=False).reset_index(drop=True)
            df_rank.insert(0, "순위", range(1, len(df_rank) + 1))

            # 포맷팅
            df_display = df_rank.copy()
            df_display["적중률"] = df_display["적중률"].apply(lambda x: f"{x:.1f}%")
            df_display["평균수익률"] = df_display["평균수익률"].apply(lambda x: f"{x:+.2f}%")
            df_display["최고수익률"] = df_display["최고수익률"].apply(lambda x: f"{x:+.2f}%")
            df_display["최저수익률"] = df_display["최저수익률"].apply(lambda x: f"{x:+.2f}%")
            df_display["총수익률"] = df_display["총수익률"].apply(lambda x: f"{x:+.2f}%")

            st.dataframe(df_display, use_container_width=True, hide_index=True)

            if len(df_comp[df_comp["수집완료"] < MIN_RECOMMENDATIONS]) > 0:
                st.caption(f"* 추천 수집 {MIN_RECOMMENDATIONS}건 미만인 인플루언서는 신뢰도가 낮을 수 있습니다.")

    st.markdown("---")

    # === 종목별 상세 현황 ===
    st.subheader("종목별 상세 현황")

    if df_detail is not None and not df_detail.empty:
        # 인플루언서별 탭
        inf_names = df_detail["인플루언서"].unique().tolist()
        tabs = st.tabs(inf_names)

        for tab, inf_name in zip(tabs, inf_names):
            with tab:
                inf_data = df_detail[df_detail["인플루언서"] == inf_name].copy()

                # 수익률 색상 표시를 위한 종목 카드
                cols_per_row = 3
                rows_data = [inf_data.iloc[i:i + cols_per_row]
                             for i in range(0, len(inf_data), cols_per_row)]

                for row_data in rows_data:
                    cols = st.columns(cols_per_row)
                    for col, (_, rec) in zip(cols, row_data.iterrows()):
                        with col:
                            ret = rec["수익률"]
                            if ret is not None:
                                color = "#2ecc71" if ret > 0 else "#e74c3c" if ret < 0 else "#95a5a6"
                                ret_text = f"{ret:+.2f}%"
                            else:
                                color = "#95a5a6"
                                ret_text = "미수집"

                            current_text = f"{rec['현재가']:,.0f}원" if rec["현재가"] else "미수집"

                            st.markdown(f"""
                            <div style="border:1px solid #333; border-radius:8px; padding:12px; margin-bottom:8px; background:#1a1a2e;">
                                <div style="font-size:16px; font-weight:bold; margin-bottom:4px;">{rec['종목']}</div>
                                <div style="color:#888; font-size:12px;">추천일: {rec['추천일']} | {rec['상태']}</div>
                                <div style="margin-top:8px;">
                                    <span style="color:#888;">추천가:</span> {rec['추천가']:,.0f}원
                                    &nbsp;→&nbsp;
                                    <span style="color:#888;">현재가:</span> {current_text}
                                </div>
                                <div style="font-size:24px; font-weight:bold; color:{color}; margin-top:4px;">
                                    {ret_text}
                                </div>
                                <div style="color:#888; font-size:12px;">경과 {rec['경과일']}일</div>
                            </div>
                            """, unsafe_allow_html=True)

                # 수익률 분포 차트
                valid_data = inf_data[inf_data["수익률"].notna()]
                if not valid_data.empty:
                    fig_stocks = go.Figure()
                    colors = ["#2ecc71" if r > 0 else "#e74c3c"
                              for r in valid_data["수익률"]]
                    fig_stocks.add_trace(go.Bar(
                        x=valid_data["종목"],
                        y=valid_data["수익률"],
                        marker_color=colors,
                        text=valid_data["수익률"].apply(lambda x: f"{x:+.2f}%"),
                        textposition="outside"
                    ))
                    fig_stocks.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_stocks.update_layout(
                        title=f"{inf_name} - 종목별 수익률",
                        yaxis_title="수익률 (%)",
                        height=350, margin=dict(t=40, b=30)
                    )
                    st.plotly_chart(fig_stocks, use_container_width=True)

    st.markdown("---")

    # === 수익률 추이 차트 (시계열) ===
    st.subheader("추천 종목 수익률 추이")
    all_recs = get_recommendations()
    active_recs = [r for r in all_recs if r["status"] == "active"]

    if active_recs:
        # 인플루언서별 색상
        inf_colors = px.colors.qualitative.Set2
        inf_color_map = {}
        for i, name in enumerate(set(r["influencer_name"] for r in active_recs)):
            inf_color_map[name] = inf_colors[i % len(inf_colors)]

        fig_timeline = go.Figure()
        for rec in active_recs:
            tracking = get_price_tracking(rec["id"])
            if not tracking:
                continue

            dates = [t["tracking_date"] for t in tracking]
            returns = [t["change_pct"] for t in tracking]
            color = inf_color_map.get(rec["influencer_name"], "#ffffff")

            fig_timeline.add_trace(go.Scatter(
                x=dates,
                y=returns,
                mode="lines+markers",
                name=f"[{rec['influencer_name']}] {rec['stock_name']}",
                line=dict(color=color, width=2),
                marker=dict(size=4)
            ))

        fig_timeline.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_timeline.update_layout(
            title="추적중인 종목 수익률 추이",
            xaxis_title="날짜",
            yaxis_title="수익률 (%)",
            height=450,
            margin=dict(t=40, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("추적중인 종목이 없습니다.")
