import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

st.set_page_config(page_title="Avdel India - Part Lookup", layout="wide")

# Avdel India Corporate Styling
st.markdown("""
    <style>
    :root {
        --avdel-blue: #3182CE;
        --avdel-blue-hover: #2B6CB0;
        --avdel-navy: #0F2942;
        --avdel-bg: #F8FAFC;
        --avdel-card: #FFFFFF;
        --avdel-text: #1E293B;
    }
    
    .stApp {
        background-color: var(--avdel-bg);
        color: var(--avdel-text);
    }
    
    h1 {
        color: var(--avdel-navy) !important;
        font-weight: 700;
        border-bottom: 3px solid var(--avdel-blue);
        padding-bottom: 8px;
    }
    
    /* Input box label readability fix */
    label, p, span {
        color: #1E293B !important;
    }
    
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] h2 {
        color: #FFFFFF !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: var(--avdel-navy) !important;
    }
    
    div[data-baseweb="slider"] div {
        background-color: var(--avdel-blue) !important;
    }
    
    /* Expander styling clean-up */
    .streamlit-expanderHeader {
        background-color: var(--avdel-navy) !important;
        color: #FFFFFF !important;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .streamlit-expanderHeader p, .streamlit-expanderHeader span, .streamlit-expanderHeader div {
        color: #FFFFFF !important;
    }
    
    .stButton>button, .stLinkButton>a {
        background-color: var(--avdel-blue) !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    .stButton>button:hover, .stLinkButton>a:hover {
        background-color: var(--avdel-blue-hover) !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Title without airplane emoji
st.title("Avdel (India) Pvt. Ltd. — Part Search & Equivalents")
st.markdown("Search aerospace part numbers with typo tolerance to retrieve specs, equivalents, and datasheets.")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQciyZmZLWUmLBF6nKgVqDlpjkqRGh6N_1HlmiZRtrgsRr_nVJLoUJiAzsYetJkcHsBXIVbUtgfiTGq/pub?output=csv"

@st.cache_data(ttl=10)
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
            with st.expander(f"📌 **{matched_pn}** (Match Score: {int(score)}%)", expanded=True):
                col1, col2 = st.columns(2)
                
                # Primary Manufacturer
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### {mfg1} (Primary)")
                    st.write(f"**Part Number:** `{matched_pn}`")
                    st.write(f"**Description:** {row.get('Description', 'N/A')}")
                    st.write(f"**Standard:** {row.get('Standard', 'N/A')}")
                    
                    allfast_cols = [c for c in df.columns if "allfast" in c.lower() and "link" in c.lower()]
                    url1 = str(row[allfast_cols[0]]).strip() if allfast_cols else ""
                    
                    if url1.startswith("http"):
                        st.link_button("📄 Open Primary Datasheet", url1)
                    else:
                        st.write("📄 **Primary Datasheet:** Link Not Available")

                # Alternate Manufacturer & Position-Based Pairing
                with col2:
                    mfg2 = row.get('Manufacturer.1', 'Alternate Manufacturer')
                    st.markdown(f"### {mfg2} (Equivalents)")
                    st.write(f"**Alt. Description:** {row.get('Description.1', 'N/A')}")
                    
                    st.markdown("---")
                    st.markdown("#### 🔗 All Alternate Part Numbers & Standards")
                    
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
                    
                    cherry_cols = [c for c in df.columns if "cherry" in c.lower() and "link" in c.lower()]
                    url2 = str(row[cherry_cols[0]]).strip() if cherry_cols else ""
                    
                    if url2.startswith("http"):
                        st.link_button("📄 Open Alternate Datasheet", url2)
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning("No matching parts found. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
