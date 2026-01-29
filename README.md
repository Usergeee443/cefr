# CEFR Mock Test Platform

CEFR imtihoniga tayyorgarlik ko'rish uchun eng yaxshi platforma. AI baholash, shaxsiy tavsiyalar va real natijalar.

## Xususiyatlar

- 🎯 **99% rasmiy formatga mos** - Real CEFR imtihoniga juda yaqin
- 🤖 **AI baholash** - Sun'iy intellekt yordamida professional tahlil
- 📊 **Zaif tomonlarni aniqlash** - Qaysi ko'nikmalarda yaxshilash kerak
- 📈 **Progress kuzatish** - O'sishingizni kuzatib boring
- 💡 **Shaxsiy tavsiyalar** - AI dan maxsus yo'riqnomalar

## Test ko'nikmalari

### Mavjud

- ✅ **Listening** - Turli xil aksent va tezlikda audio testlar
- ✅ **Reading** - Akademik va kundalik matnlarni tushunish
- ✅ **Writing** - AI tomonidan batafsil baholanadigan yozma ishlar

### Rejada

- ⏳ **Speaking** - AI bilan interaktiv suhbat (keyingi versiya)

## Tariflar

### Basic - $19
- 5 ta test
- AI baholash
- Cheklangan tahlil
- Alohida: $5/test = $25 (arzon!)

### Standard - $59 (OMMABOP)
- 20 ta test
- To'liq AI tahlil
- Zaif tomonlar tavsiyasi
- Progress kuzatish
- Alohida: $5/test = $100 (70% tejash!)

### Custom
- 1-100 ta test
- Moslashuvchan
- Qancha ko'p - shuncha arzon

## Texnologiyalar

- **Backend**: FastAPI (Python)
- **Frontend**: HTML + Tailwind CSS
- **AI**: OpenAI API (Writing baholash)
- **Database**: PostgreSQL (keyingi bosqich)

## O'rnatish va ishga tushirish

### Talablar

- Python 3.8+
- pip

### Qadamlar

1. Repository'ni klonlang:
```bash
git clone <repository-url>
cd cefr
```

2. Virtual environment yarating:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

3. Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

4. Ilovani ishga tushiring:
```bash
python app.py
```

5. Brauzerda quyidagi manzilni oching:
```
http://localhost:8000
```

### Ro'yxatdan o'tish va Google bilan kirish

- **Ro'yxatdan o'tish**: `/register` — email, parol va ism bilan.
- **Kirish**: `/login` — email/parol yoki **Google bilan kirish**.
- **Profil**: `/profile` — faqat tizimga kirgan foydalanuvchilar uchun.

**Google OAuth sozlash** (Google bilan kirish uchun):

1. [Google Cloud Console](https://console.cloud.google.com/) → loyihangizni tanlang.
2. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID** (yoki mavjud Client ID ni tanlang).
3. **Application type**: **Web application**.
4. **Muhim** — **Authorized redirect URIs** bo'limida **ikkala** manzilni qo'shing (brauzer qaysi manzilda ochilganiga qarab bittasi ishlatiladi):
   - `http://localhost:8000/auth/google/callback`
   - `http://127.0.0.1:8000/auth/google/callback`
   - **Authorized JavaScript origins** (ixtiyoriy): `http://localhost:8000` va `http://127.0.0.1:8000`
5. **Save** bosing.
6. `.env` da: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback`.

**Agar "redirect_uri_mismatch" (Error 400) chiqsa:**

- **Authorized redirect URIs** bo'limida (Credentials → OAuth 2.0 Client ID → Edit) quyidagidan **bitta** bo'lsin, boshqa belgi qo'shilmasin:
  ```
  http://localhost:8000/auth/google/callback
  ```
- Bosh sahifa yoki boshqa manzil emas, **faqat** `/auth/google/callback` bilan tugaydigan manzil.
- Orqasida `/` qo'yilmagan bo'lsin: `.../callback` ✅, `.../callback/` ❌.
- Loyiha va Client ID shu loyiha uchun yaratilgan bo'lsin (Client ID ning birinchi qismi 957401626494).

Testni boshlash uchun avval **Kirish** yoki **Ro'yxatdan o'tish** kerak.

## Render'ga deploy qilish

1. **Render.com** da hisob oching va [Dashboard](https://dashboard.render.com/) → **New** → **Web Service**.
2. Repo ulang (GitHub/GitLab). Loyiha papkasi **cefr** bo‘lsa, **Root Directory** da `cefr` yozing.
3. Sozlamalar:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. **Environment** (Environment Variables) da qo‘shing:

   | Key | Value |
   |-----|--------|
   | `SECRET_KEY` | Tasodifiy maxfiy kalit (session uchun) |
   | `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
   | `GOOGLE_CLIENT_SECRET` | Google OAuth Client secret |
   | `GOOGLE_REDIRECT_URI` | `https://YOUR-APP.onrender.com/auth/google/callback` |
   | `OPENAI_API_KEY` | (ixtiyoriy) Writing AI baholash uchun |

5. **Save** → deploy boshlanadi. Birinchi build 2–5 daqiqa davom etishi mumkin.
6. **Google OAuth:** Google Cloud Console → Credentials → OAuth 2.0 Client ID → **Authorized redirect URIs** ga production manzilni qo‘shing:
   - `https://YOUR-APP.onrender.com/auth/google/callback`
   - (localhost manzillari ham qolsin, agar lokalda ham test qilsangiz.)

**Eslatma:** Render bepul planida servis 15 daqiqa ishlamasa uyquga ketadi; birinchi so‘rov biroz sekin bo‘lishi mumkin.

## Loyiha strukturasi

```
cefr/
├── app.py              # FastAPI asosiy fayli
├── templates/          # HTML shablon fayllari
│   └── index.html      # Landing page
├── static/             # Statik fayllar
│   ├── css/           # CSS fayllari
│   ├── js/            # JavaScript fayllari
│   └── images/        # Rasm fayllari
├── requirements.txt    # Python dependencies
└── README.md          # Bu fayl
```

## Keyingi bosqichlar (Roadmap)

### Faza 2
- [x] Foydalanuvchi autentifikatsiyasi (Login/Signup, Google OAuth, Profil)
- [ ] Test funksionalligini to'liq ishlatish
- [ ] Natijalarni saqlash (PostgreSQL)
- [ ] Batafsil progress dashboard

### Faza 3
- [ ] Speaking moduli (AI bilan)
- [ ] Progress chart va statistika
- [ ] Shaxsiy cabinet
- [ ] Test tarixi

### Faza 4
- [ ] Mobile ilova
- [ ] CEFR sertifikat mock PDF
- [ ] Ko'proq test varianti
- [ ] Multi-til qo'llab-quvvatlash

## Litsenziya

Copyright © 2026 CEFR Test Platform. Barcha huquqlar himoyalangan.

## Bog'lanish

- Email: info@cefrtest.uz
- Telegram: @cefrtest
- Website: https://cefrtest.uz
