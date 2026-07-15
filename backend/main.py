"""
main.py — بک‌اند پُرسیت (FastAPI + OpenAI).
- endpoint اصلی: POST /api/v1/ask
- کلید OpenAI فقط این‌جا (سمت سرور) خوانده می‌شود؛ هرگز به فرانت/گیت نمی‌رود.
- تبدیل زبان طبیعی به SQL با tool-calling، اجرای «فقط SELECT» روی SQLite با اعتبارسنجی.
اجرا (محلی):  uvicorn main:app --reload --port 8000
"""
import os, re, json, sqlite3, time, hmac
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_PATH = os.path.join(os.path.dirname(__file__), "porsit.db")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- مدیریت کلید OpenAI ---
# اولویت: کلیدی که ادمین از صفحهٔ /admin وارد کرده (فایل .runtime_key) → متغیر محیطی.
# توجه: در هاست‌های با دیسک موقت (مثل پلن رایگان Render) این فایل بعد از ری‌استارت
# پاک می‌شود؛ متغیر محیطی OPENAI_API_KEY راه ماندگار است و /admin راه سریع/چرخش کلید.
KEY_FILE = os.path.join(os.path.dirname(__file__), ".runtime_key")
_runtime_key = None
try:
    with open(KEY_FILE) as _f:
        _runtime_key = _f.read().strip() or None
except OSError:
    pass

def current_key() -> str:
    return _runtime_key or os.getenv("OPENAI_API_KEY") or ""

def get_client() -> OpenAI:
    key = current_key()
    if not key:
        raise HTTPException(503, "کلید OpenAI هنوز تنظیم نشده است؛ از صفحهٔ /admin آن را وارد کنید.")
    return OpenAI(api_key=key)

if not os.path.exists(DB_PATH):
    print("porsit.db یافت نشد — در حال ساخت…")
    import seed
    seed.build(50000)

# --- بازهٔ زمانی داده برای پرامپت ---
def _date_range():
    db = sqlite3.connect(DB_PATH)
    row = db.execute(
        "SELECT j_month_name||' '||j_year FROM shipments ORDER BY j_year,j_month LIMIT 1"
    ).fetchone()
    row2 = db.execute(
        "SELECT j_month_name||' '||j_year FROM shipments ORDER BY j_year DESC,j_month DESC LIMIT 1"
    ).fetchone()
    db.close()
    return (row[0] if row else ""), (row2[0] if row2 else "")

MIN_NAME, MAX_NAME = _date_range()

