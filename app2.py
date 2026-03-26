# inside harvesting loop
try:
    while True:
        response = session.get(base_url, params=params, verify=False, timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        # extract records (as before)
        ...

        # handle resumptionToken safely
        token_elem = root.find(".//oai:resumptionToken", ns)
        if token_elem is None or token_elem.text is None or token_elem.text.strip() == "":
            break
        else:
            next_token = token_elem.text.strip()
            # Try next batch, but catch server errors
            try:
                params = {"verb": "ListRecords", "resumptionToken": next_token}
            except requests.exceptions.HTTPError as e:
                st.warning(f"Cannot fetch next batch: {e}. Stopping harvesting.")
                break
