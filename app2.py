import streamlit as st
import requests
from xml.etree import ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Universal OAI-PMH Harvester", layout="wide")
st.title("📡 Universal OAI-PMH Harvester (IRs & Catalogs)")

# ----------------------------
# User Inputs
# ----------------------------
base_url = st.text_input("OAI-PMH Base URL", "")
metadata_format = st.selectbox("Metadata Format", ["oai_dc", "marcxml"])

# Multi-field input, comma-separated
field_input = st.text_input(
    "Fields to Harvest",
    "dc:type" if metadata_format=="oai_dc" else "952$d",
    help="Comma-separated. DC: dc:type, dc:creator etc. MARC: 952$d, 245$a etc."
)
download_filename = st.text_input("CSV filename", "harvested_records.csv")

# ----------------------------
# Harvest button
# ----------------------------
if st.button("Start Harvesting"):

    if not base_url.strip():
        st.error("Please enter a valid OAI-PMH Base URL.")
        st.stop()

    st.info("Harvesting records. This may take a while…")

    # Prepare fields
    fields_to_harvest = [f.strip() for f in field_input.split(",")]

    # Determine namespaces
    if metadata_format == "oai_dc":
        ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        # Validate field format
        for f in fields_to_harvest:
            if ":" not in f:
                st.error("Dublin Core fields must be in the form dc:tag")
                st.stop()
    else:
        ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        for f in fields_to_harvest:
            if "$" not in f:
                st.error("MARC fields must be in the form 952$d")
                st.stop()

    # ----------------------------
    # Harvesting loop
    # ----------------------------
    params = {"verb": "ListRecords", "metadataPrefix": metadata_format}
    session = requests.Session()
    all_records = []
    batch_count = 0

    try:
        while True:
            batch_count += 1
            st.info(f"Fetching batch {batch_count}…")
            try:
                response = session.get(base_url, params=params, verify=False, timeout=60)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                st.warning(f"Server error on batch {batch_count}: {e}. Stopping harvest.")
                break
            except requests.exceptions.RequestException as e:
                st.error(f"Request error: {e}")
                break

            root = ET.fromstring(response.content)

            # Extract records
            for record in root.findall(".//oai:record", ns):
                metadata = record.find("oai:metadata", ns)
                if metadata is None:
                    continue

                record_dict = {}
                if metadata_format == "oai_dc":
                    for f in fields_to_harvest:
                        elem = metadata.find(f".//{f}", ns)
                        record_dict[f] = elem.text.strip() if elem is not None and elem.text else ""
                else:
                    marc_record = metadata.find("marc:record", ns)
                    if marc_record is not None:
                        for f in fields_to_harvest:
                            field_tag, subfield_code = f.split("$")
                            value = ""
                            for datafield in marc_record.findall("marc:datafield", ns):
                                if datafield.attrib.get("tag") == field_tag:
                                    subfield = datafield.find(f"marc:subfield[@code='{subfield_code}']", ns)
                                    if subfield is not None and subfield.text:
                                        value = subfield.text.strip()
                                        break
                            record_dict[f] = value
                all_records.append(record_dict)

            # Handle resumptionToken safely
            token_elem = root.find(".//oai:resumptionToken", ns)
            if token_elem is None or token_elem.text is None or token_elem.text.strip() == "":
                st.info("No more batches. Harvest complete.")
                break
            else:
                next_token = token_elem.text.strip()
                params = {"verb": "ListRecords", "resumptionToken": next_token}

        # ----------------------------
        # Deduplicate and create DataFrame
        # ----------------------------
        if not all_records:
            st.warning("No records found.")
            st.stop()

        df = pd.DataFrame(all_records).drop_duplicates().reset_index(drop=True)
        st.success(f"Harvested {len(all_records)} records ({len(df)} unique)")

        # Show counts for each field
        st.subheader("Field Value Counts")
        for f in fields_to_harvest:
            counts = df[f].value_counts().reset_index()
            counts.columns = [f, "count"]
            st.write(f"**{f}**")
            st.dataframe(counts)

        # ----------------------------
        # CSV download
        # ----------------------------
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=download_filename,
            mime='text/csv'
        )

    except ET.ParseError as e:
        st.error(f"XML parse error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
