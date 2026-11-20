# citizens4flood

## Run the Streamlit app

The app retrieves ERA5-Land precipitation time series for AOI points from Google
Earth Engine and includes a feedback survey whose responses are saved in SQLite.

1. Install the dependencies with `pip install -r requirements.txt`.
2. Configure Earth Engine authentication:
   - **Streamlit Community Cloud:** add the project ID and service-account
     credentials to Streamlit secrets. Either use the standard service-account
     table:

     ```toml
     [gcp_service_account]
     type = "service_account"
     project_id = "your-cloud-project-id"
     client_email = "earth-engine@your-project.iam.gserviceaccount.com"
     private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
     ```

     Or use a simple Earth Engine section:

     ```toml
     [gee]
     project_id = "your-cloud-project-id"
     client_email = "earth-engine@your-project.iam.gserviceaccount.com"
     private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
     ```

     Replace the values with credentials from the service-account JSON file.
     The private key must remain private and must not be committed to Git.
   - **Local use:** run `earthengine authenticate` or configure Application Default
     Credentials.
3. Start the app with `streamlit run app.py`.
4. Confirm or enter the Earth Engine Cloud project ID in the sidebar and connect.
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