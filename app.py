import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from collections import Counter

st.title("OAI-PMH Field Extractor")

# --- USER INPUT ---
base_url = st.text_input("OAI-PMH Base URL", "")
metadata_prefix = st.text_input("metadataPrefix (e.g., oai_dc, marcxml)", "")

mode = st.radio("Select Extraction Mode", ["Simple Field", "MARC Field + Subfield"])

field = st.text_input("Field (e.g., edm:hasType or 952)", "")
subfield = ""

if mode == "MARC Field + Subfield":
    subfield = st.text_input("Subfield (e.g., d)", "")

run_button = st.button("Run Harvest")

# --- Namespaces ---
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "marc": "http://www.loc.gov/MARC21/slim",
    "dc": "http://purl.org/dc/elements/1.1/"
}

if run_button:
    if not base_url or not metadata_prefix or not field:
        st.error("Please fill in all required fields.")
    else:
        params = {
            "verb": "ListRecords",
            "metadataPrefix": metadata_prefix
        }

        counter = Counter()
        page = 1
        total_records = 0

        progress = st.progress(0)
        status = st.empty()

        try:
            while True:
                status.text(f"Fetching page {page}...")

                response = requests.get(base_url, params=params, timeout=60)
                response.raise_for_status()

                root = ET.fromstring(response.content)

                records = root.findall(".//oai:record", NS)

                for record in records:
                    total_records += 1

                    # --- Simple field ---
                    if mode == "Simple Field":
                        try:
                            # Extract just the tag name (ignore prefix)
                            tag = field.split(":")[-1]
                            # Find elements regardless of namespace
                            elements = record.findall(f".//{{*}}{tag}")
                        except:
                            st.error("Invalid field format. Use prefix:tag (e.g., edm:hasType)")
                            st.stop()

                        for el in elements:
                            if el.text:
                                counter[el.text.strip()] += 1

                    # --- MARC ---
                    else:
                        datafields = record.findall(f".//marc:datafield[@tag='{field}']", NS)

                        for df in datafields:
                            subfields = df.findall(f"marc:subfield[@code='{subfield}']", NS)

                            for sf in subfields:
                                if sf.text:
                                    counter[sf.text.strip()] += 1

                token_elem = root.find(".//oai:resumptionToken", NS)

                if token_elem is None or not token_elem.text:
                    break

                params = {
                    "verb": "ListRecords",
                    "resumptionToken": token_elem.text.strip()
                }

                page += 1
                progress.progress(min(page / 50, 1.0))  # simple progress estimate
                time.sleep(1)

            # --- Convert to DataFrame ---
            df = pd.DataFrame(counter.items(), columns=["Value", "Count"])
            df = df.sort_values(by="Count", ascending=False)

            st.success(f"Done! {total_records} records processed.")

            st.dataframe(df)

            # --- Download button ---
            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="oai_results.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"Error: {e}")
