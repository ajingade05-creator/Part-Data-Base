import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz
import urllib.request
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
PUBHTML_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQciyZmZLWUmLBF6nKgVqDlpjkqRGh6N_1HlmiZRtrgsRr_nVJLoUJiAzsYetJkcHsBXIVbUtgfiTGq/pubhtml?gid=0&single=true"

@st.cache_data(ttl=2)
def load_data():
    try:
        # Load structured data via CSV
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        df = df.fillna("")

        # Extract underlying hyperlinks from HTML stream
        req = urllib.request.Request(PUBHTML_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html_str = urllib.request.urlopen(req).read().decode('utf-8')
        
        # Match all href targets embedded in published sheet
        raw_hrefs = re.findall(r'href=["\'](.*?)["\']', html_str)
        cleaned_urls = []
        for h in raw_hrefs:
            if 'google.com/url?q=' in h:
                h = h.split('google.com/url?q=')[1].split('&')[0]
            if h.startswith("http") and "pubhtml" not in h and "google" not in h:
                cleaned_urls.append(h)
                
        return df, cleaned_urls
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return pd.DataFrame(), []

df, extracted_urls = load_data()

st.sidebar.header("Search Settings")
similarity_threshold = st.sidebar.slider("Match Sensitivity (%)", 30, 100, 75)
max_results = st.sidebar.number_input("Max Results", 1, 20, 5)

query = st.text_input("Enter Part Number:", placeholder="e.g., AF5141-3-12PR").strip()

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
            
            primary_val = ""
            alt_val = ""
            
            for col in df.columns:
                c_lower = col.lower()
                val = str(row[col]).strip()
                if val and val != "-" and not val.startswith("#"):
                    if any(k in c_lower for k in ["sheet", "link", "url"]):
                        if any(k in c_lower for k in ["cherry", "alt"]):
                            alt_val = val
                        else:
                            if not primary_val:
                                primary_val = val

            def resolve_url(val):
                if not val or val == "-":
                    return None
                urls = re.findall(r'https?://[^\s,"]+', val)
                if urls:
                    return urls[0]
                # Match filename string to scraped HTML URLs
                for u in extracted_urls:
                    if val.replace(" ", "").lower() in u.lower():
                        return u
                return None

            primary_url = resolve_url(primary_val)
            alt_url = resolve_url(alt_val)

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
                    elif primary_val:
                        st.write(f"📄 **Primary Datasheet:** `{primary_val}` *(Paste full https:// link in sheet to enable button)*")
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
                    elif alt_val:
                        st.write(f"📄 **Alt Datasheet:** `{alt_val}` *(Paste full https:// link in sheet to enable button)*")
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning(f"No matching parts found with a score of {similarity_threshold}% or higher. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
