import requests
import xml.etree.ElementTree as ET
from collections import Counter
import csv
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional: helps on Windows corporate environments
try:
    import certifi
    VERIFY = False
except ImportError:
    VERIFY = True  # fallback

# If you're behind a corporate proxy and still get SSL errors,
# uncomment the next two lines:
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# VERIFY = False

BASE_URL = "https://bdta.ufra.edu.br/oai/request"

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/"
}

params = {
    "verb": "ListRecords",
    "metadataPrefix": "oai_dc"
}

counter = Counter()
total_records = 0
page = 1


def fetch_with_retry(url, params, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=60,
                verify=VERIFY
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}): {e}")
            time.sleep(5)

    raise Exception("Failed after multiple retries")


with open("hasType_all.txt", "w", encoding="utf-8") as raw_file:

    while True:
        print(f"\nFetching page {page}...")

        response = fetch_with_retry(BASE_URL, params)

        root = ET.fromstring(response.content)

        records = root.findall(".//oai:record", NS)

        if not records:
            print("⚠️ No records found on this page")

        for record in records:
            total_records += 1

            # Correct field for oai_dc
            types = record.findall(".//dc:type", NS)

            for t in types:
                if t.text:
                    value = t.text.strip()

                    # Save raw values
                    raw_file.write(value + "\n")

                    # Count
                    counter[value] += 1

        print(f"  Processed records so far: {total_records}")

        # Progress indicator
        if total_records % 1000 == 0:
            print(f"  ✅ Reached {total_records} records")

        # Handle resumptionToken
        token_elem = root.find(".//oai:resumptionToken", NS)

        if token_elem is None or not token_elem.text:
            print("\nNo more pages.")
            break

        params = {
            "verb": "ListRecords",
            "resumptionToken": token_elem.text.strip()
        }

        page += 1

        # Be polite to server
        time.sleep(1)


# Save aggregated counts
with open("hasType_counts.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["type", "count"])

    for value, count in counter.most_common():
        writer.writerow([value, count])


print("\n🎉 Done!")
print(f"Total records processed: {total_records}")
print(f"Unique type values: {len(counter)}")
