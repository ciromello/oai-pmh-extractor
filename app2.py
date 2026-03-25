import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from io import StringIO

st.title("OAI-PMH Harvester (Flexible)")

# ----------------------
# User Inputs
# ----------------------
base_url = st.text_input("OAI-PMH Base URL", "https://bdta.ufra.edu.br/oai/request")
metadata_prefix = st.text_input("Metadata Prefix", "oai_dc")
field_input = st.text_input("Field (DC: dc:title | MARC: 245$a)", "dc:title")
deduplicate = st.checkbox("Remove duplicates", True)

# Namespaces
namespaces = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'marc': 'http://www.loc.gov/MARC21/slim'
}

# ----------------------
# Helper Functions
# ----------------------

def parse_dc(metadata, field):
    values = []
    elements = metadata.findall(f".//{field}", namespaces)
    for el in elements:
        if el.text:
            values.append(el.text.strip())
    return values


def parse_marc(metadata, field_input):
    values = []
    try:
        tag, subfield = field_input.split('$')
    except ValueError:
        return values

    for datafield in metadata.findall(f".//marc:datafield[@tag='{tag}']", namespaces):
        for sub in datafield.findall(f"marc:subfield[@code='{subfield}']", namespaces):
            if sub.text:
                values.append(sub.text.strip())
    return values

# ----------------------
# Harvest Button
# ----------------------
if st.button("Harvest"):
    records = []
    url = f"{base_url}?verb=ListRecords&metadataPrefix={metadata_prefix}"
    total_records = 0

    progress = st.progress(0)
    status = st.empty()

    with st.spinner("Harvesting records..."):
        while True:
            response = requests.get(url)
            if response.status_code != 200:
                st.error("Error fetching data")
                break

            root = ET.fromstring(response.content)
            batch_count = 0

            for record in root.findall('.//oai:record', namespaces):
                metadata = record.find('.//oai:metadata', namespaces)
                if metadata is not None:
                    if metadata_prefix.startswith("oai_dc"):
                        values = parse_dc(metadata, field_input)
                    else:
                        values = parse_marc(metadata, field_input)

                    records.extend(values)
                    batch_count += 1

            total_records += batch_count
            status.text(f"Processed {total_records} records...")
            progress.progress(min(100, total_records % 100))

            # Resumption Token
            token = root.find('.//oai:resumptionToken', namespaces)
            if token is not None and token.text:
                url = f"{base_url}?verb=ListRecords&resumptionToken={token.text}"
            else:
                break

    # Deduplicate
    if deduplicate:
        records = list(set(records))

    st.success(f"Harvested {len(records)} values")

    # Display
    df = pd.DataFrame(records, columns=["Value"])
    st.dataframe(df)

    # CSV Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="harvest.csv",
        mime="text/csv"
    )
