"""추천 종목 입력 페이지"""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_influencers, add_recommendation, get_recommendations
from price_updater import get_stock_code_by_name, get_current_price


def render():
    st.header("추천 종목 입력")

    influencers = get_influencers()
    if not influencers:
        st.warning("먼저 '인플루언서 관리'에서 인플루언서를 등록해주세요.")
        return

    # === 종목 검색 (폼 바깥에서 실행) ===
    st.subheader("새 추천 종목 등록")

    # 세션 상태 초기화
    if "found_code" not in st.session_state:
        st.session_state.found_code = ""
    if "found_price" not in st.session_state:
        st.session_state.found_price = 0
    if "found_name" not in st.session_state:
        st.session_state.found_name = ""

    # 종목명 입력 + 자동 검색
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        stock_name_input = st.text_input("종목명 *", placeholder="예: 삼성전자",
                                          key="stock_search")
    with search_col2:
        st.write("")  # 간격 맞춤
        st.write("")
        search_clicked = st.button("종목 검색", type="primary")

    if search_clicked and stock_name_input:
        with st.spinner(f"'{stock_name_input}' 검색 중..."):
            code = get_stock_code_by_name(stock_name_input.strip())
            if code:
                price = get_current_price(code)
                st.session_state.found_code = code
                st.session_state.found_price = int(price) if price else 0
                st.session_state.found_name = stock_name_input.strip()
                st.success(f"'{stock_name_input}' 발견 - 종목코드: {code}, 현재가: {price:,.0f}원")
            else:
                st.error(f"'{stock_name_input}'을 찾을 수 없습니다. 정확한 종목명을 입력해주세요.")
                st.session_state.found_code = ""
                st.session_state.found_price = 0

    # 검색 결과 표시
    if st.session_state.found_code:
        st.info(f"종목: **{st.session_state.found_name}** ({st.session_state.found_code}) | "
                f"현재가: **{st.session_state.found_price:,}원** (자동 입력됨)")

    # === 등록 폼 ===
    with st.form("add_rec", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            inf_names = {inf["name"]: inf["id"] for inf in influencers}
            selected_inf = st.selectbox("인플루언서 *", list(inf_names.keys()))
            recommended_date = st.date_input("추천일 *", value=date.today())
            memo = st.text_input("메모", placeholder="추천 사유, 영상 제목 등")

        with col2:
            recommended_price = st.number_input(
                "추천 시점 주가 (원)",
                min_value=0, step=100,
                value=st.session_state.found_price,
                help="종목 검색 시 자동 입력됩니다. 직접 수정도 가능합니다."
            )
            target_price = st.number_input(
                "목표가 (원) - 선택사항",
                min_value=0, step=100, value=0,
                help="인플루언서가 목표가를 제시하지 않으면 비워두세요"
            )
            stop_loss_price = st.number_input(
                "손절가 (원) - 선택사항",
                min_value=0, step=100, value=0,
                help="인플루언서가 손절가를 제시하지 않으면 비워두세요"
            )

        if st.form_submit_button("등록"):
            # 종목명: 검색된 이름 또는 직접 입력값
            final_name = st.session_state.found_name or stock_name_input.strip()
            final_code = st.session_state.found_code

            if not final_name:
                st.error("종목명을 입력하고 '종목 검색' 버튼을 눌러주세요")
            elif recommended_price <= 0:
                st.error("주가를 확인할 수 없습니다. 종목 검색을 다시 해주세요.")
            else:
                add_recommendation(
                    influencer_id=inf_names[selected_inf],
                    stock_name=final_name,
                    stock_code=final_code,
                    recommended_date=recommended_date.isoformat(),
                    recommended_price=recommended_price,
                    target_price=target_price if target_price > 0 else None,
                    stop_loss_price=stop_loss_price if stop_loss_price > 0 else None,
                    memo=memo
                )
                st.success(f"'{selected_inf}'의 추천 종목 '{final_name}' 등록 완료! "
                           f"(추천가: {recommended_price:,}원)")
                # 세션 상태 초기화
                st.session_state.found_code = ""
                st.session_state.found_price = 0
                st.session_state.found_name = ""
                st.rerun()

    # === 최근 등록 내역 ===
    st.markdown("---")
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
    df_display["목표가"] = df_display["목표가"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x else "-")
    df_display["손절가"] = df_display["손절가"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x else "-")
    df_display["상태"] = df_display["상태"].map({"active": "추적중", "completed": "완료"})

    st.dataframe(df_display, use_container_width=True, hide_index=True)
