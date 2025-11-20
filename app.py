import streamlit as st
import feedparser
import google.generativeai as genai
import os
from datetime import datetime
from dateutil import parser
import time
import requests
import random

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
    
    # --- Model Selection ---
    st.subheader("🤖 모델 선택")
    selected_model_name = "gemini-1.5-flash" # Default
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # List available models
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Clean up model names
            model_options = [m.replace('models/', '') for m in models]
            
            if model_options:
                # Default to gemini-1.5-flash if available, else first option
                default_index = 0
                if "gemini-1.5-flash" in model_options:
                    default_index = model_options.index("gemini-1.5-flash")
                
                selected_model_name = st.selectbox(
                    "사용 가능한 모델을 선택하세요:",
                    model_options,
                    index=default_index
                )
                st.info(f"선택된 모델: {selected_model_name}")
            else:
                st.error("사용 가능한 모델을 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"모델 목록 로드 실패: {e}")

    st.markdown("---")
    st.markdown("### 정보")
    st.markdown("Made with ❤️ using Streamlit & Gemini")

# --- Functions ---

@st.cache_data(ttl=3600)
def fetch_news(category):
    """카테고리에 맞는 구글 뉴스 RSS를 가져옵니다."""
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
        st.warning("뉴스를 찾을 수 없습니다.")
        return []

    # ★ 중요: 기사 개수를 3개로 줄임 (API 사용량 절약)
    for entry in feed.entries[:3]:
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

# ★ 중요: 캐싱 함수 분리 (에러는 캐싱하지 않기 위함)
@st.cache_data(ttl=86400, show_spinner=False)
def _generate_summary_api_call(text, model_name):
    """실제 API 호출을 수행하는 함수 (성공 시에만 결과 반환)"""
    
    model = genai.GenerativeModel(model_name)
    prompt = f"""
    당신은 유능한 뉴스 조수입니다. 
    다음 뉴스 기사의 제목과 내용을 바탕으로 핵심 내용을 정확히 3개의 글머리 기호로 요약해 주세요.
    한국어로 간결하고 이해하기 쉽게 작성해 주세요.
    
    뉴스: {text}
    """
    
    # ★ 중요: 재시도(Retry) 로직 추가
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 시도할 때마다 대기 시간 증가 (Exponential Backoff)
            # 1회차: 2초, 2회차: 4초, 3회차: 8초
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(sleep_time)
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                # 마지막 시도였다면 에러 발생시키기
                if attempt == max_retries - 1:
                    raise e
                # 아니면 계속 진행 (재시도)
                continue
            else:
                # 429가 아닌 다른 에러는 즉시 중단
                raise e

def generate_summary_safe(text, model_name):
    """API 호출을 시도하고 에러를 처리하는 래퍼 함수"""
    try:
        return _generate_summary_api_call(text, model_name)
    except Exception as e:
        if "429" in str(e):
            return "RATE_LIMIT_ERROR"
        return f"ERROR: {str(e)}"

# --- Main UI ---

st.title("오늘의 3분 뉴스 ☕")

categories = ["Politics", "Economy", "Society", "International", "IT/Science"]
selected_category = st.radio("카테고리 선택", categories, horizontal=True)

if api_key:
    with st.spinner(f"{selected_category} 뉴스를 가져오는 중..."):
        articles = fetch_news(selected_category)
        if articles:
            st.success(f"✅ {selected_category} 최신 기사 3개를 가져왔습니다!")
        else:
            st.error(f"❌ {selected_category} 기사를 가져오지 못했습니다.")

    for article in articles:
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title"><a href="{article['link']}" target="_blank" style="text-decoration:none; color:#31333F;">{article['title']}</a></div>
            <div class="news-meta">📅 {article['published']}</div>
        """, unsafe_allow_html=True)
        
        content_to_summarize = f"{article['title']} - {article['summary']}"
        summary_placeholder = st.empty()
        
        with summary_placeholder.container():
             # 래퍼 함수 호출
             summary_result = generate_summary_safe(content_to_summarize, selected_model_name)
             
             if summary_result == "RATE_LIMIT_ERROR":
                 st.markdown(f"""
                    <div class="error-box">
                        ⚠️ 사용량이 많아 요약을 가져오지 못했습니다.<br>
                        <small>잠시 후 다시 시도해주세요.</small>
                    </div>
                 """, unsafe_allow_html=True)
             elif summary_result.startswith("ERROR:"):
                 st.markdown(f"""
                    <div class="error-box">
                        ⚠️ 오류 발생: {summary_result}<br>
                        <small>모델을 다른 것으로 변경해보세요.</small>
                    </div>
                 """, unsafe_allow_html=True)
             else:
                 st.markdown(f"""
                    <div class="summary-box">
                        <div class="summary-title">⚡ 3줄 요약</div>
                        {summary_result}
                    </div>
                 """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.warning("⚠️ 사이드바에 Gemini API 키를 입력해주세요.")
