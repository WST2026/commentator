import asyncio
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '../vectorDB'))
from vector_search import search_by_vector

# ---------------------- 환경 변수 로드 ----------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------------- Gemini 모델 설정 ----------------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# ---------------------- 답변 후처리 함수 ----------------------
def postprocess_llm_answer(answer, links, user_input=None):
    stop_patterns = [
        '\n[', '\n참고', '\n질문', '\n답변', '\nQ:', '\nA:', '\n---', '\n출처', '\nReference', '\n[참고', '\n[출처', '\n[질문', '\n[답변'
    ]
    min_idx = len(answer)
    for pat in stop_patterns:
        idx = answer.find(pat)
        if idx != -1 and idx < min_idx:
            min_idx = idx
    answer = answer[:min_idx].strip()
    url_pattern = r'https?://\S+'
    answer = re.sub(url_pattern, '', answer)
    if not answer or len(answer.strip()) == 0:
        return "관련 문서에서 답을 찾지 못했습니다."
    negative_phrases = ["정보가 없습니다", "알 수 없습니다", "자료가 없습니다", "확인되지 않", "제공되지 않", "모르"]
    # 답변이 부정적 문구만으로 이루어진 경우에는 참고 링크도 출력하지 않음
    if answer.strip() in negative_phrases:
        return "정보가 없습니다."
    links = [l for l in links if l]
    if links:
        answer = answer.strip() + '\n\n[참고 링크]\n' + '\n'.join(f"{i+1}. {l}" for i, l in enumerate(links))
    return answer.strip()

# ---------------------- Telegram Handler ----------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else None
        chat_type = update.effective_chat.type
        user_name = update.effective_user.full_name if update.effective_user else "(알 수 없음)"
        print(f"[LOG] 채팅방ID: {chat_id}, 채팅방타입: {chat_type}, 유저ID: {user_id}, 유저명: {user_name}")
        user_input = (update.message.text or "").strip()
        if not user_input:
            return
        results = await asyncio.get_running_loop().run_in_executor(
            None, lambda: search_by_vector(user_input, top_k=3)
        )
        print("검색 결과:", results)
        # 참고 링크 프롬프트 생성
        links = [doc['url'] for doc in results if doc.get('url')]
        context_text = "\n".join([
            f"{i+1}. {doc['url']}" for i, doc in enumerate(results) if doc.get('url')
        ]) if results else ""
        # 검색 결과가 없으면 context_text 없이 질문만 LLM에 전달
        if not results or all(not doc.get('url') for doc in results):
            prompt = (
                "아래 참고 문서에 정보가 없으면 '정보가 없습니다'라고 답하세요.\n"
                f"[질문]\n{user_input}\n\n[답변]"
            )
        else:
            # 링크별로 제목+내용 일부+링크를 LLM에 전달
            context_text = "\n".join([
                f"{i+1}. 제목: {doc.get('title', '')}\n내용: {doc.get('content', '')[:200]}\n링크: {doc.get('url', '')}"
                for i, doc in enumerate(results) if doc.get('url')
            ])
            prompt = (
                "아래 참고 문서의 내용을 바탕으로 질문에 답변하세요. 문서에 정보가 없으면 '정보가 없습니다'라고 답하세요.\n\n"
                f"[참고 문서]\n{context_text}\n\n[질문]\n{user_input}\n\n[답변]"
            )
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 512,
                }
            )
        )
        answer = response.text.strip()
        print("LLM 답변:", answer)
        answer = postprocess_llm_answer(answer, links, user_input)
        # 텔레그램 메시지 길이 제한 적용
        MAX_TELEGRAM_MSG_LEN = 4000
        if len(answer) > MAX_TELEGRAM_MSG_LEN:
            answer = answer[:MAX_TELEGRAM_MSG_LEN] + "\n\n(이하 생략)"
        await context.bot.send_message(
            chat_id=chat_id,
            text=answer,
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        print("텔레그램 전송 오류:", e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ 답변 생성 중 오류가 발생했습니다.\n{e}",
            reply_to_message_id=update.message.message_id,
        )

# ---------------------- Main ----------------------
def main() -> None:
    if not TOKEN:
        print("[ERROR] TELEGRAM_TOKEN 환경변수가 설정되어 있지 않습니다. .env 파일을 확인하세요.")
        sys.exit(1)
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )
    print("Bot polling…")
    application.run_polling()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
