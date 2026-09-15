import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz
from urllib.parse import quote

st.set_page_config(page_title="Avdel India - Part Lookup", layout="wide")

st.title("Avdel (India) Pvt. Ltd. — Part Search & Equivalents")
st.markdown("Search aerospace part numbers with typo tolerance to retrieve specs, equivalents, and datasheets.")

# Paste your actual folder URL prefix here:
SHAREPOINT_BASE_URL = "https://avdelaero-my.sharepoint.com/:b:/g/personal/YOUR_PATH_HERE/"

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQciyZmZLWUmLBF6nKgVqDlpjkqRGh6N_1HlmiZRtrgsRr_nVJLoUJiAzsYetJkcHsBXIVbUtgfiTGq/pub?output=csv"

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        return df.fillna("")
    except Exception as e:
        st.error(f"Error loading database sheet: {e}")
        return pd.DataFrame()

df = load_data()

st.sidebar.header("Search Settings")
similarity_threshold = st.sidebar.slider("Match Sensitivity (%)", 50, 100, 50)
max_results = st.sidebar.number_input("Max Results", 1, 20, 5)

query = st.text_input("Enter Part Number (typo-tolerant search):", "").strip()

def make_clickable_url(val):
    val = str(val).strip()
    if not val or val == "-":
        return None
    if val.startswith("http"):
        return val
    # Append raw filename to base URL and encode spaces (%20)
    return SHAREPOINT_BASE_URL + quote(val)

if query and not df.empty:
    pn_cols = [c for c in df.columns if any(w in c.lower() for w in ["part no", "part number", "p/n"])]
    target_col = pn_cols[0] if pn_cols else df.columns[1]
    
    part_numbers = df[target_col].astype(str).tolist()
    matches = process.extract(query, part_numbers, scorer=fuzz.WRatio, limit=max_results)
    filtered = [m for m in matches if m[1] >= similarity_threshold]
    
    if filtered:
        st.subheader(f"Results for '{query}':")
        for matched_pn, score, index in filtered:
            row = df.iloc[index]
            
            ds_cols = [c for c in df.columns if any(k in c.lower() for k in ["sheet", "link"])]
            
            primary_val = ""
            alt_val = ""
            
            for c in ds_cols:
                val = str(row[c]).strip()
                if val and val != "-":
                    if any(k in c.lower() for k in ["alt", "cherry", "1"]):
                        if not alt_val:
                            alt_val = val
                    else:
                        if not primary_val:
                            primary_val = val

            with st.expander(f"📌 {matched_pn} (Match Score: {int(score)}%)", expanded=True):
                col1, col2 = st.columns(2)
                
                # Primary Manufacturer
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### {mfg1} (Primary)")
                    st.write(f"**Part Number:** `{matched_pn}`")
                    st.write(f"**Description:** {row.get('Description', 'N/A')}")
                    st.write(f"**Standard:** {row.get('Standard', 'N/A')}")
                    
                    primary_url = make_clickable_url(primary_val)
                    if primary_url:
                        st.link_button("📄 Open Primary Datasheet", primary_url)
                    else:
                        st.write("📄 **Primary Datasheet:** Link Not Available")

                # Alternate Manufacturer & Equivalents
                with col2:
                    mfg2 = row.get('Manufacturer.1', 'Alternate Manufacturer')
                    st.markdown(f"### {mfg2} (Equivalents)")
                    st.write(f"**Alt. Description:** {row.get('Description.1', 'N/A')}")
                    
                    st.markdown("---")
                    st.markdown("**All Alternate Part Numbers & Standards:**")
                    
                    pairs_found = False
                    for i in range(len(df.columns)):
                        col_header = df.columns[i].lower()
                        if "alt." in col_header or "alt part" in col_header:
                            pn_val = str(row.iloc[i]).strip()
                            
                            std_val = "-"
                            if i + 1 < len(df.columns) and "standard" in df.columns[i + 1].lower():
                                std_val = str(row.iloc[i + 1]).strip()
                            
                            if pn_val and pn_val != "-":
                                st.write(f"• **Alt Part No:** `{pn_val}` | **Standard:** `{std_val if std_val else '-'}`")
                                pairs_found = True

                    if not pairs_found:
                        st.write("• *No alternate parts listed*")
                    
                    st.markdown("---")
                    
                    alt_url = make_clickable_url(alt_val)
                    if alt_url:
                        st.link_button("📄 Open Alternate Datasheet", alt_url)
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning("No matching parts found. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
