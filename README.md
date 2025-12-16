# VFS Visa Checker

VFS Global vize randevu kontrol sistemi. Otomatik olarak randevu müsaitliğini kontrol eder ve bulunduğunda bildirim gönderir.

## Özellikler

- 🔍 Otomatik randevu kontrolü
- 🤖 CAPTCHA çözme (CapSolver entegrasyonu)
- 📱 OTP desteği (Email/SMS)
- 📢 Telegram bildirimleri
- 🌐 Modern web arayüzü
- ⚡ WebSocket ile gerçek zamanlı güncelleme

## Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/akbyhakan/visa_check.git
cd visa_check

# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r backend/requirements.txt
playwright install chromium

# Environment dosyasını yapılandır
cp .env.example .env
# .env dosyasını düzenle
```

## Yapılandırma

`.env` dosyasında aşağıdaki değişkenleri ayarlayın:

```env
VFS_EMAIL=your-email@example.com
VFS_PASSWORD=your-password
CAPSOLVER_API_KEY=your-capsolver-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## Kullanım

```bash
# Uygulamayı başlat
uvicorn backend.main:app --reload

# Tarayıcıda aç
# http://localhost:8000
```

## Proje Yapısı

```
visa_check/
├── backend/
│   ├── auth/           # Kimlik doğrulama
│   ├── core/           # Tarayıcı ve CAPTCHA
│   ├── scanner/        # Randevu tarama
│   ├── notifications/  # Bildirimler
│   ├── health/         # Sağlık kontrolü
│   ├── utils/          # Yardımcı fonksiyonlar
│   └── main.py         # FastAPI uygulaması
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── requirements.txt
```

## Lisans

MIT License