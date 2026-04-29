"""매매 일지 페이지"""
import streamlit as st
import pandas as pd
from datetime import date
from database import add_trade, get_trades


def render():
    st.header("매매 일지")

    # === 입력 폼 ===
    st.subheader("매매 기록 입력")
    with st.form("add_trade", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            trade_date = st.date_input("매매일 *", value=date.today())
            stock_name = st.text_input("종목명 *")
            stock_code = st.text_input("종목코드", placeholder="모르면 비워두세요")
            action = st.selectbox("매매 구분 *", ["매수", "매도"])

        with col2:
            price = st.number_input("가격 (원) *", min_value=0, step=100)
            quantity = st.number_input("수량 (주) *", min_value=0, step=1)
            reason = st.text_input("매매 사유", placeholder="왜 이 종목을 샀는지/팔았는지")
            memo = st.text_input("메모/반성", placeholder="잘한 점, 아쉬운 점")

        if price > 0 and quantity > 0:
            total = price * quantity
            tax = total * 0.002 if action == "매도" else 0
            st.caption(f"매매 금액: {total:,.0f}원 | 거래세: {tax:,.0f}원")

        if st.form_submit_button("기록"):
            if not stock_name:
                st.error("종목명을 입력해주세요")
            elif price <= 0 or quantity <= 0:
                st.error("가격과 수량을 입력해주세요")
            else:
                add_trade(
                    trade_date=trade_date.isoformat(),
                    stock_name=stock_name.strip(),
                    stock_code=stock_code.strip() if stock_code else "",
                    action=action,
                    price=price,
                    quantity=quantity,
                    reason=reason,
                    memo=memo
                )
                st.success("매매 기록 저장 완료!")
                st.rerun()

    # === 매매 내역 ===
    st.subheader("매매 내역")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        start = st.date_input("시작일", value=date(date.today().year, date.today().month, 1))
    with col_f2:
        end = st.date_input("종료일", value=date.today())

    trades = get_trades(start.isoformat(), end.isoformat())

    if not trades:
        st.info("해당 기간의 매매 기록이 없습니다.")
        return

    df = pd.DataFrame(trades)

    # 요약 통계
    total_buy = df[df["action"] == "매수"]["total_amount"].sum()
    total_sell = df[df["action"] == "매도"]["total_amount"].sum()
    total_tax = df["tax"].sum()
    buy_count = len(df[df["action"] == "매수"])
    sell_count = len(df[df["action"] == "매도"])

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("총 매수 금액", f"{total_buy:,.0f}원")
    with col_s2:
        st.metric("총 매도 금액", f"{total_sell:,.0f}원")
    with col_s3:
        st.metric("총 거래세", f"{total_tax:,.0f}원")
    with col_s4:
        st.metric("거래 횟수", f"매수 {buy_count} / 매도 {sell_count}")

    # 테이블
    display_cols = {
        "trade_date": "날짜",
        "stock_name": "종목명",
        "action": "구분",
        "price": "가격",
        "quantity": "수량",
        "total_amount": "매매금액",
        "tax": "거래세",
        "reason": "매매사유",
        "memo": "메모"
    }
    df_display = df[list(display_cols.keys())].rename(columns=display_cols)
    df_display["가격"] = df_display["가격"].apply(lambda x: f"{x:,.0f}")
    df_display["매매금액"] = df_display["매매금액"].apply(lambda x: f"{x:,.0f}")
    df_display["거래세"] = df_display["거래세"].apply(lambda x: f"{x:,.0f}")

    st.dataframe(df_display, use_container_width=True, hide_index=True)
