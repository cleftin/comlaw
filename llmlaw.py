import os
from typing import List, Tuple, Any

from dotenv import load_dotenv
# from langchain_core.messages import ai
from pydantic import ConfigDict
from pinecone import Pinecone

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import UpstageEmbeddings, ChatUpstage
from langchain_pinecone import PineconeVectorStore

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from langchain_core.messages import HumanMessage, AIMessage


# -----------------------------
# Chat History 저장
# -----------------------------
chat_history: List[Any] = []

load_dotenv()

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROUNDLINE_INDEX = os.getenv("GROUNDLINE_INDEX")
BROADCOM_INDEX = os.getenv("BROADCOM_INDEX")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "default")

if not UPSTAGE_API_KEY:
    raise ValueError("UPSTAGE_API_KEY가 없습니다.")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY가 없습니다.")
if not GROUNDLINE_INDEX or not BROADCOM_INDEX:
    raise ValueError("GROUNDLINE_INDEX / BROADCOM_INDEX가 필요합니다.")


# -----------------------------
# 2) 임베딩 / LLM
# -----------------------------
def get_llm():
    llm = ChatUpstage()

    return llm


# -----------------------------
# 4) 멀티 인덱스 Retriever
# -----------------------------
class MultiPineconeRetriever(BaseRetriever):
    """
    두 개 이상의 PineconeVectorStore를 동시에 검색한 뒤,
    score 기준으로 정렬해서 상위 문서를 반환하는 커스텀 Retriever
    """

    vectorstores: List[Any]
    k_each: int = 5       # 각 인덱스에서 가져올 개수
    final_k: int = 5      # 최종 반환 개수

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str) -> List[Document]:
        all_docs_with_scores: List[Tuple[Document, float]] = []

        for vs in self.vectorstores:
            # PineconeVectorStore의 similarity_search_with_score 사용
            # score는 vector store 구현에 따라 거리/유사도 의미가 다를 수 있으므로
            # 실제 결과를 보고 정렬 방향을 확인하는 것이 안전함
            docs_with_scores = vs.similarity_search_with_score(query, k=self.k_each)
            all_docs_with_scores.extend(docs_with_scores)

        # 점수 정렬
        # 현재 사용 코드 흐름에 맞춰 reverse=True 유지
        # 만약 결과가 이상하면 reverse=False로 바꿔 테스트하세요.
        all_docs_with_scores = sorted(
            all_docs_with_scores,
            key=lambda x: x[1],
            reverse=True,
        )

        # 최종 상위 문서 추출
        top_docs = []
        for rank, (doc, score) in enumerate(all_docs_with_scores[: self.final_k], start=1):
            # 출처 확인용 metadata 추가
            doc.metadata["retrieval_score"] = score
            doc.metadata["retrieval_rank"] = rank
            top_docs.append(doc)
            # print("doc\n\n",doc.page_content)

        return top_docs



def get_retrieved_doc():
    embeddings = UpstageEmbeddings(
        model="solar-embedding-1-large"
    )
    # -----------------------------
    # 3) Pinecone 인덱스 연결
    # -----------------------------
    pc = Pinecone(api_key=PINECONE_API_KEY)

    groundline_index = pc.Index(GROUNDLINE_INDEX)
    broadcom_index = pc.Index(BROADCOM_INDEX)

    groundline_db = PineconeVectorStore(
        index=groundline_index,
        embedding=embeddings,
        namespace=PINECONE_NAMESPACE,
    )

    broadcom_db = PineconeVectorStore(
        index=broadcom_index,
        embedding=embeddings,
        namespace=PINECONE_NAMESPACE,
    )

    multi_retriever = MultiPineconeRetriever(
        vectorstores=[groundline_db, broadcom_db],
        k_each=5,
        final_k=5,
    )

    return multi_retriever



def format_docs(docs: List[Document]) -> str:

    formatted_docs = []

    for doc in docs:

        regulation = doc.metadata.get("regulation_name", "")
        article = doc.metadata.get("article", "")
        # clause = doc.metadata.get("clause", "")
        # source = doc.metadata.get("source", "")

        text = f"""
        규정명 : {regulation}
        조문: {article} 
        본문:
        {doc.page_content}
        """

        formatted_docs.append(text)

    return "\n\n".join(formatted_docs)


def extract_metadata(data):
    docs = data["docs"]
    question = data["input"]

    if not docs:
        return {
            "context": "",
            "regulation": "관련 규정 또는 기술기준 확인 불가",
            "article": "",
            "input": question,
        }

    top_doc = docs[0]

    return {
        "context": format_docs(docs),
        "regulation": top_doc.metadata.get("regulation_name", "관련 규정 또는 기술기준 확인 불가"),
        "article": top_doc.metadata.get("article", ""),
        "input": question,
    }


def get_ai_message(user_message):
    llm = get_llm()
    multi_retriever = get_retrieved_doc()

    # -----------------------------
    # 5) QA 프롬프트
    # -----------------------------
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
    너는 통신설비 기술 질의응답 전문가다.
    반드시 제공된 context만 근거로 답변하라.
    답변은 한국어로, 핵심부터 간결하게 답변하고, 근거를 바탕으로 답변이 나온 이유를 추가 설명해줘.

    반드시 아래 형식으로만 답하라.

    {regulation} ,\n 답변내용

    예시:
    접지설비·구내통신설비·선로설비 및 통신공동구등에 대한 기술기준 제8조, 
    통신설비의 접지저항은 10Ω 이하로 해야 합니다.

    <context>
    {context}
    </context>
    """.strip(),
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )

    
    rag_chain = (
    {
        "docs": RunnableLambda(lambda x: x["input"]) | multi_retriever,
        "input": RunnableLambda(lambda x: x["input"]),
        "chat_history": RunnableLambda(lambda x: x["chat_history"]),
    }
    | RunnableLambda(extract_metadata)
    | qa_prompt
    | llm
)

    ai_message = rag_chain.invoke(
        {
            "input": user_message,
            "chat_history": chat_history,
        }
    )

    chat_history.append(HumanMessage(content=user_message))
    chat_history.append(AIMessage(content=ai_message.content))

    return ai_message.content

