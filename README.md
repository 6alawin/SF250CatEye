# CatEye - SF250 byPiranYaa

เว็บ Demo สำหรับวิเคราะห์และคัดกรองนักฟุตบอลจากสถิติ Openplay โดยดึงข้อมูลผ่าน Flask API จาก Render PostgreSQL ผู้ใช้เปิด `index.html` แล้วเลือกลีก ฤดูกาล ตำแหน่ง และผู้เล่นได้ทันที ไม่ต้องอัปโหลด CSV เอง

## ความสามารถ

- **Player profile:** แสดงนาทีและจำนวนเกม, Goals, Assists และตัวชี้วัดที่เลือกตามตำแหน่ง เช่น Team Clean Sheets สำหรับ GK/กองหลัง, Saves สำหรับ GK, Tackles/Interceptions สำหรับกองหลัง และ xG/xA สำหรับแนวรุก
- **Player similarity:** เรียงผู้เล่นที่มีรูปแบบสถิติใกล้กับ Reference
- **Role ranking:** เลือกบทบาท แล้วจัดอันดับ Candidate ด้วยคะแนน percentile แยกตามหมวดของบทบาท
- **ตัวกรอง Candidate:** ลีก, ทีม, ช่วงฤดูกาล, ตำแหน่ง, อายุ และนาทีลงเล่นขั้นต่ำ
- **Heatmap:** เปรียบเทียบการกระจาย Event ของ Candidate กับ Reference จากข้อมูล Big Five ที่รวมเป็นโซนสนาม
- **CatEye Estimate:** ใช้มูลค่า Transfermarkt เป็นฐาน แล้วปรับตาม percentile ของสถิติเฉพาะตำแหน่ง แสดงเป็นช่วงราคาและรายงานฐาน/คะแนน/จำนวนผู้เล่นเทียบ

## วิธีประเมินราคา

1. เลือกผู้เล่นเทียบจาก position family เดียวกัน ซึ่งมีอย่างน้อย 450 นาทีและมีมูลค่า Transfermarkt
2. ถ้าหากลุ่มผู้เล่นอายุห่างไม่เกิน 4 ปีได้อย่างน้อย 5 คน จะใช้กลุ่มนั้น มิฉะนั้นขยายเป็นผู้เล่นตำแหน่งเดียวกันทั้งหมด
3. คำนวณ **Stats score** เป็นค่าเฉลี่ย percentile ของตัวชี้วัดตามตำแหน่ง โดยกลับทิศสถิติที่ค่าน้อยดีกว่า เช่น Errors
4. ใช้มูลค่า Transfermarkt ของผู้เล่นเป็นฐาน หากไม่มี จะใช้ค่ากลางของมูลค่า Transfermarkt จากผู้เล่นสถิติใกล้กันสูงสุด 15 คน
5. คำนวณค่ากลางด้วย `ฐานราคา × (1 + (Stats score − 50) / 250)` ตัวคูณจึงอยู่ระหว่าง 0.80–1.20
6. แสดงช่วงรอบค่ากลาง ±12% เมื่อมีผู้เล่นเทียบอย่างน้อย 12 คนและผู้เล่นลงเล่นอย่างน้อย 1,800 นาที, ±20% เมื่อมีอย่างน้อย 8 คนและ 900 นาทีขึ้นไป และ ±30% ในกรณีอื่น หากทราบอายุแต่จับคู่กลุ่มอายุไม่ได้ จะเพิ่มความกว้างอีก 5% สูงสุด 35%

ต้องมีผู้เล่นเทียบอย่างน้อย 5 คนจึงจะแสดงราคา ช่วงนี้เป็น **ค่าประเมินเชิง heuristic สำหรับช่วยคัดกรอง** ไม่ใช่โมเดลที่ฝึกจากค่าตัวซื้อขายจริง และไม่ใช่ราคาเสนอซื้อ ชุดข้อมูล Transfermarkt เป็น snapshot วันที่ 6 ก.ค. 2026 ส่วนช่วงราคาจะเปลี่ยนตามฟอร์มและตัวกรองที่เลือก ความกว้างของช่วงเป็นระดับความครอบคลุมของข้อมูล ไม่ใช่ความน่าจะเป็นทางสถิติ

## การไหลของข้อมูล

```text
Browser (index.html)
        │ HTTP requests
        ▼
Flask / Gunicorn (app.py)
        │ DATABASE_URL
        ▼
Render PostgreSQL: cateye_assets
  ├─ season summary, birthdays, market values
  └─ heatmap JSON แบบ gzip แยกลีก/ฤดูกาล
```

