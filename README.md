# citizens4flood

## Run the Streamlit app

The app retrieves ERA5-Land precipitation time series for AOI points from Google
Earth Engine and includes a feedback survey whose responses are saved in SQLite.

1. Install the dependencies with `pip install -r requirements.txt`.
2. Configure Earth Engine authentication in Streamlit secrets:

   ```toml
   [earthengine]
   project_id = "your-cloud-project-id"
   client_email = "earth-engine@your-project.iam.gserviceaccount.com"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   ```

   Replace the values with credentials from the service-account JSON file.
   The private key must remain private and must not be committed to Git. Earth
   Engine is initialized when the app starts; if initialization fails, the app
   displays the error and stops.
3. Start the app with `streamlit run app.py`.
4. Load AOIs from a publicly readable Google Sheet or upload a CSV. The input must
   contain `AOI`, `Center_LONG`, and `Center_LAT` columns; `Event_Number` is optional.
   When both `City` and `Point_ID` columns are present, choose a city first and then
   one or more point IDs. The included
   [hypothetical Manila points CSV](./manila_hypothetical_points.csv) provides ten
   sample locations for this flow.
5. Choose a timescale and date window, select AOIs, and run the query. Results can
   be viewed as a chart and downloaded as CSV.
6. Collect workflow feedback in the Survey tab. Responses are saved to
   `survey_responses.db` by default; set `SURVEY_DB_PATH` to choose another database
   path. Ensure the database is on persistent storage before deploying broadly.

The Earth Engine data-loading and precipitation logic is in `gee_workflow.py`,
separate from the Streamlit interface in `app.py`. The app covers the precipitation
workflow implemented in `RPDDFC.ipynb`. The notebook's Sarno-data import and
river-plastic-detection steps are not implemented in its code cells.