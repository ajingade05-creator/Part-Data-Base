import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz
import re

st.set_page_config(page_title="Avdel India - Part Lookup", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Avdel (India) Pvt. Ltd. — Part Search & Equivalents")
st.caption("Search aerospace part numbers with typo tolerance to retrieve specs, equivalents, and datasheets.")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQciyZmZLWUmLBF6nKgVqDlpjkqRGh6N_1HlmiZRtrgsRr_nVJLoUJiAzsYetJkcHsBXIVbUtgfiTGq/pub?output=csv"

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        return df.fillna("")
    except Exception as e:
        st.error(f"Error loading database sheet: {e}")
        return pd.DataFrame()

df = load_data()

# Helper to extract clean base series prefix (e.g. 'AF5141' from 'AF5141-3-01PR')
def get_series_prefix(pn):
    pn = str(pn).strip()
    match = re.match(r'^([A-Za-z0-9]+)', pn)
    return match.group(1) if match else pn

# Helper to pull the first valid URL from a column or cell
def extract_url(val):
    val = str(val).strip()
    if val and val != "-" and not val.startswith("#"):
        urls = re.findall(r'https?://[^\s,"]+', val)
        if urls:
            return urls[0]
    return None

# Build a lookup map of series prefix -> valid fallback URL for Primary & Alt datasheets
PRIMARY_SERIES_MAP = {}
ALT_SERIES_MAP = {}

if not df.empty:
    pn_cols = [c for c in df.columns if any(w in c.lower() for w in ["part no", "part number", "p/n"])]
    target_col = pn_cols[0] if pn_cols else df.columns[1]

    # Dynamically locate datasheet columns
    primary_ds_col = None
    alt_ds_col = None

    for c in df.columns:
        c_lower = c.lower()
        if any(k in c_lower for k in ["sheet", "link", "url"]):
            if any(k in c_lower for k in ["cherry", "alt"]):
                alt_ds_col = c
            else:
                if not primary_ds_col:
                    primary_ds_col = c

    # Populate fallback maps across all rows
    for _, r in df.iterrows():
        prefix = get_series_prefix(r[target_col])
        
        if primary_ds_col:
            p_url = extract_url(r[primary_ds_col])
            if p_url and prefix not in PRIMARY_SERIES_MAP:
                PRIMARY_SERIES_MAP[prefix] = p_url

        if alt_ds_col:
            a_url = extract_url(r[alt_ds_col])
            if a_url and prefix not in ALT_SERIES_MAP:
                ALT_SERIES_MAP[prefix] = a_url

st.sidebar.header("Search Settings")
similarity_threshold = st.sidebar.slider("Match Sensitivity (%)", 30, 100, 75)
max_results = st.sidebar.number_input("Max Results", 1, 20, 5)

query = st.text_input("Enter Part Number:", placeholder="e.g., AF5141-3-01PR").strip()

if query and not df.empty:
    pn_cols = [c for c in df.columns if any(w in c.lower() for w in ["part no", "part number", "p/n"])]
    target_col = pn_cols[0] if pn_cols else df.columns[1]
    
    part_numbers = df[target_col].astype(str).tolist()
    
    raw_matches = process.extract(query, part_numbers, scorer=fuzz.WRatio, limit=50)
    filtered = [m for m in raw_matches if float(m[1]) >= float(similarity_threshold)][:int(max_results)]
    
    if filtered:
        st.subheader(f"Results for '{query}':")
        for matched_pn, score, index in filtered:
            row = df.iloc[index]
            prefix = get_series_prefix(matched_pn)
            
            # Primary URL resolution with fallback
            primary_val = row[primary_ds_col] if primary_ds_col else ""
            primary_url = extract_url(primary_val)
            if not primary_url:
                primary_url = PRIMARY_SERIES_MAP.get(prefix)

            # Alternate URL resolution with fallback
            alt_val = row[alt_ds_col] if alt_ds_col else ""
            alt_url = extract_url(alt_val)
            if not alt_url:
                alt_url = ALT_SERIES_MAP.get(prefix)

            with st.expander(f"📌 **{matched_pn}** | Match Score: **{int(score)}%**", expanded=True):
                col1, col2 = st.columns(2)
                
                # Primary Panel
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### {mfg1} (Primary)")
                    st.write(f"**Part Number:** `{matched_pn}`")
                    st.write(f"**Description:** {row.get('Description', 'N/A')}")
                    st.write(f"**Standard:** `{row.get('Standard', 'N/A')}`")
                    
                    st.markdown("---")
                    if primary_url:
                        st.link_button("📄 Open Primary Datasheet", primary_url, use_container_width=True)
                    else:
                        st.write("📄 **Primary Datasheet:** Link Not Available")

                # Alternate Panel
                with col2:
                    mfg2 = row.get('Manufacturer.1', 'Alternate Manufacturer')
                    st.markdown(f"### {mfg2} / MS (Equivalents)")
                    st.write(f"**Alt. Description:** {row.get('Description.1', 'N/A')}")
                    
                    st.markdown("---")
                    st.markdown("**All Alternate & MS/NASM Part Numbers:**")
                    
                    pairs_found = False
                    for i in range(len(df.columns)):
                        col_header = df.columns[i].lower()
                        if "alt." in col_header or "alt part" in col_header:
                            pn_val = str(row.iloc[i]).strip()
                            
                            std_val = "-"
                            if i + 1 < len(df.columns) and "standard" in df.columns[i + 1].lower():
                                std_val = str(row.iloc[i + 1]).strip()
                            
                            if pn_val and pn_val != "-" and not pn_val.startswith("http") and not pn_val.endswith(".pdf"):
                                st.write(f"• **Part No:** `{pn_val}` | **Standard:** `{std_val if std_val else '-'}`")
                                pairs_found = True

                    if not pairs_found:
                        st.write("• *No alternate parts listed*")
                    
                    st.markdown("---")
                    
                    if alt_url:
                        st.link_button("📄 Open Alternate Datasheet", alt_url, use_container_width=True)
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning(f"No matching parts found with a score of {similarity_threshold}% or higher. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
