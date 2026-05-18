import streamlit as st
from pymarc import MARCReader, parse_xml_to_array
from collections import Counter
import pandas as pd
import re
import unicodedata
import matplotlib.pyplot as plt

st.set_page_config(page_title="MARC Analyzer", layout="centered")
st.title("📚 MARC Field/Subfield Analyzer")

# ----------------------------
# NORMALIZATION
# ----------------------------
def normalize(value):
    value = value.lower().strip()
    value = ''.join(
        c for c in unicodedata.normalize('NFD', value)
        if unicodedata.category(c) != 'Mn'
    )
    return value

# ----------------------------
# OPTIONS
# ----------------------------
normalize_option = st.checkbox("Normalize values (Vídeos → videos)")
separate_csv = st.checkbox("Download separate CSV per field")

uploaded_file = st.file_uploader(
    "Upload MARC file (.mrc, .iso, .xml, .mrk, .txt)",
    type=["mrc", "iso", "xml", "mrk", "txt"]
)

if uploaded_file:
    try:
        content = uploaded_file.read()
        text_sample = content[:1000].decode(errors="ignore")

        selected_fields_input = st.text_area(
            "Enter field-subfield(s), one per line (e.g., 990$a)"
        )

        if selected_fields_input:
            selected_fields = [
                line.strip() for line in selected_fields_input.splitlines() if line.strip()
            ]

            counters = {sel: Counter() for sel in selected_fields}

            # ==================================================
            # 🟢 DETECT FORMAT BY CONTENT (CRITICAL FIX)
            # ==================================================
            if text_sample.strip().startswith("="):
                st.info("Detected MRK (text MARC) format")

                lines = content.decode("utf-8", errors="ignore").splitlines()

                for line in lines:
                    if not line.startswith("="):
                        continue

                    tag = line[1:4]

                    for sel in selected_fields:
                        if "$" in sel:
                            sel_tag, code = sel.split("$")
                        else:
                            sel_tag, code = sel, None

                        if tag != sel_tag:
                            continue

                        if code:
                            pattern = rf"\${code}([^\$]+)"
                            matches = re.findall(pattern, line)

                            for m in matches:
                                val = m.strip()
                                if normalize_option:
                                    val = normalize(val)
                                counters[sel][val] += 1
                        else:
                            val = line[6:].strip()
                            if normalize_option:
                                val = normalize(val)
                            counters[sel][val] += 1

            # ==================================================
            # 🟡 BINARY MARC
            # ==================================================
            else:
                st.info("Detected binary MARC format")

                reader = MARCReader(content)

                for record in reader:
                    if record is None:
                        continue

                    for sel in selected_fields:
                        if "$" in sel:
                            tag, code = sel.split("$")
                        else:
                            tag, code = sel, None

                        for field in record.get_fields(tag):
                            sf_list = getattr(field, 'subfields', [])

                            if sf_list:
                                for i in range(0, len(sf_list)-1, 2):
                                    sf_code = str(sf_list[i]).lower()
                                    sf_value = str(sf_list[i+1]).strip()

                                    if code and sf_code == code.lower():
                                        val = sf_value
                                        if normalize_option:
                                            val = normalize(val)
                                        counters[sel][val] += 1
                            else:
                                raw = field.format_field()

                                if code:
                                    pattern = rf"\${code}([^\$]+)"
                                    matches = re.findall(pattern, raw)

                                    for m in matches:
                                        val = m.strip()
                                        if normalize_option:
                                            val = normalize(val)
                                        counters[sel][val] += 1
                                else:
                                    val = raw.strip()
                                    if normalize_option:
                                        val = normalize(val)
                                    counters[sel][val] += 1

            # ==================================================
            # 🔵 XML
            # ==================================================
            if uploaded_file.name.endswith(".xml"):
                st.info("Detected MARCXML format")

                uploaded_file.seek(0)
                records = parse_xml_to_array(uploaded_file)

                for record in records:
                    if record is None:
                        continue

                    for sel in selected_fields:
                        if "$" in sel:
                            tag, code = sel.split("$")
                        else:
                            tag, code = sel, None

                        for field in record.get_fields(tag):
                            sf_list = getattr(field, 'subfields', [])

                            for i in range(0, len(sf_list)-1, 2):
                                sf_code = str(sf_list[i]).lower()
                                sf_value = str(sf_list[i+1]).strip()

                                if code and sf_code == code.lower():
                                    val = sf_value
                                    if normalize_option:
                                        val = normalize(val)
                                    counters[sel][val] += 1

            # ==================================================
            # RESULTS
            # ==================================================
            all_rows = []

            for sel, counter in counters.items():
                if not counter:
                    st.warning(f"No values found for {sel}")

                for val, cnt in counter.items():
                    all_rows.append({
                        "Field-Subfield": sel,
                        "Value": val,
                        "Count": cnt
                    })

                # 📊 Chart
                if counter:
                    st.subheader(f"Top values for {sel}")

                    top_items = counter.most_common(10)
                    labels = [x[0] for x in top_items]
                    values = [x[1] for x in top_items]

                    fig, ax = plt.subplots()
                    ax.bar(labels, values)
                    plt.xticks(rotation=45, ha="right")
                    st.pyplot(fig)

                # 📁 Separate CSV
                if separate_csv and counter:
                    df_sep = pd.DataFrame(
                        [{"Value": v, "Count": c} for v, c in counter.items()]
                    )

                    st.download_button(
                        label=f"Download CSV for {sel}",
                        data=df_sep.to_csv(index=False).encode("utf-8"),
                        file_name=f"{sel.replace('$','_')}.csv",
                        mime="text/csv"
                    )

            # Combined CSV
            if all_rows:
                df = pd.DataFrame(all_rows)

                st.subheader("Preview")
                st.dataframe(df.head(20))

                st.download_button(
                    label="Download Combined CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="marc_counts_all.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No values found.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
