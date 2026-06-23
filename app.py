import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import json
import time

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

# State Selection
state = st.sidebar.selectbox(
    "Select State/Territory",
    ["All Australia", "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
)

# Cost Range Selection
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

# Under Management Toggle
under_management = st.sidebar.selectbox(
    "Management Structure",
    ["Any", "Strictly Run Under Management", "Owner Operated"]
)

# Business Type Keywords (Optional)
keywords = st.sidebar.text_input("Industry Keywords (e.g., Cafe, Gym, Manufacturing)", "")

# 4. Search Execution Logic
if st.sidebar.button("🚀 Search Live Listings", use_container_width=True):
    
    # Constructing a highly specific search prompt
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
    
    Find up to 5 actual business listings matching these details from popular Australian business brokers (e.g., seekbusiness,bsale, commercialrealestate etc.).
    
    Return ONLY a valid JSON array of objects with this exact schema:
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
            # We pass the google_search tool to allow live internet grounding
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json"
                )
            )
            
            if response and response.text:
                clean_text = response.text.strip()
                
                # Strip markdown blocks if returned
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                listings = json.loads(clean_text)
                
                if listings:
                    st.subheader(f"📊 Live Listings Found ({state} | {cost_range})")
                    df = pd.DataFrame(listings)
                    
                    # Display as a clean data table
                    st.dataframe(df, use_container_width=True)
                    
                    # Add export to excel button
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
                    st.warning("No listings matched your exact criteria. Try broadening your price range or state filters.")
                    
        except Exception as e:
            st.error(f"An error occurred while generating listings: {str(e)}")
else:
    st.info("💡 Adjust your filters in the sidebar and click **'Search Live Listings'** to begin your search.")
