# بک‌اند پُرسیت — راه‌اندازی و دیپلوی

بک‌اند FastAPI که سؤال فارسی را با OpenAI به SQL تبدیل و روی SQLite اجرا می‌کند.
**کلید OpenAI فقط این‌جا (سمت سرور) است و هرگز در Git یا فرانت قرار نمی‌گیرد.**

## اجرای محلی
```bash
cd backend
python -m venv venv && source venv/bin/activate      # ویندوز: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # و OPENAI_API_KEY خودت را داخلش بگذار
python seed.py                # ساخت porsit.db (~۵۰٬۰۰۰ ردیف)
uvicorn main:app --reload --port 8000
```
تست: `http://localhost:8000/` باید `{"ok":true,...}` بدهد.

## وصل‌کردن فرانت‌اند به بک‌اند
فرانت وقتی `window.PORSIT_API` ست شده باشد، به‌جای حالت درون‌مرورگری به این بک‌اند وصل می‌شود.
دو راه:
1. در کنسول مرورگر (تست سریع): `localStorage.setItem('porsit_api','http://localhost:8000')` و رفرش.
2. برای نسخهٔ منتشرشده: قبل از اسکریپت اپ، این خط را در HTML بگذار:
   ```html
   <script>window.PORSIT_API = "https://porsit-api.onrender.com";</script>
   ```

## دیپلوی (چند گزینه)

### Render (ساده‌ترین، رایگان)
1. ریپو را به Render وصل کن → New → Web Service.
2. Root Directory = `backend`، Environment = Docker (یا Python).
3. متغیر محیطی `OPENAI_API_KEY` و در صورت نیاز `CORS_ORIGINS` (دامنهٔ فرانتت) را ست کن.
4. Deploy. آدرسی مثل `https://porsit-api.onrender.com` می‌گیری → همان را در `PORSIT_API` بگذار.

### Railway / Fly.io
همان الگو: پوشهٔ `backend`، متغیر `OPENAI_API_KEY`، از `Dockerfile` استفاده می‌کنند.

### نکات تولید
- `CORS_ORIGINS` را به دامنهٔ دقیق فرانت محدود کن (نه `*`).
- برای بار بالا، `porsit.db` را در build بساز (Dockerfile این کار را می‌کند) یا به PostgreSQL مهاجرت کن
  (اسکیمای آمادهٔ `../design_handoff_porsit_backend/database_schema.sql`).
- rate-limit روی `/ask` بگذار تا مصرف OpenAI کنترل شود.

## این بک‌اند چه چیزی را پوشش نمی‌دهد (فعلاً)
احراز هویت/مدیریت کاربر روی سرور. UIِ آن در فرانت به‌صورت پروتوتایپ (localStorage) هست؛ برای نسخهٔ
سروری، endpointهای `/auth/*` و `/users/*` و اسکیمای کاربر در بستهٔ هندآف آماده است و همین‌جا قابل افزودن.

## استفاده با AI Gateway پرسیت (به‌جای کلید مستقیم OpenAI)

بک‌اند هر درگاه سازگار با OpenAI را پشتیبانی می‌کند. در صفحهٔ `/admin` کافی است کلید
`porsit_sk_...` را وارد کنی؛ آدرس درگاه (`https://api-gateway.porsit.cloud/v1`) و مدل
(`gpt-4.1-mini`) خودکار تنظیم می‌شوند. اگر درگاه یا مدل دیگری می‌خواهی، همان‌جا در
فیلدهای اختیاری بنویس (مثلاً مدل `gpt-4.1-nano` یا `porsit-2.4`).
معادل env: `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL`.
