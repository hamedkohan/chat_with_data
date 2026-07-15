# پُرسیت — گفت‌وگو با داده (Chat with Data)

تحلیل‌گر دادهٔ فارسی برای یک شرکت لجستیک بین‌شهری: سؤال را به زبان طبیعی می‌پرسید،
هوش مصنوعی آن را به SQL تبدیل می‌کند، روی پایگاه‌دادهٔ ~۵۰٬۰۰۰ ردیفی اجرا می‌کند و
جواب را با نمودار و KPI برمی‌گرداند.

## ساختار مخزن

```
chat_with_data/
├── backend/    ← بک‌اند FastAPI + OpenAI + SQLite (کلید OpenAI فقط این‌جا، سمت سرور)
└── frontend/   ← فرانت‌اند استاتیک (فایل HTML اپ این‌جا قرار می‌گیرد)
```

## شروع سریع (محلی)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # ویندوز: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # کلید OPENAI_API_KEY خودت را داخل .env بگذار
python seed.py             # ساخت porsit.db (~۵۰٬۰۰۰ ردیف)
uvicorn main:app --reload --port 8000
```

تست سلامت: `http://localhost:8000/` باید `{"ok":true,...}` برگرداند.

## دیپلوی

1. **بک‌اند** را روی Render/Railway دیپلوی کن (Root Directory = `backend`، از `Dockerfile` استفاده می‌شود)
   و متغیر محیطی `OPENAI_API_KEY` را در پنل همان سرویس ست کن — **نه در Git**.
2. در فرانت، قبل از اسکریپت اپ این خط را بگذار:
   ```html
   <script>window.PORSIT_API = "https://آدرس-بک‌اند-تو";</script>
   ```
3. **فرانت** را روی GitHub Pages / Netlify میزبانی کن → لینک عمومی کاملاً کارا.

راهنمای کامل دیپلوی در [`backend/README.md`](backend/README.md).

## امنیت کلید

کلید OpenAI هرگز وارد Git نمی‌شود: فایل `.env` در `.gitignore` است و کلید فقط
به‌صورت متغیر محیطی روی سرور (Render/Railway) قرار می‌گیرد.