หน้าเว็บไม่เชื่อม PostgreSQL โดยตรงและไม่เก็บรหัสฐานข้อมูลไว้ใน HTML การอ่านข้อมูลทั้งหมดผ่าน endpoint ของ Flask

## ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
|---|---|
| `index.html` | หน้าเว็บ, ตัวกรอง, โปรไฟล์, การจัดอันดับ, Heatmap และ CatEye Estimate |
| `app.py` | Flask endpoints สำหรับหน้าเว็บและไฟล์ข้อมูลใน PostgreSQL |
| `import_data.py` | สร้างตารางและนำ summary/Heatmap เข้า Render DB; ข้ามไฟล์ที่ checksum ตรงกัน |
| `build_heatmaps.py` | รวม Event Parquet เป็น Heatmap JSON แบบ gzip |
| `requirements.txt` | Flask, python-dotenv, Gunicorn และ psycopg |
| `.gitignore` | กัน `.env`, Parquet และไฟล์ข้อมูลที่สร้างในเครื่องออกจาก Git |

## ข้อมูลใน Render DB

ตาราง `cateye_assets` เก็บไฟล์ที่ Demo ใช้ โดยมีชื่อไฟล์, ขนาด, SHA-256 และเนื้อหา ได้แก่:

- `openplay_player_season_extended.json.gz` — สถิติผู้เล่นรายฤดูกาล รวมถ้วยยุโรปตามชุดข้อมูลที่เตรียมไว้
- `player_birthdays.json` — วันเกิดสำหรับแสดงและกรองอายุ
- `player_market_values.json` — ค่าอ้างอิง Transfermarkt เป็น EUR
- `heatmap_{eng|esp|fra|ger|ita}_{season}.json.gz` — Heatmap รวม 5 ลีกใหญ่ตามฤดูกาล

สถานะที่เตรียมไว้มี 63 ไฟล์: summary 3 ไฟล์และ Heatmap 60 ไฟล์ รวมประมาณ 21.9 MB ส่วน Parquet ต้นฉบับอยู่ใน `D:\Projects\SF250project\Openplay\Openplay_Event` ไม่จำเป็นต้องส่งไฟล์ดิบให้หน้าเว็บเพื่อใช้งาน summary/Heatmap

ตัวนำเข้ารองรับ `--event-dir` เพื่อเก็บ Parquet ต้นฉบับในตาราง `openplay_event_files` เพิ่มเติม แต่ Event ทั้งชุดประมาณ 868 MB ก่อนนับ PostgreSQL/WAL และใช้พื้นที่ฐานข้อมูลมาก ควรเพิ่มพื้นที่ Render DB ให้พอก่อนใช้ตัวเลือกนี้

## เริ่มรันในเครื่อง

ต้องมี Python 3.10 ขึ้นไป และไฟล์ `.env` ในโฟลเดอร์โปรเจกต์ โดยกำหนด:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

ติดตั้งและเปิดเว็บ:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app run
```

จากนั้นเปิด `http://127.0.0.1:5000/` ไฟล์ `.env` ถูกโหลดโดย `python-dotenv` และถูก ignore โดย Git ห้ามเพิ่มไฟล์นี้เข้า commit

## ตั้งค่า Render Web Service

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT app:app`
- ตั้ง Environment Variable ชื่อ `DATABASE_URL` ให้เป็น **Internal Database URL** ของ Render PostgreSQL
- ให้ Web Service และ Database อยู่ region เดียวกัน

Render ต้องมี `DATABASE_URL` ใน Service Environment; `.env` ในเครื่องจะไม่ถูก push ไปที่ Render

## สร้างและนำเข้าข้อมูลใหม่

ติดตั้ง DuckDB สำหรับอ่าน Parquet แล้วสร้าง Heatmap จาก Event Parquet 60 ชุดของ Big Five:

```powershell
pip install duckdb
python build_heatmaps.py <Openplay_Event-folder> <heatmap-output-folder>
```

ตั้ง `DATABASE_URL` ใน environment ของเครื่องให้เป็น External Database URL แล้วนำเข้า:

```powershell
python import_data.py <summary-folder> <heatmap-output-folder>
```

โฟลเดอร์ summary ต้องมี `openplay_player_season_extended.json.gz`, `player_birthdays.json` และ `player_market_values.json` ตัวนำเข้าตรวจ checksum และสามารถรันซ้ำเพื่อทำต่อจากไฟล์เดิมได้

แหล่งข้อมูลการแข่งขัน: [Openplay](https://github.com/nlbair/openplay), ใบอนุญาต CC BY 4.0; ข้อมูลมูลค่าตลาดจาก [Transfermarkt datasets](https://github.com/dcaribou/transfermarkt-datasets)
