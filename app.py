from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from gee_auth import init_ee
from gee_workflow import (
    PRECIPITATION_DATASETS,
    fetch_precipitation,
    load_aoi_data,
    prepare_aoi_data,
)
from survey_storage import save_survey_response


def render_analysis() -> None:
    st.header("Define the Area-of-Interest")
    data_source = st.radio(
        "Choose an AOI source",
        ("Sample points CSV", "Google Sheet", "Upload CSV"),
        horizontal=True,
    )
    uploaded_file = None
    sheet_id = ""
    sheet_name = "Sarno_Events"
    if data_source == "Sample points CSV":
        st.caption("Use the included Manila, Bangkok, and Santiago sample points.")
    elif data_source == "Google Sheet":
        sheet_id = st.text_input(
            "Google Sheet URL or ID",
            value="1sMJMJD3xOFdhyi2du6cyQdkJ6mooFLCmcsyu6_IAt_o",
        )
        sheet_name = st.text_input("Worksheet name", value=sheet_name)
        st.caption("The worksheet must be publicly readable to load it by URL.")
    else:
        uploaded_file = st.file_uploader("AOI CSV", type="csv")

    st.caption(
        "Required columns: `AOI`, `Center_LONG`, and `Center_LAT`. "
        "`Event_Number` is optional."
    )

    if data_source == "Sample points CSV":
        try:
            csv_path = Path(__file__).with_name("hypothetical_points.csv")
            raw_data = pd.read_csv(csv_path)
            aoi_data, skipped = prepare_aoi_data(raw_data)
            st.session_state["aoi_data"] = aoi_data
            st.session_state["aoi_skipped"] = skipped
            st.session_state["aoi_source"] = data_source
        except Exception as error:
            st.session_state.pop("aoi_data", None)
            st.session_state.pop("aoi_source", None)
            st.error(f"Could not load AOIs: {error}")
    elif st.button("Load AOIs"):
        try:
            raw_data = load_aoi_data(uploaded_file, sheet_id, sheet_name)
            aoi_data, skipped = prepare_aoi_data(raw_data)
            st.session_state["aoi_data"] = aoi_data
            st.session_state["aoi_skipped"] = skipped
            st.session_state["aoi_source"] = data_source
        except Exception as error:
            st.session_state.pop("aoi_data", None)
            st.session_state.pop("aoi_source", None)
            st.error(f"Could not load AOIs: {error}")

    aoi_data = (
        st.session_state.get("aoi_data")
        if st.session_state.get("aoi_source") == data_source
        else None
    )
    if aoi_data is not None:
        if st.session_state.get("aoi_skipped", 0):
            st.warning(
                f"Skipped {st.session_state['aoi_skipped']} row(s) with missing or invalid "
                "AOI names or coordinates."
            )
        st.dataframe(aoi_data, use_container_width=True)
        if {"City", "Point_ID"}.issubset(aoi_data.columns):
            city_options = aoi_data["City"].dropna().astype(str).unique().tolist()
            if city_options:
                selected_city = st.selectbox("1. City", options=city_options)
                city_data = aoi_data[aoi_data["City"].astype(str) == selected_city]
                point_options = city_data["Point_ID"].dropna().unique().tolist()
                if point_options:
                    selected_point_id = st.selectbox(
                        "2. Point ID",
                        options=point_options,
                    )
                    selected_data = city_data[
                        city_data["Point_ID"] == selected_point_id
                    ]
                    selected_point = selected_data.iloc[0]
                    st.write(
                        "Selected coordinates: "
                        f"latitude: {selected_point['Center_LAT']}, "
                        f"longitude: {selected_point['Center_LONG']}"
                    )
                else:
                    selected_data = aoi_data.iloc[0:0]
            else:
                selected_data = aoi_data.iloc[0:0]
        else:
            selected_aois = st.multiselect(
                "AOIs to query",
                options=aoi_data["AOI"].tolist(),
                default=aoi_data["AOI"].tolist(),
            )
            selected_data = aoi_data[aoi_data["AOI"].isin(selected_aois)]

        st.header("Precipitation query")
        timescale = st.selectbox("Timescale", tuple(PRECIPITATION_DATASETS))
        default_days = PRECIPITATION_DATASETS[timescale]["default_days"]
        today = date.today()
        start_date = st.date_input(
            "Start date (inclusive)",
            value=today - timedelta(days=default_days - 1),
        )
        end_date = st.date_input("End date (exclusive)", value=today + timedelta(days=1))

        if st.button("Run precipitation query", type="primary"):
            project_id = st.session_state.get("gee_project_id")
            if not project_id:
                st.error("Connect to an Earth Engine project in the sidebar before querying.")
            elif start_date >= end_date:
                st.error("The start date must be earlier than the exclusive end date.")
            elif selected_data.empty:
                st.error("Select at least one point or AOI.")
            else:
                all_results = []
                errors = []
                progress = st.progress(0)
                with st.spinner("Retrieving ERA5-Land precipitation from Earth Engine..."):
                    for index, (_, row) in enumerate(selected_data.iterrows(), start=1):
                        try:
                            result = fetch_precipitation(row, timescale, start_date, end_date)
                            if not result.empty:
                                all_results.append(result)
                        except Exception as error:
                            errors.append(f"{row['AOI']}: {error}")
                        progress.progress(index / len(selected_data))

                for error in errors:
                    st.error(f"Could not retrieve data for {error}")

                if all_results:
                    combined = pd.concat(all_results, ignore_index=True)
                    combined = combined.sort_values(["AOI", "timestamp"])
                    st.session_state["precipitation_results"] = combined
                else:
                    st.session_state.pop("precipitation_results", None)
                    if not errors:
                        st.warning("No precipitation records were returned for this period.")

    results = st.session_state.get("precipitation_results")
    if results is not None:
        st.header("Results")
        chart_data = results.pivot_table(
            index="timestamp",
            columns="AOI",
            values="precipitation",
            aggfunc="mean",
        )
        st.line_chart(chart_data, y_label="Precipitation (m)")

        valid_results = results.dropna(subset=["precipitation"])
        if not valid_results.empty:
            peak_indices = valid_results.groupby("AOI")["precipitation"].idxmax()
            peaks = valid_results.loc[
                peak_indices, ["AOI", "timestamp", "precipitation"]
            ].sort_values("AOI")
            peaks = peaks.rename(
                columns={
                    "timestamp": "Peak date",
                    "precipitation": "Maximum precipitation (m)",
                }
            )
            st.subheader("Maximum precipitation by AOI")
            st.dataframe(peaks, use_container_width=True)

        st.subheader("Time series data")
        st.dataframe(results, use_container_width=True)
        st.download_button(
            "Download precipitation CSV",
            data=results.to_csv(index=False).encode("utf-8"),
            file_name=f"{timescale.lower()}_precipitation_data.csv",
            mime="text/csv",
        )


