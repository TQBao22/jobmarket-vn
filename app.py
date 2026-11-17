"""Dashboard công khai: kỹ năng AI/Data được JD trên ITviec yêu cầu nhiều nhất.

Chỉ đọc `data/public/skill_counts.csv` (số đếm tổng hợp, không có nội dung JD).
Chạy: streamlit run app.py
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

COUNTS = Path("data/public/skill_counts.csv")
TOP_N = 20
SERIES = {"light": "#2a78d6", "dark": "#3987e5"}  # categorical slot 1, mỗi chế độ một bước (dataviz palette)

st.set_page_config(page_title="Kỹ năng AI/Data — JobMarket VN", layout="wide")
st.title("Kỹ năng AI/Data được tuyển nhiều nhất")
st.caption(
    "Nguồn: tin tuyển dụng AI/Data đang mở trên [ITviec](https://itviec.com). "
    "Kỹ năng do LLM (Claude Haiku) trích từ nội dung JD rồi gộp tên đồng nghĩa. Chỉ hiển thị số liệu tổng hợp."
)

df = pd.read_csv(COUNTS)
months = sorted(df["month"].unique())
chosen = st.multiselect("Tháng đăng", months, default=months)
view = df[df["month"].isin(chosen)]
if view.empty:
    st.info("Chọn ít nhất một tháng.")
    st.stop()

n_jd = int(view.drop_duplicates(["source", "month"])["jd_total"].sum())
top = (
    view.groupby("skill", as_index=False)["jd_count"].sum()
    .assign(share=lambda d: d["jd_count"] / n_jd)
    .sort_values(["jd_count", "skill"], ascending=[False, True])
)

c1, c2 = st.columns(2)
c1.metric("JD đã phân tích", n_jd)
c2.metric("Kỹ năng khác nhau", len(top))

st.subheader(f"Top {TOP_N} kỹ năng theo tỉ lệ JD yêu cầu")
theme = getattr(getattr(st.context, "theme", None), "type", None) or "light"
chart = (
    alt.Chart(top.head(TOP_N))
    .mark_bar(color=SERIES.get(theme, SERIES["light"]), cornerRadiusEnd=4, size=14)
    .encode(
        x=alt.X("share:Q", title="Tỉ lệ JD có kỹ năng", axis=alt.Axis(format="%", grid=True, tickCount=5)),
        y=alt.Y("skill:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("skill:N", title="Kỹ năng"),
            alt.Tooltip("jd_count:Q", title="Số JD"),
            alt.Tooltip("share:Q", title="Tỉ lệ", format=".0%"),
        ],
    )
    .properties(height=TOP_N * 24)
)
st.altair_chart(chart, width="stretch")

with st.expander("Bảng số liệu"):
    st.dataframe(
        top.rename(columns={"skill": "Kỹ năng", "jd_count": "Số JD", "share": "Tỉ lệ"}),
        hide_index=True,
        column_config={"Tỉ lệ": st.column_config.NumberColumn(format="percent")},
    )

st.caption("Giới hạn: chỉ một nguồn (ITviec), là ảnh chụp các JD đang mở, không phải toàn thị trường.")
