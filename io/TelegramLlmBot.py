import asyncio
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from transformers import pipeline

# ---------------------- Bot & Model Settings ----------------------
TOKEN = "Token"
CHAT_ID = -4883211398
MODEL_NAME = "kakaocorp/kanana-1.5-2.1b-instruct-2505"

# ---------------------- Load LLM Pipeline (once) ------------------
print("[INIT] Loading model… (최초 1회, 수십 초~수 분 소요)")
textgen = pipeline(
    "text-generation",
    model=MODEL_NAME,
    device_map="auto",
    torch_dtype="auto",
    trust_remote_code=True,
)
print(" 시스템 작동!! 준비 완료!! ")

# ---------------------- Helper ----------------------
async def llm_reply(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    result: str = await loop.run_in_executor(
        None,
        lambda: textgen(
            prompt,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            return_full_text=False,
        )[0]["generated_text"].strip()
    )
    return result

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
        prompt = f"User: {user_input}\nAssistant:"
        reply_text = await llm_reply(prompt)
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=reply_text,
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text="⚠️ LLM 응답 중 오류가 발생했습니다.",
            reply_to_message_id=update.message.message_id,
        )

# ---------------------- Main ----------------------
def main() -> None:
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
