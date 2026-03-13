import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import base64
import time
from llmlaw import get_ai_message
from PIL import Image



viewport = streamlit_js_eval(
    js_expressions="""
    ({
        width: window.innerWidth,
        height: window.innerHeight,
        screenWidth: screen.width,
        screenHeight: screen.height,
        pixelRatio: window.devicePixelRatio
    })
    """,
    key="viewport"
)

screen_width = viewport["width"]
screen_height = viewport["height"]

# print(f"viewport : {viewport}")

# 화면 높이와 너비 초기값 설정
if not screen_height or screen_height < 100:
    screen_height = 800

if not screen_width:
    screen_width = 1200

# 이미지를 base64변환
def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

icon = img_to_base64("DY.png") # Header내 아이콘 Img to base64

page_icon = Image.open("DY_pageicon.png")
page_icon = page_icon.resize((30, 30))

st.markdown("""
<style>
/* 타이틀 위 공백 제거 */
.block-container {
    padding-top: 0.5rem;
}

/* 헤더와 채팅영역 사이 구분선 */
.header-divider{
    border-top: 2px solid #d1d5db;  /* 굵기 + 색 */
    margin-top: 0px;
    margin-bottom: 0px;
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

/* PC 기본 버튼 스타일 */
div[data-testid="stButton"] button {
    margin-top:50px;
    font-size:15px;
    padding:4px 10px;
    border-radius:10px;
}

.title-text {
    font-size:20px;
    margin:0;
}

/* 모바일 버튼 스타일 + 모바일 채팅영역 높이 */
@media (max-width: 768px) {
    div[data-testid="stButton"] button {
        margin-top:5px;
        font-size:14px;
        padding:3px 8px;
        border-radius:10px;
    }

    .title-text{
        font-size:5px;
    }
    
    
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
        <div style="display:flex; align-items:center; gap:2px;">
            <img src="data:image/png;base64,{icon}" width="30">
            <h1 style="font-size:24px; margin:0;">통신관련 법령정보 QnA</h1>            
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<p style='font-size:16px; color:gray; margin-bottom:4px;'>ChatUpstage/UpstageEmbeddings 모델 적용</p>",
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
st.markdown('<div class="chat-area-wrap">', unsafe_allow_html=True)

if screen_width > 100 and screen_width < 768:
    chat_height = int(screen_height * 0.40)
    # print(f"모바일changed chat_height : {chat_height}")
elif screen_width >= 768:
    chat_height = int(screen_height * 0.60)
    # print(f"컴퓨터changed chat_height : {chat_height}")
else:
    chat_height = 500

chat_container = st.container(height=chat_height)


with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

st.markdown('</div>', unsafe_allow_html=True)
# -----------------------------
# INPUT
# -----------------------------

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
