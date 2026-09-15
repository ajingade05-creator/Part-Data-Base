import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

st.set_page_config(page_title="Avdel India - Part Lookup", layout="wide")

# Custom UI Styling for High Readability & Clean Aesthetics
st.markdown("""
    <style>
    /* Card Container */
    .result-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    /* Section Divider Line */
    hr {
        margin: 15px 0;
        border-color: #334155;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Avdel (India) Pvt. Ltd. — Part Search & Equivalents")
st.caption("🔍 Search aerospace part numbers with typo-tolerance to view specifications, alternate equivalents, and direct datasheets.")

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

# Sidebar Controls
st.sidebar.header("⚙️ Search Controls")
similarity_threshold = st.sidebar.slider(
    "Match Sensitivity (%)", 
    min_value=30, 
    max_value=100, 
    value=50,
    help="Lower values find broader/typo-tolerant matches. Higher values enforce stricter part number matches."
)
max_results = st.sidebar.number_input(
    "Max Results Displayed", 
    min_value=1, 
    max_value=20, 
    value=5
)

# Search Bar Area
query = st.text_input(
    "Enter Part Number:", 
    placeholder="e.g., AF6043-4F-04 or AF5141",
    help="Type any primary or alternate part number. Typos will automatically be corrected."
).strip()

if not query:
    st.info("💡 **Quick Tip:** Enter a part number above to instantly cross-reference primary specs, alternate part numbers, and download manufacturer datasheets.")

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
            
            # Extract links dynamically
            found_urls = []
            for col_idx in range(len(df.columns)):
                cell_val = str(row.iloc[col_idx]).strip()
                if cell_val.lower().startswith("http") and not cell_val.startswith("#"):
                    found_urls.append(cell_val)

            primary_url = found_urls[0] if len(found_urls) > 0 else ""
            alt_url = found_urls[1] if len(found_urls) > 1 else ""

            # Card Display
            with st.expander(f"📌 **{matched_pn}**  |  Match Score: **{int(score)}%**", expanded=True):
                col1, col2 = st.columns(2)
                
                # Primary Manufacturer Panel
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### 🏷️ {mfg1} (Primary)")
                    st.markdown(f"**Part Number:** `{matched_pn}`")
                    st.markdown(f"**Description:** {row.get('Description', 'N/A')}")
                    st.markdown(f"**Standard:** `{row.get('Standard', 'N/A')}`")
                    
                    st.markdown("---")
                    if primary_url:
                        st.link_button("📄 Open Primary Datasheet", primary_url, use_container_width=True)
                    else:
                        st.caption("📄 *Primary Datasheet link not available in sheet*")

                # Alternate Manufacturer Panel
                with col2:
                    mfg2 = row.get('Manufacturer.1', 'Alternate Manufacturer')
                    st.markdown(f"### 🔄 {mfg2} (Equivalents)")
                    st.markdown(f"**Alt. Description:** {row.get('Description.1', 'N/A')}")
                    
                    st.markdown("---")
                    st.markdown("**Equivalent Part Numbers:**")
                    
                    pairs_found = False
                    for i in range(len(df.columns)):
                        col_header = df.columns[i].lower()
                        if "alt." in col_header or "alt part" in col_header:
                            pn_val = str(row.iloc[i]).strip()
                            
                            std_val = "-"
                            if i + 1 < len(df.columns) and "standard" in df.columns[i + 1].lower():
                                std_val = str(row.iloc[i + 1]).strip()
                            
                            if pn_val and pn_val != "-" and not pn_val.startswith("http"):
                                st.markdown(f"• **Part:** `{pn_val}` &nbsp;|&nbsp; **Standard:** `{std_val if std_val else '-'}`")
                                pairs_found = True

                    if not pairs_found:
                        st.caption("*No alternate parts listed*")
                    
                    st.markdown("---")
                    if alt_url:
                        st.link_button("📄 Open Alternate Datasheet", alt_url, use_container_width=True)
                    else:
                        st.caption("📄 *Alternate Datasheet link not available in sheet*")
    else:
        st.warning("⚠️ No matching parts found. Try lowering the **Match Sensitivity** slider in the sidebar.")

st.markdown("---")
with st.expander("📊 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
