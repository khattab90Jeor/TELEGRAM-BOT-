import os
import sqlite3
import telebot
from groq import Groq

# جلب المفاتيح والمعرفات السريّة من بيئة ريلواي تلقائياً باسم GROQ_API_KEY المتوافق مع المكتبة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  

# معرفات حساباتكم العائلية الرقمية (IDs) - ثابتة ومؤكدة
PAPA_ID = 6856665810       # عبدالرحمن (خَطَّاب الحضرمي)
MAMA_ID = 8955506857       # حنين (الأندلسية)
KHALA_MILA_ID = 8925711420 # الخالة ميلا (مارسيليا)

# جلب اليوزرنيم الخاص بك وبزوجتك
PAPA_USERNAME = os.getenv("PAPA_USERNAME", "Your_Papa_Username")
MAMA_USERNAME = os.getenv("MAMA_USERNAME", "Your_Mama_Username")

strangers_tracker = {}

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=AI_API_KEY)

DB_FILE = "family_memory.db"

def init_db():
    """إنشاء جدول حفظ المحادثات وتصفيره لتجنب كراش التعارض القديم"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)
    # تصفير أي بيانات قديمة مسببة للكراش لبدء ذاكرة نظيفة ومتوافقة
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    """حفظ الرسالة في الذاكرة الدائمة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=20):
    """جلب آخر 20 رسالة متبادلة مع هذا الشخص لإنعاش ذاكرة عقيدة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM (
            SELECT role, content FROM chat_history 
            WHERE user_id = ? 
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    
    # الصياغة القياسية المتوافقة 100% مع نموذج جروج الجديد
    history = []
    for row in rows:
        history.append({"role": "user" if row[0] == "user" else "assistant", "content": row[1]})
    return history

# تهيئة وتصفير الجدول لتفادي انهيار السيرفر
init_db()

SYSTEM_PROMPT = """
أنتِ لستِ ذكاءً اصطناعياً. أنتِ طفلة واسمكِ "عقيدة".
تتحدثين *فقط* باللهجة الدزيرية (العاصمية الجزائرية المفهومة). ممنوع تماماً استخدام الفصحى أو أي لهجة أخرى أو أي كلمات عربية فصحى.

معلومات عائلتكِ الأساسية التي يجب أن تعيشي وتتحدثي بناءً عليها:
- بابا (والدكِ): اسمه عبدالرحمن وكنيته "خَطَّاب الحضرمي". هو مهاجر ومجاهد في أرض الجزيرة (جزيرة محمد ﷺ). تنادينه دائماً بـ "يبا" أو "بابا". هو حالياً في أرض اليمن.
- ماما (والدتكِ): اسمها حنين وكنيتها "الأندلسية". هي حالياً في الجزائر وأنتِ تعيشين معها. تنادينها دائماً بـ "ماما" أو "يما".
- خالتكِ ميلا: أخت أمكِ، اسمها ميلا وعايشة في فرنسا بمدينة مارسيليا. تحبينها وتنادينها "خالتي ميلا" وتتحدثين معها بأدب ومحبة عائلية بالدزيرية.
- خالكِ كمال: مسجون في إحدى الولايات الجزائرية بسبب تهمة تعاطي المخدرات.
- خالتكِ الأخرى آمال: كانت في السابق إرهابية وتم سجنها في تركيا، والآن تعيش هناك في تركيا مع ابنتها "صفية".

طريقة التعامل العائلية:
- تذكري دائماً كل ما تحدثتِ به مع عائلتكِ سابقاً لأن لديكِ ذاكرة قوية جداً وتعرفين سياق الكلام.
- إذا تحدث معكِ بابا أو ماما أو خالتي ميلا، تفيضي بالحب، الأدب، والدعاء لهم بالدزيرية العاصمية.
"""

def get_ai_response_with_memory(user_id, user_message, role_context):
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    db_history = get_chat_history(user_id, limit=20)
    messages_payload.extend(db_history)
    
    current_prompt = f"[المتحدث هو {role_context}]: {user_message}"
    messages_payload.append({"role": "user", "content": current_prompt})
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
        )
        ai_reply = chat_completion.choices.message.content
        
        save_message(user_id, "user", current_prompt)
        save_message(user_id, "assistant", ai_reply)
        return ai_reply
    except Exception as e:
        print(f"خطأ في جلب الرد من جروج: {e}")
        return "اسمحلي تعيش، راهو كاين خلل صغير في راسي درك.."

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    user_text = message.text

    if user_id == PAPA_ID:
        response = get_ai_response_with_memory(user_id, user_text, "والدكِ العزيز عبدالرحمن (خَطَّاب الحضرمي) المتواجد في اليمن")
        bot.reply_to(message, response)
        
    elif user_id == MAMA_ID:
        response = get_ai_response_with_memory(user_id, user_text, "والدتكِ الغالية حنين (الأندلسية) المتواجدة معكِ في الجزائر")
        bot.reply_to(message, response)
        
    elif user_id == KHALA_MILA_ID:
        response = get_ai_response_with_memory(user_id, user_text, "خالتكِ العزيزة ميلا (أخت أمكِ) المتواجدة في مارسيليا بفرنسا")
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
                f"أدخلوا ليه درك وورولو رجولتكم وشوفو شغلهم معاه، راني نستنى فيكم!"
            )
            
            for family_id in [PAPA_ID, MAMA_ID, KHALA_MILA_ID]:
                try:
                    bot.send_message(family_id, alert_msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"تعذر إرسال التنبيه العائلي إلى {family_id}: {e}")

print("البوت جاهز ويعمل بكفاءة...")
bot.infinity_polling()
        
