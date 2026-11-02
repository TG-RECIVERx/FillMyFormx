import os
import time
import telebot
from playwright.sync_api import sync_playwright

TOKEN = os.getenv("BOT_TOKEN", "9270668766:AAF32A06OavZw1djq-q5KObKk4oLSDrzjow")
bot = telebot.TeleBot(TOKEN)

user_state = {}
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_state[user_id] = 'WAITING_FOR_URL'
    bot.send_message(user_id, "As-salamu alaykum! Apnar Google Form-er link-ti din jeta fill korte chan.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    state = user_state.get(user_id)
    
    if state == 'WAITING_FOR_URL':
        form_url = message.text.strip()
        if "forms.gle" not in form_url and "docs.google.com/forms" not in form_url:
            bot.send_message(user_id, "Doya kore ekti valid Google Form link provide korun.")
            return
        
        user_data[user_id] = {'form_url': form_url}
        user_state[user_id] = 'WAITING_FOR_COUNT'
        bot.send_message(user_id, "✅ Link received!\n\nKoto gulo response generate korte chan? (Udahoron: 500, 1000, 2000)")
        
    elif state == 'WAITING_FOR_COUNT':
        try:
            total_count = int(message.text.strip())
            if total_count <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(user_id, "Doya kore ekta shothik shongkha (number) input din (e.g., 1000).")
            return

        info = user_data.get(user_id, {})
        form_url = info.get('form_url')
        user_state.pop(user_id, None)
        user_data.pop(user_id, None)

        status_msg = bot.send_message(user_id, f"🚀 Browser Automation shuru hocche...\nTotal Target: {total_count} responses.")

        batch_size = 100
        success_total = 0
        failed_total = 0

        # Playwright automation start
        try:
            with sync_playwright() as p:
                # Headless browser launch kora (Render ba cloud server er jonno headless=True)
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                for i in range(0, total_count, batch_size):
                    current_batch = min(batch_size, total_count - i)
                    
                    try:
                        # 1. FillMyForm website-e jawa
                        page.goto("https://fillmyform.xyz/fill", timeout=60000)
                        
                        # 2. Google Form URL input box e link dewa
                        page.fill("input#form-url", form_url)
                        
                        # 3. Analyze Form button-e click kora
                        page.click("button[type='submit']")
                        
                        # 4. Configure page load hobar jonno wait kora ebong response count set kora
                        page.wait_for_selector("input#response-count", timeout=30000)
                        page.fill("input#response-count", str(current_batch))
                        
                        # 5. Generate button-e click kora
                        # Site-er generate button-er text "Generate X Responses" thake
                        page.click("button:has-text('Generate')")
                        
                        # 6. Success message ba progress complete howa porjonto wait kora
                        page.wait_for_selector("text=Successful", timeout=60000)
                        
                        success_total += current_batch
                    except Exception as ex:
                        print(f"Batch Error: {ex}")
                        failed_total += current_batch

                    progress_pct = int(((i + current_batch) / total_count) * 100)
                    try:
                        bot.edit_message_text(
                            f"🔄 **Automation Progress:** {progress_pct}%\n"
                            f"✅ **Successful:** {success_total}\n"
                            f"❌ **Failed:** {failed_total}\n"
                            f"📦 **Completed:** {i + current_batch}/{total_count}",
                            user_id,
                            status_msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

                    time.sleep(2)

                browser.close()

            bot.send_message(user_id, f"🎉 **Generation Complete!**\n\n✅ Total Successful: {success_total}\n❌ Total Failed: {failed_total}", parse_mode="Markdown")

        except Exception as e:
            bot.send_message(user_id, f"❌ Critical Error during browser automation: {str(e)}")

    else:
        bot.send_message(user_id, "Doya kore /start command diye shuru korun.")

if __name__ == "__main__":
    print("Playwright Bot is running...")
    bot.infinity_polling()