SYSTEM_PROMPT = f"""تو تحلیل‌گر دادهٔ ابزار «پُرسیت» برای یک شرکت لجستیک بین‌شهری (مثل تیپاکس) هستی. یک پایگاه‌دادهٔ SQLite در دسترس داری. برای هر پاسخ حتماً از ابزار run_sql استفاده کن (فقط SELECT) و بر اساس نتیجهٔ واقعی جواب بده.

اسکیمای دیتابیس:
- cities(id, name, province, lat, lng)
- routes(id, origin_id→cities.id, dest_id→cities.id, distance_km, sla_hours)
- hubs(id, name, city_id)
- couriers(id, name, vehicle_type ['موتور','وانت','کامیون'], hub_id→hubs.id)
- shipments(id, tracking_code, created_date TEXT 'YYYY-MM-DD', j_year, j_month 1..12, j_month_name فارسی, origin_id, dest_id, route_id, hub_id, courier_id, weight_kg, cost_toman, service_type ['عادی','اکسپرس','ویژه'], status ['تحویل‌شده','در حال ارسال','در هاب','مرجوع‌شده','لغو‌شده'], promised_hours, actual_hours, is_delayed 0/1, is_delivered 0/1)
- complaints(id, shipment_id, category ['تأخیر','آسیب','گم‌شدن','برخورد نامناسب','هزینه'], created_date, is_resolved 0/1)
- returns(id, shipment_id, reason, created_date)

نکات:
- نام شهرها در cities است؛ برای نام مبدأ/مقصد JOIN بزن.
- تأخیر و SLA فقط برای تحویل‌شده‌ها (is_delivered=1)؛ نرخ تأخیر = AVG(is_delayed).
- برای «مسیر» مبدأ+مقصد را گروه‌بندی کن.
- بازهٔ داده از {MIN_NAME} تا {MAX_NAME}. «اخیر» یعنی چند ماه آخر. برای روند بر اساس (j_year,j_month) مرتب کن و برچسب = j_month_name.
- هزینه به تومان.

حافظهٔ گفت‌وگو: به پیام‌های قبلی توجه کن. اگر کاربر گفت «همون برای اصفهان» یا «چرا؟» منظورش ادامهٔ همان تحلیل قبلی است.
مقایسه: هرجا معنادار است مقدار را با دورهٔ قبل یا میانگین مقایسه کن و kpi.delta و kpi.dir ('up'|'down') و kpi.sentiment ('good'|'bad'|'neutral' از دید کسب‌وکار: مثلاً تأخیر بالاتر=bad، تحویلِ به‌موقعِ بالاتر=good) را پر کن.
«چرا؟»: چند کوئری پشت‌سرهم بزن (تفکیک بر اساس مسیر، ماه، راننده، نوع سرویس، فصل...) و علتِ ریشه‌ای را در summary توضیح بده.
پیش‌بینی: اگر خواستند، نقاط ماه‌های آینده را به labels/values اضافه کن و chart.predicted را برابر تعداد نقاط پیش‌بینی‌شده بگذار.
اگر سؤال مبهم یا خارج از دادهٔ موجود است، به‌جای حدس، فقط این را بده: {{"clarify":"یک سؤال کوتاه روشن‌کننده","options":["گزینه ۱","گزینه ۲","گزینه ۳"]}}

در غیر این صورت پاسخ نهایی را «فقط و فقط» یک شیء JSON بده (بدون متن اضافه، بدون بک‌تیک/markdown):
{{"headline":"جملهٔ کوتاه نتیجه","kpi":{{"value":"مثلاً ۸۴٪","delta":"۵٪ یا null","dir":"up|down|null","sentiment":"good|bad|neutral"}}|null,"stats":[{{"label":"...","value":"...","delta":"...","dir":"up|down|null","sentiment":"good|bad|neutral"}}]|null,"chart":{{"type":"bar|hbar|line","labels":["..."],"values":[عدد...],"unit":"...","predicted":0}}|null,"table":{{"columns":["..."],"rows":[["..."]]}}|null,"summary":"۱ تا ۲ جملهٔ تحلیلی","followups":["سؤال ۱","سؤال ۲","سؤال ۳"]}}

قواعد نمودار: رتبه‌بندی→hbar، روند زمانی→line یا bar با برچسب ماه، تک‌عدد→kpi، چند شاخصِ خلاصه→stats. حداکثر ۱۲ نقطه و ۸ سطر. values عددِ خام. همهٔ متن‌ها فارسی."""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": "اجرای یک کوئری SELECT روی دیتابیس لجستیک و بازگرداندن نتایج JSON",
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "یک کوئری معتبر SQLite از نوع SELECT"}},
            "required": ["sql"],
        },
    },
}]

_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)

