"""
seed.py — ساخت پایگاه‌دادهٔ SQLite «porsit.db» با داده‌های مصنوعی لجستیک بین‌شهری.
پورت مستقیم منطق buildDb() در فرانت‌اند (همان اسکیمای پروتوتایپ).

اجرا:  python seed.py            # ۵۰٬۰۰۰ مرسوله
       python seed.py 20000      # تعداد دلخواه
"""
import sqlite3, math, random, sys, os

DB_PATH = os.path.join(os.path.dirname(__file__), "porsit.db")

CITY = [
    ("تهران","تهران",35.69,51.39,35),("مشهد","خراسان رضوی",36.30,59.61,12),
    ("اصفهان","اصفهان",32.65,51.67,9),("شیراز","فارس",29.59,52.58,7),
    ("تبریز","آذربایجان شرقی",38.08,46.29,6),("کرج","البرز",35.84,50.94,5),
    ("اهواز","خوزستان",31.32,48.67,5),("قم","قم",34.64,50.88,4),
    ("رشت","گیلان",37.28,49.58,3),("کرمانشاه","کرمانشاه",34.31,47.06,3),
    ("یزد","یزد",31.90,54.37,2.5),("بندرعباس","هرمزگان",27.18,56.28,2.5),
    ("کرمان","کرمان",30.28,57.08,2),("زاهدان","سیستان و بلوچستان",29.50,60.86,2),
    ("ارومیه","آذربایجان غربی",37.55,45.07,2),("ساری","مازندران",36.57,53.06,2),
    ("اراک","مرکزی",34.09,49.70,1.5),("همدان","همدان",34.80,48.52,1.5),
]
JMONTH = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
          "مهر","آبان","آذر","دی","بهمن","اسفند"]

def haversine(a, b, c, d):
    R, tr = 6371, math.pi/180
    dLa, dLo = (c-a)*tr, (d-b)*tr
    x = math.sin(dLa/2)**2 + math.cos(a*tr)*math.cos(c*tr)*math.sin(dLo/2)**2
    return round(R*2*math.atan2(math.sqrt(x), math.sqrt(1-x)))

