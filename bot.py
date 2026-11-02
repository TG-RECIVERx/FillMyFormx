import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import aiohttp

# Token directly set kora holo (Render-e env variable o use korte paren)
TOKEN = os.getenv("BOT_TOKEN", "9270668766:AAF32A06OavZw1djq-q5KObKk4oLSDrzjow")

dp = Dispatcher()
router = Router()

class FormStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_count = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("As-salamu alaykum! Apnar Google Form-er link-ti din jeta fill korte chan.")
    await state.set_state(FormStates.waiting_for_url)

@router.message(FormStates.waiting_for_url, F.text)
async def process_url(message: Message, state: FSMContext):
    form_url = message.text.strip()
    if "forms.gle" not in form_url and "docs.google.com/forms" not in form_url:
        await message.answer("Doya kore ekti valid Google Form link provide korun.")
        return

    parsing_msg = await message.answer("🔄 Form analyze kora hocche...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Parse form API hit
            async with session.post("https://www.fillmyform.xyz/api/parse-form", json={"url": form_url}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await state.update_data(form_url=form_url, form_data=data)
                    await parsing_msg.delete()
                    await message.answer("✅ Form successfully analyzed!\n\nKoto gulo response generate korte chan? (Udahoron: 1000 ba 2000)")
                    await state.set_state(FormStates.waiting_for_count)
                else:
                    await parsing_msg.edit_text("❌ Form parse korte shomossha hoyeche. Link-ti thik ache ki na check korun.")
                    await state.clear()
        except Exception as e:
            await parsing_msg.edit_text(f"❌ Error: {str(e)}")
            await state.clear()

@router.message(FormStates.waiting_for_count, F.text)
async def process_count(message: Message, state: FSMContext):
    try:
        total_count = int(message.text.strip())
        if total_count <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Doya kore ekta shothik shongkha (number) input din (e.g., 1000, 2000).")
        return

    user_data = await state.get_data()
    form_url = user_data.get('form_url')
    form_info = user_data.get('form_data', {})
    await state.clear()

    status_msg = await message.answer(f"🚀 Response generation shuru hocche...\nTotal: {total_count} ta response pathano hobe.")

    batch_size = 100
    success_total = 0
    failed_total = 0

    async with aiohttp.ClientSession() as session:
        for i in range(0, total_count, batch_size):
            current_batch = min(batch_size, total_count - i)
            
            try:
                payload = {
                    "url": form_url,
                    "response_count": current_batch,
                    "form_data": form_info
                }
                # Submit response API hit in batches of 100
                async with session.post("https://www.fillmyform.xyz/api/submit-response", json=payload) as resp:
                    if resp.status == 200:
                        success_total += current_batch
                    else:
                        failed_total += current_batch
            except Exception:
                failed_total += current_batch

            progress_pct = int(((i + current_batch) / total_count) * 100)
            try:
                await status_msg.edit_text(
                    f"🔄 **Progress:** {progress_pct}%\n"
                    f"✅ **Successful:** {success_total}\n"
                    f"❌ **Failed:** {failed_total}\n"
                    f"📦 **Completed:** {i + current_batch}/{total_count}"
                )
            except Exception:
                pass

            await asyncio.sleep(2) # Realistic delay between batches

    await message.answer(f"🎉 **Generation Complete!**\n\n✅ Total Successful: {success_total}\n❌ Total Failed: {failed_total}")

async def main():
    bot = Bot(token=TOKEN)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
