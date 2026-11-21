import os
import asyncio
import re
import unicodedata
from datetime import datetime
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
# 1. KONFIGURASI API & KLIEN
# ==========================================
API_ID = int(os.environ.get("API_ID", 36156436))
API_HASH = os.environ.get("API_HASH", "e2a8a08504aa88c37f7c941080d6a180")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ID_GRUP_UTAMA = -1003903118196

# ID TOPIK BERLINE
ID_TOPIK_BERLINE_JOCKEY = 74
ID_TOPIK_BERLINE_ANOTHER = 75

# ID TOPIK ROLAND
ID_TOPIK_ROLAND_JOCKEY = 13683   # Roland (2) Jockey Money
ID_TOPIK_ROLAND_ANOTHER = 13682  # Roland (1) Another Base

client_amel = TelegramClient("sesi_amel", API_ID, API_HASH)
client_berline = TelegramClient("sesi_berline", API_ID, API_HASH)
client_roland = TelegramClient("sesi_roland", API_ID, API_HASH)

clients_eksekutor = {
    # Tim Berline (2 Akun)
    "Arul": TelegramClient("sesi_arul", API_ID, API_HASH),
    "Hazel": TelegramClient("sesi_hazel", API_ID, API_HASH),
    # Tim Roland (1 Akun per Jalur)
    "Land": TelegramClient("sesi_land", API_ID, API_HASH),
    "Vasa": TelegramClient("sesi_vasa", API_ID, API_HASH),
}

ID_AMEL = None
ID_BERLINE = None
ID_ROLAND = None
PEER_MARKAS_AMEL = None

# ==========================================
# 2. DATABASE SUPABASE & DEFAULT STATE
# ==========================================
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

