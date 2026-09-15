import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz
import urllib.request
from html.parser import HTMLParser

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

PUBHTML_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQciyZmZLWUmLBF6nKgVqDlpjkqRGh6N_1HlmiZRtrgsRr_nVJLoUJiAzsYetJkcHsBXIVbUtgfiTGq/pubhtml?gid=0&single=true"

# Native HTML parser to extract tables & hidden <a> links
class GoogleSheetsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = ""
        self.current_href = None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ['td', 'th']:
            self.in_cell = True
            self.current_cell = ""
            self.current_href = None
        elif tag == 'a' and self.in_cell:
            for attr, val in attrs:
                if attr == 'href':
                    # Extract raw URL from Google wrapper redirect if present
                    if 'google.com/url?q=' in val:
                        val = val.split('google.com/url?q=')[1].split('&')[0]
                    self.current_href = val

    def handle_endtag(self, tag):
        if tag in ['td', 'th']:
            self.in_cell = False
            cell_val = self.current_href if self.current_href else self.current_cell.strip()
            self.current_row.append(cell_val)
        elif tag == 'tr':
            if self.current_row:
                self.rows.append(self.current_row)
                self.current_row = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

@st.cache_data(ttl=5)
def load_data():
    try:
        req = urllib.request.Request(PUBHTML_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html_content = urllib.request.urlopen(req).read().decode('utf-8')
        
        parser = GoogleSheetsHTMLParser()
        parser.feed(html_content)
        
        if parser.rows:
            # First row as header
            df = pd.DataFrame(parser.rows[1:], columns=parser.rows[0])
            df.columns = df.columns.str.strip()
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
        return pd.DataFrame()

df = load_data()

st.sidebar.header("Search Settings")
similarity_threshold = st.sidebar.slider("Match Sensitivity (%)", 30, 100, 50)
max_results = st.sidebar.number_input("Max Results", 1, 20, 5)

query = st.text_input("Enter Part Number:", placeholder="e.g., AF5141-3-01PR").strip()

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
            
            # Collect URLs from row
            found_urls = []
            for col_idx in range(len(df.columns)):
                cell_val = str(row.iloc[col_idx]).strip()
                if cell_val.startswith("http") and not cell_val.startswith("#"):
                    found_urls.append(cell_val)

            primary_url = found_urls[0] if len(found_urls) > 0 else ""
            alt_url = found_urls[1] if len(found_urls) > 1 else ""

            with st.expander(f"📌 **{matched_pn}** | Match Score: **{int(score)}%**", expanded=True):
                col1, col2 = st.columns(2)
                
                # Primary Panel
                with col1:
                    mfg1 = row.get('Manufacturer', 'Primary Manufacturer')
                    st.markdown(f"### {mfg1} (Primary)")
                    st.write(f"**Part Number:** `{matched_pn}`")
                    st.write(f"**Description:** {row.get('Description', 'N/A')}")
                    st.write(f"**Standard:** `{row.get('Standard', 'N/A')}`")
                    
                    if primary_url:
                        st.link_button("📄 Open Primary Datasheet", primary_url, use_container_width=True)
                    else:
                        st.write("📄 **Primary Datasheet:** Link Not Available")

                # Alternate Panel
                with col2:
                    mfg2 = row.get('Manufacturer.1', 'Alternate Manufacturer')
                    st.markdown(f"### {mfg2} (Equivalents)")
                    st.write(f"**Alt. Description:** {row.get('Description.1', 'N/A')}")
                    
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
                                st.write(f"• **Part:** `{pn_val}` | **Standard:** `{std_val if std_val else '-'}`")
                                pairs_found = True

                    if not pairs_found:
                        st.write("• *No alternate parts listed*")
                    
                    st.markdown("---")
                    
                    if alt_url:
                        st.link_button("📄 Open Alternate Datasheet", alt_url, use_container_width=True)
                    else:
                        st.write("📄 **Alt Datasheet:** Link Not Available")
    else:
        st.warning("No matching parts found. Try lowering the match sensitivity slider.")

st.markdown("---")
with st.expander("🔍 View Complete Database Table"):
    st.dataframe(df, use_container_width=True)
