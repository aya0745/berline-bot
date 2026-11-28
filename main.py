import os
import asyncio
import re
import unicodedata
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChatForwardsRestrictedError
from telethon.tl.functions.messages import ForwardMessagesRequest
from supabase import create_client, Client
import uvicorn

load_dotenv()

# ==========================================
# 1. KONFIGURASI API & KLIEN (4 AKUN)
# ==========================================
API_ID = int(os.environ.get("API_ID", 36156436))
API_HASH = os.environ.get("API_HASH", "e2a8a08504aa88c37f7c941080d6a180")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ID_GRUP_UTAMA = -1003903118196

# ID TOPIK BERLINE
ID_TOPIK_BERLINE_JOCKEY = 74
ID_TOPIK_BERLINE_ANOTHER = 75

client_amel = TelegramClient("sesi_amel", API_ID, API_HASH)
client_berline = TelegramClient("sesi_berline", API_ID, API_HASH)

clients_eksekutor = {
    "Jourd": TelegramClient("sesi_jourd", API_ID, API_HASH),
    "Ejeh": TelegramClient("sesi_ejeh", API_ID, API_HASH),
}

ID_AMEL = None
ID_BERLINE = None
PEER_MARKAS_AMEL = None
BACKGROUND_TASKS = []

# ==========================================
# 2. DATABASE SUPABASE & DEFAULT STATE
# ==========================================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

STATUS_EKSEKUTOR = {
    "Jourd": {"nama": "Jourd", "aktif": True, "jalur": "semua"},
    "Ejeh": {"nama": "Ejeh", "aktif": True, "jalur": "semua"},
}

TEMPLATE_EKSEKUTOR = {
    "1": "HIT @Berrline As Seller ★ start 3-20k! Do check @ELGALERIES for more 📂🩷 Avail rush and revisi ⓘ Check @Elgatesult for testi & result.",
    "edit": "HIT @Berrline As Seller ꩜ ࣪ Editing start from 15-20k 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result @elgaresult & testi @elgatesti. ♡",
    "vid": "HIT @Berrline As Seller ꩜ ࣪ Edit vid start from 12-20k/menit 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "kti": "HIT @Berrline As Seller ꩜ ࣪ Start from 15-18k/hal. bisa rush, revisi, jaminan NO AI, dan handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "parafrase": "HIT @Berrline As Seller ꩜ ࣪ Turnitin 15k/cek, AI 6k/cek, parafrase 12k/hal & 7k/℅. avrush dan di handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "formatting": "HIT @Berrline As Seller ꩜ ࣪ Formatting start 2k/hal, dafis, dafpus, tabel dan gambar start 10k. avail for rush dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "teks": "HIT @Berrline As Seller ꩜ ࣪ Pantun, puisi, cerpen, surat dan lainnya start 10k- 20k/hal. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "cv": "HIT @Berrline As Seller ꩜ ࣪ Visi misi start 3-5k/point, CV start from 15-25k, kebutuhan organisasi start 15k. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "data": "HIT @Berrline As Seller ꩜ ࣪ Olah data start 25-50k, avail tugas akuntansi lainnya, di handle lulusan akuntansi. bisa rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "it": "HIT @Berrline As Seller ꩜ ࣪ Coding start 20k, web start 100k, scratch start 50k, UI/UX start 70k, avail tugas IT lainnya start 15k. Handle by mahasiswi Teknik Informatika 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "jastik": "HIT @Berrline As Seller ꩜ ࣪ jasa ketik word & excel start 3-5k/halaman. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡",
    "jurnal": "HIT @Berrline As Seller ꩜ ࣪ Unlock/download jurnal nasional start 5-8k, jurnal inter start 10-15k, review jurnal start 25k 💕 avail rush, revisi, dan NO AI. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "ppt": "HIT @Berrline As Seller ꩜ ࣪ PPT start 3k materi dari seller, materi dari buyyer 4k, +1,5k with design. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡"
}

WORDING_BERLINE = {
    "a": "HMU @Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕",
    "b": "HMU @.Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕"
}

SEMUA_KEYWORDS = [
    "makalah", "jasa makalah", "joki makalah", "tugas makalah",
    "joki coding", "coding", "ngoding", "website", "bug fixing", "database", "app android", "aplikasi", "joki web", "landing page", "joki app", "joki program", "program python", "program java", "program c++", "sistem informasi", "joki si", "machine learning", "joki ml", "joki database", "joki excel vba", "bug", "debug", "error coding", "joki tugas coding", "script python", "aplikasi skripsi", "sistem pakar", "joki uas coding", "framework laravel", "framework react", "joki html css",
    "cv ats", "cv kreatif", "visi misi", "organisasi", "portofolio", "cover letter", "surat lamaran", "ad/art organisasi",
    "infografis", "poster", "banner", "mindmap", "mind mapping", "famplet", "logo", "logo kelas", "logo 2d", "logo 3d", "jasa edit", "edit logo", "ui/ux", "edit video", "edit vid", "video animasi", "animasi ai", "edit feeds ig", "cover buku", "cover proposal", "presentasi", "ppt", "sertifikat", "undangan", "thumbnail", "desain grafis", "feeds instagram", "konten ig", "konten sosmed", "id card", "x banner", "roll banner", "brosur", "kartu nama", "mockup", "vector", "edit foto", "retouch foto", "motion graphic", "intro video", "reels editing", "tiktok editing", "desain feed", "konten canva", "template canva", "video promosi", "video profile", "wedding invitation", "undangan digital",
    "spss", "olah data", "kimia", "biologi", "fisika", "akuntansi", "matematika", "mtk", "statistik", "olah data excel", "minitab", "ekonometrika", "joki matkul", "r studio", "spss anova", "uji spss", "uji validitas", "uji reliabilitas", "regresi", "sample data", "uji normalitas", "uji t", "path analysis", "sem", "amos", "lisrel", "joki tugas statistik", "joki tugas mtk",
    "formatting", "revisi makalah", "revisi proposal", "daftar isi", "daftar pustaka", "nomor halaman", "no halaman", "parafrase", "turnitin", "ai detector", "mendeley", "cek plagiarisme", "similarity", "convert pdf ke word", "convert word ke pdf", "layout", "rapihin dokumen", "edit margin", "spasi", "kutipan", "sitasi", "citation", "referensi", "bibliography", "cek similarity", "cek turnitin", "styling word", "template skripsi", "template proposal",
    "jasa ketik", "jastik", "jasa tulis", "jastul", "resume", "resume materi", "transkrip", "transkrip wawancara", "translate", "terjemahan", "jasa ketik cepat", "ketik ulang", "input data", "entry data", "ketik dokumen", "salin tulisan", "tulis ulang",
    "cerpen", "puisi", "naskah drama", "ebook", "novel", "skenario", "lirik lagu", "caption", "copywriting", "cerita pendek", "flash fiction", "monolog", "storytelling",
    "resume jurnal", "tugas akhir", "essai", "essay", "artikel", "laporan", "joki artikel", "joki laporan", "proposal", "joki proposal", "skripsi", "joki skripsi", "revisi skripsi", "bab 1-5", "bab 1", "bab 2", "bab 3", "bab 4", "bab 5", "sidang skripsi", "laprak", "laporan praktikum", "studi kasus", "literature review", "review jurnal", "cari jurnal", "pkm", "jurnal internasional", "tesis", "disertasi", "revisi tesis", "kuisioner", "kuesioner", "survey", "pengolahan data skripsi", "jurnal sinta", "artikel ilmiah", "outline skripsi", "judul skripsi", "metodologi penelitian", "bab pembahasan", "jurnal scopus", "abstrak", "latar belakang", "laporan pkl", "pkl", "laporan pkm",
    "joktug", "joki tugas", "bimbel", "tugas kuliah", "joki quiz", "joki ujian", "joki uas", "joki uts", "rangkuman", "ringkasan materi", "joki absen", "joki kelas online", "joki praktikum", "kkn", "laporan kkn", "laporan magang", "joki magang", "joki hafalan", "joki presentasi", "resume buku", "joki resume", "tuton", "laporan pkl rush"
]

def load_database():
    global STATUS_EKSEKUTOR, TEMPLATE_EKSEKUTOR, WORDING_BERLINE, SEMUA_KEYWORDS
    if not supabase:
        return
    try:
        response = supabase.table("berline_settings").select("data").eq("id", 1).execute()
        if response.data and response.data[0].get("data"):
            data = response.data[0]["data"]
            for k, v in data.get("STATUS_EKSEKUTOR", {}).items():
                if k in STATUS_EKSEKUTOR:
                    STATUS_EKSEKUTOR[k].update(v)

            for k, v in data.get("TEMPLATE_EKSEKUTOR", {}).items():
                if k in TEMPLATE_EKSEKUTOR:
                    TEMPLATE_EKSEKUTOR[k] = v

            for k, v in data.get("WORDING_BERLINE", {}).items():
                if k in WORDING_BERLINE:
                    WORDING_BERLINE[k] = v

            db_kws = data.get("SEMUA_KEYWORDS")
            if db_kws and isinstance(db_kws, list):
                SEMUA_KEYWORDS = [k.strip() for k in db_kws if k.strip() and k.strip().lower() not in ("si", "ta")]
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal memuat Supabase: {e}")

def save_database():
    if not supabase:
        return
    data = {
        "STATUS_EKSEKUTOR": STATUS_EKSEKUTOR,
        "TEMPLATE_EKSEKUTOR": TEMPLATE_EKSEKUTOR,
        "WORDING_BERLINE": WORDING_BERLINE,
        "SEMUA_KEYWORDS": SEMUA_KEYWORDS
    }
    try:
        supabase.table("berline_settings").upsert({"id": 1, "data": data}).execute()
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal menyimpan ke Supabase: {e}")

load_database()

# ==========================================
# 3. ROUTE MAP & STRICT REGEX FILTER
# ==========================================
ID_JOCKEYFESS = -1002233967429
ID_MONEYFESS = -1001274048263

BASE_JOCKEY_MONEY_IDS = [ID_JOCKEYFESS, ID_MONEYFESS]
BASE_REGULER_IDS = [
    -1001611324665, -1001525948158, -1001303979309,
    -1001260932905, -1003058482095, -1001202510480
]
SEMUA_BASE_IDS = BASE_JOCKEY_MONEY_IDS + BASE_REGULER_IDS

