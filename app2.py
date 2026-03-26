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

# --- 3️⃣ Field & Subfield selection ---
st.markdown("### Fields & Subfields to Extract")
st.markdown(
    "You can select suggested fields or manually type any field/subfield in the format `dc:type`, `dc:creator`, etc."
)

# Suggested fields dropdown (multi-select)
field_suggestions = [
    "dc:title", "dc:creator", "dc:subject", "dc:description",
    "dc:type", "dc:publisher", "dc:date", "dc:identifier"
]
selected_fields = st.multiselect(
    "Select Suggested Fields",
    options=field_suggestions,
    default=["dc:type"]
)

# Manual fields input
manual_fields = st.text_area(
    "Manual Fields (one per line)",
    placeholder="dc:type\ndc:creator\nmarc:245$a",
    help="Enter any field/subfield you want to harvest, one per line"
)

# Combine both lists into final fields to extract
manual_fields_list = [f.strip() for f in manual_fields.splitlines() if f.strip()]
fields_to_extract = list(set(selected_fields + manual_fields_list))

# --- 4️⃣ Run Extraction button ---
if st.button("Run Extraction"):

    if not fields_to_extract:
        st.warning("Please select or enter at least one field to extract.")
    else:
        st.info(f"Fetching records from {base_url} using metadata format '{metadata_prefix}'...")

        params = {
            "verb": "ListRecords",
            "metadataPrefix": metadata_prefix
        }

        try:
            # SSL verification disabled for testing
            response = requests.get(base_url, params=params, verify=False, timeout=20)

            if response.status_code != 200:
                st.error(f"HTTP {response.status_code} Error accessing the OAI-PMH endpoint.")
            else:
                st.success("Records fetched successfully!")

                # Parse XML
                xml_root = ET.fromstring(response.text)

                # Define default namespaces
                ns = {
                    "oai": "http://www.openarchives.org/OAI/2.0/",
                    "dc": "http://purl.org/dc/elements/1.1/",
                    "marc": "http://www.loc.gov/MARC21/slim"
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
                            # Support namespaces like dc or marc
                            if ':' in field:
                                prefix, tag_name = field.split(":", 1)
                            else:
                                prefix, tag_name = "", field

                            # Use namespace if available
                            ns_prefix = ns.get(prefix, "")
                            if ns_prefix:
                                nodes = rec.findall(f".//{prefix}:{tag_name}", ns)
                            else:
                                nodes = rec.findall(f".//{tag_name}")

                            # Join multiple values
                            row[field] = "; ".join([n.text for n in nodes if n.text])
                        data_rows.append(row)

                    # Convert to DataFrame and display
                    df = pd.DataFrame(data_rows)
                    st.write("### Extracted Records")
                    st.dataframe(df)

                    # Download button
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
