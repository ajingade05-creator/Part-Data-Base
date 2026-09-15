import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
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

def extract_url(val):
    val = str(val).strip()
    if val and val != "-" and not val.startswith("#"):
        urls = re.findall(r'https?://[^\s,"]+', val)
        if urls:
            return urls[0]
    return None

def get_base_prefix(pn):
    pn = str(pn).strip().upper()
    match = re.match(r'^([A-Z0-9]{4,6})', pn)
    return match.group(1) if match else pn[:6]

PRIMARY_SERIES_MAP = {}
ALT_SERIES_MAP = {}

if not df.empty:
    pn_cols = [c for c in df.columns if any(w in c.lower() for w in ["part no", "part number", "p/n"])]
    primary_pn_col = pn_cols[0] if pn_cols else df.columns[1]

    primary_ds_cols = [c for c in df.columns if any(k in c.lower() for k in ["sheet", "link", "url"]) and not any(k in c.lower() for k in ["cherry", "alt"])]
    alt_ds_cols = [c for c in df.columns if any(k in c.lower() for k in ["sheet", "link", "url"]) and any(k in c.lower() for k in ["cherry", "alt"])]

    for _, r in df.iterrows():
        prefix = get_base_prefix(r[primary_pn_col])
        if prefix not in PRIMARY_SERIES_MAP:
            for col in primary_ds_cols:
                u = extract_url(r[col])
                if u:
                    PRIMARY_SERIES_MAP[prefix] = u
                    break
        if prefix not in ALT_SERIES_MAP:
            for col in alt_ds_cols:
                u = extract_url(r[col])
                if u:
                    ALT_SERIES_MAP[prefix] = u
                    break

st.sidebar.header("Search Settings")
similarity_threshold = st.sidebar.slider("Match Sensitivity (%)", 30, 100, 75)
max_results = st.sidebar.number_input("Max Results", 1, 20, 5)

query = st.text_input("Enter Part Number or Standard:", placeholder="e.g., AF5141, CCR264, or NASM20605").strip()

if query and not df.empty:
    search_cols = [c for c in df.columns if any(k in c.lower() for k in ["part", "p/n", "standard"])]
    search_records = {}
    query_clean = query.lower()

    # Smart Search: Prioritize Exact Substrings, fallback to Fuzzy Typos
    for col in search_cols:
        col_values = df[col].astype(str).tolist()
        
        for row_idx, val in enumerate(col_values):
            val_str = val.strip()
            if not val_str or val_str == "-":
                continue
            
            val_clean = val_str.lower()
            
            # 1. Exact Substring Match (e.g. searching 'ccr264' hits 'CCR264-3-01PR' automatically)
            if query_clean in val_clean:
                score = 100.0
            # 2. Fuzzy Match Backup (for typos)
            else:
                score = fuzz.WRatio(query_clean, val_clean)
            
            if score >= float(similarity_threshold):
                if row_idx not in search_records or score > search_records[row_idx]['score']:
                    search_records[row_idx] = {
                        'score': score, 
                        'matched_term': val_str,
                        'matched_col': col
                    }
    
    filtered = sorted(search_records.items(), key=lambda x: x[1]['score'], reverse=True)[:int(max_results)]
    
    if filtered:
        st.subheader(f"Results for '{query}':")
        for row_idx, match_data in filtered:
            row = df.iloc[row_idx]
            score = match_data['score']
            matched_term = match_data['matched_term']
            
            primary_pn = str(row[primary_pn_col]).strip()
            prefix = get_base_prefix(primary_pn)
            
            # --- Link Resolution ---
            primary_text = ""
            primary_url = None
            for col in primary_ds_cols:
                val = str(row[col]).strip()
                u = extract_url(val)
                if u and not primary_url:
                    primary_url = u
                elif val and val != "-" and not val.startswith("http") and not val.startswith("#") and not primary_text:
                    primary_text = val
            
            if not primary_url:
                primary_url = PRIMARY_SERIES_MAP.get(prefix)

            alt_text = ""
            alt_url = None
            for col in alt_ds_cols:
                val = str(row[col]).strip()
                u = extract_url(val)
                if u and not alt_url:
                    alt_url = u
                elif val and val != "-" and not val.startswith("http") and not val.startswith("#") and not alt_text:
                    alt_text = val
            
            if not alt_url:
                alt_url = ALT_SERIES_MAP.get(prefix)

            expander_title = f"📌 **{primary_pn}** "
            if matched_term.upper() != primary_pn.upper():
                expander_title += f"*(Matched via: {matched_term})* "
            expander_title += f"| Match Score: **{int(score)}%**"

            with st.expander(expander_title, expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### {mfg1} (Primary)")
                    st.write(f"**Part Number:** `{primary_pn}`")
                    st.write(f"**Description:** {row.get('Description', 'N/A')}")
                    st.write(f"**Standard:** `{row.get('Standard', 'N/A')}`")
                    
                    st.markdown("---")
                    if primary_url:
                        st.link_button("📄 Open Primary Datasheet", primary_url, use_container_width=True)
                    elif primary_text:
                        st.write(f"📄 **Primary Datasheet:** `{primary_text}` *(Link unavailable in Database)*")
                    else:
                        st.write("📄 **Primary Datasheet:** Link Not Available")

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
                    elif alt_text:
                        st.write(f"📄 **Alt Datasheet:** `{alt_text}` *(Link unavailable in Database)*")
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning(f"No matching parts found with a score of {similarity_threshold}% or higher. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
