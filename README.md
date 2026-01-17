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
- [ ] Foydalanuvchi autentifikatsiyasi (Login/Signup)
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
