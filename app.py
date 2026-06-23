import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import json
import re
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
        "Listing_URL": "The exact full website address or link to the listing found in search results"
      }}
    ]
    """

    # Retry configurations
    max_retries = 5
    wait_time = 45
    success = False
    
    # Placeholder for displaying live status messages to the user
    status_box = st.empty()
    countdown_box = st.empty()

    for attempt in range(1, max_retries + 1):
        status_box.info(f"⏳ Attempt {attempt} of {max_retries}: Contacting Google servers and scraping listings...")
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            )
            
            if response and response.text:
                raw_text = response.text.strip()
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                
                if json_match:
                    clean_json = json_match.group(0)
                    listings = json.loads(clean_json)
                    
                    if listings:
                        status_box.success("🎉 Search successful!")
                        st.subheader(f"📊 Live Listings Found ({state} | {cost_range})")
                        df = pd.DataFrame(listings)
                        
                        st.dataframe(
                            df, 
                            use_container_width=True,
                            column_config={
                                "Listing_URL": st.column_config.LinkColumn(
                                    "Source Link",
                                    help="Click to open the live business listing page",
                                    display_text="Open Listing 🔗"
                                )
                            }
                        )
                        
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
                        success = True
                        break  # Break out of the retry loop on success
                    else:
                        st.warning("No listings found. Try broadening your filters.")
                        success = True
                        break
                else:
                    st.error("The AI found listings but returned them in an unreadable format.")
                    with st.expander("See Raw Response"):
                        st.text(raw_text)
                    success = True
                    break
                    
        except Exception as e:
            error_msg = str(e)
            
            # Check specifically for the 503 error
            if "503" in error_msg or "UNAVAILABLE" in error_msg:
                if attempt < max_retries:
                    status_box.warning(f"⚠️ Google servers are busy (503 error). Initiating automatic cool-down...")
                    
                    # Visual live countdown timer
                    for remaining in range(wait_time, 0, -1):
                        countdown_box.error(f"⏱️ Servers overloaded. Retrying automatically in {remaining} seconds... Please leave this tab open.")
                        time.sleep(1)
                    
                    countdown_box.empty()  # Clear the countdown before the next attempt
                else:
                    status_box.error("❌ App stopped: Google servers remained unavailable after 5 attempts. Please try again later.")
            else:
                # For any other errors (like 400 or 429), stop immediately and show it
                status_box.error(f"An unexpected error occurred: {error_msg}")
                break

    if not success and "503" in error_msg:
        st.info("💡 Tip: Try changing your search keywords slightly or wait a minute before clicking Search again.")
        
else:
    st.info("💡 Adjust your filters in the sidebar and click **'Search Live Listings'** to begin your search.")
