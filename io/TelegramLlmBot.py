import asyncio
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
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

# ---------------------- 점수 표시 설정 ----------------------
# 사용자별 점수 표시 설정 저장
score_display_settings = {}

# ---------------------- 답변 후처리 함수 ----------------------
def postprocess_llm_answer(answer, links, user_input=None, show_scores=False, results=None):
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
        if show_scores and results:
            # 점수와 함께 링크 표시
            answer = answer.strip() + '\n\n[참고 링크 (관련성 점수)]\n'
            for i, (link, result) in enumerate(zip(links, results)):
                score = result.get('score', 0)
                answer += f"{i+1}. {link} (점수: {score:.2f})\n"
        else:
            # 기본 링크 표시
            answer = answer.strip() + '\n\n[참고 링크]\n' + '\n'.join(f"{i+1}. {l}" for i, l in enumerate(links))
    
    # 점수 표시가 활성화된 경우 검색 결과 요약 추가
    if show_scores and results:
        answer += f"\n\n📊 검색 정보: {len(results)}개 문서 검색됨"
        if results:
            max_score = max(r.get('score', 0) for r in results)
            min_score = min(r.get('score', 0) for r in results)
            answer += f" (최고 관련성: {max_score:.2f}, 최저: {min_score:.2f})"
    
    return answer.strip()

# ---------------------- 점수 표시 토글 명령어 ----------------------
async def toggle_score_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_setting = score_display_settings.get(user_id, False)
    new_setting = not current_setting
    score_display_settings[user_id] = new_setting
    
    if new_setting:
        message = "✅ 관련성 점수 표시가 활성화되었습니다.\n이제 검색 결과와 함께 관련성 점수가 표시됩니다."
    else:
        message = "❌ 관련성 점수 표시가 비활성화되었습니다.\n일반적인 답변 형태로 표시됩니다."
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_to_message_id=update.message.message_id,
    )

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
        
        # 사용자별 점수 표시 설정 확인
        show_scores = score_display_settings.get(user_id, False)
        
        results = await asyncio.get_running_loop().run_in_executor(
            None, lambda: search_by_vector(user_input, top_k=3)
        )
        print("검색 결과:", results)
        
        # 관련성 점수가 1 이하인 결과들 필터링
        filtered_results = [doc for doc in results if doc.get('score', 0) > 1.0]
        print(f"점수 필터링 후 결과: {len(filtered_results)}개 (원본: {len(results)}개)")
        
        if results and not filtered_results:
            print("모든 검색 결과의 관련성 점수가 1 이하여서 필터링됨")
        
        # 필터링된 결과 사용
        results = filtered_results
        
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
            if show_scores:
                # 점수와 함께 컨텍스트 생성
                context_text = "\n".join([
                    f"{i+1}. 제목: {doc.get('title', '')}\n내용: {doc.get('content', '')[:200]}\n링크: {doc.get('url', '')}\n관련성: {doc.get('score', 0):.2f}"
                    for i, doc in enumerate(results) if doc.get('url')
                ])
            else:
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
        answer = postprocess_llm_answer(answer, links, user_input, show_scores, results)
        
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
    
    # 메시지 핸들러
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )
    
    # 점수 표시 토글 명령어
    application.add_handler(CommandHandler("score", toggle_score_display))
    
    print("Bot polling…")
    print("사용 가능한 명령어:")
    print("  /score - 관련성 점수 표시 토글")
    application.run_polling()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
