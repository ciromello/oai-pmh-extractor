import streamlit as st
import requests
from xml.etree import ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Universal OAI-PMH Harvester", layout="wide")
st.title("📡 Universal OAI-PMH Harvester (DC & MARC XML)")

# ----------------------------
# User Inputs
# ----------------------------
base_url = st.text_input("OAI-PMH Base URL", "https://bdta.ufra.edu.br/oai/request")
metadata_format = st.selectbox("Metadata Format", ["oai_dc", "marcxml"])
field_to_harvest = st.text_input(
    "Field to Harvest",
    "dc:type" if metadata_format=="oai_dc" else "952$d",
    help="For Dublin Core use dc:tag. For MARC use fieldTag$subfieldCode (e.g., 952$d)"
)
download_filename = st.text_input("CSV filename", "harvested_records.csv")

# ----------------------------
# Button to start harvesting
# ----------------------------
if st.button("Start Harvesting"):

    st.info("Harvesting records. This may take some time…")
    
    # Determine namespaces
    if metadata_format == "oai_dc":
        ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        # Split field_to_harvest
        try:
            prefix, tag = field_to_harvest.split(":")
        except ValueError:
            st.error("Dublin Core fields must be in the form dc:tag")
            st.stop()
    else:
        ns = {
            'oai': 'http://www.openarchives.org/OAI/2.0/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        try:
            field_tag, subfield_code = field_to_harvest.split("$")
        except ValueError:
            st.error("MARC fields must be in the form 952$d")
            st.stop()
    
    # ----------------------------
    # Harvesting loop
    # ----------------------------
    params = {"verb": "ListRecords", "metadataPrefix": metadata_format}
    session = requests.Session()
    all_values = []

    try:
        while True:
            response = session.get(base_url, params=params, verify=False, timeout=60)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            
            # Iterate over records
            for record in root.findall(".//oai:record", ns):
                metadata = record.find("oai:metadata", ns)
                if metadata is None:
                    continue
                
                if metadata_format == "oai_dc":
                    # Dublin Core extraction
                    elem = metadata.find(f".//{field_to_harvest}", ns)
                    if elem is not None and elem.text:
                        all_values.append(elem.text.strip())
                else:
                    # MARC extraction
                    marc_record = metadata.find("marc:record", ns)
                    if marc_record is not None:
                        for datafield in marc_record.findall("marc:datafield", ns):
                            if datafield.attrib.get("tag") == field_tag:
                                subfield = datafield.find(f"marc:subfield[@code='{subfield_code}']", ns)
                                if subfield is not None and subfield.text:
                                    all_values.append(subfield.text.strip())
            
            # Check for resumptionToken
            token_elem = root.find(".//oai:resumptionToken", ns)
            if token_elem is None or token_elem.text is None or token_elem.text.strip() == "":
                break
            else:
                params = {"verb": "ListRecords", "resumptionToken": token_elem.text.strip()}

        # ----------------------------
        # Deduplicate and create DataFrame
        # ----------------------------
        if not all_values:
            st.warning("No records found.")
            st.stop()

        df = pd.DataFrame(all_values, columns=[field_to_harvest])
        df = df.drop_duplicates().reset_index(drop=True)

        # Counts
        counts = df[field_to_harvest].value_counts().reset_index()
        counts.columns = [field_to_harvest, "count"]

        st.success(f"Harvested {len(all_values)} records ({len(df)} unique)")
        st.dataframe(counts)

        # ----------------------------
        # CSV Download
        # ----------------------------
        csv_data = counts.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=download_filename,
            mime='text/csv'
        )

    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {e}")
    except ET.ParseError as e:
        st.error(f"XML parse error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