STATUS_EKSEKUTOR = {
    # Tim Berline: 2 akun aktif di semua jalur
    "Arul": {"nama": "Arul", "aktif": True, "jalur": "semua", "tim": "berline"},
    "Hazel": {"nama": "Hazel", "aktif": True, "jalur": "semua", "tim": "berline"},
    # Tim Roland: 1 akun per jalur (Land = Reguler/1, Vasa = Jockey&Money/2)
    "Land": {"nama": "Land", "aktif": True, "jalur": "reguler", "tim": "roland"},
    "Vasa": {"nama": "Vasa", "aktif": True, "jalur": "jockey_money", "tim": "roland"},
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

TEMPLATE_ROLAND = {
    "1": "Hit @DebugW as seller ! 🕶️ Check @ARDUINOST. 👨‍💻 Start 3-20k, avail rush & 100% NO AI. Testi @ArduProof, Result @ArduPorto. 🎓",
    "edit": "HIT @DebugW As Seller ꩜ ࣪ Editing start from 15-20k 💕 avrush, revisi, NO AI.",
    "vid": "HIT @DebugW As Seller ꩜ ࣪ Edit vid start from 12-20k/menit 💕 avrush, revisi, NO AI."
}

WORDING_BERLINE = {
    "a": "HMU @Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕",
    "b": "HMU @.Berrline (as seller) 📝 ꩜ ࣪ start from 3-20k. do check @Elgaleries! avail rush, revisi, & jaminan NO AI. result @Elgaresult & testi @Elgatesult 📂💕"
}

WORDING_ROLAND = {
    "a": "HMU @DebugW as seller 👨‍💻 @ARDUINOST. Start 3-20k. Avail rush & no AI. 🎓\n☆ Testi @Arduproof\n☆ Result @ArduPorto",
    "b": "HMU @.DebugW as seller👨‍💻 @ARDUINOST. Start 3-20k. Avail rush & no AI. 🎓\n☆ Testi @Arduproof\n☆ Result @ArduPorto"
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
    global STATUS_EKSEKUTOR, TEMPLATE_EKSEKUTOR, TEMPLATE_ROLAND, WORDING_BERLINE, WORDING_ROLAND, SEMUA_KEYWORDS
    if not supabase: return
    try:
        response = supabase.table("berline_settings").select("data").eq("id", 1).execute()
        if response.data and response.data[0].get("data"):
            data = response.data[0]["data"]
            for k, v in data.get("STATUS_EKSEKUTOR", {}).items():
                if k in STATUS_EKSEKUTOR: STATUS_EKSEKUTOR[k].update(v)
            
            STATUS_EKSEKUTOR["Arul"]["jalur"] = "semua"
            STATUS_EKSEKUTOR["Hazel"]["jalur"] = "semua"
            STATUS_EKSEKUTOR["Land"]["jalur"] = "reguler"
            STATUS_EKSEKUTOR["Vasa"]["jalur"] = "jockey_money"
            
            for k, v in data.get("TEMPLATE_EKSEKUTOR", {}).items():
                if k in TEMPLATE_EKSEKUTOR: TEMPLATE_EKSEKUTOR[k] = v
                
            for k, v in data.get("TEMPLATE_ROLAND", {}).items():
                if k in TEMPLATE_ROLAND:
                    if "DebugW" not in v and "DebugW" in TEMPLATE_ROLAND[k]: continue
                    TEMPLATE_ROLAND[k] = v
                
            for k, v in data.get("WORDING_BERLINE", {}).items():
                if k in WORDING_BERLINE: WORDING_BERLINE[k] = v
                
            for k, v in data.get("WORDING_ROLAND", {}).items():
                if k in WORDING_ROLAND:
                    if "DebugW" not in v and "DebugW" in WORDING_ROLAND[k]: continue
                    WORDING_ROLAND[k] = v
                
            db_kws = data.get("SEMUA_KEYWORDS")
            if db_kws and isinstance(db_kws, list):
                SEMUA_KEYWORDS = [k.strip() for k in db_kws if k.strip() and k.strip().lower() not in ("si", "ta")]
    except Exception as e:
        print(f"🚨 [DB ERROR] Gagal memuat Supabase: {e}")

def save_database():
    if not supabase: return
    data = {
        "STATUS_EKSEKUTOR": STATUS_EKSEKUTOR,
        "TEMPLATE_EKSEKUTOR": TEMPLATE_EKSEKUTOR,
        "TEMPLATE_ROLAND": TEMPLATE_ROLAND,
        "WORDING_BERLINE": WORDING_BERLINE,
        "WORDING_ROLAND": WORDING_ROLAND,
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
    if not teks: return ""
    return unicodedata.normalize('NFKC', teks)

# ==========================================
# 4. LOGGING TERMINAL SYSTEM
# ==========================================
MENFESS_LOGS = []
def simpan_log(chat_id, teks, cocok_kw):
    waktu = datetime.now().strftime("%H:%M:%S")
    nama_base = "Base Lainnya"
    if chat_id == ID_JOCKEYFESS: nama_base = "Jockeyfess"
    elif chat_id == ID_MONEYFESS: nama_base = "Moneyfess"
    elif chat_id == -1001611324665: nama_base = "Base WIB"
    elif chat_id == -1001525948158: nama_base = "Base WTB"
    elif chat_id == -1001303979309: nama_base = "Berdagang Online"
    elif chat_id == -1001260932905: nama_base = "Dagangfess"
    elif chat_id == -1003058482095: nama_base = "Base Lelang"
    elif chat_id == -1001202510480: nama_base = "Swalayan"
    
    teks_tampil = teks if teks else "[Media/Gambar tanpa teks]"
    snippet = (teks_tampil[:80] + '...') if len(teks_tampil) > 80 else teks_tampil
    snippet = snippet.replace('\n', ' ')
    pesan_log = f"[{waktu}] 📥 {nama_base} (KW: {cocok_kw}) -> {snippet}"
    MENFESS_LOGS.insert(0, pesan_log)
    if len(MENFESS_LOGS) > 100: MENFESS_LOGS.pop()

# ==========================================
# 5. PORTAL DASHBOARD API (DENGAN TAB)
# ==========================================
app = FastAPI()

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

def buat_kartu_eksekutor(tim_target):
    html = ""
    for nama, info in STATUS_EKSEKUTOR.items():
        if info["tim"] != tim_target: continue
        bg_color = "#16a34a" if info["aktif"] else "#dc2626"
        teks_onoff = "ON" if info["aktif"] else "OFF"
        html += f"""
        <div class="card">
            <div class="row">
                <strong>{info["nama"]}</strong>
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
    kartu_berline = buat_kartu_eksekutor("berline")
    kartu_roland = buat_kartu_eksekutor("roland")
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
            <button class="tab-btn" onclick="bukaTab('tab-roland', this)">🎩 Tim Roland</button>
            <button class="tab-btn" onclick="bukaTab('tab-keywords', this)">🔑 Keyword Filter</button>
        </div>

        <div id="tab-logs" class="tab-content active">
            <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                <button onclick="fetchLogs()" style="background: #475569; width: auto; margin: 0; cursor: pointer;">🔄 Refresh Log</button>
                <button onclick="testNotif()" style="background: #eab308; color: #000; width: auto; margin: 0; font-weight: bold; cursor: pointer;">🔔 Tes Notifikasi Grup</button>
            </div>
            <div id="terminal" style="background: #000; color: #4ade80; padding: 16px; border-radius: 8px; font-family: monospace; height: 420px; overflow-y: auto; white-space: pre-wrap; font-size: 13px; border: 1px solid #334155;">
                Menunggu menfess masuk...
            </div>
        </div>

        <div id="tab-berline" class="tab-content">
            <h2>⚡ ON/OFF Eksekutor Berline</h2>
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

        <div id="tab-roland" class="tab-content">
            <h2>⚡ ON/OFF Eksekutor Roland</h2>
            <div class="grid">{kartu_roland}</div>

            <h2>🎩 Wording Akun Utama Roland (Command: a, b)</h2>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command {kode}</strong><textarea id="rol-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#8b5cf6;" onclick="updateWording('roland', '{kode}', 'rol-{kode}')">Simpan</button></div>''' for kode, teks in WORDING_ROLAND.items()])}
            </div>

            <h2>📝 Wording Eksekutor Roland (Command: 1, edit, vid)</h2>
            <p style="font-size:13px; color:#94a3b8;">Tag #L (Land) dan #VS (Vasa) otomatis ditambahkan di akhir pesan.</p>
            <div class="wording-grid">
                {''.join([f'''<div class="card"><strong>Command: {kode}</strong><textarea id="eks-rol-{kode}" rows="3">{teks}</textarea><button class="action-btn" style="background:#8b5cf6;" onclick="updateWording('eksekutor_roland', '{kode}', 'eks-rol-{kode}')">Simpan</button></div>''' for kode, teks in TEMPLATE_ROLAND.items()])}
            </div>
        </div>

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
async def get_logs(): return {"logs": MENFESS_LOGS}

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
    if data.tipe == "eksekutor_berline" and data.kode in TEMPLATE_EKSEKUTOR: TEMPLATE_EKSEKUTOR[data.kode] = data.teks
    elif data.tipe == "eksekutor_roland" and data.kode in TEMPLATE_ROLAND: TEMPLATE_ROLAND[data.kode] = data.teks
    elif data.tipe == "berline" and data.kode in WORDING_BERLINE: WORDING_BERLINE[data.kode] = data.teks
    elif data.tipe == "roland" and data.kode in WORDING_ROLAND: WORDING_ROLAND[data.kode] = data.teks
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

# ==========================================
# 6. FITUR NOTIFIKASI KESIAPAN
# ==========================================
async def kirim_notifikasi_kesiapan():
    topik_berline = [ID_TOPIK_BERLINE_JOCKEY, ID_TOPIK_BERLINE_ANOTHER]
    topik_roland = [ID_TOPIK_ROLAND_JOCKEY, ID_TOPIK_ROLAND_ANOTHER]
    
    for tid in topik_berline + topik_roland:
        try: await client_amel.send_message(ID_GRUP_UTAMA, f"👁️ [RADAR AMEL] Aktif memantau {len(SEMUA_BASE_IDS)} Channel.", reply_to=tid); await asyncio.sleep(0.2)
        except: pass
    for tid in topik_berline:
        try: await client_berline.send_message(ID_GRUP_UTAMA, "👑 [SISTEM] Berline siap!", reply_to=tid); await asyncio.sleep(0.2)
        except: pass
    for tid in topik_roland:
        try: await client_roland.send_message(ID_GRUP_UTAMA, "🎩 [SISTEM] Roland siap!", reply_to=tid); await asyncio.sleep(0.2)
        except: pass
    for nama_eks, client_eks in clients_eksekutor.items():
        info = STATUS_EKSEKUTOR[nama_eks]
        target_topik = topik_berline if info["tim"] == "berline" else topik_roland
        for tid in target_topik:
            try: await client_eks.send_message(ID_GRUP_UTAMA, f"🤖 [{info['nama']}] siap!", reply_to=tid); await asyncio.sleep(0.2)
            except: pass

# ==========================================
# 7. HANDLER AMEL DUAL-FORWARDER (JOCKEY ALL + BASE LAIN STRICT)
# ==========================================
SUDAH_DIPROSES = set()

async def proses_pesan(msg, chat_id):
    global PEER_MARKAS_AMEL
    key = (chat_id, msg.id)
    if key in SUDAH_DIPROSES: return
    SUDAH_DIPROSES.add(key)
    if len(SUDAH_DIPROSES) > 5000: SUDAH_DIPROSES.clear()

    teks_bersih = normalisasi_teks(msg.raw_text or "")
    
    if chat_id == ID_JOCKEYFESS:
        cocok_kw = "ALL (Jockeyfess)"
        target_berline = ID_TOPIK_BERLINE_JOCKEY
        target_roland = ID_TOPIK_ROLAND_JOCKEY
    else:
        if not teks_bersih or not REGEX_KEYWORDS:
            return
        match = REGEX_KEYWORDS.search(teks_bersih)
        if not match:
            return
        cocok_kw = match.group(0)
        if chat_id == ID_MONEYFESS:
            target_berline = ID_TOPIK_BERLINE_JOCKEY
            target_roland = ID_TOPIK_ROLAND_JOCKEY
        else:
            target_berline = ID_TOPIK_BERLINE_ANOTHER
            target_roland = ID_TOPIK_ROLAND_ANOTHER

    try:
        if not PEER_MARKAS_AMEL:
            PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)
            
        from_peer = await msg.get_input_chat()

        await asyncio.gather(
            client_amel(ForwardMessagesRequest(
                from_peer=from_peer, id=[msg.id], to_peer=PEER_MARKAS_AMEL, top_msg_id=target_berline
            )),
            client_amel(ForwardMessagesRequest(
                from_peer=from_peer, id=[msg.id], to_peer=PEER_MARKAS_AMEL, top_msg_id=target_roland
            )),
            return_exceptions=True
        )
        
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
        try: m = await client_amel.get_messages(cid, limit=1); last_id[cid] = m[0].id if m else 0
        except: last_id[cid] = 0
            
    while True:
        await asyncio.sleep(5)
        for cid in SEMUA_BASE_IDS:
            try:
                async for m in client_amel.iter_messages(cid, min_id=last_id[cid], reverse=True):
                    last_id[cid] = max(last_id[cid], m.id)
                    asyncio.create_task(proses_pesan(m, cid))
            except FloodWaitError as e: await asyncio.sleep(e.seconds)
            except: pass

# ==========================================
# 8. SISTEM KONTROL MANAGER & REPLY BERANTAI
# ==========================================
queue_pesan = asyncio.Queue()
RIWAYAT_KOMENTAR = {}  # {msg_id_di_topik: {"tipe": "manager"|"eksekutor", "tim": ..., "targets": [...]}}

def simpan_riwayat(msg_id_topik, data):
    RIWAYAT_KOMENTAR[msg_id_topik] = data
    if len(RIWAYAT_KOMENTAR) > 2000:
        RIWAYAT_KOMENTAR.pop(next(iter(RIWAYAT_KOMENTAR)))

def format_daftar_nama(daftar_nama):
    if not daftar_nama: return ""
    if len(daftar_nama) == 1: return daftar_nama[0]
    if len(daftar_nama) == 2: return f"{daftar_nama[0]} dan {daftar_nama[1]}"
    return ", ".join(daftar_nama[:-1]) + f", dan {daftar_nama[-1]}"

def register_manager_handlers(client_manager, manager_type, my_id, topik_jockey, dict_template, dict_wording):
    @client_manager.on(events.NewMessage(chats=ID_GRUP_UTAMA))
    async def tangkap_command(event):
        if not event.is_reply: return
        
        sender = await event.get_sender()
        if not sender or sender.id != my_id: return

        reply_msg = await event.get_reply_message()
        if not reply_msg: return

        input_teks = event.raw_text.strip()
        cmd_lower = input_teks.lower()

        # -------------------------------------------------------
        # A. JIKA REPLY KE PESAN "✅ ..." (REPLY BERANTAI INSTAN)
        # -------------------------------------------------------
        if reply_msg.id in RIWAYAT_KOMENTAR:
            riwayat = RIWAYAT_KOMENTAR[reply_msg.id]
            if riwayat["tim"] != manager_type:
                return

            if riwayat["tipe"] == "manager":
                target = riwayat["targets"][0]
                teks_kirim = dict_wording.get(cmd_lower, input_teks)
                try:
                    sent = await client_manager.send_message(
                        entity=target["chat_id"],
                        message=teks_kirim,
                        reply_to=target["msg_id"]
                    )
                    simpan_riwayat(event.id, {
                        "tipe": "manager",
                        "tim": manager_type,
                        "targets": [{"chat_id": sent.chat_id, "msg_id": sent.id}]
                    })
                    await event.edit("✅ Balasan mandiri terkirim ke Base!")
                except FloodWaitError as e:
                    await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
                except Exception as e:
                    await event.edit(f"❌ Gagal membalas: {e}")
                return

            elif riwayat["tipe"] == "eksekutor":
                async def balas_eksekutor(t):
                    nama_akun = t["akun"]
                    try:
                        sent = await clients_eksekutor[nama_akun].send_message(
                            entity=t["chat_id"],
                            message=input_teks,
                            reply_to=t["msg_id"]
                        )
                        return (True, STATUS_EKSEKUTOR[nama_akun]["nama"], {
                            "akun": nama_akun, "chat_id": sent.chat_id, "msg_id": sent.id
                        })
                    except FloodWaitError as e:
                        STATUS_EKSEKUTOR[nama_akun]["aktif"] = False
                        asyncio.get_event_loop().run_in_executor(None, save_database)
                        return (False, f"{STATUS_EKSEKUTOR[nama_akun]['nama']} floodwait {e.seconds}s.", None)
                    except Exception:
                        return (False, None, None)

                results = await asyncio.gather(*[balas_eksekutor(t) for t in riwayat["targets"]])
                berhasil = [r[1] for r in results if r[0]]
                targets_baru = [r[2] for r in results if r[0] and r[2]]
                laporan_fw = [r[1] for r in results if not r[0] and r[1]]

                if targets_baru:
                    simpan_riwayat(event.id, {
                        "tipe": "eksekutor",
                        "tim": manager_type,
                        "targets": targets_baru
                    })

                baris = [f"✅ Balasan terkirim oleh {format_daftar_nama(berhasil)}." if berhasil else "❌ Gagal membalas."]
                if laporan_fw: baris.extend(laporan_fw)
                await event.edit("\n".join(baris))
                return

        # -------------------------------------------------------
        # B. JIKA REPLY KE FORWARD-AN MENFESS DARI BASE
        # -------------------------------------------------------
        if not reply_msg.forward: return
        forward_from = reply_msg.forward
        if not forward_from.chat_id or not forward_from.channel_post:
            return

        # Trigger Eksekutor
        if cmd_lower in dict_template:
            asal_thread = reply_msg.reply_to_msg_id if reply_msg.reply_to_msg_id else 0
            jalur = "jockey_money" if asal_thread == topik_jockey else "reguler"
            
            await queue_pesan.put({
                "event": event, "reply_msg": reply_msg, "cmd": cmd_lower, 
                "jalur": jalur, "tim": manager_type, "template": dict_template
            })
            return

        # Command Mandiri Manager (a, b, atau ketikan bebas)
        try:
            teks_kirim = dict_wording.get(cmd_lower, input_teks)
            sent = await client_manager.send_message(
                entity=forward_from.chat_id,
                message=teks_kirim,
                comment_to=forward_from.channel_post
            )
            simpan_riwayat(event.id, {
                "tipe": "manager",
                "tim": manager_type,
                "targets": [{"chat_id": sent.chat_id, "msg_id": sent.id}]
            })
            await event.edit("✅ Berhasil mengirim komentar mandiri ke Base!")
        except FloodWaitError as e:
            await event.edit(f"⏳ Terkena FloodWait {e.seconds} detik.")
        except Exception as e:
            await event.edit(f"❌ Gagal: {e}")

async def worker_eksekutor():
    while True:
        task = await queue_pesan.get()
        event_mgr = task["event"]
        reply_msg = task["reply_msg"]
        
        try:
            forward_from = reply_msg.forward
            chat_asal = forward_from.chat_id
            msg_asal = forward_from.channel_post
            
            akun_bertugas = [
                nama for nama, info in STATUS_EKSEKUTOR.items() 
                if info["aktif"] and (info["jalur"] == task["jalur"] or info["jalur"] == "semua") and info["tim"] == task["tim"]
            ]
            
            async def kirim_pesan_eksekutor(nama_akun):
                try:
                    teks_final = task["template"][task["cmd"]]
                    
                    if task["jalur"] == "jockey_money":
                        teks_final = teks_final.replace("@Berrline", "@.Berrline").replace("@Roland", "@.Roland").replace("@DebugW", "@.DebugW")
                    
                    if task["tim"] == "roland":
                        if nama_akun == "Land": teks_final += " #L"
                        elif nama_akun == "Vasa": teks_final += " #VS"
                    
                    sent = await clients_eksekutor[nama_akun].send_message(
                        entity=chat_asal, message=teks_final, comment_to=msg_asal
                    )
                    return (True, STATUS_EKSEKUTOR[nama_akun]["nama"], {
                        "akun": nama_akun, "chat_id": sent.chat_id, "msg_id": sent.id
                    })
                except FloodWaitError as e:
                    STATUS_EKSEKUTOR[nama_akun]["aktif"] = False
                    asyncio.get_event_loop().run_in_executor(None, save_database)
                    return (False, f"{STATUS_EKSEKUTOR[nama_akun]['nama']} floodwait {e.seconds}s.", None)
                except Exception:
                    return (False, None, None)

            tasks = [kirim_pesan_eksekutor(nama) for nama in akun_bertugas]
            results = await asyncio.gather(*tasks)

            berhasil = [res[1] for res in results if res[0]]
            targets_berhasil = [res[2] for res in results if res[0] and res[2]]
            laporan_floodwait = [res[1] for res in results if not res[0] and res[1]]

            if targets_berhasil:
                simpan_riwayat(event_mgr.id, {
                    "tipe": "eksekutor",
                    "tim": task["tim"],
                    "targets": targets_berhasil
                })

            baris_laporan = [f"✅ Terkirim oleh {format_daftar_nama(berhasil)}." if berhasil else "❌ Gagal terkirim."]
            if laporan_floodwait: baris_laporan.extend(laporan_floodwait)
            
            await event_mgr.edit("\n".join(baris_laporan))
        except Exception as e:
            await event_mgr.edit(f"❌ Error: {e}")
        queue_pesan.task_done()

# ==========================================
# 9. STARTUP SERVICES
# ==========================================
async def start_services():
    global ID_AMEL, ID_BERLINE, ID_ROLAND, PEER_MARKAS_AMEL
    
    print("\n⏳ Menghubungkan akun Amel & Mengisi State Cache Dialogs...")
    await client_amel.start()
    await client_amel.get_dialogs(limit=50)
    ID_AMEL = (await client_amel.get_me()).id
    PEER_MARKAS_AMEL = await client_amel.get_input_entity(ID_GRUP_UTAMA)
    register_amel_handlers(client_amel)
    print(f"✅ Amel Berhasil Terhubung! (ID: {ID_AMEL})")

    print("⏳ Menghubungkan akun Berline...")
    await client_berline.start()
    ID_BERLINE = (await client_berline.get_me()).id
    register_manager_handlers(client_berline, "berline", ID_BERLINE, ID_TOPIK_BERLINE_JOCKEY, TEMPLATE_EKSEKUTOR, WORDING_BERLINE)
    print(f"✅ Berline Berhasil Terhubung! (ID: {ID_BERLINE})")

    print("⏳ Menghubungkan akun Roland...")
    await client_roland.start()
    ID_ROLAND = (await client_roland.get_me()).id
    register_manager_handlers(client_roland, "roland", ID_ROLAND, ID_TOPIK_ROLAND_JOCKEY, TEMPLATE_ROLAND, WORDING_ROLAND)
    print(f"✅ Roland Berhasil Terhubung! (ID: {ID_ROLAND})")

    for nama, client in clients_eksekutor.items():
        print(f"⏳ Menghubungkan eksekutor: {nama}...")
        await client.start()
        me_eks = await client.get_me()
        
        nama_asli = me_eks.first_name or me_eks.username or nama
        STATUS_EKSEKUTOR[nama]["nama"] = nama_asli
        print(f"✅ Terhubung: {nama_asli} ({STATUS_EKSEKUTOR[nama]['tim']})")

    save_database()

    asyncio.create_task(kirim_notifikasi_kesiapan())
    asyncio.create_task(worker_eksekutor())
    asyncio.create_task(poll_fallback())
    
    print("\n🚀 Markas Utama (Berline & Roland) Siap Tempur!\n")

@app.on_event("startup")
async def startup_event(): asyncio.create_task(start_services())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False)