def render_survey() -> None:
    st.header("Share your feedback")
    st.write(
        "Your response helps us improve the precipitation analysis and related tools. "
        "Do not include sensitive or identifying information in your comments."
    )

    with st.form("workflow_feedback"):
        role = st.selectbox(
            "Which best describes your role?",
            ("Community member", "Researcher", "Practitioner", "Other", "Prefer not to say"),
        )
        usefulness = st.slider(
            "How useful was this workflow for your work?",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = not useful, 5 = very useful",
        )
        actionable = st.radio(
            "Were the results actionable?",
            ("Yes", "Partly", "No", "I did not run an analysis"),
        )
        comments = st.text_area(
            "What worked well, or what should we improve?",
            max_chars=2000,
        )
        submitted = st.form_submit_button("Submit feedback")

    if submitted:
        try:
            response_id = save_survey_response(
                role=role,
                usefulness=usefulness,
                actionable=actionable,
                comments=comments,
            )
        except Exception as error:
            st.error(f"Could not save your response: {error}")
        else:
            st.success(f"Thank you. Your feedback was saved (response {response_id}).")
            st.caption(
                "Responses are stored in the app's local SQLite database. "
                "For a multi-instance or ephemeral deployment, configure shared persistent storage."
            )


def main() -> None:
    st.set_page_config(page_title="River Plastic Detection", page_icon="🌧️", layout="wide")
    try:
        init_ee()
    except Exception as error:
        st.error(f"Could not initialize Earth Engine: {error}")
        st.stop()

    project_id = str(st.secrets["earthengine"]["project_id"]).strip()
    st.session_state["gee_project_id"] = project_id

    st.title("River Plastic Detection")
    st.write(
        "Explore ERA5-Land precipitation for areas of interest and share feedback "
        "about the workflow."
    )

    with st.sidebar:
        st.header("Google Earth Engine")
        st.success(f"Connected project: {project_id}")

        with st.expander("One-time authentication setup"):
            st.markdown(
                "Add the Earth Engine Cloud project ID and service-account credentials "
                "to Streamlit secrets under `[earthengine]` before starting the app."
            )

    analysis_tab, survey_tab = st.tabs(["Precipitation analysis", "Survey"])
    with analysis_tab:
        render_analysis()
    with survey_tab:
        render_survey()


if __name__ == "__main__":
    main()
