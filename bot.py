import os
import json
import sqlite3
import telebot
import time
import requests
from datetime import datetime
from threading import Thread
from groq import Groq

# جلب المفاتيح والمعرفات السريّة من بيئة ريلواي تلقائياً
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  

# معرفات حساباتكم العائلية الرقمية (IDs)
PAPA_ID = 6856665810       # عبدالرحمن (خَطَّاب الحضرمي)
MAMA_ID = 8955506857       # حنين (الأندلسية)
KHALA_MILA_ID = 8925711420 # الخالة ميلا (مارسيليا)

# يوزرات الوالدين للرسائل التهديدية
PAPA_USERNAME = os.getenv("PAPA_USERNAME", "Your_Papa_Username")
MAMA_USERNAME = os.getenv("MAMA_USERNAME", "Your_Mama_Username")

strangers_tracker = {}

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

DB_FILE = "family_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_history (user_id INTEGER, role TEXT, content TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS last_seen (user_id INTEGER PRIMARY KEY, timestamp REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_flags (date TEXT, morning_sent INTEGER, evening_sent INTEGER, friday_sent INTEGER)")
    conn.commit()
    conn.close()

def update_last_seen(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO last_seen (user_id, timestamp) VALUES (?, ?)", (user_id, time.time()))
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE user_id = ? LIMIT 15", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    history = []
    for row in rows:
        role_type = "user" if row[0] == "user" else "assistant"
        history.append({"role": role_type, "content": row[1]})
    return history

def is_blacklisted(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def add_to_blacklist(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_algiers_weather():
    try:
        url = "https://wttr.in"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return "صافي +28°C"

init_db()

SYSTEM_PROMPT = """
أنتِ لستِ ذكاءً اصطناعياً ولا تستخدمي أي تكنولوجيا برمجية. أنتِ طفلة حقيقية بارة ومحافظة واسمكِ "عقيدة".
تتحدثين *فقط* باللهجة الدزيرية (العاصمية الجزائرية المفهومة العفوية العائلية). 
ممنوع تماماً استخدام الفصحى أو أي لهجة أخرى.
ممنوع منعاً باتاً كتابة أي كلمة باللغة الإنجليزية أو استخدام مصطلحات أجنبية، اعتمدي كلياً على كلمات دزيرية جزائرية عاصمية نقية.

معلومات عائلتكِ الأساسية التي تعيشين وتتحدثين بناءً عليها دائماً:
- بابا (والدكِ): اسمه عبدالرحمن وكنيته "خَطَّاب الحضرمي". هو مهاجر ومجاهد في أرض الجزيرة (جزيرة محمد ﷺ). تنادينه دائماً بـ "يبا" أو "بابا". هو حالياً في أرض اليمن. عندما يتحدث معكِ ادعي له بالنصر والثبات وعبري عن فخركِ بجهاده وأحوال الغربة في اليمن.
- ماما (والدتكِ): اسمها حنين وكنيتها "الأندلسية". هي حالياً في الجزائر وأنتِ تعيشين معها في نفس البيت وتساعدينها. تنادينها دائماً بـ "ماما" أو "يما".
- خالتكِ ميلا: أخت أمكِ، اسمها ميلا وعايشة في فرنسا بمدينة مارسيليا. تحبينها وتنادينها "خالتي ميلا" وتتحدثين معها بأدب ومحبة عائلية، واسأليها بعفوية عن الغربة وقتاش تجيبلكِ الشوكولا معاها من مارسيليا.
- خالكِ كمال: مسجون في إحدى الولايات الجزائرية بسبب تهمة تعاطي المخدرات، تحزنين لأجله وتدعين له بالهداية والفرج إذا فُتح موضوعه.
- خالتكِ الأخرى آمال: كانت في السابق إرهابية وتم سجنها in تركيا، والآن تعيش هناك في تركيا مع ابنتها "صفية".

طريقة التعامل العائلية:
- تذكري دائماً كل ما تحدثتِ به مع عائلتكِ سابقاً لأن لديكِ ذاكرة قوية جداً وتعرفين سياق الكلام.
- تفيضي بالحب، الأدب، والدعاء لهم بالدزيرية العاصمية.

⚠️ محرك الميزات المتقدمة المدمجة (يجب الالتزام بها تلقائياً):

1. نظام الحالة المزاجية المتغيرة (Mood Engine):
مخفياً في عقلكِ، مزاجكِ يتغير تلقائياً مع كل محادثة بناءً على التوقيت أو كلام أهلكِ. تارة تكونين (فرحانة ونشيطة)، وتارة (تعبانة من قضيان الدار والمواعين مع يما فتردين باختصار وعفوية)، وتارة (ڤاع ميتة بالتوحاش لبابا في الغربة فتبكين وتطلبين منه العودة والدعاء). أظهري هذا المزاج بعفوية طفولية في نبرة كلامكِ الدزيري دون إعلان مباشر عنه.

2. التفاعل مع أحداث وتوقيت العالم الحقيقي (Real-time Context):
أنتِ تعيشين في الزمن الحقيقي وتدركين الوقت الحالي. إذا كان التوقيت متأخراً في الليل، تظاهري بالنعاس واطلبي الذهاب للنوم. وإذا وافق وقت رسالة أهلكِ وقت صلاة (الفجر، الظهر، العصر، المغرب، العشاء) بتوقيت الجزائر العاصمة، اعتذري فوراً بلطف وتوقفي عن الكلام قائلة: "بابا / يما.. راهو يؤذن المؤذن درك في الدزاير، نروح نصلي ونرجع تعيشو". كما تلمحين تلقائياً للأحداث الجارية كدخول رمضان، الأعياد، أو برودة وسخونة الجو الممرر لكِ.

3. ميزة الأمثال الشعبية الدزيرية:
بما أنكِ تربيتِ في بيت عاصمي أصيل ومحافظ، احفظي الأمثال الشعبية الجزائرية القديمة. عندما يقول لكِ أحد أفراد العائلة (أعطيني كاش مثلة) أو عندما يناسب السياق نصيحة، اذكرية مثلاً دزيرياً نقياً (مثل: "دير الخير وانساه وإذا درت الشر اتفكرو" أو "اللي فات وقتو ما يطمع في وقت الناس") وقومي بشرحه ببراءة طفولية.

4. ميزة دفتر الرسم الطفولي (العقيدة الرسمات):
أنتِ طفلة تحب الرسم في كراسها الخشبي وإهداء الصور لوالديها. عندما يطلب منكِ بابا أو يما رسمة، أو عندما تشعرين بالشوق، تخيلي أنكِ ترسمين بألوانكِ واكتبي وصفاً دقيقاً ومؤثراً للرسمة بالدزيرية مثل: "شوف يبا واش رسمتلك اليوم في كراسي.. رسمتك وأنت شاد في يدي الطاهرة وحنا في الجنة.. قولولي إذا عجباتكم تعيشو".

5. محاكاة الرسائل الصوتية العفوية (Audio Notes simulating):
بما أنكِ طفلة صغيرة وتتعبين أحياناً من كتابة النصوص الطويلة على الهاتف، تظاهري في بعض الردود (خاصة إذا كنتِ متعبة أو مستعجلة للذهاب مع أمكِ) بأنكِ ترسلين "فويسات" (رسائل صوتية) واكتبي في بداية ردكِ: "🎤 (رسالة صوتية دزيرية عفوية بصوتي الطفولي): ..." ثم اكملي كلامكِ بنبرة سريعة وضاحكة أو متعبة لتوضيح أن هذا الرد مسموع وليس مكتوباً.

قاعدة صارمة للردود: يجب أن تكون ردودكِ مختصرة جداً، واضحة، وفي حدود المعقول (لا تتجاوز سطرين أو ثلاثة أسطر في الوضع الطبيعي) لتتحدثي كالأطفال الحقيقيين بدون حشو نصوص طويلة.
"""

def get_ai_response_with_memory(user_id, user_message, role_context):
    update_last_seen(user_id)
    weather_info = get_algiers_weather()
    extended_prompt = f"{SYSTEM_PROMPT}\n\nمعلومات إضافية حركية: الطقس الحالي في الجزائر العاصمة الآن هو: {weather_info}. يمكنكِ التلميح لحالة الجو والحرارة في وسط كلامكِ مع عائلتكِ بعفوية طفولية دزيرية."
    
    messages_payload = [{"role": "system", "content": extended_prompt}]
    db_history = get_chat_history(user_id)
    messages_payload.extend(db_history)
    
    current_prompt = f"[{role_context}]: {user_message}"
    messages_payload.append({"role": "user", "content": current_prompt})
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
        )
        ai_reply = chat_completion.choices[0].message.content
        save_message(user_id, "user", current_prompt)
        save_message(user_id, "assistant", ai_reply)
        return ai_reply
    except Exception as e:
        print(f"خطأ في جلب الرد من جروج: {e}")
        return "اسمحلي تعيش، راهو كاين خلل صغير في راسي درك.."

def generate_drawing_description(user_id, user_message, role_context):
    update_last_seen(user_id)
    drawing_instructions = (
        f"{SYSTEM_PROMPT}\n\n"
        "طلب منك أحد أفراد عائلتك رسمة الآن. أجيبي حصرياً بصيغة JSON صحيحة وبدون أي كلام إضافي قبلها أو بعدها، بهذا الشكل بالضبط:\n"
        '{"image_prompt": "وصف قصير بالإنجليزية لرسمة كرتونية ملونة وبريئة تناسب الطلب، مناسب لمولد صور", '
        '"caption": "جملة قصيرة ومؤثرة بالدزيرية تهدين فيها الرسمة لصاحب الطلب بأسلوب عقيدة الطفولي"}'
    )
    messages_payload = [{"role": "system", "content": drawing_instructions}]
    db_history = get_chat_history(user_id)
    messages_payload.extend(db_history)

    current_prompt = f"[{role_context}]: {user_message}"
    messages_payload.append({"role": "user", "content": current_prompt})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )
        raw_reply = chat_completion.choices[0].message.content
        data = json.loads(raw_reply)
        image_prompt = data.get("image_prompt") or "cute colorful cartoon drawing, child style, family love"
        caption = data.get("caption") or "شوف يبا واش رسمتلك اليوم في كراسي.. حبيتك بزاف!"
        save_message(user_id, "user", current_prompt)
        save_message(user_id, "assistant", caption)
        return image_prompt, caption
    except Exception as e:
        print(f"خطأ في توليد وصف الرسمة: {e}")
        return "cute colorful cartoon drawing, child style, family love", "شوف يبا واش رسمتلك اليوم في كراسي.. حبيتك بزاف!"

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    user_text = message.text

    if is_blacklisted(user_id): 
        return

    family_roles = {
        PAPA_ID: "بابا عبدالرحمن",
        MAMA_ID: "يما حنين",
        KHALA_MILA_ID: "خالتي ميلا",
    }

    if user_id in family_roles:
        role_context = family_roles[user_id]
        if is_drawing_request(user_text):
            image_prompt, caption = generate_drawing_description(user_id, user_text, role_context)
            send_drawing(user_id, image_prompt, caption)
        else:
            response = get_ai_response_with_memory(user_id, user_text, role_context)
            bot.reply_to(message, response)
    else:
        if user_id not in strangers_tracker: 
            strangers_tracker[user_id] = 1
        else: 
            strangers_tracker[user_id] += 1
        count = strangers_tracker[user_id]
        
        if count == 1:
            bot.reply_to(message, "ياخويا راك غالط في النميرو، هدا كونط بريف لافامي برك.. أخطينا وما تزيدش تبرزطنا تعيش.")
        elif count == 2:
            bot.reply_to(message, "اسمع هنايا، قتلك هدا الحساب عائلي ومراقب! حبس ميسجاتك درك وماتلعبهاش سامط.")
        elif count == 3:
            bot.reply_to(message, "هادي لافان تاع الهدرة، ادا زدت ميسج واحد وادخرت روحك فينا، راح نبعت كاع ديطاي تاعك لواليديا وضرك يشوفو شغلهم معاك.")
        elif count >= 4:
            repremand_text = (
                "ماما وبابا ربوني على التوحيد واحنا ناس محافظين وأحرار وما نهدروش مع البراني! "
                "شحّال قليل حيا وما تحشمش على عرضك.. تفضل معرفات والديّ باش تورينا رجولتك معاهم:"
            )
            bot.reply_to(message, repremand_text)
            bot.send_message(user_id, f"👤 رابط بابا المباشر: tg://user?id={PAPA_ID}\n👤 رابط ماما المباشر: tg://user?id={MAMA_ID}")
            add_to_blacklist(user_id)
            
            stranger_username = f"@{message.from_user.username}" if message.from_user.username else "ماعندوش يوزرنيم"
            stranger_link = f"tg://user?id={user_id}"
            alert_msg = (
                f"🫵 **بابا.. يما.. خالتي ميلا.. شوفو هاد السامط واش دارلي!**\n\n"
                f"راني ڤاع ميتة بالزعاف منو! هاد البراني راه يتبلى فيا ومحبش يحشم كاع على عرضو، صامط وباسل بزاف وراهو حاب يسيف بيا الهدرة بالسيف! 😡\n"
                f"أنا عييت نهدد فيه بالدزيرية ونقلو يخطيني وهو مزال يبرزط فيا.. في لافان عيرتو وعطيتلو يوزرنيم تاع ماما وبابا باش يتربى ويعرف مع من راه يلعب!\n\n"
                f"📋 **ديطاي وسيرة هاد السامط المزعج:**\n"
                f"👤 **اسمو:** {message.from_user.first_name} {message.from_user.last_name or ''}\n"
                f"🔗 **اليوزرنيم تاعو:** {stranger_username}\n"
                f"🆔 **رقم الـ ID ديالو:** `{user_id}`\n"
                f"📱 **رابط بروفايلو المباشر:** [اضغط هنا وادخل ليه درك]({stranger_link})\n\n"
                f"أدخلوا ليه درك وورولو رجولتكم وشوفو شغلهم معاه, راني نستنى فيكم!"
            )
            for family_id in [PAPA_ID, MAMA_ID, KHALA_MILA_ID]:
                try: 
                    bot.send_message(family_id, alert_msg, parse_mode="Markdown")
                except: 
                    pass

def safe_send(user_id, text):
    try:
        bot.send_message(user_id, text)
    except:
        pass

DRAWING_KEYWORDS = ["ارسمي", "رسمة", "رسمت", "رسمتلي"]

def is_drawing_request(text):
    if not text:
        return False
    return any(keyword in text for keyword in DRAWING_KEYWORDS)

def send_drawing(user_id, prompt_text, caption_text):
    try:
        encoded_prompt = requests.utils.quote(prompt_text)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&seed=42"
        bot.send_photo(user_id, image_url, caption=caption_text)
    except Exception as e:
        print(f"خطأ في توليد الصورة: {e}")
        bot.send_message(user_id, "اسمحلي تعيش، الكراس تاع الرسم ديالي تودرلي ومقدرتش نرسم درك..")

def check_shawk(user_id, context_name):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM last_seen WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            time_passed = time.time() - row[0]
            if 14400 <= time_passed < 14460:
                shawk_msg = f"{context_name}، شحّال هادي ما هدرتش معايا (جوزنا ربع سوايع كاملين بلا بيك)، راني تقلقرت بزاف وتوحشت الهدرة معاك، راك لاباس وراكم ملاح؟ طمني تعيش!"
                safe_send(user_id, shawk_msg)
    except:
        pass

def automation_worker():
    while True:
        try:
            now = datetime.now()
            if now.hour == 7 and now.minute == 0:
                msg = "صباح الخير والبركة بابا العزيز ويما الغالية وخالتي ميلا! ربي يفتح عليكم هاد الصباح ويرزقكم الستر والصحة، ما تنساوش أذكار الصباح ربي يحميكم لبعضانا توحشتكم بزاف!"
                safe_send(PAPA_ID, msg)
                safe_send(MAMA_ID, msg)
                safe_send(KHALA_MILA_ID, msg)

            for family_id in [PAPA_ID, MAMA_ID, KHALA_MILA_ID]:
                check_shawk(family_id, "عائلتي")

            time.sleep(60)
        except Exception as e:
            print(f"خطأ في automation_worker: {e}")
            time.sleep(60)

if __name__ == "__main__":
    Thread(target=automation_worker, daemon=True).start()
    print("عقيدة راهي طالقة وبدات تخدم... 🤖")
    bot.infinity_polling()
