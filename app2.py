import streamlit as st
import requests
from xml.etree import ElementTree as ET
import pandas as pd

st.set_page_config(page_title="OAI‑PMH Harvester", layout="wide")
st.title("OAI‑PMH Extractor — Fields & Subfields")

# --- 1️⃣ Base URL input ---
base_url = st.text_input(
    "OAI‑PMH Base URL",
    value="https://OAI-PMH_Base_URL/oai/request",
    help="Enter the base URL of the OAI-PMH repository"
)

# --- 2️⃣ Metadata format selection ---
metadata_options = [
    "oai_dc", "marc21", "marcxml", "mods", "dim", "emd", "md", "mets"
]
metadata_prefix = st.selectbox(
    "Metadata Format (metadataPrefix)",
    options=metadata_options,
    index=0,
    help="Select the metadata format to harvest"
)

# --- 3️⃣ Field & Subfield selection ---
field_suggestions = [
    "dc:title", "dc:creator", "dc:subject", "dc:description",
    "dc:type", "dc:publisher", "dc:date", "dc:identifier"
]
fields_to_extract = st.multiselect(
    "Fields to Extract (can select multiple)",
    options=field_suggestions,
    default=["dc:type"],
    help="Select one or more fields to extract from the records"
)

# --- 4️⃣ Run button ---
if st.button("Run Extraction"):

    st.info(f"Fetching records from {base_url} using metadata format '{metadata_prefix}'...")

    params = {
        "verb": "ListRecords",
        "metadataPrefix": metadata_prefix
    }

    try:
        # Make request, ignoring SSL verification for testing
        response = requests.get(base_url, params=params, verify=False, timeout=20)

        if response.status_code != 200:
            st.error(f"HTTP {response.status_code} Error accessing the OAI-PMH endpoint.")
        else:
            st.success("Records fetched successfully!")

            # Parse XML
            xml_root = ET.fromstring(response.text)

            # Define namespaces for OAI-PMH and Dublin Core
            ns = {
                "oai": "http://www.openarchives.org/OAI/2.0/",
                "dc": "http://purl.org/dc/elements/1.1/"
            }

            # Extract records
            records = xml_root.findall(".//oai:record", ns)

            if not records:
                st.warning("No records found.")
            else:
                st.info(f"Found {len(records)} records. Extracting fields...")

                data_rows = []

                for rec in records:
                    row = {}
                    for field in fields_to_extract:
                        tag_name = field.split(":")[1]
                        nodes = rec.findall(f".//dc:{tag_name}", ns)
                        # join multiple values with semicolon
                        row[field] = "; ".join([n.text for n in nodes if n.text])
                    data_rows.append(row)

                # Convert to DataFrame and display
                df = pd.DataFrame(data_rows)
                st.write("### Extracted Records")
                st.dataframe(df)

                # Optional: allow export
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name='oai_records.csv',
                    mime='text/csv'
                )

    except requests.exceptions.SSLError as ssl_err:
        st.error("SSL Error — certificate verification failed. You may use verify=False for testing.")
        st.text(str(ssl_err))

    except Exception as e:
        st.error("An unexpected error occurred:")
        st.text(str(e))
