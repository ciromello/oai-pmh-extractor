import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="OAI-PMH Harvester", layout="wide")

st.title("📚 OAI-PMH Harvester")
st.markdown("Harvest metadata from any OAI-PMH repository with flexible options.")

# ----------------------
# Sidebar (like example app)
# ----------------------
st.sidebar.header("⚙️ Configuration")

base_url = st.sidebar.text_input("OAI-PMH Base URL", "https://bdta.ufra.edu.br/oai/request")

metadata_prefix = st.sidebar.selectbox(
    "Metadata Format",
    ["oai_dc", "marc21", "mods", "dim"],
    index=0
)

field_input = st.sidebar.text_input(
    "Field",
    "dc:title",
    help="DC: dc:title | MARC: 245$a"
)

from_date = st.sidebar.text_input("From Date (YYYY-MM-DD)", "")
until_date = st.sidebar.text_input("Until Date (YYYY-MM-DD)", "")

set_spec = st.sidebar.text_input("Set (optional)", "")

deduplicate = st.sidebar.checkbox("Remove duplicates", True)

start_button = st.sidebar.button("🚀 Start Harvest")

# ----------------------
# Namespaces
# ----------------------
namespaces = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'marc': 'http://www.loc.gov/MARC21/slim'
}

# ----------------------
# Parsers
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
# Harvest Logic
# ----------------------
if start_button:
    records = []

    url = f"{base_url}?verb=ListRecords&metadataPrefix={metadata_prefix}"

    if from_date:
        url += f"&from={from_date}"
    if until_date:
        url += f"&until={until_date}"
    if set_spec:
        url += f"&set={set_spec}"

    st.subheader("📊 Harvest Results")

    progress = st.progress(0)
    status = st.empty()

    total_records = 0

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
                if metadata_prefix == "oai_dc":
                    values = parse_dc(metadata, field_input)
                else:
                    values = parse_marc(metadata, field_input)

                records.extend(values)
                batch_count += 1

        total_records += batch_count

        status.info(f"Processed {total_records} records...")
        progress.progress(min(100, (total_records % 500) / 5))

        token = root.find('.//oai:resumptionToken', namespaces)

        if token is not None and token.text:
            url = f"{base_url}?verb=ListRecords&resumptionToken={token.text}"
        else:
            break

    if deduplicate:
        records = list(set(records))

    st.success(f"✅ Harvested {len(records)} values")

    df = pd.DataFrame(records, columns=["Value"])

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        "⬇️ Download CSV",
        csv,
        "harvest.csv",
        "text/csv"
    )
