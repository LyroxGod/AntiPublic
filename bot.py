import telebot
from telebot import types
import re
import os

BOT_TOKEN = "8573458017:AAHcLdylGaCBhx6adI1IknIjxdyZijVw9zU"

bot = telebot.TeleBot(BOT_TOKEN)

# Luhn kontrolü
def is_valid_card(cc):
    cc = re.sub(r'\D', '', str(cc))
    if not cc.isdigit() or len(cc) < 13:
        return False
    digits = [int(d) for d in cc]
    total = sum(digits[::-2]) + sum(sum(divmod(d*2, 10)) for d in digits[-2::-2])
    return total % 10 == 0

# Satır parse (CC|MM|YY|CVV veya benzer formatlar)
def parse_line(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    parts = re.split(r'[\|\s,;]+', line)
    if len(parts) >= 1:
        cc = re.sub(r'\D', '', parts[0])
        if len(cc) >= 13:
            mm = parts[1] if len(parts) > 1 else ""
            yy = parts[2] if len(parts) > 2 else ""
            cvv = parts[3] if len(parts) > 3 else ""
            return f"{cc}|{mm}|{yy}|{cvv}".rstrip("|")
    return None

# Ana menü
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🔍 Check", "🗑 Clean")
    markup.add("⭐ Filters", "⚡ BIN manipulations")
    markup.add("💡 Info")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
                     "Welcome to CC friendly sorter! ❤️\n\n"
                     "Kart dump'larını gönder, ayrıştırayım.", 
                     reply_markup=main_menu())

# ===================== CLEAN =====================
@bot.message_handler(func=lambda m: m.text == "🗑 Clean")
def clean_start(message):
    bot.send_message(message.chat.id, "Dump.txt dosyasını gönder (veya kartları tek mesajda yapıştır).")

# ===================== CHECK =====================
@bot.message_handler(func=lambda m: m.text == "🔍 Check")
def check_start(message):
    bot.send_message(message.chat.id, "Check için dump.txt dosyasını veya kart listesini gönder.")

# ===================== FILTERS =====================
@bot.message_handler(func=lambda m: m.text == "⭐ Filters")
def filters_start(message):
    bot.send_message(message.chat.id, "Filters için önce dump.txt gönder. Sonra filtreleri uygula.\nŞu an basit Brand/Type filtresi var.")

# Dosya işleme (hem Check hem Clean için)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not message.document.file_name.lower().endswith('.txt'):
        bot.send_message(message.chat.id, "Sadece .txt dosyası kabul ediyorum!")
        return

    bot.send_message(message.chat.id, "Dosya işleniyor... ⏳")

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    lines = downloaded.decode('utf-8', errors='ignore').splitlines()

    private = []   # Luhn geçen
    public = []    # Luhn geçmeyen

    for line in lines:
        parsed = parse_line(line)
        if parsed:
            cc = parsed.split('|')[0]
            if is_valid_card(cc):
                private.append(parsed)
            else:
                public.append(parsed)

    total = len(private) + len(public)
    if total == 0:
        bot.send_message(message.chat.id, "Hiç kart bulunamadı.")
        return

    private_percent = (len(private) / total * 100) if total > 0 else 0

    # ===================== CHECK SONUCU =====================
    if message.reply_to_message and "Check" in str(message.reply_to_message.text) or "check" in message.text.lower():
        result_text = f"✅ Check results:\n" \
                      f"Total cards: {total}\n" \
                      f"Private: {len(private)}. Public: {len(public)}\n" \
                      f"Private percentage: {private_percent:.2f}%"

        bot.send_message(message.chat.id, result_text)

        # private.txt
        if private:
            with open("private.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(private))
            with open("private.txt", "rb") as f:
                bot.send_document(message.chat.id, f, caption="private.txt", visible_file_name=f"[@{bot.get_me().username}] private.txt")

        # public.txt
        if public:
            with open("public.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(public))
            with open("public.txt", "rb") as f:
                bot.send_document(message.chat.id, f, caption="public.txt", visible_file_name=f"[@{bot.get_me().username}] public.txt")

        os.remove("private.txt") if os.path.exists("private.txt") else None
        os.remove("public.txt") if os.path.exists("public.txt") else None
        return

    # ===================== CLEAN =====================
    if message.reply_to_message and "Clean" in str(message.reply_to_message.text) or "clean" in message.text.lower():
        if private:
            with open("clean.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(private))
            with open("clean.txt", "rb") as f:
                bot.send_document(message.chat.id, f,
                                  caption=f"Your cards have been cleaned! 😂\nTemizlenen: {len(private)}",
                                  visible_file_name=f"[@{bot.get_me().username}] clean ({len(private)}).txt")
            os.remove("clean.txt")
        else:
            bot.send_message(message.chat.id, "Temizlenecek geçerli kart yok.")
        return

    # Varsayılan: Sadece private gönder (eski Clean davranışı)
    if private:
        with open("clean.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(private))
        with open("clean.txt", "rb") as f:
            bot.send_document(message.chat.id, f,
                              caption=f"Your cards have been cleaned! 😂\nTemizlenen: {len(private)}",
                              visible_file_name=f"[@{bot.get_me().username}] clean ({len(private)}).txt")
        os.remove("clean.txt")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip()
    if text in ["🔍 Check", "🗑 Clean", "⭐ Filters", "⚡ BIN manipulations", "💡 Info"]:
        bot.send_message(message.chat.id, "Dosya veya kart listesini göndererek devam et.")
        return

    # Tek mesajda kart varsa işle (Check veya Clean gibi davran)
    lines = text.splitlines()
    private = [parse_line(l) for l in lines if parse_line(l) and is_valid_card(parse_line(l).split('|')[0])]
    private = [p for p in private if p]

    if private:
        with open("temp_clean.txt", "w") as f:
            f.write("\n".join(private))
        with open("temp_clean.txt", "rb") as f:
            bot.send_document(message.chat.id, f, caption="Processed!")
        os.remove("temp_clean.txt")

print("Friendly Sorter Bot çalışıyor...")
bot.infinity_polling()
