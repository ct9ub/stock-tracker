"""인플루언서 관리 페이지"""
import streamlit as st
import pandas as pd
from database import add_influencer, get_influencers, delete_influencer


def render():
    st.header("인플루언서 관리")

    # === 등록 폼 ===
    st.subheader("새 인플루언서 등록")
    with st.form("add_influencer", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름 (채널명) *")
            platform = st.selectbox("플랫폼", ["youtube", "blog", "community", "other"])
        with col2:
            channel_url = st.text_input("채널 URL")
            memo = st.text_input("메모")

        if st.form_submit_button("등록"):
            if not name:
                st.error("이름을 입력해주세요")
            else:
                success, msg = add_influencer(name, platform, channel_url, memo)
                if success:
                    st.success(f"'{name}' {msg}")
                    st.rerun()
                else:
                    st.error(msg)

    # === 목록 ===
    st.subheader("등록된 인플루언서")
    influencers = get_influencers()

    if not influencers:
        st.info("등록된 인플루언서가 없습니다. 위에서 등록해주세요.")
        return

    df = pd.DataFrame(influencers)
    df = df[["id", "name", "platform", "channel_url", "memo", "created_at"]]
    df.columns = ["ID", "이름", "플랫폼", "채널URL", "메모", "등록일"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    # === 삭제 ===
    st.subheader("인플루언서 삭제")
    names = {inf["name"]: inf["id"] for inf in influencers}
    selected = st.selectbox("삭제할 인플루언서", ["선택하세요"] + list(names.keys()))
    if selected != "선택하세요":
        st.warning(f"'{selected}'를 삭제하면 해당 인플루언서의 모든 추천 기록도 삭제됩니다.")
        if st.button("삭제 확인"):
            delete_influencer(names[selected])
            st.success(f"'{selected}' 삭제 완료")
            st.rerun()
