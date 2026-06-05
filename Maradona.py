import json
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta

BOT_TOKEN = "8813486106:AAG4-WF7mBQfog0GgdJDWjpoJIKFI6NpkWc"

class MaradoBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.users_data = {}
        self.users = {}
        self.load_users()
        self.offset = 0
    
    def load_users(self):
        try:
            with open('marado.json', 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        except:
            self.users = {}
    
    def save_users(self):
        with open('marado.json', 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.users:
            self.users[uid] = {
                "chocolates": 0,
                "last_daily": None,
                "mode": None
            }
            self.save_users()
        return self.users[uid]
    
    def can_claim(self, uid):
        u = self.get_user(uid)
        if not u["last_daily"]:
            return True
        last = datetime.fromisoformat(u["last_daily"])
        return datetime.now() - last >= timedelta(hours=24)
    
    def api_call(self, method, data=None):
        url = f"{self.base_url}/{method}"
        if data:
            data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode('utf-8'))
        except:
            return None
    
    def send_message(self, chat_id, text, keyboard=None):
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        return self.api_call("sendMessage", data)
    
    def edit_message(self, chat_id, msg_id, text, keyboard=None):
        data = {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        return self.api_call("editMessageText", data)
    
    def answer_callback(self, callback_id):
        return self.api_call("answerCallbackQuery", {"callback_query_id": callback_id})
    
    def main_menu_keyboard(self):
        return {
            "inline_keyboard": [
                [{"text": "🧠 چت با هوش مصنوعی (۱ 🍬)", "callback_data": "gpt"}],
                [{"text": "🎁 جایزه روزانه (+۱۰ 🍬)", "callback_data": "daily"}],
                [{"text": "🎒 موجودی شکلات", "callback_data": "balance"}]
            ]
        }
    
    def back_keyboard(self):
        return {
            "inline_keyboard": [
                [{"text": "⏪ برگشت", "callback_data": "back"}]
            ]
        }
    
    def ask_ai(self, prompt):
        url = "https://chat.deepseek.com/api/v0/chat/completions"
        data = json.dumps({
            "messages": [
                {"role": "system", "content": "تو یک دستیار مفید به نام مارادو هستی. مختصر و مفید به فارسی جواب بده."},
                {"role": "user", "content": prompt}
            ],
            "model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 800
        }).encode('utf-8')
        
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, data=data, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as r:
                result = json.loads(r.read().decode('utf-8'))
                return result["choices"][0]["message"]["content"]
        except:
            return None
    
    def process_update(self, update):
        # پیام متنی
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            uid = msg["from"]["id"]
            user = self.get_user(uid)
            
            # دستور /start
            if msg.get("text") == "/start":
                welcome = """🍫 سلام! به ربات مارادو خوش آمدید!

مارادو عاشق شکلات است 🍬❤️

از دکمه‌های زیر انتخاب کن 👇"""
                self.send_message(chat_id, welcome, self.main_menu_keyboard())
                return
            
            # پیام کاربر
            text = msg.get("text", "")
            
            if user["mode"] == "gpt" and text:
                self.send_message(chat_id, "🤔 **در حال فکر کردن...**")
                
                user["chocolates"] -= 1
                user["mode"] = None
                self.save_users()
                
                answer = self.ask_ai(text)
                
                if answer:
                    self.send_message(
                        chat_id,
                        f"🧠 **پاسخ:**\n\n{answer}\n\n━━━━━━━━\n🍬 موجودی: {user['chocolates']}",
                        self.main_menu_keyboard()
                    )
                else:
                    user["chocolates"] += 1
                    self.save_users()
                    self.send_message(chat_id, "❌ خطا! دوباره تلاش کن", self.main_menu_keyboard())
            else:
                self.send_message(chat_id, "👇 لطفاً از دکمه‌ها استفاده کن:", self.main_menu_keyboard())
        
        # دکمه‌ها
        elif "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            chat_id = cb["message"]["chat"]["id"]
            msg_id = cb["message"]["message_id"]
            uid = cb["from"]["id"]
            data = cb["data"]
            user = self.get_user(uid)
            
            self.answer_callback(cb_id)
            
            if data == "back":
                user["mode"] = None
                self.save_users()
                self.edit_message(chat_id, msg_id, "🏠 منوی اصلی:", self.main_menu_keyboard())
            
            elif data == "gpt":
                if user["chocolates"] < 1:
                    self.edit_message(
                        chat_id, msg_id,
                        f"❌ شکلات کافی نداری!\nموجودی: {user['chocolates']} 🍬",
                        self.main_menu_keyboard()
                    )
                    return
                
                user["mode"] = "gpt"
                self.save_users()
                self.edit_message(
                    chat_id, msg_id,
                    "✅ **حالت چت فعال شد**\n\nسوالت رو بپرس 🧠",
                    self.back_keyboard()
                )
            
            elif data == "daily":
                if self.can_claim(uid):
                    user["chocolates"] += 10
                    user["last_daily"] = datetime.now().isoformat()
                    self.save_users()
                    self.edit_message(
                        chat_id, msg_id,
                        "🎁 **+10 🍬 به کیف تو اضافه شد!**",
                        self.main_menu_keyboard()
                    )
                else:
                    self.edit_message(
                        chat_id, msg_id,
                        "😅 **قبلاً جایزه امروز رو گرفتی!**",
                        self.main_menu_keyboard()
                    )
            
            elif data == "balance":
                self.edit_message(
                    chat_id, msg_id,
                    f"🎒 **موجودی: {user['chocolates']} 🍬**",
                    self.main_menu_keyboard()
                )
    
    def run(self):
        print("🍫 ربات مارادو آماده‌س!")
        
        while True:
            try:
                result = self.api_call("getUpdates", {"offset": self.offset, "timeout": 30})
                
                if result and result.get("ok") and result.get("result"):
                    for update in result["result"]:
                        self.offset = update["update_id"] + 1
                        self.process_update(update)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    bot = MaradoBot(BOT_TOKEN)
    bot.run()