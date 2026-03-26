import streamlit as st
import requests
from xml.etree import ElementTree as ET
import pandas as pd

# ----------------------------
# Streamlit App
# ----------------------------
st.title("OAI-PMH Extractor (SSL Fix)")

# User inputs
base_url = st.text_input("Base URL", "https://bdta.ufra.edu.br/oai/request")
metadata_prefix = st.text_input("Metadata Format", "oai_dc")
harvest_field = st.text_input("Field to Harvest", "dc:type")

if st.button("Harvest Records"):
    st.info("Harvesting records… this may take a while")
    
    params = {
        "verb": "ListRecords",
        "metadataPrefix": metadata_prefix
    }
    
    all_records = []
    session = requests.Session()
    
    try:
        while True:
            # Disable SSL verification to bypass certificate issues
            response = session.get(base_url, params=params, verify=False, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            ns = {'oai': 'http://www.openarchives.org/OAI/2.0/'}
            
            # Iterate over records
            for record in root.findall(".//oai:record", ns):
                metadata = record.find("oai:metadata", ns)
                if metadata is not None:
                    data_elem = metadata.find(f".//{harvest_field}")
                    if data_elem is not None and data_elem.text:
                        all_records.append(data_elem.text)
            
            # Check for resumptionToken
            token_elem = root.find(".//oai:resumptionToken", ns)
            if token_elem is None or token_elem.text is None:
                break
            else:
                params = {"verb": "ListRecords", "resumptionToken": token_elem.text}
        
        # Display results
        if all_records:
            df = pd.DataFrame(all_records, columns=[harvest_field])
            st.success(f"Harvested {len(all_records)} records")
            st.dataframe(df)
        else:
            st.warning("No records found.")
    
    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {e}")
    except ET.ParseError as e:
        st.error(f"XML parse error: {e}")
