import asyncio
import sys
from telegram import Bot

async def main():
    token = "7609467234:AAEstu__ksWkEJYFyTYxP2XvFJUE2V3I3YA"
    bot = Bot(token=token)
    await bot.send_message(chat_id="-4883211398", text="일단 이렇게는 가능한것 같아")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())


'''
input이 들어왔을때, text로 나올 수 있도록
'''