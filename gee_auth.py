import json

import ee
import streamlit as st


@st.cache_resource(show_spinner="Initializing Google Earth Engine...")
def init_ee() -> bool:
    """Authenticate and initialize Earth Engine once per app process."""
    if "earthengine" not in st.secrets:
        raise ValueError(
            "Add an [earthengine] section with project_id, client_email, and "
            "private_key to Streamlit secrets."
        )

    ee_cfg = st.secrets["earthengine"]
    project_id = str(ee_cfg.get("project_id", "")).strip()
    email = ee_cfg.get("client_email")
    private_key = ee_cfg.get("private_key")
    if not project_id or not email or not private_key:
        raise ValueError(
            "The [earthengine] secrets section requires project_id, "
            "client_email, and private_key."
        )

    service_account = dict(ee_cfg)
    service_account["type"] = "service_account"
    service_account["project_id"] = project_id
    service_account["client_email"] = email
    service_account["private_key"] = str(private_key).replace("\\n", "\n")
    service_account["token_uri"] = (
        service_account.get("token_uri") or "https://oauth2.googleapis.com/token"
    )

    credentials = ee.ServiceAccountCredentials(
        email=email,
        key_data=json.dumps(service_account),
    )
    ee.Initialize(credentials=credentials, project=project_id)
    return True