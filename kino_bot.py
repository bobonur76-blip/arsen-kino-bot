import telebot
import sqlite3

# ========== SOZLAMALAR ==========

import os
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8402829174  # Keyin o'z Telegram ID raqamingizni yozasiz

DB = "kinolar.db"

bot = telebot.TeleBot(TOKEN)

# Har bir admin amali uchun vaqtinchalik holat
holat = {}


# ========== MA'LUMOTLAR BAZASI ==========

def db_och():
    return sqlite3.connect(DB)


def db_yarat():
    with db_och() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS kinolar (
                kod TEXT PRIMARY KEY,
                nom TEXT NOT NULL,
                file_id TEXT NOT NULL
            )
        """)


db_yarat()


# ========== YORDAMCHI FUNKSIYALAR ==========

def adminmi(message):
    return (
        ADMIN_ID != 0
        and message.from_user.id == ADMIN_ID
    )


def admin_tekshir(message):
    if not adminmi(message):
        bot.send_message(
            message.chat.id,
            "⛔ Bu buyruq faqat admin uchun."
        )
        return False
    return True


def menyu(message):
    matn = (
        "🎬 ARSEN_HD KINO BOT\n\n"
        "🔢 Kino kodini yuboring — video olasiz.\n"
        "🔎 Kino nomini yozing — qidiruv ishlaydi.\n\n"
        "Buyruqlar:\n"
        "/start — bosh menyu\n"
        "/search — qidirish\n"
        "/myid — Telegram ID\n"
        "/cancel — amalni bekor qilish"
    )

    if adminmi(message):
        matn += (
            "\n\n🔐 ADMIN BUYRUQLARI:\n"
            "/add — kino qo‘shish\n"
            "/list — kinolar ro‘yxati\n"
            "/delete — kino o‘chirish"
        )

    bot.send_message(message.chat.id, matn)


# ========== START VA ID ==========

@bot.message_handler(commands=["start"])
def start(message):
    menyu(message)


@bot.message_handler(commands=["myid"])
def myid(message):
    bot.send_message(
        message.chat.id,
        f"Telegram ID raqamingiz:\n{message.from_user.id}"
    )


@bot.message_handler(commands=["cancel"])
def cancel(message):
    holat.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ Amal bekor qilindi.")


# ========== KINO QO'SHISH ==========

@bot.message_handler(commands=["add"])
def add_start(message):
    if not admin_tekshir(message):
        return

    holat[message.from_user.id] = {
        "amal": "add",
        "qadam": "nom"
    }

    bot.send_message(
        message.chat.id,
        "➕ YANGI KINO QO‘SHISH\n\n"
        "Kino kodini va nomini yuboring.\n\n"
        "Masalan:\n"
        "23 | Oshiqman senga\n\n"
        "Keyin bot videoni so‘raydi.\n"
        "Bekor qilish: /cancel"
    )


# ========== KINO O'CHIRISH ==========

@bot.message_handler(commands=["delete"])
def delete_start(message):
    if not admin_tekshir(message):
        return

    holat[message.from_user.id] = {
        "amal": "delete",
        "qadam": "kod"
    }

    bot.send_message(
        message.chat.id,
        "🗑 O‘chirmoqchi bo‘lgan kino kodini yuboring.\n"
        "Bekor qilish: /cancel"
    )


# ========== KINOLAR RO'YXATI ==========

@bot.message_handler(commands=["list"])
def list_movies(message):
    if not admin_tekshir(message):
        return

    with db_och() as con:
        rows = con.execute(
            "SELECT kod, nom FROM kinolar ORDER BY kod"
        ).fetchall()

    if not rows:
        bot.send_message(message.chat.id, "Hozircha kino yo‘q.")
        return

    matn = "🎞 KINOLAR RO‘YXATI\n\n"

    for kod, nom in rows:
        matn += f"🔢 {kod} — {nom}\n"

    bot.send_message(message.chat.id, matn)


# ========== VIDEO QABUL QILISH ==========

@bot.message_handler(content_types=["video"])
def video_qabul(message):
    user_id = message.from_user.id
    hol = holat.get(user_id)

    if (
        adminmi(message)
        and hol
        and hol.get("amal") == "add"
        and hol.get("qadam") == "video"
    ):
        kod = hol["kod"]
        nom = hol["nom"]
        file_id = message.video.file_id

        try:
            with db_och() as con:
                con.execute(
                    """
                    INSERT OR REPLACE INTO kinolar
                    (kod, nom, file_id)
                    VALUES (?, ?, ?)
                    """,
                    (kod, nom, file_id)
                )

            holat.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "✅ KINO MUVAFFAQIYATLI SAQLANDI!\n\n"
                f"🎬 Nomi: {nom}\n"
                f"🔢 Kodi: {kod}\n\n"
                "Endi shu kodni yuborib videoni tekshirishingiz mumkin."
            )

        except Exception as e:
            print("Bazaga saqlash xatosi:", e)
            bot.send_message(
                message.chat.id,
                "❌ Kino bazaga saqlanmadi. Qayta urinib ko‘ring."
            )

    else:
        bot.send_message(
            message.chat.id,
            "Video qabul qilindi.\n"
            "Kino qo‘shish uchun admin /add buyrug‘ini ishlatsin."
        )


# ========== MATNLARNI QABUL QILISH ==========

@bot.message_handler(content_types=["text"])
def matn_qabul(message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Buyruqlarni boshqa matn sifatida qayta ishlamaymiz
    if text.startswith("/"):
        return

    hol = holat.get(user_id)

    # Admin yangi kino kodi va nomini yubordi
    if (
        adminmi(message)
        and hol
        and hol.get("amal") == "add"
        and hol.get("qadam") == "nom"
    ):
        if "|" not in text:
            bot.send_message(
                message.chat.id,
                "❗ Format noto‘g‘ri.\n\n"
                "Masalan: 23 | Kino nomi"
            )
            return

        kod, nom = [
            qism.strip()
            for qism in text.split("|", 1)
        ]

        if not kod or not nom:
            bot.send_message(
                message.chat.id,
                "Kod va kino nomini to‘liq kiriting."
            )
            return

        if len(kod) > 30 or len(nom) > 150:
            bot.send_message(
                message.chat.id,
                "Kod yoki nom juda uzun."
            )
            return

        holat[user_id] = {
            "amal": "add",
            "qadam": "video",
            "kod": kod,
            "nom": nom
        }

        bot.send_message(
            message.chat.id,
            f"🎬 Kino: {nom}\n"
            f"🔢 Kod: {kod}\n\n"
            "Endi shu kinoning videosini yuboring.\n"
            "Bekor qilish: /cancel"
        )
        return

    # Admin kino o'chirmoqda
    if (
        adminmi(message)
        and hol
        and hol.get("amal") == "delete"
        and hol.get("qadam") == "kod"
    ):
        kod = text

        with db_och() as con:
            cursor = con.execute(
                "DELETE FROM kinolar WHERE kod = ?",
                (kod,)
            )
            topildi = cursor.rowcount

        holat.pop(user_id, None)

        if topildi:
            bot.send_message(
                message.chat.id,
                f"✅ {kod} kodli kino o‘chirildi."
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Bunday kodli kino topilmadi."
            )
        return

    # Avval kod bo'yicha qidiramiz
    with db_och() as con:
        row = con.execute(
            "SELECT kod, nom, file_id FROM kinolar WHERE kod = ?",
            (text,)
        ).fetchone()

        if row:
            kod, nom, file_id = row

            try:
                bot.send_video(
                    message.chat.id,
                    file_id,
                    caption=f"🎬 {nom}\n🔢 Kod: {kod}"
                )
            except Exception as e:
                print("Video yuborish xatosi:", e)
                bot.send_message(
                    message.chat.id,
                    "❌ Video yuborilmadi. Admin tekshirishi kerak."
                )
            return

        # Kod topilmasa, nomidan qidiramiz
        rows = con.execute(
            """
            SELECT kod, nom
            FROM kinolar
            WHERE nom LIKE ?
            ORDER BY nom
            LIMIT 10
            """,
            (f"%{text}%",)
        ).fetchall()

    if rows:
        natija = "🔎 TOPILGAN KINOLAR:\n\n"

        for kod, nom in rows:
            natija += f"🎬 {nom}\n🔢 Kod: {kod}\n\n"

        natija += "Videoni olish uchun kodni yuboring."
        bot.send_message(message.chat.id, natija)
    else:
        bot.send_message(
            message.chat.id,
            "❌ Bunday kino mavjud emas.\n"
            "Kino kodi yoki nomini tekshiring."
        )


# ========== BOTNI ISHGA TUSHIRISH ==========

if __name__ == "__main__":
    print("Arsen_hd bot ishga tushdi!")
    bot.infinity_polling()
