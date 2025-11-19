import streamlit as st
import feedparser
import google.generativeai as genai
import os
from datetime import datetime
from dateutil import parser
import time
import requests

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
    st.header("📰 설정")
    
    # API Key Management
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = st.text_input("Gemini API 키를 입력하세요", type="password")
        if api_key:
            st.success("API 키가 입력되었습니다!")
    else:
        st.success("✅ API 키가 로드되었습니다")

    st.markdown("---")
    st.markdown("### 정보")
    st.markdown("Made with ❤️ using Streamlit & Gemini")

# --- Functions ---

@st.cache_data(ttl=3600)  # 뉴스는 1시간 동안 저장(캐싱)
def fetch_news(category):
    """카테고리에 맞는 구글 뉴스 RSS를 가져옵니다."""
    # 카테고리별 정확한 URL 설정 (Google News KR Standard URLs)
    if category == "Politics":
        url = "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko"
    elif category == "Economy":
        url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    elif category == "Society":
        url = "https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko"
    elif category == "International":
        url = "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"
    elif category == "IT/Science":
        url = "https://news.google.com/rss/headlines/section/topic/SCIENCE_AND_TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko"
    else:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"

    # 구글의 차단을 피하기 위해 '사람인 척' 하는 헤더 추가
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        st.error(f"뉴스 가져오기 실패: {e}")
        return []

    articles = []
    
    if not feed.entries:
        st.warning("뉴스를 찾을 수 없습니다. 구글이 요청을 차단했을 수 있습니다.")
        return []

    for entry in feed.entries[:5]:  # 상위 5개 기사
        try:
            published = parser.parse(entry.published).strftime("%Y-%m-%d %H:%M")
        except:
            published = "날짜 없음"
            
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": published,
            "summary": entry.description if 'description' in entry else ""
        })
    return articles

@st.cache_data(ttl=86400, show_spinner=False) # 요약문은 24시간 동안 저장!
def generate_summary(text, _model):
    """Gemini를 사용하여 3줄 요약을 생성합니다."""
    try:
        # API 호출 속도 조절을 위한 대기 (Rate Limit 방지)
        time.sleep(1) 
        
        prompt = f"""
        당신은 유능한 뉴스 조수입니다. 
        다음 뉴스 기사의 제목과 내용을 바탕으로 핵심 내용을 정확히 3개의 글머리 기호로 요약해 주세요.
        한국어로 간결하고 이해하기 쉽게 작성해 주세요.
        
        뉴스: {text}
        """
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ 사용량이 초과되었습니다. 잠시 후 다시 시도해주세요."
        return f"⚠️ 오류 발생: {str(e)}"

# --- Main UI ---

st.title("오늘의 3분 뉴스 ☕")

categories = ["Politics", "Economy", "Society", "International", "IT/Science"]
selected_category = st.radio("카테고리 선택", categories, horizontal=True)

if api_key:
    genai.configure(api_key=api_key)
    # 더 안정적인 모델로 변경 (gemini-1.5-flash)
    model = genai.GenerativeModel('gemini-1.5-flash')

    with st.spinner(f"{selected_category} 뉴스를 가져오는 중..."):
        articles = fetch_news(selected_category)
        if articles:
            st.success(f"✅ {selected_category} 최신 기사 5개를 가져왔습니다!")
        else:
            st.error(f"❌ {selected_category} 기사를 가져오지 못했습니다.")

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
             # 캐시된 결과가 있는지 확인
             summary = generate_summary(content_to_summarize, model)
             
             if "사용량이 초과되었습니다" in summary:
                 st.markdown(f"""
                    <div class="error-box">
                        {summary}<br>
                        <small>걱정 마세요! 결과가 저장되고 있으니 1분 뒤에 새로고침 해보세요.</small>
                    </div>
                 """, unsafe_allow_html=True)
             else:
                 st.markdown(f"""
                    <div class="summary-box">
                        <div class="summary-title">⚡ 3줄 요약</div>
                        {summary}
                    </div>
                 """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.warning("⚠️ 사이드바에 Gemini API 키를 입력해주세요.")