def build_regex(keywords):
    bersih = sorted(set(k.strip() for k in keywords if k.strip()), key=len, reverse=True)
    if not bersih:
        return None
    patterns = [r'(?<!\w)' + re.escape(kw) + r'(?!\w)' for kw in bersih]
    return re.compile('|'.join(patterns), re.IGNORECASE)

REGEX_KEYWORDS = build_regex(SEMUA_KEYWORDS)

def normalisasi_teks(teks: str) -> str:
    return unicodedata.normalize('NFKC', teks) if teks else ""

# ==========================================
# 4. LOGGING TERMINAL SYSTEM
# ==========================================
MENFESS_LOGS = []
NAMA_BASE_MAP = {
    ID_JOCKEYFESS: "Jockeyfess",
    ID_MONEYFESS: "Moneyfess",
    -1001611324665: "Base WIB",
    -1001525948158: "Base WTB",
    -1001303979309: "Berdagang Online",
    -1001260932905: "Dagangfess",
    -1003058482095: "Base Lelang",
    -1001202510480: "Swalayan",
}

def simpan_log(chat_id, teks, cocok_kw):
    waktu = datetime.now().strftime("%H:%M:%S")
    nama_base = NAMA_BASE_MAP.get(chat_id, "Base Lainnya")
    teks_tampil = teks if teks else "[Media/Gambar tanpa teks]"
    snippet = (teks_tampil[:80] + '...') if len(teks_tampil) > 80 else teks_tampil
    snippet = snippet.replace('\n', ' ')
    MENFESS_LOGS.insert(0, f"[{waktu}] 📥 {nama_base} (KW: {cocok_kw}) -> {snippet}")
    if len(MENFESS_LOGS) > 100:
        MENFESS_LOGS.pop()

# ==========================================
# 5. HANDLER AMEL (PEMANTAU CHAT MASUK)
# ==========================================
SUDAH_DIPROSES = set()

async def proses_pesan(msg, chat_id):
    global PEER_MARKAS_AMEL
    key = (chat_id, msg.id)
    if key in SUDAH_DIPROSES:
        return
    SUDAH_DIPROSES.add(key)
    if len(SUDAH_DIPROSES) > 5000:
        SUDAH_DIPROSES.clear()

    teks_bersih = normalisasi_teks(msg.raw_text or "")

    # Jockeyfess lolos semua tanpa filter
    if chat_id == ID_JOCKEYFESS:
        cocok_kw = "ALL (Jockeyfess)"
        target_berline = ID_TOPIK_BERLINE_JOCKEY
    else:
        if not teks_bersih or not REGEX_KEYWORDS:
            return
        match = REGEX_KEYWORDS.search(teks_bersih)
        if not match:
            return
        cocok_kw = match.group(0)
        target_berline = ID_TOPIK_BERLINE_JOCKEY if chat_id == ID_MONEYFESS else ID_TOPIK_BERLINE_ANOTHER

    try:
        if not PEER_MARKAS_AMEL:
            PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)

        from_peer = await msg.get_input_chat()
        await client_amel(ForwardMessagesRequest(
            from_peer=from_peer,
            id=[msg.id],
            to_peer=PEER_MARKAS_AMEL,
            top_msg_id=target_berline
        ))

        simpan_log(chat_id, teks_bersih, cocok_kw)
        print(f"⚡ [FORWARD] Base {chat_id} | KW: {cocok_kw}")
    except ChatForwardsRestrictedError:
        pass
    except Exception as e:
        print(f"🚨 [ERROR FORWARD] {e}")

def register_amel_handlers(client):
    @client.on(events.NewMessage(chats=SEMUA_BASE_IDS))
    async def saring_menfess_instan(event):
        asyncio.create_task(proses_pesan(event.message, event.chat_id))

async def poll_fallback():
    last_id = {}
    for cid in SEMUA_BASE_IDS:
        try:
            m = await client_amel.get_messages(cid, limit=1)
            last_id[cid] = m[0].id if m else 0
        except Exception:
            last_id[cid] = 0

    while True:
        await asyncio.sleep(5)
        if not client_amel.is_connected():
            continue
        for cid in SEMUA_BASE_IDS:
            try:
                async for m in client_amel.iter_messages(cid, min_id=last_id[cid], reverse=True):
                    last_id[cid] = max(last_id[cid], m.id)
                    asyncio.create_task(proses_pesan(m, cid))
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception:
                pass

# ==========================================
# 6. SISTEM KONTROL BERLINE & EKSEKUTOR (JOURD & EJEH)
# ==========================================
queue_pesan = asyncio.Queue()
RIWAYAT_KOMENTAR = {}  # {id_pesan_markas: (chat_id_diskusi, msg_id_komentar, jalur)}

def simpan_riwayat(id_markas, chat_diskusi, msg_komentar, jalur):
    RIWAYAT_KOMENTAR[id_markas] = (chat_diskusi, msg_komentar, jalur)
    if len(RIWAYAT_KOMENTAR) > 2000:
        RIWAYAT_KOMENTAR.pop(next(iter(RIWAYAT_KOMENTAR)))

def format_daftar_nama(daftar_nama):
    if not daftar_nama:
        return ""
    if len(daftar_nama) == 1:
        return daftar_nama[0]
    if len(daftar_nama) == 2:
        return f"{daftar_nama[0]} dan {daftar_nama[1]}"
    return ", ".join(daftar_nama[:-1]) + f", dan {daftar_nama[-1]}"

def register_berline_handlers(client_manager, my_id):
    @client_manager.on(events.NewMessage(chats=ID_GRUP_UTAMA))
    async def tangkap_command(event):
        if not event.is_reply:
            return

        sender = await event.get_sender()
        if not sender or sender.id != my_id:
            return

        reply_msg = await event.get_reply_message()
        if not reply_msg:
            return

        input_teks = event.raw_text.strip()
        cmd_lower = input_teks.lower()

        # KASUS 1: Reply ke pesan ✅ (balas langsung ke komentar sebelumnya di comment section)
        if reply_msg.id in RIWAYAT_KOMENTAR:
            chat_diskusi, msg_komentar, jalur = RIWAYAT_KOMENTAR[reply_msg.id]

            if cmd_lower in TEMPLATE_EKSEKUTOR:
                await queue_pesan.put({
                    "event": event,
                    "chat_asal": chat_diskusi,
                    "msg_asal": msg_komentar,
                    "cmd": cmd_lower,
                    "jalur": jalur,
                    "is_reply_komentar": True
                })
                return

            try:
                teks_kirim = WORDING_BERLINE.get(cmd_lower, input_teks)
                sent = await client_manager.send_message(
                    entity=chat_diskusi,
                    message=teks_kirim,
                    reply_to=msg_komentar
                )
                simpan_riwayat(event.id, sent.chat_id, sent.id, jalur)
                await event.edit("✅ Berhasil membalas komentar sebelumnya di Base!")
            except FloodWaitError as e:
                await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
            except Exception as e:
                await event.edit(f"❌ Gagal reply komentar: {e}")
            return

        # KASUS 2: Reply langsung ke pesan forward menfess dari Amel
        if not reply_msg.forward:
            return

        forward_from = reply_msg.forward
        if not forward_from.chat_id or not forward_from.channel_post:
            return

        asal_thread = reply_msg.reply_to_msg_id if reply_msg.reply_to_msg_id else 0
        jalur = "jockey_money" if asal_thread == ID_TOPIK_BERLINE_JOCKEY else "reguler"

        if cmd_lower in TEMPLATE_EKSEKUTOR:
            await queue_pesan.put({
                "event": event,
                "chat_asal": forward_from.chat_id,
                "msg_asal": forward_from.channel_post,
                "cmd": cmd_lower,
                "jalur": jalur,
                "is_reply_komentar": False
            })
            return

        try:
            teks_kirim = WORDING_BERLINE.get(cmd_lower, input_teks)
            sent = await client_manager.send_message(
                entity=forward_from.chat_id,
                message=teks_kirim,
                comment_to=forward_from.channel_post
            )
            simpan_riwayat(event.id, sent.chat_id, sent.id, jalur)
            await event.edit("✅ Berhasil mengirim komentar mandiri ke Base!")
        except FloodWaitError as e:
            await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
        except Exception as e:
            await event.edit(f"❌ Gagal: {e}")

async def worker_eksekutor():
    while True:
        task = await queue_pesan.get()
        event_mgr = task["event"]

        try:
            chat_asal = task["chat_asal"]
            msg_asal = task["msg_asal"]
            is_reply_komentar = task["is_reply_komentar"]

            akun_bertugas = [
                nama for nama, info in STATUS_EKSEKUTOR.items()
                if info["aktif"] and (info["jalur"] == task["jalur"] or info["jalur"] == "semua")
                and clients_eksekutor[nama].is_connected()
            ]

            if not akun_bertugas:
                await event_mgr.edit("❌ Tidak ada eksekutor (Jourd/Ejeh) yang aktif/terhubung.")
                continue

            async def kirim_pesan_eksekutor(nama_akun):
                try:
                    teks_final = TEMPLATE_EKSEKUTOR[task["cmd"]]
                    if task["jalur"] == "jockey_money":
                        teks_final = teks_final.replace("@Berrline", "@.Berrline")

                    if is_reply_komentar:
                        sent = await clients_eksekutor[nama_akun].send_message(
                            entity=chat_asal,
                            message=teks_final,
                            reply_to=msg_asal
                        )
                    else:
                        sent = await clients_eksekutor[nama_akun].send_message(
                            entity=chat_asal,
                            message=teks_final,
                            comment_to=msg_asal
                        )
                    return (True, STATUS_EKSEKUTOR[nama_akun]["nama"], sent.chat_id, sent.id)
                except FloodWaitError as e:
                    STATUS_EKSEKUTOR[nama_akun]["aktif"] = False
                    asyncio.get_event_loop().run_in_executor(None, save_database)
                    return (False, f"{STATUS_EKSEKUTOR[nama_akun]['nama']} floodwait {e.seconds}s.", None, None)
                except Exception as e:
                    print(f"🚨 [EKSEKUTOR ERROR - {nama_akun}] {e}")
                    return (False, None, None, None)

            results = await asyncio.gather(*(kirim_pesan_eksekutor(nama) for nama in akun_bertugas))
            berhasil = [res for res in results if res[0]]
            laporan_floodwait = [res[1] for res in results if not res[0] and res[1]]

            if berhasil:
                simpan_riwayat(event_mgr.id, berhasil[0][2], berhasil[0][3], task["jalur"])
                nama_berhasil = [res[1] for res in berhasil]
                baris_laporan = [f"✅ Terkirim oleh {format_daftar_nama(nama_berhasil)}."]
            else:
                baris_laporan = ["❌ Gagal terkirim."]

            if laporan_floodwait:
                baris_laporan.extend(laporan_floodwait)

            await event_mgr.edit("\n".join(baris_laporan))
        except Exception as e:
            await event_mgr.edit(f"❌ Error: {e}")
        finally:
            queue_pesan.task_done()