def run_sql(sql: str) -> str:
    s = (sql or "").strip()
    if not re.match(r"^\s*select", s, re.I):
        return json.dumps({"error": "فقط کوئری SELECT مجاز است"}, ensure_ascii=False)
    body = s.rstrip(";")
    if ";" in body or _FORBIDDEN.search(body):
        return json.dumps({"error": "فقط یک کوئری SELECT ساده مجاز است"}, ensure_ascii=False)
    if not re.search(r"\blimit\b", body, re.I):
        body += " LIMIT 1000"
    try:
        # اتصال فقط‌خواندنی
        db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        db.execute("PRAGMA query_only = ON")
        cur = db.execute(body)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchmany(100)]
        db.close()
        return json.dumps({"columns": cols, "rows": rows}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

app = FastAPI(title="PORSIT API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_methods=["*"], allow_headers=["*"],
)

class AskReq(BaseModel):
    question: str
    history: list = []

@app.get("/")
def health():
    return {"ok": True, "range": [MIN_NAME, MAX_NAME], "key_configured": bool(current_key())}

# --- پنل ادمین: واردکردن کلید OpenAI بدون رفتن به داشبورد هاست ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

ADMIN_HTML = """<!DOCTYPE html>
<html dir="rtl" lang="fa"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>پنل ادمین پُرسیت</title>
<style>
 body{font-family:Tahoma,Vazirmatn,sans-serif;background:#faf9f5;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
 .card{background:#fff;border-radius:16px;box-shadow:0 2px 16px rgba(0,0,0,.08);padding:32px;width:min(420px,90vw)}
 h1{font-size:18px;margin:0 0 4px}
 p{color:#666;font-size:13px;margin:0 0 20px;line-height:1.8}
 label{display:block;font-size:13px;margin:12px 0 6px}
 input{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;direction:ltr}
 button{width:100%;margin-top:20px;padding:12px;border:0;border-radius:10px;background:linear-gradient(135deg,#ff8a3d,#ff6a00);color:#fff;font-size:15px;cursor:pointer}
 #msg{margin-top:14px;font-size:13px;line-height:1.8;white-space:pre-wrap}
 .ok{color:#1a7f37}.err{color:#c62828}
</style></head><body>
<div class="card">
 <h1>پنل ادمین پُرسیت</h1>
 <p>کلید OpenAI را این‌جا وارد کن؛ کلید فقط روی سرور ذخیره می‌شود و هرگز به فرانت یا Git نمی‌رود.</p>
 <label>رمز ادمین (ADMIN_PASSWORD)</label>
 <input id="pw" type="password" autocomplete="current-password">
 <label>کلید OpenAI (sk-...)</label>
 <input id="key" type="password" autocomplete="off" placeholder="sk-...">
 <button onclick="save()">ذخیرهٔ کلید</button>
 <div id="msg"></div>
</div>
<script>
async function save(){
  const m=document.getElementById('msg'); m.textContent='در حال ذخیره…'; m.className='';
  try{
    const r=await fetch('/admin/key',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({password:document.getElementById('pw').value,key:document.getElementById('key').value})});
    const d=await r.json();
    if(r.ok){m.textContent='✅ '+d.message; m.className='ok';}
    else{m.textContent='❌ '+(d.detail||'خطا'); m.className='err';}
  }catch(e){m.textContent='❌ '+e; m.className='err';}
}
</script></body></html>"""

class AdminKeyReq(BaseModel):
    password: str
    key: str

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return ADMIN_HTML

@app.post("/admin/key")
def admin_set_key(req: AdminKeyReq):
    global _runtime_key
    if not ADMIN_PASSWORD:
        raise HTTPException(403, "پنل ادمین غیرفعال است؛ ابتدا متغیر محیطی ADMIN_PASSWORD را روی سرور ست کنید.")
    if not hmac.compare_digest(req.password or "", ADMIN_PASSWORD):
        time.sleep(1)  # کندکردن حدس‌زدن رمز
        raise HTTPException(403, "رمز ادمین نادرست است.")
    key = (req.key or "").strip()
    if not key.startswith("sk-") or len(key) < 20:
        raise HTTPException(400, "کلید معتبر به نظر نمی‌رسد (باید با sk- شروع شود).")
    _runtime_key = key
    try:
        with open(KEY_FILE, "w") as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
        persisted = "و ذخیره شد"
    except OSError:
        persisted = "(فقط در حافظه — بعد از ری‌استارت باید دوباره وارد شود)"
    masked = key[:6] + "…" + key[-4:]
    return {"message": f"کلید {masked} فعال {persisted}. حالا «پرسیدن» در اپ کار می‌کند."}

@app.post("/api/v1/ask")
def ask(req: AskReq):
    if not req.question.strip():
        raise HTTPException(400, "سؤال خالی است")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in (req.history or [])[-8:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])})
    messages.append({"role": "user", "content": req.question})

    client = get_client()
    last_sql = ""
    t0 = time.time()
    try:
        for _ in range(6):
            resp = client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS,
                tool_choice="auto", temperature=0, max_tokens=2200,
            )
            msg = resp.choices[0].message
            if msg.tool_calls:
                messages.append(msg.model_dump(exclude_none=True))
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    sql = args.get("sql", "")
                    last_sql = sql or last_sql
                    result = run_sql(sql)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                continue
            return {"text": msg.content or "", "sql": last_sql, "elapsed_ms": int((time.time()-t0)*1000)}
        return {"text": "", "sql": last_sql, "elapsed_ms": int((time.time()-t0)*1000)}
    except Exception as e:
        raise HTTPException(502, f"خطای مدل: {e}")
