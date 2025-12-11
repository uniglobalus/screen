import asyncio
import os
import io
from playwright.async_api import async_playwright
from flask import Flask, request, jsonify
from telegram import Bot

app = Flask(__name__)

# Կարդում ենք Տելեգրամի փոփոխականները միջավայրից (Environment)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("⚠️ Զգուշացում. Տելեգրամի TOKEN-ը կամ CHAT ID-ն բացակայում են: Սքրինշոթերը չեն ուղարկվի:")

# Ավտոմատացիայի հիմնական ասինխրոն ֆունկցիան
async def run_screenshot_task(urls):
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return [{"status": "error", "message": "Telegram-ի կոնֆիգուրացիան բացակայում է։"}]

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    results = []
    
    async with async_playwright() as p:
        # Այս դեպքում օգտագործում ենք headless=True՝ օնլայն ծառայության համար
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for index, url in enumerate(urls):
            try:
                # 1. Անցնում ենք URL-ին
                await page.goto(url, timeout=60000)

                # 2. Անում ենք սքրինշոթը հիշողության մեջ (առանց ֆայլային համակարգում պահելու)
                image_bytes = await page.screenshot(full_page=True)

                # 3. Ուղարկում ենք Telegram
                # File-ը ստեղծում ենք հիշողության մեջ
                file_io = io.BytesIO(image_bytes)
                file_io.name = f"screenshot_{index + 1}_{url.split('//')[-1].replace('/', '_')[:30]}.png"
                
                await bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=file_io,
                    caption=f"✅ Սքրինշոթ {index + 1}: {url}",
                )

                results.append({"url": url, "status": "success", "telegram_sent": True})

            except Exception as e:
                # Ուղարկում ենք սխալի մասին հաղորդագրություն
                error_msg = f"❌ Սխալ տեղի ունեցավ {url}-ը մշակելիս. {e}"
                print(error_msg)
                
                try:
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=error_msg)
                except Exception as tele_e:
                    print(f"❌ Չհաջողվեց ուղարկել սխալը Telegram. {tele_e}")

                results.append({"url": url, "status": "error", "message": str(e)})

        await browser.close()
        return results

@app.route('/screenshot', methods=['POST'])
def handle_screenshot():
    data = request.get_json()
    
    if not data or 'urls' not in data or not isinstance(data['urls'], list):
        return jsonify({"error": "Խնդրում ենք տրամադրել 'urls' դաշտը՝ URL-ների ցանկով։"}), 400

    urls_to_capture = data['urls']
    
    # Գործարկում ենք ասինխրոն ֆունկցիան
    # Քանի որ Flask-ը սինխրոն է, անհրաժեշտ է այս կերպ գործարկել asyncio-ն
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(run_screenshot_task(urls_to_capture))
        return jsonify({"message": "Հարցումն ուղարկված է։ Արդյունքները Telegram-ում են:", "results": results})
    except Exception as e:
        return jsonify({"error": "Ընդհանուր սխալ տեղի ունեցավ սքրինշոթի գործընթացում", "details": str(e)}), 500

if __name__ == '__main__':
    # Տեղական փորձարկման համար
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