# ==========================================
# 7. FITUR NOTIFIKASI KESIAPAN
# ==========================================
async def kirim_notifikasi_kesiapan():
    topik_berline = [ID_TOPIK_BERLINE_JOCKEY, ID_TOPIK_BERLINE_ANOTHER]

    if client_amel.is_connected():
        for tid in topik_berline:
            try:
                await client_amel.send_message(ID_GRUP_UTAMA, f"👁️ [RADAR AMEL] Aktif memantau {len(SEMUA_BASE_IDS)} Channel.", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

    if client_berline.is_connected():
        for tid in topik_berline:
            try:
                await client_berline.send_message(ID_GRUP_UTAMA, "👑 [SISTEM] Berline siap!", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

    for nama_eks, client_eks in clients_eksekutor.items():
        if not client_eks.is_connected():
            continue
        info = STATUS_EKSEKUTOR[nama_eks]
        for tid in topik_berline:
            try:
                await client_eks.send_message(ID_GRUP_UTAMA, f"🤖 [{info['nama']}] siap!", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

# ==========================================
# 8. STARTUP TERISOLASI (LIFESPAN)
# ==========================================
async def konek_aman(client, nama):
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ [{nama}] Sesi mati / belum login! Buat ulang file .session-nya.")
            await client.disconnect()
            return None
        me = await client.get_me()
        print(f"✅ [{nama}] Berhasil Terhubung! (ID: {me.id} | Nama: {me.first_name})")
        return me
    except Exception as e:
        print(f"❌ [{nama}] Gagal terhubung: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ID_AMEL, ID_BERLINE, PEER_MARKAS_AMEL

    print("\n⏳ Menghubungkan akun Amel...")
    me_amel = await konek_aman(client_amel, "Amel")
    if me_amel:
        ID_AMEL = me_amel.id
        await client_amel.get_dialogs(limit=50)
        PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)
        register_amel_handlers(client_amel)

    print("⏳ Menghubungkan akun Berline...")
    me_berline = await konek_aman(client_berline, "Berline")
    if me_berline:
        ID_BERLINE = me_berline.id
        register_berline_handlers(client_berline, ID_BERLINE)

    for nama, client_eks in clients_eksekutor.items():
        print(f"⏳ Menghubungkan eksekutor: {nama}...")
        me_eks = await konek_aman(client_eks, nama)
        if me_eks:
            STATUS_EKSEKUTOR[nama]["nama"] = me_eks.first_name or me_eks.username or nama
        else:
            STATUS_EKSEKUTOR[nama]["aktif"] = False

    save_database()

    BACKGROUND_TASKS.append(asyncio.create_task(kirim_notifikasi_kesiapan()))
    BACKGROUND_TASKS.append(asyncio.create_task(worker_eksekutor()))
    if me_amel:
        BACKGROUND_TASKS.append(asyncio.create_task(poll_fallback()))

    print("\n🚀 Markas Utama (Amel, Berline, Jourd, Ejeh) Siap Tempur!\n")
    yield

    for task in BACKGROUND_TASKS:
        task.cancel()
    await asyncio.gather(
        client_amel.disconnect(),
        client_berline.disconnect(),
        *(c.disconnect() for c in clients_eksekutor.values()),
        return_exceptions=True
    )

# ==========================================
# 9. PORTAL DASHBOARD API
# ==========================================
app = FastAPI(lifespan=lifespan)

class ToggleModel(BaseModel):
    nama: str
    aktif: bool
    jalur: str

class WordingModel(BaseModel):
    tipe: str
    kode: str
    teks: str

class KeywordModel(BaseModel):
    keywords: str

def buat_kartu_eksekutor():
    html = ""
    for nama, info in STATUS_EKSEKUTOR.items():
        bg_color = "#16a34a" if info["aktif"] else "#dc2626"
        teks_onoff = "ON" if info["aktif"] else "OFF"
        html += f"""
        <div class="card">
            <div class="row">
                <strong>{info["nama"]} ({nama})</strong>
                <button id="btn-onoff-{nama}" onclick="toggleOnOff('{nama}')"
                        style="background: {bg_color}; border: none; padding: 6px 16px; border-radius: 6px; color: white; cursor: pointer; font-weight: bold; width: auto; margin: 0;">
                    {teks_onoff}
                </button>
            </div>
            <label style="display:block; margin-top:12px; margin-bottom:4px; font-size:14px; color:#94a3b8;">Jalur Base:</label>
            <select id="jalur-{nama}" onchange="updateJalur('{nama}')">
                <option value="jockey_money" {"selected" if info["jalur"] == "jockey_money" else ""}>Jockey & Money</option>
                <option value="reguler" {"selected" if info["jalur"] == "reguler" else ""}>Base Reguler</option>
                <option value="semua" {"selected" if info["jalur"] == "semua" else ""}>Semua Base</option>
            </select>
        </div>
        """
    return html

@app.get("/", response_class=HTMLResponse)
async def halaman_dashboard():
    kartu_berline = buat_kartu_eksekutor()
    keyword_text = ", ".join(SEMUA_KEYWORDS)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Markas Utama Command Center</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; max-width: 960px; margin: auto; }}
            h1 {{ color: #e2e8f0; text-align: center; margin-bottom: 20px; font-size: 24px; }}
            h2 {{ border-bottom: 1px solid #334155; padding-bottom: 8px; color: #38bdf8; margin-top: 24px; font-size: 18px; }}
            .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; border-bottom: 2px solid #334155; padding-bottom: 12px; }}
            .tab-btn {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; width: auto; margin: 0; }}
            .tab-btn.active {{ background: #0284c7; color: #fff; border-color: #38bdf8; }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
            .card {{ background: #1e293b; padding: 16px; border-radius: 10px; border: 1px solid #334155; }}
            .row {{ display: flex; justify-content: space-between; align-items: center; }}
            select, textarea, button {{ width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-top: 6px; box-sizing: border-box; }}
            button.action-btn {{ background: #0284c7; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; }}
            .wording-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
        </style>
    </head>
    <body>
        <h1>🎛️ MARKAS UTAMA CONTROL PANEL</h1>

        <div class="tabs">
            <button class="tab-btn active" onclick="bukaTab('tab-logs', this)">📥 Pesan Masuk</button>
            <button class="tab-btn" onclick="bukaTab('tab-berline', this)">👑 Tim Berline</button>
            <button class="tab-btn" onclick="bukaTab('tab-keywords', this)">🔑 Keyword Filter</button>
        </div>

        <!-- TAB 1: LOG PESAN MASUK -->
        <div id="tab-logs" class="tab-content active">
            <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                <button onclick="fetchLogs()" style="background: #475569; width: auto; margin: 0; cursor: pointer;">🔄 Refresh Log</button>
                <button onclick="testNotif()" style="background: #eab308; color: #000; width: auto; margin: 0; font-weight: bold; cursor: pointer;">🔔 Tes Notifikasi Grup</button>
            </div>
            <div id="terminal" style="background: #000; color: #4ade80; padding: 16px; border-radius: 8px; font-family: monospace; height: 420px; overflow-y: auto; white-space: pre-wrap; font-size: 13px; border: 1px solid #334155;">
                Menunggu menfess masuk...
            </div>
        </div>

        <!-- TAB 2: TIM BERLINE -->
        <div id="tab-berline" class="tab-content">
            <h2>⚡ ON/OFF Eksekutor (Jourd & Ejeh)</h2>
            <div class="grid">{kartu_berline}</div>

            <h2>👑 Wording Akun Utama Berline (Command: a, b)</h2>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command {kode}</strong><textarea id="ber-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#ec4899;" onclick="updateWording('berline', '{kode}', 'ber-{kode}')">Simpan</button></div>''' for kode, teks in WORDING_BERLINE.items()])}
            </div>

            <h2>📝 Wording Eksekutor Berline (Command: 1, edit, vid, dll)</h2>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command: {kode}</strong><textarea id="eks-ber-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#ec4899;" onclick="updateWording('eksekutor_berline', '{kode}', 'eks-ber-{kode}')">Simpan</button></div>''' for kode, teks in TEMPLATE_EKSEKUTOR.items()])}
            </div>
        </div>

        <!-- TAB 3: KEYWORD FILTER -->
        <div id="tab-keywords" class="tab-content">
            <h2>🔑 Daftar Keyword Filter (Pisahkan dengan Koma ,)</h2>
            <p style="font-size:13px; color:#94a3b8;">Jockeyfess otomatis lolos semua tanpa filter. Keyword di bawah ini berlaku ketat untuk Moneyfess & 6 Base Reguler.</p>
            <div class="card">
                <textarea id="keyword-editor" rows="12">{keyword_text}</textarea>
                <button class="action-btn" onclick="saveKeywords()">💾 Simpan Semua Keyword</button>
            </div>
        </div>

        <script>
            function bukaTab(tabId, btnEl) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                btnEl.classList.add('active');
            }}

            async function fetchLogs() {{
                try {{
                    const res = await fetch('/api/logs');
                    const data = await res.json();
                    document.getElementById('terminal').innerHTML = data.logs.length === 0 ? "Menunggu menfess masuk..." : data.logs.join('\\n');
                }} catch (err) {{}}
            }}
            setInterval(fetchLogs, 2500); fetchLogs();

            async function testNotif() {{
                await fetch('/api/test-notif', {{method: 'POST'}});
                alert("Perintah notifikasi dikirim!");
            }}

            async function```python
import os
import asyncio
import re
import unicodedata
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChatForwardsRestrictedError
from telethon.tl.functions.messages import ForwardMessagesRequest
from supabase import create_client, Client
import uvicorn

load_dotenv()

# ==========================================
# 1. KONFIGURASI API & KLIEN (4 AKUN)
# ==========================================
API_ID = int(os.environ.get("API_ID", 36156436))
API_HASH = os.environ.get("API_HASH", "e2a8a08504aa88c37f7c941080d6a180")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ID_GRUP_UTAMA = -1003903118196

# ID TOPIK BERLINE
ID_TOPIK_BERLINE_JOCKEY = 74
ID_TOPIK_BERLINE_ANOTHER = 75

client_amel = TelegramClient("sesi_amel", API_ID, API_HASH)
client_berline = TelegramClient("sesi_berline", API_ID, API_HASH)

clients_eksekutor = {
    "Jourd": TelegramClient("sesi_jourd", API_ID, API_HASH),
    "Ejeh": TelegramClient("sesi_ejeh", API_ID, API_HASH),
}

ID_AMEL = None
ID_BERLINE = None
PEER_MARKAS_AMEL = None
BACKGROUND_TASKS = []

# ==========================================
# 2. DATABASE SUPABASE & DEFAULT STATE
# ==========================================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

STATUS_EKSEKUTOR = {
    "Jourd": {"nama": "Jourd", "aktif": True, "jalur": "semua"},
    "Ejeh": {"nama": "Ejeh", "aktif": True, "jalur": "semua"},
}

TEMPLATE_EKSEKUTOR = {
    "1": "HIT @Berrline As Seller ★ start 3-20k! Do check @ELGALERIES for more 📂🩷 Avail rush and revisi ⓘ Check @Elgatesult for testi & result.",
    "edit": "HIT @Berrline As Seller ꩜ ࣪ Editing start from 15-20k 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result @elgaresult & testi @elgatesti. ♡",
    "vid": "HIT @Berrline As Seller ꩜ ࣪ Edit vid start from 12-20k/menit 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "kti": "HIT @Berrline As Seller ꩜ ࣪ Start from 15-18k/hal. bisa rush, revisi, jaminan NO AI, dan handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "parafrase": "HIT @Berrline As Seller ꩜ ࣪ Turnitin 15k/cek, AI 6k/cek, parafrase 12k/hal & 7k/℅. avrush dan di handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "formatting": "HIT @Berrline As Seller ꩜ ࣪ Formatting start 2k/hal, dafis, dafpus, tabel dan gambar start 10k. avail for rush dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "teks": "HIT @Berrline As Seller ꩜ ࣪ Pantun, puisi, cerpen, surat dan lainnya start 10k- 20k/hal. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "cv": "HIT @Berrline As Seller ꩜ ࣪ Visi misi start 3-5k/point, CV start from 15-25k, kebutuhan organisasi start 15k. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "data": "HIT @Berrline As Seller ꩜ ࣪ Olah data start 25-50k, avail tugas akuntansi lainnya, di handle lulusan akuntansi. bisa rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "it": "HIT @Berrline As Seller ꩜ ࣪ Coding start 20k, web start 100k, scratch start 50k, UI/UX start 70k, avail tugas IT lainnya start 15k. Handle by mahasiswi Teknik Informatika 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "jastik": "HIT @Berrline As Seller ꩜ ࣪ jasa ketik word & excel start 3-5k/halaman. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡",
    "jurnal": "HIT @Berrline As Seller ꩜ ࣪ Unlock/download jurnal nasional start 5-8k, jurnal inter start 10-15k, review jurnal start 25k 💕 avail rush, revisi, dan NO AI. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "ppt": "HIT @Berrline As Seller ꩜ ࣪ PPT start 3k materi dari seller, materi dari buyyer 4k, +1,5k with design. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡"
}

WORDING_BERLINE = {
    "a": "HMU @Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕",
    "b": "HMU @.Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕"
}

SEMUA_KEYWORDS = [
    "makalah", "jasa makalah", "joki makalah", "tugas makalah",
    "joki coding", "coding", "ngoding", "website", "bug fixing", "database", "app android", "aplikasi", "joki web", "landing page", "joki app", "joki program", "program python", "program java", "program c++", "sistem informasi", "joki si", "machine learning", "joki ml", "joki database", "joki excel vba", "bug", "debug", "error coding", "joki tugas coding", "script python", "aplikasi skripsi", "sistem pakar", "joki uas coding", "framework laravel", "framework react", "joki html css",
    "cv ats", "cv kreatif", "visi misi", "organisasi", "portofolio", "cover letter", "surat lamaran", "ad/art organisasi",
    "infografis", "poster", "banner", "mindmap", "mind mapping", "famplet", "logo", "logo kelas", "logo 2d", "logo 3d", "jasa edit", "edit logo", "ui/ux", "edit video", "edit vid", "video animasi", "animasi ai", "edit feeds ig", "cover buku", "cover proposal", "presentasi", "ppt", "sertifikat", "undangan", "thumbnail", "desain grafis", "feeds instagram", "konten ig", "konten sosmed", "id card", "x banner", "roll banner", "brosur", "kartu nama", "mockup", "vector", "edit foto", "retouch foto", "motion graphic", "intro video", "reels editing", "tiktok editing", "desain feed", "konten canva", "template canva", "video promosi", "video profile", "wedding invitation", "undangan digital",
    "spss", "olah data", "kimia", "biologi", "fisika", "akuntansi", "matematika", "mtk", "statistik", "olah data excel", "minitab", "ekonometrika", "joki matkul", "r studio", "spss anova", "uji spss", "uji validitas", "uji reliabilitas", "regresi", "sample data", "uji normalitas", "uji t", "path analysis", "sem", "amos", "lisrel", "joki tugas statistik", "joki tugas mtk",
    "formatting", "revisi makalah", "revisi proposal", "daftar isi", "daftar pustaka", "nomor halaman", "no halaman", "parafrase", "turnitin", "ai detector", "mendeley", "cek plagiarisme", "similarity", "convert pdf ke word", "convert word ke pdf", "layout", "rapihin dokumen", "edit margin", "spasi", "kutipan", "sitasi", "citation", "referensi", "bibliography", "cek similarity", "cek turnitin", "styling word", "template skripsi", "template proposal",
    "jasa ketik", "jastik", "jasa tulis", "jastul", "resume", "resume materi", "transkrip", "transkrip wawancara", "translate", "terjemahan", "jasa ketik cepat", "ketik ulang", "input data", "entry data", "ketik dokumen", "salin tulisan", "tulis ulang",
    "cerpen", "puisi", "naskah drama", "ebook", "novel", "skenario", "lirik lagu", "caption", "copywriting", "cerita pendek", "flash fiction", "monolog", "storytelling",
    "resume jurnal", "tugas akhir", "essai", "essay", "artikel", "laporan", "joki artikel", "joki laporan", "proposal", "joki proposal", "skripsi", "joki skripsi", "revisi skripsi", "bab 1-5", "bab 1", "bab 2", "bab 3", "bab 4", "bab 5", "sidang skripsi", "laprak", "laporan praktikum", "studi kasus", "literature review", "review jurnal", "cari jurnal", "pkm", "jurnal internasional", "tesis", "disertasi", "revisi tesis", "kuisioner", "kuesioner", "survey", "pengolahan data skripsi", "jurnal sinta", "artikel ilmiah", "outline skripsi", "judul skripsi", "metodologi penelitian", "bab pembahasan", "jurnal scopus", "abstrak", "latar belakang", "laporan pkl", "pkl", "laporan pkm",
    "joktug", "joki tugas", "bimbel", "tugas kuliah", "joki quiz", "joki ujian", "joki uas", "joki uts", "rangkuman", "ringkasan materi", "joki absen", "joki kelas online", "joki praktikum", "kkn", "laporan kkn", "laporan magang", "joki magang", "joki hafalan", "joki presentasi", "resume buku", "joki resume", "tuton", "laporan pkl rush"
]

def load_database():
    global STATUS_EKSEKUTOR, TEMPLATE_EKSEKUTOR, WORDING_BERLINE, SEMUA_KEYWORDS
    if not supabase:
        return
    try:
        response = supabase.table("berline_settings").select("data").eq("id", 1).execute()
        if response.data and response.data[0].get("data"):
            data = response.data[0]["data"]
            for k, v in data.get("STATUS_EKSEKUTOR", {}).items():
                if k in STATUS_EKSEKUTOR:
                    STATUS_EKSEKUTOR[k].update(v)

            for k, v in data.get("TEMPLATE_EKSEKUTOR", {}).items():
                if k in TEMPLATE_EKSEKUTOR:
                    TEMPLATE_EKSEKUTOR[k] = v

            for k, v in data.get("WORDING_BERLINE", {}).items():
                if k in WORDING_BERLINE:
                    WORDING_BERLINE[k] = v

            db_kws = data.get("SEMUA_KEYWORDS")
            if db_kws and isinstance(db_kws, list):
                SEMUA_KEYWORDS = [k.strip() for k in db_kws if k.strip() and k.strip().lower() not in ("si", "ta")]
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal memuat Supabase: {e}")

def save_database():
    if not supabase:
        return
    data = {
        "STATUS_EKSEKUTOR": STATUS_EKSEKUTOR,
        "TEMPLATE_EKSEKUTOR": TEMPLATE_EKSEKUTOR,
        "WORDING_BERLINE": WORDING_BERLINE,
        "SEMUA_KEYWORDS": SEMUA_KEYWORDS
    }
    try:
        supabase.table("berline_settings").upsert({"id": 1, "data": data}).execute()
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal menyimpan ke Supabase: {e}")

load_database()

# ==========================================
# 3. ROUTE MAP & STRICT REGEX FILTER
# ==========================================
ID_JOCKEYFESS = -1002233967429
ID_MONEYFESS = -1001274048263

BASE_JOCKEY_MONEY_IDS = [ID_JOCKEYFESS, ID_MONEYFESS]
BASE_REGULER_IDS = [
    -1001611324665, -1001525948158, -1001303979309,
    -1001260932905, -1003058482095, -1001202510480
]
SEMUA_BASE_IDS = BASE_JOCKEY_MONEY_IDS + BASE_REGULER_IDS

def build_regex(keywords):
    bersih = sorted(set(k.strip() for k in keywords if k.strip()), key=len, reverse=True)
    if not bersih:
        return None
    patterns = [r'(?<!\w)' + re.escape(kw) + r'(?!\w)' for kw in bersih]
    return re.compile('|'.join(patterns), re.IGNORECASE)

REGEX_KEYWORDS = build_regex(SEMUA_KEYWORDS)

def normalisasi_teks(teks: str) -> str:
    return unicodedata.normalize('NFKC', teks) if teks else ""

# ==========================================
# 4. LOGGING TERMINAL SYSTEM
# ==========================================
MENFESS_LOGS = []
NAMA_BASE_MAP = {
    ID_JOCKEYFESS: "Jockeyfess",
    ID_MONEYFESS: "Moneyfess",
    -1001611324665: "Base WIB",
    -1001525948158: "Base WTB",
    -1001303979309: "Berdagang Online",
    -1001260932905: "Dagangfess",
    -1003058482095: "Base Lelang",
    -1001202510480: "Swalayan",
}

def simpan_log(chat_id, teks, cocok_kw):
    waktu = datetime.now().strftime("%H:%M:%S")
    nama_base = NAMA_BASE_MAP.get(chat_id, "Base Lainnya")
    teks_tampil = teks if teks else "[Media/Gambar tanpa teks]"
    snippet = (teks_tampil[:80] + '...') if len(teks_tampil) > 80 else teks_tampil
    snippet = snippet.replace('\n', ' ')
    MENFESS_LOGS.insert(0, f"[{waktu}] 📥 {nama_base} (KW: {cocok_kw}) -> {snippet}")
    if len(MENFESS_LOGS) > 100:
        MENFESS_LOGS.pop()

# ==========================================
# 5. HANDLER AMEL (PEMANTAU CHAT MASUK)
# ==========================================
SUDAH_DIPROSES = set()

async def proses_pesan(msg, chat_id):
    global PEER_MARKAS_AMEL
    key = (chat_id, msg.id)
    if key in SUDAH_DIPROSES:
        return
    SUDAH_DIPROSES.add(key)
    if len(SUDAH_DIPROSES) > 5000:
        SUDAH_DIPROSES.clear()

    teks_bersih = normalisasi_teks(msg.raw_text or "")

    # Jockeyfess lolos semua tanpa filter
    if chat_id == ID_JOCKEYFESS:
        cocok_kw = "ALL (Jockeyfess)"
        target_berline = ID_TOPIK_BERLINE_JOCKEY
    else:
        if not teks_bersih or not REGEX_KEYWORDS:
            return
        match = REGEX_KEYWORDS.search(teks_bersih)
        if not match:
            return
        cocok_kw = match.group(0)
        target_berline = ID_TOPIK_BERLINE_JOCKEY if chat_id == ID_MONEYFESS else ID_TOPIK_BERLINE_ANOTHER

    try:
        if not PEER_MARKAS_AMEL:
            PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)

        from_peer = await msg.get_input_chat()
        await client_amel(ForwardMessagesRequest(
            from_peer=from_peer,
            id=[msg.id],
            to_peer=PEER_MARKAS_AMEL,
            top_msg_id=target_berline
        ))

        simpan_log(chat_id, teks_bersih, cocok_kw)
        print(f"⚡ [FORWARD] Base {chat_id} | KW: {cocok_kw}")
    except ChatForwardsRestrictedError:
        pass
    except Exception as e:
        print(f"🚨 [ERROR FORWARD] {e}")

def register_amel_handlers(client):
    @client.on(events.NewMessage(chats=SEMUA_BASE_IDS))
    async def saring_menfess_instan(event):
        asyncio.create_task(proses_pesan(event.message, event.chat_id))

async def poll_fallback():
    last_id = {}
    for cid in SEMUA_BASE_IDS:
        try:
            m = await client_amel.get_messages(cid, limit=1)
            last_id[cid] = m[0].id if m else 0
        except Exception:
            last_id[cid] = 0

    while True:
        await asyncio.sleep(5)
        if not client_amel.is_connected():
            continue
        for cid in SEMUA_BASE_IDS:
            try:
                async for m in client_amel.iter_messages(cid, min_id=last_id[cid], reverse=True):
                    last_id[cid] = max(last_id[cid], m.id)
                    asyncio.create_task(proses_pesan(m, cid))
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception:
                pass

# ==========================================
# 6. SISTEM KONTROL BERLINE & EKSEKUTOR (JOURD & EJEH)
# ==========================================
queue_pesan = asyncio.Queue()
RIWAYAT_KOMENTAR = {}  # {id_pesan_markas: (chat_id_diskusi, msg_id_komentar, jalur)}

def simpan_riwayat(id_markas, chat_diskusi, msg_komentar, jalur):
    RIWAYAT_KOMENTAR[id_markas] = (chat_diskusi, msg_komentar, jalur)
    if len(RIWAYAT_KOMENTAR) > 2000:
        RIWAYAT_KOMENTAR.pop(next(iter(RIWAYAT_KOMENTAR)))

def format_daftar_nama(daftar_nama):
    if not daftar_nama:
        return ""
    if len(daftar_nama) == 1:
        return daftar_nama[0]
    if len(daftar_nama) == 2:
        return f"{daftar_nama[0]} dan {daftar_nama[1]}"
    return ", ".join(daftar_nama[:-1]) + f", dan {daftar_nama[-1]}"

def register_berline_handlers(client_manager, my_id):
    @client_manager.on(events.NewMessage(chats=ID_GRUP_UTAMA))
    async def tangkap_command(event):
        if not event.is_reply:
            return

        sender = await event.get_sender()
        if not sender or sender.id != my_id:
            return

        reply_msg = await event.get_reply_message()
        if not reply_msg:
            return

        input_teks = event.raw_text.strip()
        cmd_lower = input_teks.lower()

        # KASUS 1: Reply ke pesan ✅ (balas langsung ke komentar sebelumnya di comment section)
        if reply_msg.id in RIWAYAT_KOMENTAR:
            chat_diskusi, msg_komentar, jalur = RIWAYAT_KOMENTAR[reply_msg.id]

            if cmd_lower in TEMPLATE_EKSEKUTOR:
                await queue_pesan.put({
                    "event": event,
                    "chat_asal": chat_diskusi,
                    "msg_asal": msg_komentar,
                    "cmd": cmd_lower,
                    "jalur": jalur,
                    "is_reply_komentar": True
                })
                return

            try:
                teks_kirim = WORDING_BERLINE.get(cmd_lower, input_teks)
                sent = await client_manager.send_message(
                    entity=chat_diskusi,
                    message=teks_kirim,
                    reply_to=msg_komentar
                )
                simpan_riwayat(event.id, sent.chat_id, sent.id, jalurBerikut kode lengkap `main.py` yang sudah menggabungkan arsitektur **4 akun (Amel, Berline, Jourd, Ejeh)**, koneksi terisolasi (`lifespan`), dan fitur **reply langsung ke komentar sebelumnya di kolom komentar base (`RIWAYAT_KOMENTAR`)**. Langsung *copy-paste* ke GitHub:

```python
import os
import asyncio
import re
import unicodedata
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChatForwardsRestrictedError
from telethon.tl.functions.messages import ForwardMessagesRequest
from supabase import create_client, Client
import uvicorn

load_dotenv()

# ==========================================
# 1. KONFIGURASI API & KLIEN (4 AKUN)
# ==========================================
API_ID = int(os.environ.get("API_ID", 36156436))
API_HASH = os.environ.get("API_HASH", "e2a8a08504aa88c37f7c941080d6a180")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ID_GRUP_UTAMA = -1003903118196

# ID TOPIK BERLINE
ID_TOPIK_BERLINE_JOCKEY = 74
ID_TOPIK_BERLINE_ANOTHER = 75

client_amel = TelegramClient("sesi_amel", API_ID, API_HASH)
client_berline = TelegramClient("sesi_berline", API_ID, API_HASH)

clients_eksekutor = {
    "Jourd": TelegramClient("sesi_jourd", API_ID, API_HASH),
    "Ejeh": TelegramClient("sesi_ejeh", API_ID, API_HASH),
}

ID_AMEL = None
ID_BERLINE = None
PEER_MARKAS_AMEL = None
BACKGROUND_TASKS = []

# ==========================================
# 2. DATABASE SUPABASE & DEFAULT STATE
# ==========================================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

STATUS_EKSEKUTOR = {
    "Jourd": {"nama": "Jourd", "aktif": True, "jalur": "semua"},
    "Ejeh": {"nama": "Ejeh", "aktif": True, "jalur": "semua"},
}

TEMPLATE_EKSEKUTOR = {
    "1": "HIT @Berrline As Seller ★ start 3-20k! Do check @ELGALERIES for more 📂🩷 Avail rush and revisi ⓘ Check @Elgatesult for testi & result.",
    "edit": "HIT @Berrline As Seller ꩜ ࣪ Editing start from 15-20k 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result @elgaresult & testi @elgatesti. ♡",
    "vid": "HIT @Berrline As Seller ꩜ ࣪ Edit vid start from 12-20k/menit 💕 avrush, revisi, NO AI, dan bisa discuss terkait detail. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "kti": "HIT @Berrline As Seller ꩜ ࣪ Start from 15-18k/hal. bisa rush, revisi, jaminan NO AI, dan handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "parafrase": "HIT @Berrline As Seller ꩜ ࣪ Turnitin 15k/cek, AI 6k/cek, parafrase 12k/hal & 7k/℅. avrush dan di handle by admin berpengalaman 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "formatting": "HIT @Berrline As Seller ꩜ ࣪ Formatting start 2k/hal, dafis, dafpus, tabel dan gambar start 10k. avail for rush dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "teks": "HIT @Berrline As Seller ꩜ ࣪ Pantun, puisi, cerpen, surat dan lainnya start 10k- 20k/hal. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "cv": "HIT @Berrline As Seller ꩜ ࣪ Visi misi start 3-5k/point, CV start from 15-25k, kebutuhan organisasi start 15k. avail for rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "data": "HIT @Berrline As Seller ꩜ ࣪ Olah data start 25-50k, avail tugas akuntansi lainnya, di handle lulusan akuntansi. bisa rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "it": "HIT @Berrline As Seller ꩜ ࣪ Coding start 20k, web start 100k, scratch start 50k, UI/UX start 70k, avail tugas IT lainnya start 15k. Handle by mahasiswi Teknik Informatika 💕 cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "jastik": "HIT @Berrline As Seller ꩜ ࣪ jasa ketik word & excel start 3-5k/halaman. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡",
    "jurnal": "HIT @Berrline As Seller ꩜ ࣪ Unlock/download jurnal nasional start 5-8k, jurnal inter start 10-15k, review jurnal start 25k 💕 avail rush, revisi, dan NO AI. cek result t.me/Elgaresult/16 & testi @elgatesti. ♡",
    "ppt": "HIT @Berrline As Seller ꩜ ࣪ PPT start 3k materi dari seller, materi dari buyyer 4k, +1,5k with design. avail rush, revisi, dan NO AI 💕 cek result t.me/Elgaresult/16 & testi @elgatesti ♡"
}

WORDING_BERLINE = {
    "a": "HMU @Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕",
    "b": "HMU @.Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕"
}

SEMUA_KEYWORDS = [
    "makalah", "jasa makalah", "joki makalah", "tugas makalah",
    "joki coding", "coding", "ngoding", "website", "bug fixing", "database", "app android", "aplikasi", "joki web", "landing page", "joki app", "joki program", "program python", "program java", "program c++", "sistem informasi", "joki si", "machine learning", "joki ml", "joki database", "joki excel vba", "bug", "debug", "error coding", "joki tugas coding", "script python", "aplikasi skripsi", "sistem pakar", "joki uas coding", "framework laravel", "framework react", "joki html css",
    "cv ats", "cv kreatif", "visi misi", "organisasi", "portofolio", "cover letter", "surat lamaran", "ad/art organisasi",
    "infografis", "poster", "banner", "mindmap", "mind mapping", "famplet", "logo", "logo kelas", "logo 2d", "logo 3d", "jasa edit", "edit logo", "ui/ux", "edit video", "edit vid", "video animasi", "animasi ai", "edit feeds ig", "cover buku", "cover proposal", "presentasi", "ppt", "sertifikat", "undangan", "thumbnail", "desain grafis", "feeds instagram", "konten ig", "konten sosmed", "id card", "x banner", "roll banner", "brosur", "kartu nama", "mockup", "vector", "edit foto", "retouch foto", "motion graphic", "intro video", "reels editing", "tiktok editing", "desain feed", "konten canva", "template canva", "video promosi", "video profile", "wedding invitation", "undangan digital",
    "spss", "olah data", "kimia", "biologi", "fisika", "akuntansi", "matematika", "mtk", "statistik", "olah data excel", "minitab", "ekonometrika", "joki matkul", "r studio", "spss anova", "uji spss", "uji validitas", "uji reliabilitas", "regresi", "sample data", "uji normalitas", "uji t", "path analysis", "sem", "amos", "lisrel", "joki tugas statistik", "joki tugas mtk",
    "formatting", "revisi makalah", "revisi proposal", "daftar isi", "daftar pustaka", "nomor halaman", "no halaman", "parafrase", "turnitin", "ai detector", "mendeley", "cek plagiarisme", "similarity", "convert pdf ke word", "convert word ke pdf", "layout", "rapihin dokumen", "edit margin", "spasi", "kutipan", "sitasi", "citation", "referensi", "bibliography", "cek similarity", "cek turnitin", "styling word", "template skripsi", "template proposal",
    "jasa ketik", "jastik", "jasa tulis", "jastul", "resume", "resume materi", "transkrip", "transkrip wawancara", "translate", "terjemahan", "jasa ketik cepat", "ketik ulang", "input data", "entry data", "ketik dokumen", "salin tulisan", "tulis ulang",
    "cerpen", "puisi", "naskah drama", "ebook", "novel", "skenario", "lirik lagu", "caption", "copywriting", "cerita pendek", "flash fiction", "monolog", "storytelling",
    "resume jurnal", "tugas akhir", "essai", "essay", "artikel", "laporan", "joki artikel", "joki laporan", "proposal", "joki proposal", "skripsi", "joki skripsi", "revisi skripsi", "bab 1-5", "bab 1", "bab 2", "bab 3", "bab 4", "bab 5", "sidang skripsi", "laprak", "laporan praktikum", "studi kasus", "literature review", "review jurnal", "cari jurnal", "pkm", "jurnal internasional", "tesis", "disertasi", "revisi tesis", "kuisioner", "kuesioner", "survey", "pengolahan data skripsi", "jurnal sinta", "artikel ilmiah", "outline skripsi", "judul skripsi", "metodologi penelitian", "bab pembahasan", "jurnal scopus", "abstrak", "latar belakang", "laporan pkl", "pkl", "laporan pkm",
    "joktug", "joki tugas", "bimbel", "tugas kuliah", "joki quiz", "joki ujian", "joki uas", "joki uts", "rangkuman", "ringkasan materi", "joki absen", "joki kelas online", "joki praktikum", "kkn", "laporan kkn", "laporan magang", "joki magang", "joki hafalan", "joki presentasi", "resume buku", "joki resume", "tuton", "laporan pkl rush"
]

def load_database():
    global STATUS_EKSEKUTOR, TEMPLATE_EKSEKUTOR, WORDING_BERLINE, SEMUA_KEYWORDS
    if not supabase:
        return
    try:
        response = supabase.table("berline_settings").select("data").eq("id", 1).execute()
        if response.data and response.data[0].get("data"):
            data = response.data[0]["data"]
            for k, v in data.get("STATUS_EKSEKUTOR", {}).items():
                if k in STATUS_EKSEKUTOR:
                    STATUS_EKSEKUTOR[k].update(v)

            for k, v in data.get("TEMPLATE_EKSEKUTOR", {}).items():
                if k in TEMPLATE_EKSEKUTOR:
                    TEMPLATE_EKSEKUTOR[k] = v

            for k, v in data.get("WORDING_BERLINE", {}).items():
                if k in WORDING_BERLINE:
                    WORDING_BERLINE[k] = v

            db_kws = data.get("SEMUA_KEYWORDS")
            if db_kws and isinstance(db_kws, list):
                SEMUA_KEYWORDS = [k.strip() for k in db_kws if k.strip() and k.strip().lower() not in ("si", "ta")]
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal memuat Supabase: {e}")

def save_database():
    if not supabase:
        return
    data = {
        "STATUS_EKSEKUTOR": STATUS_EKSEKUTOR,
        "TEMPLATE_EKSEKUTOR": TEMPLATE_EKSEKUTOR,
        "WORDING_BERLINE": WORDING_BERLINE,
        "SEMUA_KEYWORDS": SEMUA_KEYWORDS
    }
    try:
        supabase.table("berline_settings").upsert({"id": 1, "data": data}).execute()
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal menyimpan ke Supabase: {e}")

load_database()

# ==========================================
# 3. ROUTE MAP & STRICT REGEX FILTER
# ==========================================
ID_JOCKEYFESS = -1002233967429
ID_MONEYFESS = -1001274048263

BASE_JOCKEY_MONEY_IDS = [ID_JOCKEYFESS, ID_MONEYFESS]
BASE_REGULER_IDS = [
    -1001611324665, -1001525948158, -1001303979309,
    -1001260932905, -1003058482095, -1001202510480
]
SEMUA_BASE_IDS = BASE_JOCKEY_MONEY_IDS + BASE_REGULER_IDS

def build_regex(keywords):
    bersih = sorted(set(k.strip() for k in keywords if k.strip()), key=len, reverse=True)
    if not bersih:
        return None
    patterns = [r'(?<!\w)' + re.escape(kw) + r'(?!\w)' for kw in bersih]
    return re.compile('|'.join(patterns), re.IGNORECASE)

REGEX_KEYWORDS = build_regex(SEMUA_KEYWORDS)

def normalisasi_teks(teks: str) -> str:
    return unicodedata.normalize('NFKC', teks) if teks else ""

# ==========================================
# 4. LOGGING TERMINAL SYSTEM
# ==========================================
MENFESS_LOGS = []
NAMA_BASE_MAP = {
    ID_JOCKEYFESS: "Jockeyfess",
    ID_MONEYFESS: "Moneyfess",
    -1001611324665: "Base WIB",
    -1001525948158: "Base WTB",
    -1001303979309: "Berdagang Online",
    -1001260932905: "Dagangfess",
    -1003058482095: "Base Lelang",
    -1001202510480: "Swalayan",
}

def simpan_log(chat_id, teks, cocok_kw):
    waktu = datetime.now().strftime("%H:%M:%S")
    nama_base = NAMA_BASE_MAP.get(chat_id, "Base Lainnya")
    teks_tampil = teks if teks else "[Media/Gambar tanpa teks]"
    snippet = (teks_tampil[:80] + '...') if len(teks_tampil) > 80 else teks_tampil
    snippet = snippet.replace('\n', ' ')
    MENFESS_LOGS.insert(0, f"[{waktu}] 📥 {nama_base} (KW: {cocok_kw}) -> {snippet}")
    if len(MENFESS_LOGS) > 100:
        MENFESS_LOGS.pop()

# ==========================================
# 5. HANDLER AMEL (PEMANTAU CHAT MASUK)
# ==========================================
SUDAH_DIPROSES = set()

async def proses_pesan(msg, chat_id):
    global PEER_MARKAS_AMEL
    key = (chat_id, msg.id)
    if key in SUDAH_DIPROSES:
        return
    SUDAH_DIPROSES.add(key)
    if len(SUDAH_DIPROSES) > 5000:
        SUDAH_DIPROSES.clear()

    teks_bersih = normalisasi_teks(msg.raw_text or "")

    # Jockeyfess lolos semua tanpa filter
    if chat_id == ID_JOCKEYFESS:
        cocok_kw = "ALL (Jockeyfess)"
        target_berline = ID_TOPIK_BERLINE_JOCKEY
    else:
        if not teks_bersih or not REGEX_KEYWORDS:
            return
        match = REGEX_KEYWORDS.search(teks_bersih)
        if not match:
            return
        cocok_kw = match.group(0)
        target_berline = ID_TOPIK_BERLINE_JOCKEY if chat_id == ID_MONEYFESS else ID_TOPIK_BERLINE_ANOTHER

    try:
        if not PEER_MARKAS_AMEL:
            PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)

        from_peer = await msg.get_input_chat()
        await client_amel(ForwardMessagesRequest(
            from_peer=from_peer,
            id=[msg.id],
            to_peer=PEER_MARKAS_AMEL,
            top_msg_id=target_berline
        ))

        simpan_log(chat_id, teks_bersih, cocok_kw)
        print(f"⚡ [FORWARD] Base {chat_id} | KW: {cocok_kw}")
    except ChatForwardsRestrictedError:
        pass
    except Exception as e:
        print(f"🚨 [ERROR FORWARD] {e}")

def register_amel_handlers(client):
    @client.on(events.NewMessage(chats=SEMUA_BASE_IDS))
    async def saring_menfess_instan(event):
        asyncio.create_task(proses_pesan(event.message, event.chat_id))

async def poll_fallback():
    last_id = {}
    for cid in SEMUA_BASE_IDS:
        try:
            m = await client_amel.get_messages(cid, limit=1)
            last_id[cid] = m[0].id if m else 0
        except Exception:
            last_id[cid] = 0

    while True:
        await asyncio.sleep(5)
        if not client_amel.is_connected():
            continue
        for cid in SEMUA_BASE_IDS:
            try:
                async for m in client_amel.iter_messages(cid, min_id=last_id[cid], reverse=True):
                    last_id[cid] = max(last_id[cid], m.id)
                    asyncio.create_task(proses_pesan(m, cid))
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception:
                pass

# ==========================================
# 6. SISTEM KONTROL BERLINE & EKSEKUTOR (JOURD & EJEH)
# ==========================================
queue_pesan = asyncio.Queue()
RIWAYAT_KOMENTAR = {}  # {id_pesan_markas: (chat_id_diskusi, msg_id_komentar, jalur)}

def simpan_riwayat(id_markas, chat_diskusi, msg_komentar, jalur):
    RIWAYAT_KOMENTAR[id_markas] = (chat_diskusi, msg_komentar, jalur)
    if len(RIWAYAT_KOMENTAR) > 2000:
        RIWAYAT_KOMENTAR.pop(next(iter(RIWAYAT_KOMENTAR)))

def format_daftar_nama(daftar_nama):
    if not daftar_nama:
        return ""
    if len(daftar_nama) == 1:
        return daftar_nama[0]
    if len(daftar_nama) == 2:
        return f"{daftar_nama[0]} dan {daftar_nama[1]}"
    return ", ".join(daftar_nama[:-1]) + f", dan {daftar_nama[-1]}"

def register_berline_handlers(client_manager, my_id):
    @client_manager.on(events.NewMessage(chats=ID_GRUP_UTAMA))
    async def tangkap_command(event):
        if not event.is_reply:
            return

        sender = await event.get_sender()
        if not sender or sender.id != my_id:
            return

        reply_msg = await event.get_reply_message()
        if not reply_msg:
            return

        input_teks = event.raw_text.strip()
        cmd_lower = input_teks.lower()

        # KASUS 1: Reply ke pesan ✅ (balas langsung ke komentar sebelumnya di comment section)
        if reply_msg.id in RIWAYAT_KOMENTAR:
            chat_diskusi, msg_komentar, jalur = RIWAYAT_KOMENTAR[reply_msg.id]

            if cmd_lower in TEMPLATE_EKSEKUTOR:
                await queue_pesan.put({
                    "event": event,
                    "chat_asal": chat_diskusi,
                    "msg_asal": msg_komentar,
                    "cmd": cmd_lower,
                    "jalur": jalur,
                    "is_reply_komentar": True
                })
                return

            try:
                teks_kirim = WORDING_BERLINE.get(cmd_lower, input_teks)
                sent = await client_manager.send_message(
                    entity=chat_diskusi,
                    message=teks_kirim,
                    reply_to=msg_komentar
                )
                simpan_riwayat(event.id, sent.chat_id, sent.id, jalur)
                await event.edit("✅ Berhasil membalas komentar sebelumnya di Base!")
            except FloodWaitError as e:
                await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
            except Exception as e:
                await event.edit(f"❌ Gagal reply komentar: {e}")
            return

        # KASUS 2: Reply langsung ke pesan forward menfess dari Amel
        if not reply_msg.forward:
            return

        forward_from = reply_msg.forward
        if not forward_from.chat_id or not forward_from.channel_post:
            return

        asal_thread = reply_msg.reply_to_msg_id if reply_msg.reply_to_msg_id else 0
        jalur = "jockey_money" if asal_thread == ID_TOPIK_BERLINE_JOCKEY else "reguler"

        if cmd_lower in TEMPLATE_EKSEKUTOR:
            await queue_pesan.put({
                "event": event,
                "chat_asal": forward_from.chat_id,
                "msg_asal": forward_from.channel_post,
                "cmd": cmd_lower,
                "jalur": jalur,
                "is_reply_komentar": False
            })
            return

        try:
            teks_kirim = WORDING_BERLINE.get(cmd_lower, input_teks)
            sent = await client_manager.send_message(
                entity=forward_from.chat_id,
                message=teks_kirim,
                comment_to=forward_from.channel_post
            )
            simpan_riwayat(event.id, sent.chat_id, sent.id, jalur)
            await event.edit("✅ Berhasil mengirim komentar mandiri ke Base!")
        except FloodWaitError as e:
            await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
        except Exception as e:
            await event.edit(f"❌ Gagal: {e}")

async def worker_eksekutor():
    while True:
        task = await queue_pesan.get()
        event_mgr = task["event"]

        try:
            chat_asal = task["chat_asal"]
            msg_asal = task["msg_asal"]
            is_reply_komentar = task["is_reply_komentar"]

            akun_bertugas = [
                nama for nama, info in STATUS_EKSEKUTOR.items()
                if info["aktif"] and (info["jalur"] == task["jalur"] or info["jalur"] == "semua")
                and clients_eksekutor[nama].is_connected()
            ]

            if not akun_bertugas:
                await event_mgr.edit("❌ Tidak ada eksekutor (Jourd/Ejeh) yang aktif/terhubung.")
                continue

            async def kirim_pesan_eksekutor(nama_akun):
                try:
                    teks_final = TEMPLATE_EKSEKUTOR[task["cmd"]]
                    if task["jalur"] == "jockey_money":
                        teks_final = teks_final.replace("@Berrline", "@.Berrline")

                    if is_reply_komentar:
                        sent = await clients_eksekutor[nama_akun].send_message(
                            entity=chat_asal,
                            message=teks_final,
                            reply_to=msg_asal
                        )
                    else:
                        sent = await clients_eksekutor[nama_akun].send_message(
                            entity=chat_asal,
                            message=teks_final,
                            comment_to=msg_asal
                        )
                    return (True, STATUS_EKSEKUTOR[nama_akun]["nama"], sent.chat_id, sent.id)
                except FloodWaitError as e:
                    STATUS_EKSEKUTOR[nama_akun]["aktif"] = False
                    asyncio.get_event_loop().run_in_executor(None, save_database)
                    return (False, f"{STATUS_EKSEKUTOR[nama_akun]['nama']} floodwait {e.seconds}s.", None, None)
                except Exception as e:
                    print(f"🚨 [EKSEKUTOR ERROR - {nama_akun}] {e}")
                    return (False, None, None, None)

            results = await asyncio.gather(*(kirim_pesan_eksekutor(nama) for nama in akun_bertugas))
            berhasil = [res for res in results if res[0]]
            laporan_floodwait = [res[1] for res in results if not res[0] and res[1]]

            if berhasil:
                simpan_riwayat(event_mgr.id, berhasil[0][2], berhasil[0][3], task["jalur"])
                nama_berhasil = [res[1] for res in berhasil]
                baris_laporan = [f"✅ Terkirim oleh {format_daftar_nama(nama_berhasil)}."]
            else:
                baris_laporan = ["❌ Gagal terkirim."]

            if laporan_floodwait:
                baris_laporan.extend(laporan_floodwait)

            await event_mgr.edit("\n".join(baris_laporan))
        except Exception as e:
            await event_mgr.edit(f"❌ Error: {e}")
        finally:
            queue_pesan.task_done()

# ==========================================
# 7. FITUR NOTIFIKASI KESIAPAN
# ==========================================
async def kirim_notifikasi_kesiapan():
    topik_berline = [ID_TOPIK_BERLINE_JOCKEY, ID_TOPIK_BERLINE_ANOTHER]

    if client_amel.is_connected():
        for tid in topik_berline:
            try:
                await client_amel.send_message(ID_GRUP_UTAMA, f"👁️ [RADAR AMEL] Aktif memantau {len(SEMUA_BASE_IDS)} Channel.", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

    if client_berline.is_connected():
        for tid in topik_berline:
            try:
                await client_berline.send_message(ID_GRUP_UTAMA, "👑 [SISTEM] Berline siap!", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

    for nama_eks, client_eks in clients_eksekutor.items():
        if not client_eks.is_connected():
            continue
        info = STATUS_EKSEKUTOR[nama_eks]
        for tid in topik_berline:
            try:
                await client_eks.send_message(ID_GRUP_UTAMA, f"🤖 [{info['nama']}] siap!", reply_to=tid)
                await asyncio.sleep(0.2)
            except Exception:
                pass

# ==========================================
# 8. STARTUP TERISOLASI (LIFESPAN)
# ==========================================
async def konek_aman(client, nama):
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"❌ [{nama}] Sesi mati / belum login! Buat ulang file .session-nya.")
            await client.disconnect()
            return None
        me = await client.get_me()
        print(f"✅ [{nama}] Berhasil Terhubung! (ID: {me.id} | Nama: {me.first_name})")
        return me
    except Exception as e:
        print(f"❌ [{nama}] Gagal terhubung: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ID_AMEL, ID_BERLINE, PEER_MARKAS_AMEL

    print("\n⏳ Menghubungkan akun Amel...")
    me_amel = await konek_aman(client_amel, "Amel")
    if me_amel:
        ID_AMEL = me_amel.id
        await client_amel.get_dialogs(limit=50)
        PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)
        register_amel_handlers(client_amel)

    print("⏳ Menghubungkan akun Berline...")
    me_berline = await konek_aman(client_berline, "Berline")
    if me_berline:
        ID_BERLINE = me_berline.id
        register_berline_handlers(client_berline, ID_BERLINE)

    for nama, client_eks in clients_eksekutor.items():
        print(f"⏳ Menghubungkan eksekutor: {nama}...")
        me_eks = await konek_aman(client_eks, nama)
        if me_eks:
            STATUS_EKSEKUTOR[nama]["nama"] = me_eks.first_name or me_eks.username or nama
        else:
            STATUS_EKSEKUTOR[nama]["aktif"] = False

    save_database()

    BACKGROUND_TASKS.append(asyncio.create_task(kirim_notifikasi_kesiapan()))
    BACKGROUND_TASKS.append(asyncio.create_task(worker_eksekutor()))
    if me_amel:
        BACKGROUND_TASKS.append(asyncio.create_task(poll_fallback()))

    print("\n🚀 Markas Utama (Amel, Berline, Jourd, Ejeh) Siap Tempur!\n")
    yield

    for task in BACKGROUND_TASKS:
        task.cancel()
    await asyncio.gather(
        client_amel.disconnect(),
        client_berline.disconnect(),
        *(c.disconnect() for c in clients_eksekutor.values()),
        return_exceptions=True
    )

# ==========================================
# 9. PORTAL DASHBOARD API
# ==========================================
app = FastAPI(lifespan=lifespan)

class ToggleModel(BaseModel):
    nama: str
    aktif: bool
    jalur: str

class WordingModel(BaseModel):
    tipe: str
    kode: str
    teks: str

class KeywordModel(BaseModel):
    keywords: str

def buat_kartu_eksekutor():
    html = ""
    for nama, info in STATUS_EKSEKUTOR.items():
        bg_color = "#16a34a" if info["aktif"] else "#dc2626"
        teks_onoff = "ON" if info["aktif"] else "OFF"
        html += f"""
        <div class="card">
            <div class="row">
                <strong>{info["nama"]} ({nama})</strong>
                <button id="btn-onoff-{nama}" onclick="toggleOnOff('{nama}')"
                        style="background: {bg_color}; border: none; padding: 6px 16px; border-radius: 6px; color: white; cursor: pointer; font-weight: bold; width: auto; margin: 0;">
                    {teks_onoff}
                </button>
            </div>
            <label style="display:block; margin-top:12px; margin-bottom:4px; font-size:14px; color:#94a3b8;">Jalur Base:</label>
            <select id="jalur-{nama}" onchange="updateJalur('{nama}')">
                <option value="jockey_money" {"selected" if info["jalur"] == "jockey_money" else ""}>Jockey & Money</option>
                <option value="reguler" {"selected" if info["jalur"] == "reguler" else ""}>Base Reguler</option>
                <option value="semua" {"selected" if info["jalur"] == "semua" else ""}>Semua Base</option>
            </select>
        </div>
        """
    return html

@app.get("/", response_class=HTMLResponse)
async def halaman_dashboard():
    kartu_berline = buat_kartu_eksekutor()
    keyword_text = ", ".join(SEMUA_KEYWORDS)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Markas Utama Command Center</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; max-width: 960px; margin: auto; }}
            h1 {{ color: #e2e8f0; text-align: center; margin-bottom: 20px; font-size: 24px; }}
            h2 {{ border-bottom: 1px solid #334155; padding-bottom: 8px; color: #38bdf8; margin-top: 24px; font-size: 18px; }}
            .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; border-bottom: 2px solid #334155; padding-bottom: 12px; }}
            .tab-btn {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; width: auto; margin: 0; }}
            .tab-btn.active {{ background: #0284c7; color: #fff; border-color: #38bdf8; }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
            .card {{ background: #1e293b; padding: 16px; border-radius: 10px; border: 1px solid #334155; }}
            .row {{ display: flex; justify-content: space-between; align-items: center; }}
            select, textarea, button {{ width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-top: 6px; box-sizing: border-box; }}
            button.action-btn {{ background: #0284c7; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; }}
            .wording-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
        </style>
    </head>
    <body>
        <h1>🎛️ MARKAS UTAMA CONTROL PANEL</h1>

        <div class="tabs">
            <button class="tab-btn active" onclick="bukaTab('tab-logs', this)">📥 Pesan Masuk</button>
            <button class="tab-btn" onclick="bukaTab('tab-berline', this)">👑 Tim Berline</button>
            <button class="tab-btn" onclick="bukaTab('tab-keywords', this)">🔑 Keyword Filter</button>
        </div>

        <!-- TAB 1: LOG PESAN MASUK -->
        <div id="tab-logs" class="tab-content active">
            <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                <button onclick="fetchLogs()" style="background: #475569; width: auto; margin: 0; cursor: pointer;">🔄 Refresh Log</button>
                <button onclick="testNotif()" style="background: #eab308; color: #000; width: auto; margin: 0; font-weight: bold; cursor: pointer;">🔔 Tes Notifikasi Grup</button>
            </div>
            <div id="terminal" style="background: #000; color: #4ade80; padding: 16px; border-radius: 8px; font-family: monospace; height: 420px; overflow-y: auto; white-space: pre-wrap; font-size: 13px; border: 1px solid #334155;">
                Menunggu menfess masuk...
            </div>
        </div>

        <!-- TAB 2: TIM BERLINE -->
        <div id="tab-berline" class="tab-content">
            <h2>⚡ ON/OFF Eksekutor (Jourd & Ejeh)</h2>
            <div class="grid">{kartu_berline}</div>

            <h2>👑 Wording Akun Utama Berline (Command: a, b)</h2>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command {kode}</strong><textarea id="ber-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#ec4899;" onclick="updateWording('berline', '{kode}', 'ber-{kode}')">Simpan</button></div>''' for kode, teks in WORDING_BERLINE.items()])}
            </div>

            <h2>📝 Wording Eksekutor Berline (Command: 1, edit, vid, dll)</h2>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command: {kode}</strong><textarea id="eks-ber-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#ec4899;" onclick="updateWording('eksekutor_berline', '{kode}', 'eks-ber-{kode}')">Simpan</button></div>''' for kode, teks in TEMPLATE_EKSEKUTOR.items()])}
            </div>
        </div>

        <!-- TAB 3: KEYWORD FILTER -->
        <div id="tab-keywords" class="tab-content">
            <h2>🔑 Daftar Keyword Filter (Pisahkan dengan Koma ,)</h2>
            <p style="font-size:13px; color:#94a3b8;">Jockeyfess otomatis lolos semua tanpa filter. Keyword di bawah ini berlaku ketat untuk Moneyfess & 6 Base Reguler.</p>
            <div class="card">
                <textarea id="keyword-editor" rows="12">{keyword_text}</textarea>
                <button class="action-btn" onclick="saveKeywords()">💾 Simpan Semua Keyword</button>
            </div>
        </div>

        <script>
            function bukaTab(tabId, btnEl) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                btnEl.classList.add('active');
            }}

            async function fetchLogs() {{
                try {{
                    const res = await fetch('/api/logs');
                    const data = await res.json();
                    document.getElementById('terminal').innerHTML = data.logs.length === 0 ? "Menunggu menfess masuk..." : data.logs.join('\\n');
                }} catch (err) {{}}
            }}
            setInterval(fetchLogs, 2500); fetchLogs();

            async function testNotif() {{
                await fetch('/api/test-notif', {{method: 'POST'}});
                alert("Perintah notifikasi dikirim!");
            }}

            async function toggleOnOff(nama) {{
                const btn = document.getElementById(`btn-onoff-${{nama}}`);
                const newState = btn.innerText !== "ON";
                const jalur = document.getElementById(`jalur-${{nama}}`).value;
                await fetch('/api/update-akun', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{nama: nama, aktif: newState, jalur: jalur}})}});
                btn.innerText = newState ? "ON" : "OFF";
                btn.style.background = newState ? "#16a34a" : "#dc2626";
            }}

            async function updateJalur(nama) {{
                const btn = document.getElementById(`btn-onoff-${{nama}}`);
                await fetch('/api/update-akun', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{nama: nama, aktif: btn.innerText === "ON", jalur: document.getElementById(`jalur-${{nama}}`).value}})}});
            }}

            async function saveKeywords() {{
                const kwText = document.getElementById('keyword-editor').value;
                await fetch('/api/update-keywords', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{keywords: kwText}})}});
                alert('Keyword diperbarui dan langsung aktif!');
            }}

            async function updateWording(tipe, kode, elemId) {{
                const teks = document.getElementById(elemId).value;
                await fetch('/api/update-wording', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{tipe: tipe, kode: kode, teks: teks}})}});
                alert('Wording berhasil disimpan!');
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/logs")
async def get_logs():
    return {"logs": MENFESS_LOGS}

