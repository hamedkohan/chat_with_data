# فرانت‌اند پُرسیت

`index.html` نسخهٔ مستقل (standalone) اپ است: تمام منابع داخلش باندل شده و بیرون از
هر محیط خاصی — روی GitHub Pages، Netlify یا حتی با دابل‌کلیک — اجرا می‌شود.

## اتصال به بک‌اند

نزدیک ابتدای `index.html` (حدود خط ۱۴) این بلوک هست:

```html
// window.PORSIT_API = "https://YOUR-BACKEND-URL";
```

بعد از دیپلوی بک‌اند (Render/Railway)، خط را از کامنت دربیاور و آدرس واقعی را بگذار:

```html
window.PORSIT_API = "https://porsit-api.onrender.com";
```

- **با `PORSIT_API` ست‌شده:** سؤال‌ها به بک‌اند تو (و OpenAI سمت سرور) می‌روند.
- **بدون آن:** اپ در حالت درون‌مرورگری بالا می‌آید (دیتابیس نمونه را در خود مرورگر
  می‌سازد؛ برای این حالت اینترنت لازم است چون sql.js از CDN بارگیری می‌شود) ولی
  بخش هوش مصنوعی بدون بک‌اند جواب نمی‌دهد.

راه جایگزین برای تست سریع بدون تغییر فایل، در کنسول مرورگر:
`localStorage.setItem('porsit_api','http://localhost:8000')` و رفرش.

## میزبانی روی GitHub Pages

workflow آماده است (`.github/workflows/pages.yml`) و با هر push به `main` پوشهٔ
`frontend/` را دیپلوی می‌کند. فقط یک بار:

1. Settings → Pages → Source را روی **«GitHub Actions»** بگذار.
2. آدرس عمومی: `https://hamedkohan.github.io/chat_with_data/`
3. در پنل Render متغیر `CORS_ORIGINS` را روی `https://hamedkohan.github.io` ست کن.
