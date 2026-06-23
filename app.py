import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import json
import re

# 1. Page Title and Styling
st.set_page_config(page_title="Aus Business Finder", layout="wide")
st.title("🇦🇺 Australian Businesses for Sale Finder")
st.write("Searches the live web using AI to find business listings matching your criteria.")

# 2. Key Configuration
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please add your 'GEMINI_API_KEY' to your Streamlit App Secrets.")
    st.stop()

# 3. Sidebar Filter Configuration
st.sidebar.header("🔍 Search Filters")

state = st.sidebar.selectbox(
    "Select State/Territory",
    ["All Australia", "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
)

cost_range = st.sidebar.selectbox(
    "Select Price Range",
    [
        "Any Price",
        "Under $100,000",
        "$100,000 - $250,000",
        "$250,000 - $500,000",
        "$500,000 - $1,000,000",
        "$1,000,000+"
    ]
)

under_management = st.sidebar.selectbox(
    "Management Structure",
    ["Any", "Strictly Run Under Management", "Owner Operated"]
)

keywords = st.sidebar.text_input("Industry Keywords (e.g., Cafe, Gym, Manufacturing)", "")

# 4. Search Execution Logic
if st.sidebar.button("🚀 Search Live Listings", use_container_width=True):
    
    management_clause = ""
    if under_management == "Strictly Run Under Management":
        management_clause = "The business must be explicitly advertised as 'run under management' or 'fully managed'."
    elif under_management == "Owner Operated":
        management_clause = "The business should be suitable for an owner-operator."

    prompt = f"""
    Search the internet for real, active businesses currently listed for sale in Australia.
    
    Criteria:
    - Location: {state}
    - Price Range: {cost_range}
    - Management: {management_clause}
    - Keywords/Industry: {keywords if keywords else 'Any'}
    
    Find up to 5 actual business listings matching these details from popular Australian business brokers (e.g., seekbusiness, bsale, commercialrealestate etc.).
    
    You must format your entire response as a valid JSON array of objects. Do not include any conversational text before or after the JSON block. Use this exact schema:
    [
      {{
        "Business_Name": "Headline title of the listing",
        "Location": "Suburb and State",
        "Price": "Asking price or price guide",
        "Revenue_Profit": "Stated weekly/annual turnover or profit if available (else 'Not stated')",
        "Management_Type": "Under Management or Owner Operated status",
        "Summary": "1-2 sentence description of what the business does",
        "Source_Platform": "The name of the site hosting the listing"
      }}
    ]
    """

    with st.spinner("Searching the web and extracting real-time listings... Please wait."):
        try:
            # Removed response_mime_type="application/json" to prevent the 400 error
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            )
            
            if response and response.text:
                raw_text = response.text.strip()
                
                # Use regex to safely extract the JSON array even if markdown syntax is wrapped around it
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                
                if json_match:
                    clean_json = json_match.group(0)
                    listings = json.loads(clean_json)
                    
                    if listings:
                        st.subheader(f"📊 Live Listings Found ({state} | {cost_range})")
                        df = pd.DataFrame(listings)
                        
                        st.dataframe(df, use_container_width=True)
                        
                        import io
                        towrite = io.BytesIO()
                        df.to_excel(towrite, index=False, header=True)
                        towrite.seek(0)
                        st.download_button(
                            label="📥 Download Listings Report (.xlsx)",
                            data=towrite,
                            file_name="aus_business_listings.xlsx",
                            use_container_width=True
                        )
                    else:
                        st.warning("No listings found. Try broadening your filters.")
                else:
                    st.error("The AI found listings but returned them in an unreadable format. Please click Search again.")
                    with st.expander("See Raw Response"):
                        st.text(raw_text)
                    
        except Exception as e:
            st.error(f"An error occurred while generating listings: {str(e)}")
else:
    st.info("💡 Adjust your filters in the sidebar and click **'Search Live Listings'** to begin your search.")
