"""
Name:        Phuong Vu
CS602:       Section XXX
Data:        NYC 311 Noise Complaints (Dec 24, 2025 - Jan 2, 2026)
URL:         Link to your web application on Streamlit Cloud (if posted)

Description:
This program explores noise complaints reported to NYC's 311 service over the
2025 holiday week. The user can filter the data by borough, by one or more
complaint types, and by the hour of day using sidebar widgets. The app then
shows where and when New Yorkers complained about noise using a bar chart
(complaints per borough), a pie chart (complaint-type breakdown), a line chart
(complaints by hour of day), and an interactive map of complaint locations.
"""

import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk
import streamlit as st

DATA_FILE = "311_Noise_Complaints_20260403.csv"

BOROUGH_COLORS = {
    "BROOKLYN": "#1f77b4",
    "MANHATTAN": "#ff7f0e",
    "BRONX": "#2ca02c",
    "QUEENS": "#d62728",
    "STATEN ISLAND": "#9467bd",
}


@st.cache_data
def load_data(path, encoding="utf-8"):
    df = pd.read_csv(path, encoding=encoding, low_memory=False)
    keep = {
        "Created Date": "Created Date",
        "Problem (formerly Complaint Type)": "Complaint Type",
        "Location Type": "Location Type",
        "Borough": "Borough",
        "Latitude": "Latitude",
        "Longitude": "Longitude",
    }
    df = df[list(keep.keys())].rename(columns=keep)
    df = df.dropna(subset=["Latitude", "Longitude", "Borough"])
    df = df[df["Borough"] != "Unspecified"]
    df["Created Date"] = pd.to_datetime(
        df["Created Date"], format="%Y %b %d %I:%M:%S %p", errors="coerce"
    )
    df = df.dropna(subset=["Created Date"])
    df["Hour"] = df["Created Date"].dt.hour
    return df

def filter_data(df, borough, complaint_types, hour_range):
    result = df
    if borough != "All Boroughs":
        result = result[result["Borough"] == borough]
    low, high = hour_range
    result = result[
        (result["Complaint Type"].isin(complaint_types))
        & (result["Hour"] >= low)
        & (result["Hour"] <= high)
    ]
    return result


def busiest_hour(df):
    if len(df) == 0:
        return None, 0
    counts = df["Hour"].value_counts()
    return int(counts.index[0]), int(counts.iloc[0])


def top_complaints(df, n=5):
    counts = df["Complaint Type"].value_counts()
    return counts.sort_values(ascending=False).head(n)


def make_bar_chart(df):
    counts = df["Borough"].value_counts().sort_values(ascending=False)  # [DA2]
    colors = [BOROUGH_COLORS.get(b, "#888888") for b in counts.index]
    fig, ax = plt.subplots()
    ax.bar(counts.index, counts.values, color=colors)
    # ax.set_title("Noise Complaints by Borough")
    ax.set_xlabel("Borough")
    ax.set_ylabel("Number of Complaints")
    ax.tick_params(axis="x", rotation=20)
    return fig


def make_pie_chart(df):
    counts = top_complaints(df, 5)
    fig, ax = plt.subplots()
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=90)
    # ax.set_title("Top 5 Complaint Types")
    ax.axis("equal")
    return fig


def make_line_chart(df):
    by_hour = df.groupby("Hour").size()
    by_hour = by_hour.reindex(range(24), fill_value=0)
    fig, ax = plt.subplots()
    ax.plot(by_hour.index, by_hour.values, marker="o", color="#d62728")
    # ax.set_title("Complaints by Hour of Day")
    ax.set_xlabel("Hour (0 = midnight, 23 = 11 PM)")
    ax.set_ylabel("Number of Complaints")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, linestyle="--", alpha=0.5)
    return fig


def make_map(df):
    map_df = df[["Latitude", "Longitude", "Borough", "Complaint Type"]].copy()
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position=["Longitude", "Latitude"],
        get_color=[214, 39, 40, 140],
        get_radius=120,
        pickable=True,
    )
    view = pdk.ViewState(latitude=40.71, longitude=-73.95, zoom=9.5)
    tooltip = {"text": "{Complaint Type}\nBorough: {Borough}"}
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style=pdk.map_styles.LIGHT,
    )


def main():
    st.set_page_config(page_title="NYC Noise Complaints", layout="wide")
    st.title("NYC Noise Complaints Explorer")
    st.write(
        "Noise complaints reported to NYC 311 between Dec 24, 2025 and Jan 2, 2026. "
        "Use the filters on the left to explore where and when they happened."
    )

    df = load_data(DATA_FILE, encoding="utf-8")

    st.sidebar.header("Filters")

    borough_options = ["All Boroughs"] + [b for b in sorted(df["Borough"].unique())]
    borough = st.sidebar.selectbox("Choose a borough", borough_options)
    all_types = sorted(df["Complaint Type"].unique())
    complaint_types = st.sidebar.multiselect(
        "Complaint types", all_types, default=all_types
    )
    hour_range = st.sidebar.slider("Hour of day range", 0, 23, (0, 23))

    if len(complaint_types) == 0:
        st.warning("Please select at least one complaint type in the sidebar.")
        return

    filtered = filter_data(df, borough, complaint_types, hour_range)
    hour, count = busiest_hour(filtered)
    total = len(filtered)
    percent = round(total / len(df) * 100, 1) if len(df) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Complaints shown", f"{total:,}")
    c2.metric("Share of all complaints", f"{percent}%")
    if hour is not None:
        c3.metric("Busiest hour", f"{hour}:00 ({count})")
    if total == 0:
        st.info("No complaints match these filters. Try widening them.")
        return

    left, right = st.columns(2)
    with left:
        st.subheader("Noise Complaints by Borough")
        st.pyplot(make_bar_chart(filtered))
    with right:
        st.subheader("Top 5 Complaint Types")
        st.pyplot(make_pie_chart(filtered))


    left, right = st.columns(2)
    with left:
        st.subheader("Complaints by Hour of Day")
        st.pyplot(make_line_chart(filtered))
    with right:
        st.subheader("Map of Complaint Locations")
        st.pydeck_chart(make_map(filtered))

    st.subheader("Borough vs. Complaint Type")
    pivot = pd.pivot_table(
        filtered,
        index="Borough",
        columns="Complaint Type",
        values="Hour",
        aggfunc="count",
        fill_value=0,
    )
    st.dataframe(pivot)

    left, right = st.columns(2)
    with left:
        st.subheader("Most Common Complaint Types")
        st.write(top_complaints(filtered))

if __name__ == "__main__":
    main()
