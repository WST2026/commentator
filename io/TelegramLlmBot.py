import asyncio
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '../vectorDB'))
from vector_search import search_by_vector

# ---------------------- 환경 변수 로드 ----------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = -4883211398

# ---------------------- LLM 모델/토크나이저 로드 ----------------------
MODEL_NAME = "kakaocorp/kanana-1.5-2.1b-instruct-2505"
device = "cuda" if torch.cuda.is_available() else "cpu"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto", torch_dtype="auto", trust_remote_code=True)

# ---------------------- 답변 후처리 함수 ----------------------
def postprocess_llm_answer(answer, links, user_input=None):
    # EOS/불필요한 반복/프롬프트 잔여물 자르기
    stop_patterns = [
        '\n[', '\n참고', '\n질문', '\n답변', '\nQ:', '\nA:', '\n---', '\n출처', '\nReference', '\n[참고', '\n[출처', '\n[질문', '\n[답변'
    ]
    min_idx = len(answer)
    for pat in stop_patterns:
        idx = answer.find(pat)
        if idx != -1 and idx < min_idx:
            min_idx = idx
    answer = answer[:min_idx].strip()
    # 답변 내 URL 제거(출처는 마지막에만)
    url_pattern = r'https?://\S+'
    answer = re.sub(url_pattern, '', answer)
    # 답변이 너무 짧거나, 질문의 키워드만 반복하거나, '없다'/'알 수 없다' 등 부정적 답변이면 안내
    if not answer or len(answer) < 10 or (user_input and user_input.strip() in answer):
        return "관련 문서에서 답을 찾지 못했습니다."
    if any(x in answer for x in ["모르", "없", "알 수 없", "정보가 없습니다", "자료가 없습니다", "확인되지 않", "제공되지 않"]):
        return "관련 문서에서 답을 찾지 못했습니다."
    # 마지막에 [참고 링크] 한 번만 출력
    links = [l for l in links if l]
    if links:
        answer = answer.strip() + '\n\n[참고 링크]\n' + '\n'.join(f"{i+1}. {l}" for i, l in enumerate(links))
    return answer.strip()

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
        # 검색 결과 없으면 바로 안내
        if not results or all(not doc['url'] for doc in results):
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text="관련 문서를 찾지 못했습니다.",
                reply_to_message_id=update.message.message_id,
            )
            return
        # 참고 링크 프롬프트 생성
        links = [doc['url'] for doc in results if doc['url']]
        context_text = "\n".join([
            f"{i+1}. {doc['url']}" for i, doc in enumerate(results) if doc['url']
        ])
        prompt = f"다음은 참고 문서 링크와 사용자의 질문입니다. 아래 링크들을 참고해서 질문에 답변해 주세요.\n\n[참고 문서 링크]\n{context_text}\n\n[질문]\n{user_input}\n\n[답변]"
        # LLM 증강 답변 생성 (generate 직접 사용)
        input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
        eos_token_id = tokenizer.eos_token_id
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
                eos_token_id=eos_token_id,
                pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos_token_id,
            )
        answer = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
        answer = postprocess_llm_answer(answer, links, user_input)
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=answer,
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=CHAT_ID,
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
