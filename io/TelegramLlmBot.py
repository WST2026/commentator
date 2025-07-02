import asyncio
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
sys.path.append(os.path.join(os.path.dirname(__file__), '../vectorDB'))
from vector_search import search_by_vector

# ---------------------- 환경 변수 로드 ----------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = -4883211398

# ---------------------- Telegram Handler ----------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.id != CHAT_ID:
            return
        if update.effective_user.is_bot:
            return
        user_input = (update.message.text or "").strip()
        if not user_input:
            return
        # 벡터 유사도 검색 호출
        results = await asyncio.get_running_loop().run_in_executor(
            None, lambda: search_by_vector(user_input, top_k=3)
        )
        # 결과 포맷팅
        if results:
            result_text = "\n\n".join([
                f"[{i+1}] {doc['title']}\n{doc['content'][:200]}...\nURL: {doc['url']}"
                for i, doc in enumerate(results)
            ])
        else:
            result_text = "(유사한 문서를 찾지 못했습니다.)"
        reply_text = f"[입력]\n{user_input}\n\n[유사 문서 Top 3]\n{result_text}"
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=reply_text,
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"⚠️ 벡터DB 응답 중 오류가 발생했습니다.\n{e}",
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
