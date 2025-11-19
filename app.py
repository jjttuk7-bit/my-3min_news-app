import streamlit as st
import feedparser
import google.generativeai as genai
import os
from datetime import datetime
from dateutil import parser
import time

# --- Page Config ---
st.set_page_config(
    page_title="Today's 3-Minute News",
    page_icon="📰",
    layout="centered"
)

# --- Styles ---
st.markdown("""
<style>
    .news-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #ff4b4b;
    }
    .news-title {
        font-size: 18px;
        font-weight: bold;
        color: #31333F;
        margin-bottom: 10px;
    }
    .news-meta {
        font-size: 12px;
        color: #808495;
        margin-bottom: 15px;
    }
    .summary-box {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        border: 1px solid #e0e0e0;
    }
    .summary-title {
        font-weight: bold;
        color: #ff4b4b;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .error-box {
        background-color: #ffebee;
        color: #c62828;
        padding: 10px;
        border-radius: 5px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar & Settings ---
with st.sidebar:
    st.header("📰 Settings")
    
    # API Key Management
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if api_key:
            st.success("API Key entered!")
    else:
        st.success("✅ API Key loaded from Secrets")

    st.markdown("---")
    st.markdown("### About")
    st.markdown("Made with ❤️ using Streamlit & Gemini")

# --- Functions ---

@st.cache_data(ttl=3600)  # Cache news for 1 hour
def fetch_news(category):
    """Fetches news from Google News RSS based on category."""
    rss_urls = {
        "Politics": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0VnSm5iV1ZmY21WaWJ5Z3lDZ29FVEJpQ1N3?hl=ko&gl=KR&ceid=KR%3Ako",
        "Economy": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0VnSm5iV1ZmY21WaWJ5Z3lDZ29FVEJpQ1N3?hl=ko&gl=KR&ceid=KR%3Ako", # Placeholder, adjusted below if needed
        "Society": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0VnSm5iV1ZmY21WaWJ5Z3lDZ29FVEJpQ1N3?hl=ko&gl=KR&ceid=KR%3Ako", # Placeholder
        "International": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0VnSm5iV1ZmY21WaWJ5Z3lDZ29FVEJpQ1N3?hl=ko&gl=KR&ceid=KR%3Ako", # Placeholder
        "IT/Science": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0VnSm5iV1ZmY21WaWJ5Z3lDZ29FVEJpQ1N3?hl=ko&gl=KR&ceid=KR%3Ako", # Placeholder
    }
    
    # Correct URLs for specific categories (Google News KR)
    if category == "Politics":
        url = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERJU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR%3Ako"
    elif category == "Economy":
        url = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR2PoWjJJU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR%3Ako"
    elif category == "Society":
        url = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRmh6Y21JU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR%3Ako"
    elif category == "International":
        url = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR5Z0WjJJU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR%3Ako"
    elif category == "IT/Science":
        url = "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR1J4Y1hJU0FtdHZLQUFQAQ?hl=ko&gl=KR&ceid=KR%3Ako"
    else:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"

    feed = feedparser.parse(url)
    articles = []
    
    for entry in feed.entries[:5]:  # Get top 5
        try:
            published = parser.parse(entry.published).strftime("%Y-%m-%d %H:%M")
        except:
            published = "Unknown Date"
            
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": published,
            "summary": entry.description if 'description' in entry else ""
        })
    return articles

@st.cache_data(ttl=86400, show_spinner=False) # Cache summaries for 24 hours!
def generate_summary(text, _model):
    """Generates a 3-line summary using Gemini."""
    try:
        prompt = f"""
        You are a helpful news assistant. 
        Summarize the following news article title and snippet into exactly 3 bullet points in Korean.
        Keep it concise and easy to understand.
        
        News: {text}
        """
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ API Quota Exceeded. Please try again later."
        return f"⚠️ Error: {str(e)}"

# --- Main UI ---

st.title("Today's 3-Minute News ☕")

categories = ["Politics", "Economy", "Society", "International", "IT/Science"]
selected_category = st.radio("Select Category", categories, horizontal=True)

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    with st.spinner(f"Fetching {selected_category} news..."):
        articles = fetch_news(selected_category)
        st.success(f"✅ Loaded top 5 articles for {selected_category}")

    for article in articles:
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title"><a href="{article['link']}" target="_blank" style="text-decoration:none; color:#31333F;">{article['title']}</a></div>
            <div class="news-meta">📅 {article['published']}</div>
        """, unsafe_allow_html=True)
        
        # Generate Summary
        content_to_summarize = f"{article['title']} - {article['summary']}"
        
        # Use a placeholder to show loading state for each summary individually
        summary_placeholder = st.empty()
        
        with summary_placeholder.container():
             # Check if we have a cached result implicitly via the function call
             # We can't easily check cache existence without calling it, but st.cache_data handles it.
             # To make the UI smoother, we just call it.
             
             summary = generate_summary(content_to_summarize, model)
             
             if "Quota Exceeded" in summary:
                 st.markdown(f"""
                    <div class="error-box">
                        {summary}<br>
                        <small>Don't worry! Since we are caching results, try refreshing in a minute.</small>
                    </div>
                 """, unsafe_allow_html=True)
             else:
                 st.markdown(f"""
                    <div class="summary-box">
                        <div class="summary-title">⚡ 3-Line Summary</div>
                        {summary}
                    </div>
                 """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to generate summaries.")