@app.post("/api/test-notif")
async def trigger_test_notif():
    asyncio.create_task(kirim_notifikasi_kesiapan())
    return {"status": "ok"}

@app.post("/api/update-akun")
async def update_akun(data: ToggleModel):
    if data.nama in STATUS_EKSEKUTOR:
        STATUS_EKSEKUTOR[data.nama]["aktif"] = data.aktif
        STATUS_EKSEKUTOR[data.nama]["jalur"] = data.jalur
        asyncio.get_event_loop().run_in_executor(None, save_database)
    return {"status": "ok"}

@app.post("/api/update-wording")
async def update_wording(data: WordingModel):
    if data.tipe == "eksekutor_berline" and data.kode in TEMPLATE_EKSEKUTOR:
        TEMPLATE_EKSEKUTOR[data.kode] = data.teks
    elif data.tipe == "berline" and data.kode in WORDING_BERLINE:
        WORDING_BERLINE[data.kode] = data.teks
    asyncio.get_event_loop().run_in_executor(None, save_database)
    return {"status": "ok"}

@app.post("/api/update-keywords")
async def update_keywords(data: KeywordModel):
    global SEMUA_KEYWORDS, REGEX_KEYWORDS
    kws = [k.strip() for k in data.keywords.split(",") if k.strip()]
    SEMUA_KEYWORDS = kws
    REGEX_KEYWORDS = build_regex(SEMUA_KEYWORDS)
    asyncio.get_event_loop().run_in_executor(None, save_database)
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False)
