import asyncio
import sys
from datetime import datetime
from telegram import Bot, Update

TOKEN   = "PASTE_YOUR_TOKEN"        # 깃이나 공개 저장소에 노출되지 않게 주의!
CHAT_ID = -4883211398               # 그룹 채팅 ID

async def remove_webhook(bot: Bot):
    # 웹훅 비활성화 → long-polling 모드
    info = await bot.get_webhook_info()
    if info.url:
        await bot.delete_webhook()

async def reader(bot: Bot):
    # 그룹 채팅 메시지를 읽고 회답
    offset = None
    while True:
        updates: list[Update] = await bot.get_updates(
            offset=offset,
            timeout=3600,
            allowed_updates=["message"]
        )

        for upd in updates:
            offset = upd.update_id + 1
            msg = upd.message
            if not msg or not msg.text:
                continue

            # 봇이 보낸 메시지는 무시 (무한루프 방지)
            if msg.from_user.is_bot:
                continue

            if msg.chat.id == CHAT_ID:
                sender = msg.from_user.username or msg.from_user.first_name or "Unknown"
                print(f"[RECV] {sender}: {msg.text}")

                # echo reply
                reply = f"{msg.text}(이)라고 하셨네요"
                await bot.send_message(chat_id=CHAT_ID, text=reply)

        await asyncio.sleep(0.5)

async def main():
    bot = Bot(token=TOKEN)
    await remove_webhook(bot)
    await reader(bot)   # 단일 코루틴 실행

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
