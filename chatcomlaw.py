import streamlit as st
import base64
import time
from llmlaw import get_ai_message
from PIL import Image


def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

icon = img_to_base64("DY.png") # Header내 아이콘 Img to base64

page_icon = Image.open("DY_pageicon.png")
page_icon = page_icon.resize((30, 30))

st.markdown("""
<style>
/* 헤더와 채팅영역 사이 구분선 */
.header-divider{
    border-top: 2px solid #d1d5db;  /* 굵기 + 색 */
    margin-top: 0px;
    margin-bottom: 0px;
}

/* 대화 초기화 버튼 */
div[data-testid="stButton"] button {
    margin-top:60px;
    font-size:15px;
    padding:4px 10px;
    border-radius:10px;
}

/* 채팅 영역 border 제거 */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
}

/* container 내부 border 제거 */
[data-testid="stVerticalBlock"] {
    border: none !important;
}

/* 입력창 테두리 회색 */
[data-testid="stChatInput"] > div{
    border:1px solid #d1d5db !important;
    border-radius:25px;
    background:white;
}

/* 입력창 내부 */
[data-testid="stChatInput"] textarea{
    border:none !important;
    outline:none !important;
    background:white !important;
}

/* 입력 중일 때도 회색 유지 */
[data-testid="stChatInput"]:focus-within > div{
    border:1px solid #d1d5db !important;
    box-shadow:none !important;
}

</style>
""", unsafe_allow_html=True)

#page_config 설정
st.set_page_config(
    page_title="통신관련 법령정보 QnA",
    page_icon=page_icon,
    layout="wide"
)

# -----------------------------
# HEADER
# -----------------------------
header = st.container()

with header:

    col1, col2 = st.columns([9,1])

    with col1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:5px;">
            <img src="data:image/png;base64,{icon}" width="45">
            <h1 style="font-size:30px; margin:0;">통신관련 법령정보 QnA</h1>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<p style='font-size:15px; color:gray;'>ChatUpstage모델, UpstageEmbeddings임베딩모델 사용, 2026.03.11.</p>",
            unsafe_allow_html=True
        ) 
      

    with col2:
        if st.button("대화 초기화"):
            st.session_state.messages = []
            st.rerun()

st.markdown('<div class="header-divider"></div>', unsafe_allow_html=True) #header영역과 chatting영역 사이 구분선 삽입

# -----------------------------
# SESSION
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [] #사용자와 AI 대화 저장 리스트

# -----------------------------
# CHAT AREA
# -----------------------------
chat_container = st.container(height=350)

with chat_container:

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.write(message["content"])

# -----------------------------
# INPUT
# -----------------------------
# print("printing",st.session_state.messages)

if prompt := st.chat_input("통신관련 법령정보를 검색하세요!"):

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)

        with st.spinner("답변 생성중..."):
            answer = get_ai_message(prompt) #사용자 질문에 대한 답변 요청

        # streaming 출력
        with chat_container:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_text = ""

                for word in answer.split():
                    full_text += word + " "
                    placeholder.markdown(full_text)
                    time.sleep(0.02)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

    st.rerun()