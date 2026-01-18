import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

engine = create_engine("postgresql://postgres:Python123456789@localhost:5432/traffic_logs")

@st.cache_data
def load_data():
    return pd.read_sql("SELECT * FROM police_traffic_logs", engine)

df = load_data()

st.title("🚓 SecureCheck Police Dashboard")
st.markdown("---")

st.subheader("📌 Latest 10 Traffic Stops")
st.dataframe(df.sort_values(by=["stop_date", "stop_time"], ascending=False).head(10))
st.markdown("---")

st.subheader("🔍 Filters")

country_list = ["All"] + sorted(df["country_name"].dropna().unique().tolist())
country = st.selectbox("Select Country", country_list)

if country == "All":
    violation_list = ["All"] + sorted(df["violation"].dropna().unique().tolist())
else:
    violation_list = ["All"] + sorted(df[df["country_name"] == country]["violation"].dropna().unique().tolist())

violation = st.selectbox("Select Violation", violation_list)

filtered_df = df.copy()

if country != "All":
    filtered_df = filtered_df[filtered_df["country_name"] == country]

if violation != "All":
    filtered_df = filtered_df[filtered_df["violation"] == violation]

st.subheader("📋 Filtered Traffic Stops")
st.dataframe(filtered_df)
st.markdown("---")

st.subheader("📊 Summary Metrics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Stops", len(filtered_df))
c2.metric("Total Arrests", int(filtered_df["is_arrested"].sum()))
c3.metric("Searches Conducted", int(filtered_df["search_conducted"].sum()))
c4.metric("Drug-Related Stops", int(filtered_df["drugs_related_stop"].sum()))
st.markdown("---")

st.subheader("📈 Violation Counts")

if len(filtered_df) > 0:
    vc = filtered_df["violation"].value_counts().reset_index()
    vc.columns = ["Violation", "Count"]
    st.bar_chart(vc.set_index("Violation"))
else:
    st.info("No data available")

st.markdown("---")

st.subheader("🧑 Driver Gender Distribution")

if filtered_df["driver_gender"].nunique() > 0:
    fig, ax = plt.subplots()
    filtered_df["driver_gender"].value_counts().plot.pie(autopct="%1.1f%%", ax=ax, ylabel="")
    st.pyplot(fig)
else:
    st.info("No data available")

st.markdown("---")

st.subheader("📝 Add New Police Log")

with st.form("police_log_form"):
    stop_date = st.date_input("Stop Date")
    stop_time = st.time_input("Stop Time")
    country_name = st.selectbox("Country", sorted(df["country_name"].dropna().unique()))
    driver_gender = st.selectbox("Driver Gender", ["Male", "Female"])
    driver_age = st.number_input("Driver Age", min_value=16, max_value=100)
    driver_race = st.selectbox("Driver Race", sorted(df["driver_race"].dropna().unique()))
    violation = st.selectbox("Violation", sorted(df["violation"].dropna().unique()))
    search_conducted = st.selectbox("Search Conducted", [True, False])
    search_type = st.selectbox("Search Type", sorted(df["search_type"].dropna().unique()))
    is_arrested = st.selectbox("Arrested", [True, False])
    stop_duration = st.selectbox("Stop Duration", sorted(df["stop_duration"].dropna().unique()))
    drugs_related_stop = st.selectbox("Drug Related", [True, False])
    vehicle_number = st.text_input("Vehicle Number")
    submit = st.form_submit_button("Add Log")

if submit:
    insert_df = pd.DataFrame([{
        "stop_date": stop_date,
        "stop_time": stop_time,
        "country_name": country_name,
        "driver_gender": driver_gender,
        "driver_age": driver_age,
        "driver_race": driver_race,
        "violation": violation,
        "search_conducted": search_conducted,
        "search_type": search_type,
        "is_arrested": is_arrested,
        "stop_duration": stop_duration,
        "drugs_related_stop": drugs_related_stop,
        "vehicle_number": vehicle_number
    }])
    insert_df.to_sql("police_traffic_logs", engine, if_exists="append", index=False)
    st.success("Police log added successfully")
    st.cache_data.clear()

st.markdown("---")

st.subheader("🌟 Advanced Insights")

queries = {
    "Top 5 Violations": """
        SELECT violation, COUNT(*) AS count
        FROM police_traffic_logs
        GROUP BY violation
        ORDER BY count DESC
        LIMIT 5;
    """,
    "Top 5 Search Types": """
        SELECT search_type, COUNT(*) AS count
        FROM police_traffic_logs
        GROUP BY search_type
        ORDER BY count DESC
        LIMIT 5;
    """,
    "Night Stops Arrest Rate": """
        SELECT
            CASE
                WHEN stop_time BETWEEN '18:00' AND '23:59' OR stop_time BETWEEN '00:00' AND '05:59'
                THEN 'Night'
                ELSE 'Day'
            END AS time_period,
            ROUND(AVG(CASE WHEN is_arrested THEN 1 ELSE 0 END)*100,2) AS arrest_rate
        FROM police_traffic_logs
        GROUP BY time_period;
    """
}

choice = st.selectbox("Select Analysis", list(queries.keys()))

if st.button("Run Analysis"):
    result = pd.read_sql(queries[choice], engine)
    st.dataframe(result)
