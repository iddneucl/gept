import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import re
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import StringIO

# ---------------------------
# 1. 페이지 설정
# ---------------------------
st.set_page_config(page_title="AI STRATEGY AGENT PRO", page_icon="🏢", layout="wide")

st.markdown("""
<style>
.report-paper { 
    background-color: #fcfcfc; padding: 40px; border: 1px solid #ddd; 
    border-radius: 5px; color: #1a1a1a; line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 2. 사이드바
# ---------------------------
with st.sidebar:
    st.title("🏢 AGENT CONTROL")

    gemini_key = st.text_input("Gemini API Key", type="password")
    gpt_key = st.text_input("OpenAI API Key", type="password")

    model_choice = st.selectbox("LLM Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    temp = st.slider("Temperature", 0.0, 1.0, 0.2)
    top_p = st.slider("Top P", 0.0, 1.0, 0.9)

# ---------------------------
# 3. 메인 UI
# ---------------------------
st.title("🏢 전략 기획실: 하이브리드 AI 에이전트")

user_input = st.text_input(
    "📝 분석 주제",
    placeholder="예: 2026년 반도체 시장 분석"
)

# ---------------------------
# 4. 실행
# ---------------------------
if st.button("🚀 실행", use_container_width=True):

    # 입력 검증
    if not gemini_key or not gpt_key:
        st.error("API 키 필요")
        st.stop()

    if not user_input:
        st.warning("주제 입력 필요")
        st.stop()

    if len(user_input) > 200:
        st.warning("입력 200자 이하")
        st.stop()

    try:
        progress = st.progress(0)
        log = st.empty()

        # ---------------------------
        # STEP 1: Gemini
        # ---------------------------
        log.info("🌐 데이터 수집 중...")
        genai.configure(api_key=gemini_key)
        g_model = genai.GenerativeModel("gemini-1.5-flash")

        g_res = g_model.generate_content(
            f"{user_input} 관련 최신 시장 데이터, 기업 동향, 기술 트렌드 수집"
        )

        # 안전 처리
        raw_text = getattr(g_res, "text", None)
        if not raw_text:
            try:
                raw_text = g_res.candidates[0].content.parts[0].text
            except:
                raw_text = str(g_res)

        raw_intel = raw_text[:3000]
        progress.progress(30)

        # ---------------------------
        # STEP 2: GPT
        # ---------------------------
        log.info("✍️ 리포트 작성 중...")
        client = OpenAI(api_key=gpt_key)

        gpt_prompt = f"""
너는 전략 컨설턴트다.

[데이터]
{raw_intel}

[출력 구조]
1. 제목
2. 요약
3. 시장 분석
4. SWOT
5. 전략 제언

[차트 데이터]
반드시 아래 형식 유지:

[CHART_START]
Category,Value
A,100
B,200
[CHART_END]

조건:
- CSV 외 텍스트 금지
"""

        gpt_res = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": gpt_prompt}],
            temperature=temp,
            top_p=top_p
        )

        final = getattr(gpt_res.choices[0].message, "content", None)

        if not final:
            st.error("리포트 생성 실패")
            st.stop()

        progress.progress(80)

        # ---------------------------
        # STEP 3: 출력
        # ---------------------------
        log.success("✅ 완료")
        progress.progress(100)

        tab1, tab2, tab3 = st.tabs(["📄 리포트", "📊 차트", "🔍 원본"])

        # 리포트
        with tab1:
            st.markdown(f'<div class="report-paper">{final}</div>', unsafe_allow_html=True)

        # 차트
        with tab2:
            try:
                match = re.search(r'\[CHART_START\](.*?)\[CHART_END\]', final, re.DOTALL)

                if match:
                    csv_str = match.group(1).strip()
                    df = pd.read_csv(StringIO(csv_str))

                    if df.shape[1] >= 2:
                        val_col = df.columns[1]
                        df[val_col] = pd.to_numeric(
                            df[val_col].astype(str).str.replace(r'[^0-9.]', '', regex=True),
                            errors='coerce'
                        )

                        fig = px.bar(df, x=df.columns[0], y=df.columns[1])
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(df)
                    else:
                        st.warning("차트 데이터 부족")

                else:
                    st.info("차트 없음")

            except Exception as e:
                st.error(f"차트 오류: {e}")

        # 원본 데이터
        with tab3:
            st.write(raw_intel)

        # 다운로드
        safe_name = re.sub(r'[^a-zA-Z0-9가-힣_]', '', user_input)[:10]

        st.download_button(
            "📥 다운로드",
            final,
            file_name=f"Report_{safe_name}.md"
        )

    except Exception as e:
        st.error(f"❌ 오류: {e}")

# ---------------------------
# footer
# ---------------------------
st.markdown("---")
st.caption("AI Strategy Agent System")
