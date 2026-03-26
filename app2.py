import streamlit as st
import requests
from xml.etree import ElementTree as ET

st.set_page_config(page_title="OAI‑PMH Extractor", layout="wide")
st.title("OAI‑PMH Extractor")

# --- 1️⃣ Base URL input ---
base_url = st.text_input(
    "OAI‑PMH Base URL",
    value="https://OAI-PMH_Base_URL/oai/request",
    help="Enter the base URL of the OAI-PMH repository (example: https://bdta.ufra.edu.br/oai/request)"
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

# --- 3️⃣ Field selection ---
field_suggestions = [
    "dc:title", "dc:creator", "dc:subject", "dc:description", 
    "dc:type", "dc:publisher", "dc:date", "dc:identifier"
]
field_to_extract = st.selectbox(
    "Field to Extract",
    options=field_suggestions,
    index=4,
    help="Select which field to extract from the records"
)

# --- 4️⃣ Run button ---
if st.button("Run Extraction"):

    st.info(f"Fetching records from {base_url} using metadata format '{metadata_prefix}'...")

    params = {
        "verb": "ListRecords",
        "metadataPrefix": metadata_prefix
    }

    try:
        # SSL verification disabled for testing (set verify=True in production)
        response = requests.get(base_url, params=params, verify=False, timeout=20)

        if response.status_code != 200:
            st.error(f"HTTP {response.status_code} Error accessing the OAI-PMH endpoint.")
        else:
            st.success("Records fetched successfully!")

            # Parse XML response
            xml_root = ET.fromstring(response.text)

            # Common namespaces for OAI-PMH and Dublin Core
            ns = {
                "oai": "http://www.openarchives.org/OAI/2.0/",
                "dc": "http://purl.org/dc/elements/1.1/"
            }

            # Extract records
            records = xml_root.findall(".//oai:record", ns)
            extracted_values = []

            for rec in records:
                # Get the tag name after colon
                tag_name = field_to_extract.split(":")[1]
                field_nodes = rec.findall(f".//dc:{tag_name}", ns)
                values = [n.text for n in field_nodes if n.text]
                extracted_values.extend(values)

            # Display results
            if extracted_values:
                st.write(f"Extracted {len(extracted_values)} values for `{field_to_extract}`:")
                for idx, val in enumerate(extracted_values, 1):
                    st.write(f"{idx}. {val}")
            else:
                st.warning(f"No values found for field `{field_to_extract}` in the retrieved records.")

    except requests.exceptions.SSLError as ssl_err:
        st.error("SSL Error — certificate verification failed.")
        st.text(str(ssl_err))

    except Exception as e:
        st.error("An unexpected error occurred:")
        st.text(str(e))
