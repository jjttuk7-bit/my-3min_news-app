import streamlit as st
import feedparser
import google.generativeai as genai
import time
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Today's 3-Minute News",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Card Styling
st.markdown("""
<style>
    .news-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
        transition: transform 0.2s;
    }
    .news-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .news-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1f1f1f;
        margin-bottom: 10px;
        text-decoration: none;
    }
    .news-title:hover {
        text-decoration: underline;
        color: #0066cc;
    }
    .news-meta {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 15px;
    }
    .news-summary {
        font-size: 1rem;
        color: #333;
        line-height: 1.6;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
    }
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .news-card {
            background-color: #262730;
            border-color: #444;
        }
        .news-title {
            color: #ffffff;
        }
        .news-title:hover {
            color: #66b3ff;
        }
        .news-meta {
            color: #aaa;
        }
        .news-summary {
            background-color: #1e1e1e;
            color: #ddd;
            border-left-color: #66b3ff;
        }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📰 Settings")
    
    # Check for API Key in Secrets
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        # Robust cleaning: remove spaces and accidental quotes
        api_key = api_key.strip().strip('"').strip("'")
        st.success("✅ API Key loaded from Secrets")
    else:
        api_key = st.text_input("Gemini API Key", value="AIzaSyBQzU6DZYDEP3QEWco-F_bq5dV8H5lXtko", type="password", help="Get your key from Google AI Studio")
    
    st.markdown("---")
    
    categories = {
        "Politics": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
        "Economy": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
        "Society": "https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko",
        "Culture": "https://news.google.com/rss/search?q=Culture&hl=ko&gl=KR&ceid=KR:ko", # Google News doesn't have a direct 'Culture' topic in KR edition usually, using search or closest equivalent. Let's try search or entertainment if culture is not distinct.
        # Actually, let's use Entertainment as a proxy for Culture/Arts if specific Culture feed is tricky, or just search '문화'.
        # Let's stick to the requested list.
        "Sports": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
        "International": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"
    }
    
    # Adjusting Culture URL to be more specific if needed, but search query is a safe bet for now.
    categories["Culture"] = "https://news.google.com/rss/search?q=%EB%AC%B8%ED%99%94&hl=ko&gl=KR&ceid=KR:ko"

    selected_category = st.radio("Select Category", list(categories.keys()))
    
    st.markdown("---")
    st.markdown("Made with ❤️ using Streamlit & Gemini")

# Helper Functions
import urllib.request
import ssl

def fetch_news(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        # Create unverified SSL context
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=context) as response:
            xml_data = response.read()
            feed = feedparser.parse(xml_data)
            return feed.entries[:5]
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []

def summarize_news(text, api_key):
    if not api_key:
        return "Please enter your Gemini API Key in the sidebar to see the summary."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # Refined prompt for cleaner output
        prompt = f"Summarize the following news article into exactly 3 bullet points in Korean. Output ONLY the bullet points. Do not add any introductory or concluding text:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Main Content
st.title(f"Today's 3-Minute News: {selected_category}")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to enable AI summaries.")

# Fetch and Display News
if selected_category:
    with st.spinner(f"Fetching latest {selected_category} news..."):
        news_items = fetch_news(categories[selected_category])
        
        if not news_items:
            st.error(f"뉴스 기사를 가져오지 못했습니다. (URL: {categories[selected_category]})")
            st.info("인터넷 연결을 확인하거나, 잠시 후 다시 시도해주세요.")
        else:
            st.success(f"✅ {len(news_items)}개의 최신 기사를 가져왔습니다!")

        for item in news_items:
            # Layout
            col1, col2 = st.columns([1, 0.05]) # Spacer
            
            with col1:
                # Open Card Container
                st.markdown(f"""
                <div class="news-card">
                    <a href="{item.link}" target="_blank" class="news-title">{item.title}</a>
                    <div class="news-meta">Published: {item.get('published', 'N/A')}</div>
                """, unsafe_allow_html=True)
                
                # Summary Section (Rendered as native Markdown inside the HTML container context is tricky, 
                # so we close the top part, render markdown, then close the card. 
                # But Streamlit adds divs around markdown. 
                # Better approach: Keep it inside one block but use HTML for bullets if needed, 
                # OR just use the previous approach but fix indentation/string format.)
                
                # Let's stick to the previous approach but clean up the prompt to avoid text that looks like markdown/html interference
                # and remove indentation from the f-string to be safe.
                
                if api_key:
                    content_to_summarize = f"{item.title}\n{item.get('description', '')}"
                    summary = summarize_news(content_to_summarize, api_key)
                    
                    # Using a separate div for summary to ensure isolation
                    st.markdown(f"""
                    <div class="news-summary">
                        <strong>⚡ 3-Line Summary:</strong><br>
                        {summary.replace(chr(10), '<br>')} 
                    </div>
                    """, unsafe_allow_html=True) 
                    # Note: Replacing newlines with <br> ensures it renders as HTML text, preventing Markdown parsing issues inside HTML.
                else:
                     st.markdown("""
                    <div class="news-summary" style="color: #999;">
                        <em>Enter API Key to see summary...</em>
                    </div>
                    """, unsafe_allow_html=True)

                # Close Card Container
                st.markdown("</div>", unsafe_allow_html=True)
