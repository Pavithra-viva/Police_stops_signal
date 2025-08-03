import datetime
import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text

# --- DB connection ---
user = "postgres"
password = "Python123456789"
host = "localhost"
database = "traffic_signal"
db_url = f"postgresql://{user}:{password}@{host}/{database}"
engine = create_engine(db_url)

# --- Helpers ---
def run_query(query):
    return pd.read_sql(query, engine)

def ensure_columns_and_backfill():
    with engine.begin() as conn:
        # Ensure 'drug_related'
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'vehicle_stops'
              AND column_name = 'drug_related';
        """))
        if not result.fetchone():
            conn.execute(text("ALTER TABLE vehicle_stops ADD COLUMN drug_related BOOLEAN;"))
        conn.execute(text("""
            UPDATE vehicle_stops
            SET drug_related = TRUE
            WHERE violation_raw ILIKE '%drug%';
        """))

        # Ensure 'stop_datetime'
        conn.execute(text("""
            ALTER TABLE vehicle_stops
            ADD COLUMN IF NOT EXISTS stop_datetime TIMESTAMP;
        """))

        # Ensure 'location' column exists
        conn.execute(text("""
            ALTER TABLE vehicle_stops
            ADD COLUMN IF NOT EXISTS location TEXT;
        """))

        # Ensure 'country' column exists
        conn.execute(text("""
            ALTER TABLE vehicle_stops
            ADD COLUMN IF NOT EXISTS country TEXT;
        """))

        # Fill missing locations
        conn.execute(text("""
            UPDATE vehicle_stops
            SET location = 'Unknown'
            WHERE location IS NULL OR location = '';
        """))

        # Fill missing country from location
        conn.execute(text("""
            UPDATE vehicle_stops
            SET country = 'India'
            WHERE country IS NULL AND location ILIKE '%Chennai%';
        """))

        # Identify date-like column
        date_column = None
        for candidate in ["date", "stop_date", "incident_date", "date_of_incident"]:
            chk = conn.execute(text(f"""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'vehicle_stops' AND column_name = '{candidate}';
            """))
            if chk.fetchone():
                date_column = candidate
                break

        # Check stop_time column
        has_stop_time = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'vehicle_stops' AND column_name = 'stop_time';
        """)).fetchone() is not None

        # Backfill stop_datetime
        if date_column and has_stop_time:
            conn.execute(text(f"""
                UPDATE vehicle_stops
                SET stop_datetime = (({date_column}::text)::date + stop_time::time)
                WHERE stop_datetime IS NULL
                  AND stop_time IS NOT NULL
                  AND {date_column} IS NOT NULL;
            """))
        if date_column:
            conn.execute(text(f"""
                UPDATE vehicle_stops
                SET stop_datetime = (({date_column}::text)::date)::timestamp
                WHERE stop_datetime IS NULL
                  AND {date_column} IS NOT NULL;
            """))
        if has_stop_time and not date_column:
            conn.execute(text("""
                UPDATE vehicle_stops
                SET stop_datetime = (CURRENT_DATE + stop_time::time)
                WHERE stop_datetime IS NULL
                  AND stop_time IS NOT NULL;
            """))

# --- Page Title ---
st.title("Vehicle Stops Dashboard")

# Run schema setup once
if "schema_initialized" not in st.session_state:
    ensure_columns_and_backfill()
    st.session_state.schema_initialized = True
    st.success("'drug_related', 'stop_datetime', 'location', and 'country' ensured/backfilled.")

# --- Show preview ---
st.dataframe(run_query("SELECT * FROM vehicle_stops LIMIT 5;"))

# --- Log Submission Form ---
st.title("🚓 Add New Police Log")
with st.form("log_form"):
    officer_name = st.text_input("Officer Name")
    incident_type = st.selectbox("Incident Type", ["Accident", "Probable Cause", "Investigation", "Violation", "Other"])
    driver_name = st.text_input("Driver Name")
    vehicle_type = st.selectbox("Vehicle Type", ["Car", "Bike", "Truck", "Other"])
    location = st.text_input("Location")
    date = st.date_input("Date of Incident")
    violation = st.text_input("Violation Type")
    submit = st.form_submit_button("Submit Log")

if submit:
    insert_query = text("""
        INSERT INTO vehicle_stops (officer_name, incident_type, driver_name, vehicle_type, location, date, violation_raw)
        VALUES (:officer_name, :incident_type, :driver_name, :vehicle_type, :location, :date, :violation_raw);
    """)
    with engine.begin() as conn:
        conn.execute(insert_query, {
            "officer_name": officer_name,
            "incident_type": incident_type,
            "driver_name": driver_name,
            "vehicle_type": vehicle_type,
            "location": location,
            "date": date,
            "violation_raw": violation
        })
    st.success("✅ New Police Log Submitted to Database")

# --- Advanced Insights ---
st.markdown("---")
st.header("🌟 Advanced Insights")

if "selected_insight" not in st.session_state:
    st.session_state.selected_insight = "Top 5 Violations"

