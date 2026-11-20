# citizens4flood

## Run the Streamlit app

The app retrieves ERA5-Land precipitation time series for AOI points from Google
Earth Engine and includes a feedback survey whose responses are saved in SQLite.

1. Install the dependencies with `pip install -r requirements.txt`.
2. Authenticate Earth Engine in the same environment with `earthengine authenticate`
   (or configure Application Default Credentials/service-account credentials for a
   deployment).
3. Start the app with `streamlit run app.py`.
4. Enter your Earth Engine Cloud project ID in the sidebar and connect.
5. Load AOIs from a publicly readable Google Sheet or upload a CSV. The input must
   contain `AOI`, `Center_LONG`, and `Center_LAT` columns; `Event_Number` is optional.
6. Choose a timescale and date window, select AOIs, and run the query. Results can
   be viewed as a chart and downloaded as CSV.
7. Collect workflow feedback in the Survey tab. Responses are saved to
   `survey_responses.db` by default; set `SURVEY_DB_PATH` to choose another database
   path. Ensure the database is on persistent storage before deploying broadly.

The Earth Engine data-loading and precipitation logic is in `gee_workflow.py`,
separate from the Streamlit interface in `app.py`. The app covers the precipitation
workflow implemented in `RPDDFC.ipynb`. The notebook's Sarno-data import and
river-plastic-detection steps are not implemented in its code cells.