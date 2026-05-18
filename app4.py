import streamlit as st
import requests
from xml.etree import ElementTree as ET
import pandas as pd

st.set_page_config(page_title="OAI‑PMH Harvester", layout="wide")
st.title("OAI‑PMH Extractor — Field & Subfield CSV Export")

# --- 1️⃣ Input OAI-PMH Base URL ---
base_url = st.text_input(
    "OAI‑PMH Base URL",
    value="https://OAI-PMH_Base_URL/oai/request",
    help="Enter the OAI-PMH repository URL to harvest"
)

# --- 2️⃣ Metadata format (user input) ---
metadata_prefix = st.text_input(
    "Metadata Format (metadataPrefix)",
    value="oai_dc",
    help="Enter metadata format (e.g., oai_dc, marcxml, mods, etc.)"
)

# --- 3️⃣ Field and optional Subfield input ---
st.markdown(
    "### Field and Subfield to Extract\n"
    "For institutional repositories, input fields like `dc:type`.\n"
    "For catalogs, you can input fields and subfields like `952$d`."
)
field_input = st.text_input(
    "Field (and subfield)",
    value="dc:type",
    help="Enter the field (and optional subfield) to extract, e.g., dc:type or 952$d"
)

# --- 4️⃣ Run button ---
if st.button("Run Extraction"):

    if not base_url or not metadata_prefix or not field_input:
        st.warning("Please fill in Base URL, Metadata Format, and Field/Subfield.")
    else:
        st.info(f"Harvesting field '{field_input}' from {base_url}...")

        params = {
            "verb": "ListRecords",
            "metadataPrefix": metadata_prefix
        }

        try:
            # SSL verification disabled for testing
            response = requests.get(base_url, params=params, verify=False, timeout=30)
            response.raise_for_status()

            # Parse XML
            xml_root = ET.fromstring(response.text)

            # Namespaces
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
                st.info(f"Found {len(records)} records. Extracting values for '{field_input}'...")

                # Determine prefix and tag/subfield
                if ":" in field_input:
                    prefix, tag = field_input.split(":", 1)
                elif "$" in field_input:
                    tag, subfield = field_input.split("$", 1)
                    prefix = "marc"
                else:
                    tag = field_input
                    prefix = ""

                extracted_values = []

                for rec in records:
                    if prefix == "marc":
                        # MARC: find datafield with tag and subfield code
                        datafields = rec.findall(f".//marc:datafield[@tag='{tag}']", ns)
                        for df in datafields:
                            subfields = df.findall(f"marc:subfield[@code='{subfield}']", ns)
                            for sf in subfields:
                                if sf.text:
                                    extracted_values.append(sf.text)
                    elif prefix:
                        # Namespaced fields (e.g., dc)
                        nodes = rec.findall(f".//{prefix}:{tag}", ns)
                        for n in nodes:
                            if n.text:
                                extracted_values.append(n.text)
                    else:
                        # Non-namespaced
                        nodes = rec.findall(f".//{tag}")
                        for n in nodes:
                            if n.text:
                                extracted_values.append(n.text)

                if extracted_values:
                    df = pd.DataFrame({field_input: extracted_values})
                    st.write(f"### Extracted Values ({len(extracted_values)})")
                    st.dataframe(df)

                    # CSV download
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"oai_harvest_{field_input.replace('$','_')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(f"No values found for field '{field_input}'.")

        except requests.exceptions.RequestException as e:
            st.error(f"Request Error: {str(e)}")

        except ET.ParseError as e:
            st.error(f"XML Parse Error: {str(e)}")
