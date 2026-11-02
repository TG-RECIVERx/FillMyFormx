import os
import time
import requests
import telebot

TOKEN = os.getenv("BOT_TOKEN", "9270668766:AAF32A06OavZw1djq-q5KObKk4oLSDrzjow")
bot = telebot.TeleBot(TOKEN)

# User states and data tracking dictionary
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
        
        parsing_msg = bot.send_message(user_id, "🔄 Form analyze kora hocche...")
        
        try:
            resp = requests.post("https://www.fillmyform.xyz/api/parse-form", json={"url": form_url}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                user_data[user_id] = {'form_url': form_url, 'form_data': data}
                user_state[user_id] = 'WAITING_FOR_COUNT'
                try:
                    bot.delete_message(user_id, parsing_msg.message_id)
                except Exception:
                    pass
                bot.send_message(user_id, "✅ Form successfully analyzed!\n\nKoto gulo response generate korte chan? (Udahoron: 1000 ba 2000)")
            else:
                bot.edit_message_text("❌ Form parse korte shomossha hoyeche. Link-ti thik ache ki na check korun.", user_id, parsing_msg.message_id)
                user_state.pop(user_id, None)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", user_id, parsing_msg.message_id)
            user_state.pop(user_id, None)
            
    elif state == 'WAITING_FOR_COUNT':
        try:
            total_count = int(message.text.strip())
            if total_count <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(user_id, "Doya kore ekta shothik shongkha (number) input din (e.g., 1000, 2000).")
            return

        info = user_data.get(user_id, {})
        form_url = info.get('form_url')
        form_info = info.get('form_data', {})
        user_state.pop(user_id, None)
        user_data.pop(user_id, None)

        status_msg = bot.send_message(user_id, f"🚀 Response generation shuru hocche...\nTotal: {total_count} ta response pathano hobe.")

        batch_size = 100
        success_total = 0
        failed_total = 0

        for i in range(0, total_count, batch_size):
            current_batch = min(batch_size, total_count - i)
            try:
                payload = {
                    "url": form_url,
                    "response_count": current_batch,
                    "form_data": form_info
                }
                resp = requests.post("https://www.fillmyform.xyz/api/submit-response", json=payload, timeout=60)
                if resp.status_code == 200:
                    success_total += current_batch
                else:
                    failed_total += current_batch
            except Exception:
                failed_total += current_batch

            progress_pct = int(((i + current_batch) / total_count) * 100)
            try:
                bot.edit_message_text(
                    f"🔄 **Progress:** {progress_pct}%\n"
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

        bot.send_message(user_id, f"🎉 **Generation Complete!**\n\n✅ Total Successful: {success_total}\n❌ Total Failed: {failed_total}", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Doya kore /start command diye shuru korun.")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
