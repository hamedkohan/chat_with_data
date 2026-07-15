# فرانت‌اند پُرسیت

فایل HTML اپ («تجربهٔ داده») این‌جا قرار می‌گیرد — به‌صورت `index.html`.

> ⚠️ فایل فرانت هنوز اضافه نشده است. فایل HTML خروجی اپ را در همین پوشه با نام
> `index.html` قرار بده (یا در چت آپلود کن تا اضافه شود).

## اتصال به بک‌اند

فرانت وقتی `window.PORSIT_API` ست شده باشد، به‌جای حالت درون‌مرورگری به بک‌اند وصل می‌شود.
بعد از دیپلوی بک‌اند (Render/Railway)، در ابتدای `index.html` و قبل از اسکریپت اپ این خط را بگذار:

```html
<script>window.PORSIT_API = "https://آدرس-بک‌اند-تو";</script>
```

## میزبانی روی GitHub Pages

1. در تنظیمات مخزن: Settings → Pages → Source = «Deploy from a branch».
2. Branch = `main` و Folder = `/frontend` (یا root اگر فایل را به ریشه منتقل کردی).
3. آدرس عمومی: `https://hamedkohan.github.io/chat_with_data/`