def to_jalaali(gy, gm, gd):
    g = [0,31,59,90,120,151,181,212,243,273,304,334]
    gy2 = gy+1 if gm > 2 else gy
    days = 355666 + 365*gy + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400 + gd + g[gm-1]
    jy = -1595 + 33*(days//12053); days %= 12053
    jy += 4*(days//1461); days %= 1461
    if days > 365:
        jy += (days-1)//365; days = (days-1) % 365
    if days < 186:
        jm = 1 + days//31; jd = 1 + days % 31
    else:
        jm = 7 + (days-186)//30; jd = 1 + (days-186) % 30
    return jy, jm, jd

def wpick(rng, items, weights):
    t = sum(weights); x = rng.random()*t
    for it, w in zip(items, weights):
        x -= w
        if x <= 0:
            return it
    return items[-1]

def gauss(rng, m, s):
    return rng.gauss(m, s)

def build(n=50000):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    c.executescript("""
        CREATE TABLE cities(id INTEGER PRIMARY KEY,name TEXT,province TEXT,lat REAL,lng REAL);
        CREATE TABLE routes(id INTEGER PRIMARY KEY,origin_id INT,dest_id INT,distance_km INT,sla_hours INT);
        CREATE TABLE hubs(id INTEGER PRIMARY KEY,name TEXT,city_id INT);
        CREATE TABLE couriers(id INTEGER PRIMARY KEY,name TEXT,vehicle_type TEXT,hub_id INT);
        CREATE TABLE shipments(id INTEGER PRIMARY KEY,tracking_code TEXT,created_date TEXT,j_year INT,j_month INT,j_month_name TEXT,origin_id INT,dest_id INT,route_id INT,hub_id INT,courier_id INT,weight_kg REAL,cost_toman INT,service_type TEXT,status TEXT,promised_hours INT,actual_hours INT,is_delayed INT,is_delivered INT);
        CREATE TABLE complaints(id INTEGER PRIMARY KEY,shipment_id INT,category TEXT,created_date TEXT,is_resolved INT);
        CREATE TABLE returns(id INTEGER PRIMARY KEY,shipment_id INT,reason TEXT,created_date TEXT);
    """)

    rng = random.Random(987654321)
    C = CITY
    c.executemany("INSERT INTO cities VALUES (?,?,?,?,?)",
                  [(i+1, x[0], x[1], x[2], x[3]) for i, x in enumerate(C)])
    c.executemany("INSERT INTO hubs VALUES (?,?,?)",
                  [(i+1, "هاب "+x[0], i+1) for i, x in enumerate(C)])

    fn = ["علی","رضا","محمد","حسین","مهدی","امیر","سعید","جواد","بهرام","کاوه","فرهاد","یاسر","نیما","پیمان","حامد","مجید"]
    ln = ["محمدی","رضایی","کریمی","موسوی","حسینی","اکبری","نوری","قاسمی","صادقی","رستمی","بابایی","عباسی"]
    veh, vehW = ["موتور","وانت","کامیون"], [0.2,0.55,0.25]
    couriers_by_hub, courier_q, cid = {}, {}, 0
    couriers_rows = []
    for h in range(1, len(C)+1):
        couriers_by_hub[h] = []
        for _ in range(8 + int(rng.random()*8)):
            cid += 1
            v = wpick(rng, veh, vehW)
            name = fn[int(rng.random()*len(fn))] + " " + ln[int(rng.random()*len(ln))]
            couriers_rows.append((cid, name, v, h))
            couriers_by_hub[h].append(cid)
            courier_q[cid] = max(0, gauss(rng, 0.05, 0.14)) + (0.28 if rng.random() < 0.12 else 0)
    c.executemany("INSERT INTO couriers VALUES (?,?,?,?)", couriers_rows)

    route_id, route_stress, route_sla, rid = {}, {}, {}, 0
    routes_rows = []
    for o in range(1, len(C)+1):
        for d in range(1, len(C)+1):
            if o == d:
                continue
            rid += 1
            route_id[o*100+d] = rid
            dist = haversine(C[o-1][2], C[o-1][3], C[d-1][2], C[d-1][3])
            sla = 24 if dist < 300 else 40 if dist < 700 else 56 if dist < 1200 else 80
            routes_rows.append((rid, o, d, dist, sla))
            st = random.Random(o*997 + d*131).random() * 0.4
            on, dn = C[o-1][0], C[d-1][0]
            if (on == "تهران" and dn in ("زاهدان","بندرعباس","کرمان")) or on == "زاهدان" or dn == "زاهدان":
                st += 0.3
            route_stress[rid] = st
            route_sla[rid] = sla
    c.executemany("INSERT INTO routes VALUES (?,?,?,?,?)", routes_rows)

    svc, svcW = ["عادی","اکسپرس","ویژه"], [0.62,0.30,0.08]
    svcT = {"عادی":1.0,"اکسپرس":0.55,"ویژه":0.75}
    svcC = {"عادی":1.0,"اکسپرس":1.7,"ویژه":2.4}
    cityW = [x[4] for x in C]
    cpCat, cpCatW = ["آسیب","گم‌شدن","برخورد نامناسب","هزینه","تأخیر"], [0.28,0.14,0.24,0.2,0.14]
    retR, retW = ["آدرس اشتباه","عدم حضور مشتری","آسیب کالا","انصراف مشتری"], [0.3,0.3,0.2,0.2]

    from datetime import datetime, timedelta
    end = datetime(2026, 7, 13)
    ships, comps, rets = [], [], []
    comp_id = ret_id = 0
    for i in range(1, n+1):
        off = int(400 * (1 - rng.random()**1.6))
        dt = end - timedelta(days=off)
        gy, gm, gd = dt.year, dt.month, dt.day
        iso = f"{gy:04d}-{gm:02d}-{gd:02d}"
        jy, jm, _ = to_jalaali(gy, gm, gd)
        jn = JMONTH[jm-1]
        o = C.index(wpick(rng, C, cityW)) + 1
        d = o
        while d == o:
            d = C.index(wpick(rng, C, cityW)) + 1
        route = route_id[o*100+d]
        service = wpick(rng, svc, svcW)
        base = route_sla[route]
        promised = max(6, round(base * svcT[service]))
        dist = haversine(C[o-1][2], C[o-1][3], C[d-1][2], C[d-1][3])
        weight = round((0.5 + rng.random()**3 * 29) * 10) / 10
        cost = round((25000 + dist*300 + weight*3500) * svcC[service] / 1000) * 1000
        hub = o
        cour = couriers_by_hub[hub][int(rng.random()*len(couriers_by_hub[hub]))]
        delivered = delayed = 0
        actual = None
        if off <= 6:
            status = wpick(rng, ["در حال ارسال","در هاب","تحویل‌شده"], [0.45,0.2,0.35])
        else:
            rr = rng.random()
            status = "مرجوع‌شده" if rr < 0.035 else "لغو‌شده" if rr < 0.05 else "تحویل‌شده"
        if status == "تحویل‌شده":
            delivered = 1
            seas = 0.18 if jm >= 10 else 0.08 if jm == 9 else 0
            mean = 0.82 + route_stress[route] + courier_q[cour] + seas
            if service == "اکسپرس":
                mean *= 0.9
            f = max(0.45, min(3.2, gauss(rng, mean, 0.22)))
            actual = max(2, round(promised * f))
            delayed = 1 if actual > promised else 0
        ships.append((i, "PS"+str(100000+i), iso, jy, jm, jn, o, d, route, hub, cour,
                      weight, cost, service, status, promised, actual, delayed, delivered))
        p = 0.025 + (0.20 if delayed else 0) + (0.35 if status == "مرجوع‌شده" else 0) + (0.12 if status == "لغو‌شده" else 0)
        if rng.random() < p:
            comp_id += 1
            if delayed:
                cat = "تأخیر" if rng.random() < 0.8 else wpick(rng, ["برخورد نامناسب","هزینه"], [0.5,0.5])
            else:
                cat = wpick(rng, cpCat, cpCatW)
            cdt = dt + timedelta(days=int(rng.random()*4)+1)
            ciso = f"{cdt.year:04d}-{cdt.month:02d}-{cdt.day:02d}"
            comps.append((comp_id, i, cat, ciso, 1 if rng.random() < 0.68 else 0))
        if status == "مرجوع‌شده":
            ret_id += 1
            rets.append((ret_id, i, wpick(rng, retR, retW), iso))

    c.executemany("INSERT INTO shipments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ships)
    c.executemany("INSERT INTO complaints VALUES (?,?,?,?,?)", comps)
    c.executemany("INSERT INTO returns VALUES (?,?,?,?)", rets)
    c.executescript("""
        CREATE INDEX ix1 ON shipments(created_date);
        CREATE INDEX ix2 ON shipments(origin_id,dest_id);
        CREATE INDEX ix3 ON shipments(route_id);
        CREATE INDEX ix4 ON shipments(status);
        CREATE INDEX ix5 ON shipments(service_type);
        CREATE INDEX ix6 ON shipments(courier_id);
        CREATE INDEX ix7 ON shipments(j_year,j_month);
        CREATE INDEX ix8 ON complaints(shipment_id);
    """)
    db.commit()
    db.close()
    print(f"✅ ساخته شد: {DB_PATH} — {n} مرسوله، {comp_id} شکایت، {ret_id} مرجوعی")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    build(n)