with st.expander("🚗 Vehicle-Based"):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Top 10 Drug-Related Vehicles"):
            st.session_state.selected_insight = "Top 10 Drug-Related Vehicles"
    with col2:
        if st.button("Most Frequently Searched Vehicles"):
            st.session_state.selected_insight = "Most Frequently Searched Vehicles"

with st.expander("🧍 Demographic-Based", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Highest Arrest Rate by Age Group"):
            st.session_state.selected_insight = "Highest Arrest Rate by Age Group"
    with col2:
        if st.button("Gender Distribution by Country"):
            st.session_state.selected_insight = "Gender Distribution by Country"
    with col3:
        if st.button("Highest Search Rate by Race & Gender"):
            st.session_state.selected_insight = "Highest Search Rate by Race & Gender"

with st.expander("🕒 Time & Duration Based", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Peak Traffic Stop Times"):
            st.session_state.selected_insight = "Peak Traffic Stop Times"
    with col2:
        if st.button("Average Stop Duration per Violation"):
            st.session_state.selected_insight = "Average Stop Duration per Violation"
    with col3:
        if st.button("Night Arrest Likelihood"):
            st.session_state.selected_insight = "Night Arrest Likelihood"

with st.expander("⚖️ Violation-Based"):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Top 5 Violations"):
            st.session_state.selected_insight = "Top 5 Violations"
    with col2:
        if st.button("Violations by Drivers <25"):
            st.session_state.selected_insight = "Violations by Young Drivers"
    with col3:
        if st.button("Rarely Arrested/Search Violations"):
            st.session_state.selected_insight = "Rare Search/Arrest Violations"

with st.expander("🌍 Location-Based"):
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Countries with Most Drug Stops"):
            st.session_state.selected_insight = "Countries with Most Drug Stops"
    with col2:
        if st.button("Arrest Rate by Country & Violation"):
            st.session_state.selected_insight = "Arrest Rate by Country & Violation"
    with col3:
        if st.button("Searches by Country"):
            st.session_state.selected_insight = "Searches by Country"

# --- Insights Logic ---
selected_insight = st.session_state.selected_insight

if selected_insight == "Top 5 Violations":
    query = """
    SELECT violation_raw AS label, COUNT(*) AS value
    FROM vehicle_stops
    GROUP BY violation_raw
    ORDER BY value DESC
    LIMIT 5;
    """
    df = run_query(query)
    st.subheader("🔍 Top 5 Violations")
    st.dataframe(df)
    st.bar_chart(df.set_index("label"))

elif selected_insight == "Top 10 Drug-Related Vehicles":
    query = """
    SELECT vehicle_number AS label, COUNT(*) AS value
    FROM vehicle_stops
    WHERE drug_related = TRUE
    GROUP BY vehicle_number
    ORDER BY value DESC
    LIMIT 10;
    """
    df = run_query(query)
    st.subheader("💊 Top 10 Drug-Related Vehicles")
    st.dataframe(df)
    st.bar_chart(df.set_index("label"))

elif selected_insight == "Most Frequently Searched Vehicles":
    query = """
    SELECT vehicle_number AS label, COUNT(*) AS value
    FROM vehicle_stops
    WHERE search_conducted = TRUE
    GROUP BY vehicle_number
    ORDER BY value DESC
    LIMIT 10;
    """
    df = run_query(query)
    st.subheader("🔍 Most Frequently Searched Vehicles")
    st.dataframe(df)
    st.bar_chart(df.set_index("label"))

elif selected_insight == "Peak Traffic Stop Times":
    query = """
    SELECT
        EXTRACT(HOUR FROM stop_datetime) AS hour_of_day,
        COUNT(*) AS stop_count
    FROM vehicle_stops
    WHERE stop_datetime IS NOT NULL
    GROUP BY hour_of_day
    ORDER BY hour_of_day;
    """
    df = run_query(query)
    st.subheader("⏰ Peak Traffic Stop Times")

    if df.empty:
        st.warning("No stop datetime data available to compute peak times.")
    else:
        df["hour_of_day"] = df["hour_of_day"].astype(int)
        st.dataframe(df)
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("hour_of_day:O", title="Hour of Day (0-23)"),
            y=alt.Y("stop_count:Q", title="Number of Stops"),
            tooltip=["hour_of_day", "stop_count"]
        ).properties(title="Traffic Stops by Hour")
        st.altair_chart(chart, use_container_width=True)
        peak = df.nlargest(3, "stop_count")
        top_hours = ", ".join(f"{int(h)}:00" for h in peak["hour_of_day"])
        st.markdown(f"**Top peak hours:** {top_hours}")

elif selected_insight == "Countries with Most Drug Stops":
    query = """
    SELECT COALESCE(country, location, 'Unknown') AS label, COUNT(*) AS value
    FROM vehicle_stops
    WHERE drug_related = TRUE
    GROUP BY COALESCE(country, location, 'Unknown')
    ORDER BY value DESC;
    """
    df = run_query(query)
    st.subheader("🌍 Countries (Locations) with Most Drug Stops")
    if df.empty:
        st.warning("No drug-related stop data found.")
    else:
        st.dataframe(df)
        st.bar_chart(df.set_index("label"))
