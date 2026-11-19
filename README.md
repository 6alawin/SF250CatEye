# CatEye - SF250 byPiranYaa

เว็บสำหรับคัดกรองและเปรียบเทียบนักฟุตบอลจากสถิติ Openplay หน้า `index.html` โหลดข้อมูลผ่าน Flask API จาก Render PostgreSQL ผู้ใช้เลือกลีก ฤดูกาล ตำแหน่ง ผู้เล่น และตัวกรอง Candidate ได้ทันที ไม่ต้องอัปโหลด CSV

เอกสารนี้ถอดสูตรจากโค้ดที่ใช้งานจริงใน `index.html`, `app.py`, `build_heatmaps.py` และ `import_data.py` ชื่อวิธีทางสถิติด้านล่างจึงอธิบายวิธีที่คำนวณอยู่จริง ไม่ได้อ้างว่าเป็นโมเดลที่ไม่ได้ทำไว้

## ภาพรวมการไหลของข้อมูล

```text
Browser: index.html
  ├─ GET /openplay_player_season_extended.json.gz
  ├─ GET /player_birthdays.json
  ├─ GET /player_market_values.json
  └─ GET /heatmap-data/heatmap_{league}_{season}.json.gz
             │
             ▼
Flask/Gunicorn: app.py ── DATABASE_URL ── Render PostgreSQL: cateye_assets
```

เบราว์เซอร์ไม่เชื่อมฐานข้อมูลโดยตรง `app.py` ตรวจชื่อไฟล์ที่อนุญาต ดึงเนื้อหาจาก `cateye_assets` และส่ง gzip/byte range เมื่อร้องขอ

## นิยามข้อมูลและสูตรพื้นฐาน

กำหนดให้ `p` เป็นผู้เล่น, `c` เป็นรายการแข่งขัน/ฤดูกาล, `m` เป็นนาทีลงเล่น และ `x` เป็นสถิติที่อยู่ในไฟล์ summary

| ขั้นตอน/Feature | สูตรหรือกฎ | ชื่อวิธี/ทฤษฎี |
|---|---|---|
| รวมลีกกับถ้วยยุโรป | รวมเมื่อ `player_id + team_id + season` ตรงกัน; นาทีและเกมรวมด้วยผลบวก | Data integration / การรวมข้อมูลตาม composite key |
| รวมสถิติข้ามรายการ | `x_combined = Σ(x_c × m_c) / Σm_c` สำหรับสถิติอัตราต่อ 90 หรืออัตราสำเร็จ | Exposure-weighted mean / ค่าเฉลี่ยถ่วงน้ำหนักตามเวลาที่สัมผัสข้อมูล |
| Goals/Assists รวมในโปรไฟล์ | `round((stat_per90 × minutes) / 90)` | Rate-to-count conversion / การแปลงอัตราต่อหน่วยเป็นยอดรวม |
| ค่าสถิติที่ไม่มี/ไม่ใช่ตัวเลข | แปลงเป็น `0` ก่อนคำนวณ (`n(row,key)`) | Missing-value handling แบบ zero imputation; อาจทำให้สถิติที่หายถูกมองเป็นศูนย์ |
| นาทีขั้นต่ำ | เก็บผู้เล่นเมื่อ `Σminutes ≥ ค่าที่เลือก` | Threshold filtering / การกรองตามเกณฑ์ |
| อายุ | `ปีปัจจุบัน − ปีเกิด − 1` ถ้าวันเกิดปีนี้ยังมาไม่ถึง; ไม่เช่นนั้น `ปีปัจจุบัน − ปีเกิด` | Calendar age / อายุจริงตามปฏิทิน |
| จำนวน Candidate/ทีม | นับผู้เล่นไม่ซ้ำ และนับชื่อทีมไม่ซ้ำหลังตัวกรอง | Distinct count / สถิติเชิงพรรณนา |

Candidate ใช้ฤดูกาลล่าสุด 1 ฤดูกาล หรือ 2 ฤดูกาลล่าสุดตามตัวเลือก จากนั้นรวมสถิติยุโรปเฉพาะผู้เล่น ทีม และฤดูกาลที่จับคู่กันได้ ค่า per 90 มาจาก season summary และเมื่อนำหลายแถวมารวมจะถ่วงตามนาที

## Player Profile และตัวชี้วัดตามตำแหน่ง

### เปอร์เซ็นไทล์และดัชนีโปรไฟล์

ใน Reference Profile ผู้เล่นถูกเทียบกับผู้เล่นลีก/ฤดูกาลเดียวกันและตำแหน่งเดียวกัน โดยใช้กลุ่มตำแหน่งแทนเมื่อตำแหน่งหลักมีผู้เล่นเทียบน้อยกว่า 5 คน บทบาทใช้กลุ่ม role เดียวกันและ fallback ไปกลุ่มตำแหน่งเมื่อมีน้อยกว่า 5 คน สำหรับค่าสถิติ `x` ใน cohort ขนาด `N`:

`P(x) = 100 × (L + 0.5E) / N`; เมื่อ `N = 0` โค้ดกำหนดค่าเริ่มต้นเป็น `50`

`L` คือจำนวนผู้เล่นที่ค่าน้อยกว่า `x`; `E` คือจำนวนผู้เล่นที่ค่าเท่ากับ `x` สูตรนี้เป็น **Empirical Percentile Rank with Midrank Ties** หรือเปอร์เซ็นไทล์จากอันดับเชิงประจักษ์ที่เฉลี่ยอันดับเมื่อเสมอกัน

สถิติที่ค่าน้อยดีกว่า เช่น errors, offsides, dispossessed และ big chances missed กลับทิศด้วย `P_good = 100 − P(x)` ส่วนอื่นใช้ `P(x)` ตามเดิม

- คะแนนการ์ดแต่ละหมวด = ค่าเฉลี่ยเลขคณิตของเปอร์เซ็นไทล์ในหมวดนั้น (**Equal-weight Composite Index**)
- ดัชนีตำแหน่ง = ค่าเฉลี่ยเปอร์เซ็นไทล์ของตัวชี้วัดตำแหน่งทั้งหมด
- ดัชนีบทบาท = ค่าเฉลี่ยเปอร์เซ็นไทล์ของตัวชี้วัดบทบาททั้งหมด
- Tags จุดเด่น = ตัวชี้วัด 4 อันดับเปอร์เซ็นไทล์สูงสุดในหมวด

ดัชนีเป็นคะแนนเปรียบเทียบภายใน cohort ไม่ใช่คะแนนคุณภาพสัมบูรณ์ และไม่ใช่ความน่าจะเป็นที่ผู้เล่นจะทำผลงานได้

### กลุ่มตัวชี้วัดสำหรับ Role Profile

การ์ด “เทียบบทบาท” ใช้ `roleProfiles` เลือก feature ตาม `role_group` ของ Reference แล้วคำนวณ percentile แบบเดียวกันและเฉลี่ยแบบให้น้ำหนักเท่ากัน รายการที่ใช้มีดังนี้:

| Role group | Feature |
|---|---|
| Goalkeeper | saves, claims, claims_failed, punches, smothers, keeper_sweeper, keeper_pickups, passes, pass_pct, long_balls_completed, errors, errors_leading_to_shot, errors_leading_to_goal |
| Defender | tackles_won, interceptions, clearances, shot_blocks, pass_blocks, ball_recoveries, aerials_won, aerials, dribbled_past, passes, pass_pct, progressive_passes, errors |
| Midfielder | passes, pass_pct, progressive_passes, passes_final_third, passes_into_box, through_balls_completed, key_passes, xa, dribbles_completed, ball_recoveries, tackles_won, interceptions |
| Attacking Midfielder | key_passes, xa, assists, big_chances_created, through_balls_completed, xg, npxg, goals, shots_inside_box, dribbles_completed, passes_into_box |
| Wide Attacker | dribbles_completed, crosses_completed, crosses, key_passes, xa, assists, big_chances_created, xg, goals, passes_into_box, fouls_won |
| Striker | xg, npxg, goals, non_penalty_goals, shots_inside_box, shots_outside_box, shots_on_target, big_chances, big_chances_missed, headed_goals, xa, assists, offsides, dispossessed |

หาก `role_group` ไม่ตรงกับ 6 กลุ่มนี้ โค้ด fallback ไปใช้ feature ของ Midfielder ส่วน constants `roleGroups`/`roleWeights` เป็นชุดเดิมที่ไม่ได้ถูกเรียกโดยฟังก์ชัน Role Ranking; สูตรจัดอันดับที่ใช้งานจริงมาจาก `rolePresets` ในตารางถัดไป

### ตัวชี้วัดที่โปรไฟล์ใช้

ค่าที่ระบุ `/90` เป็น rate ต่อ 90 นาทีจาก season summary; ค่าร้อยละคำนวณตามสูตรในตารางถัดไป

| Position family | หมวดและตัวชี้วัด |
|---|---|
| **GK** | Shot stopping: saves, claims, claims failed, punches, smothers, keeper pickups. Distribution: passes, pass accuracy, long balls completed/completion, keeper throws, goal kicks, progressive passes. Sweeping & errors: sweeper actions, interceptions, errors, errors leading to shot/goal. |
| **CB** | Defending: tackles won, interceptions, clearances, shot blocks, pass blocks, ball recoveries, aerials won. Build-up: passes, pass accuracy, progressive/final-third passes, long balls completed/completion, through balls completed/completion. Risk & aerials: aerial win rate, miscontrols, dispossessed, errors, errors leading to shot, headed goals. |
| **FB** | Wide progression: progressive passes, completed dribbles/success rate, final-third passes, completed crosses/cross rate, passes into box, fouls won. Defending: tackles won/win rate, interceptions, recoveries, dribbled past, clearances. Chance creation: key passes, xA, assists, big chances created, completed crosses. |
| **CM** | Build-up: passes, pass accuracy, progressive/final-third passes, through balls completed/completion, long balls completed/completion. Progression: completed dribbles/success rate, passes into box, recoveries, fouls won. Chance creation: key passes, xA, big chances created, assists. Defending: tackles won/win rate, interceptions, pass blocks, shot blocks. |
| **AM** | Chance creation: key passes, xA, assists, big chances created, through balls completed, passes into box. Goal threat: xG, npxG, goals, shots in box/on target, shot accuracy, big chances. Ball carrying/link play: completed dribbles/success rate, fouls won, dispossessed. |
| **FW** | Goal threat: xG, npxG, goals, non-penalty goals, shots in/out of box, shots on target, shot accuracy, goal conversion, big chances/missed. Creation: xA, assists, key passes, big chances created, passes into box. Link play: completed dribbles/success rate, fouls won, offsides, dispossessed. |

ตำแหน่งถูกจัดกลุ่มดังนี้: `GK`; `CB = DC/DCL/DCR`; `FB = DL/DR/WBL/WBR`; `FW = FW/ST`; `AM = AMC/AML/AMR/FWL/FWR`; `CM = DMC/DM*/MC/ML/MR` และตำแหน่งกลางที่เหลือ

### อัตราสำเร็จที่คำนวณจากจำนวนครั้ง

| Feature | สูตร | ชื่อวิธี |
|---|---|---|
| Cross completion % | `100 × crosses_completed / crosses` | Ratio estimator / อัตราส่วนสำเร็จ |
| Aerial win % | `100 × aerials_won / aerials` | อัตราส่วนสำเร็จ |
| Dribble success % | `100 × dribbles_completed / dribbles` | อัตราส่วนสำเร็จ |
| Tackle win % | `100 × tackles_won / tackles` | อัตราส่วนสำเร็จ |
| Long-ball completion % | `100 × long_balls_completed / long_balls` | อัตราส่วนสำเร็จ |
| Through-ball completion % | `100 × through_balls_completed / through_balls` | อัตราส่วนสำเร็จ |
| Shot accuracy % | `100 × shots_on_target / shots` | อัตราส่วนสำเร็จ |
| Goal conversion % | `100 × goals / shots` | อัตราส่วนสำเร็จ |

ถ้าตัวหารเป็น 0 โค้ดคืนค่า 0 ไม่ได้ประมาณค่าแบบ Bayesian smoothing

### Goal, Assist และ Clean Sheet

- Goal และ Assist ที่แสดงเป็นยอดรวมคำนวณจาก rate `/90 × minutes / 90` แล้วปัดเป็นจำนวนเต็ม
- Clean Sheet ที่มีในชุดข้อมูลคือ **Team Clean Sheets**: จำนวนเกมที่ทีมไม่เสียประตูในเกมที่ผู้เล่นลงสนาม ไม่ใช่ Clean Sheet รายบุคคลที่คำนวณจากนาทีที่ผู้เล่นอยู่ในสนาม
- ระยะวิ่งต่อเกมและ Top Speed ไม่คำนวณ เพราะข้อมูล Openplay ชุดนี้ไม่มี tracking ของการวิ่ง

## Player Similarity

ใช้ Feature แยกตามตระกูลตำแหน่ง และเมื่อ Candidate บทบาทเดียวกันมีอย่างน้อย 5 คน จะใช้ชุดตัวชี้วัดตาม `role_group` โดยยังจำกัด Candidate ให้อยู่ตระกูลตำแหน่งเดียวกับ Reference ก่อนเสมอ หาก Candidate บทบาทเดียวกันมีน้อยกว่า 5 คน จะ fallback ไปใช้กลุ่มตัวชี้วัดของตระกูลตำแหน่ง

| ตระกูล/บทบาท | หมวดและตัวชี้วัด |
|---|---|
| GK / Goalkeeper | Shot stopping: saves, claims, claims failed, punches, smothers, keeper pickups; Sweeping: sweeper actions, interceptions; Distribution: passes, pass accuracy, completed long balls, long-ball accuracy, keeper throws, goal kicks, progressive passes |
| CB / Defender | Defending: tackles won, interceptions, clearances, shot/pass blocks, recoveries, aerials won, dribbled past; Build-up: passes, pass accuracy, progressive/final-third passes, completed long balls; Risk: errors, errors leading to shots/goals, dispossessed |
| FB / Defender | บทบาท Defender: ใช้ชุด Defender เมื่อมีอย่างน้อย 5 คน; fallback ตระกูล FB: Wide progression (progressive passes, completed dribbles, dribble success, final-third passes, completed crosses, cross accuracy, passes into box, fouls won), Defending (tackles won, tackle success, interceptions, recoveries, dribbled past, clearances), Chance creation (key passes, xA, assists, big chances created, completed crosses) |
| CM / Midfielder | Build-up & progression: passes, pass accuracy, progressive/final-third/into-box passes, through balls, completed dribbles; Chance creation: key passes, xA, assists, big chances created; Defending: recoveries, tackles, interceptions, pass/shot blocks |
| AM / Attacking Midfielder | Creation: key passes, xA, assists, big chances created, through balls, passes into box; Goal threat: xG, npxG, goals, shots in box/on target, big chances; Carrying: completed dribbles, fouls won, dispossessed |
| AM / Wide Attacker | Wide creation: completed crosses, crosses, key passes, xA, assists, big chances created, passes into box; Carrying: completed dribbles, fouls won; Goal threat: xG, goals, shots in box, big chances |
| FW / Striker | Goal threat: xG, npxG, goals, non-penalty goals, shots in/out of box, shots on target, big chances, missed big chances, headed goals; Creation & link play: xA, assists, key passes, completed dribbles, fouls won, offsides, dispossessed |

กลุ่ม FB ใช้บทบาท Defender หากมี Candidate บทบาทเดียวกันพอ ส่วน Winger ใช้ Wide Attacker; บทบาทอื่นที่ไม่อยู่ในตาราง fallback ไปใช้ชุดตัวชี้วัดของตระกูลตำแหน่ง

### ขั้นตอน

1. เลือก Candidate ในตระกูลตำแหน่งเดียวกับ Reference; หากกลุ่มบทบาทเดียวกันมีอย่างน้อย 5 คน ใช้เฉพาะกลุ่มบทบาทนั้น แล้วตัด Reference คนเดียวกันออกจาก Candidate
2. คำนวณค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานแบบประชากรในกลุ่ม `[Reference + Candidate cohort]` สำหรับแต่ละ Feature:
   - `μ_f = Σx_f / N`
   - `σ_f = sqrt(Σ(x_f − μ_f)^2 / N)`; ถ้า `σ_f = 0` ใช้ 1 เพื่อเลี่ยงการหารด้วยศูนย์
3. แปลงแต่ละ feature เป็น **Z-score / Standard Score**: `z_f = (x_f − μ_f) / σ_f`; ตัวชี้วัดที่ค่ายิ่งน้อยยิ่งดีจะกลับทิศเป็น `−z_f`
4. ให้น้ำหนักหมวดเท่ากันด้วยการคูณ Z-score ทุก Feature ในหมวดที่มี `k` Feature ด้วย `1 / sqrt(k)`, จากนั้นหาความคล้ายด้วย **Cosine Similarity**:
   - `cos(A,B) = Σ(A_f B_f) / (sqrt(ΣA_f²) × sqrt(ΣB_f²))` โดยรวมทุก Feature หลังถ่วงน้ำหนัก
   - `Similarity = clamp(50 × (cos(A,B) + 1), 0, 100)`
5. เรียงคะแนนจากมากไปน้อยและแสดง 15 อันดับแรก

`0` หมายถึงเวกเตอร์ชี้คนละทิศ, `50` คือ cosine 0, `100` คือทิศทางสถิติเดียวกัน คะแนนนี้เป็นความใกล้ของรูปแบบตัวเลขในกลุ่มตำแหน่ง/บทบาทที่เลือก ไม่ได้ยืนยันว่าเล่นแท็กติกเดียวกัน หน้าแสดงชื่อหมวดและ Feature ที่นำไปคำนวณไว้เหนือผลลัพธ์ด้วย

คลิกชื่อ Candidate เพื่อเปิดหน้าต่างเทียบตัวชี้วัดกับ Reference: `Δ% = 100 × (Candidate − Reference) / |Reference|`; สำหรับสถิติที่ค่ายิ่งน้อยยิ่งดีจะกลับทิศเฉพาะการตัดสินว่าดีกว่าหรือด้อยกว่า ส่วนเปอร์เซ็นต์ยังแสดงขนาดความต่างจากค่า Reference. สรุป `สัดส่วนสถิติที่ดีกว่า = 100 × จำนวนตัวชี้วัดที่ Candidate ดีกว่า / จำนวนตัวชี้วัดที่นำมาเทียบ`. หากค่า Reference เป็น 0 เปอร์เซ็นต์ของตัวชี้วัดนั้นไม่มีนิยาม จึงแสดงขีด และบอกกรณี Reference = 0 แทน

## Role Ranking

ใช้ **Empirical Percentile Rank** ภายในกลุ่ม Candidate ที่ผ่านตัวกรองเดียวกัน สำหรับค่า `x` ในกลุ่มเรียง `N` คน โค้ดหาอันดับ `R` ซึ่งเป็นตำแหน่งสุดท้ายที่ `value ≤ x` แล้วคำนวณ:

`P_role(x) = 100 × (R − 1) / (N − 1)` เมื่อ `N ≥ 2`; ถ้ามีคนเดียวให้ `50`

ค่าที่เสมอกันได้ percentile อันดับสุดท้ายร่วมกัน ส่วนคะแนนหมวดเป็น **Weighted Sum Model (WSM)** หรือ weighted linear composite:

`GroupScore_g = Σ(w_j × P_role(feature_j))`, โดยผลรวมน้ำหนัก `w_j` ในแต่ละหมวดเท่ากับ 1

`Overall = ค่าเฉลี่ยเลขคณิตของ GroupScore ทุกหมวด` ดังนั้นแต่ละหมวดมีน้ำหนักรวมเท่ากัน ไม่มีการใช้น้ำหนักข้ามหมวดเพิ่มเติม เป็นแนว **Multi-Criteria Decision Analysis (MCDA)** แบบ weighted sum ไม่ใช่ AHP หรือ Machine Learning

### Role presets และน้ำหนักจริงในโค้ด

ตำแหน่งด้านซ้ายเป็นตำแหน่งที่เข้า cohort ได้; สูตรในวงเล็บเป็นน้ำหนักของ feature ภายในหมวดนั้น

| Role (eligible positions) | หมวด: weighted feature formula |
|---|---|
| **Inverted Fullback** (DL/DR/DML/DMR/ML/MR) | Build-up: `.25 passes + .40 progressive_passes + .35 passes_final_third`; Chance: `.55 key_passes + .45 xa`; Ball progression: `.45 dribbles_completed + .55 passes_into_box`; Defence: `.35 tackles_won + .30 interceptions + .35 ball_recoveries`; Reliability: `1.00 pass_pct` |
| **Playmaking Midfielder** (DMC/DML/DMR/MC/ML/MR/AMC) | Build-up: `.30 passes + .40 progressive_passes + .30 passes_final_third`; Chance: `.40 key_passes + .35 xa + .25 assists`; Progression: `.30 dribbles_completed + .30 through_balls_completed + .40 passes_into_box`; Defence: `.30 tackles_won + .30 interceptions + .40 ball_recoveries`; Reliability: `1.00 pass_pct` |
| **Wide Creator** (AML/AMR/FWL/FWR/DL/DR) | Chance: `.35 key_passes + .25 xa + .20 assists + .20 crosses_completed`; Progression: `.55 dribbles_completed + .45 passes_into_box`; Goal threat: `.40 xg + .30 goals + .30 shots_inside_box`; Reliability: `1.00 pass_pct` |
| **Striker** (FW/FWL/FWR) | Goal threat: `.30 xg + .25 npxg + .25 goals + .20 shots_on_target`; Creation/link: `.30 xa + .20 assists + .20 key_passes + .30 dribbles_completed`; Box presence: `.50 shots_inside_box + .25 headed_goals + .25 big_chances` |
| **Centre Back** (DC) | Defending: `.20 tackles_won + .25 interceptions + .25 clearances + .15 shot_blocks + .15 ball_recoveries`; Build-up: `.25 passes + .20 pass_pct + .30 progressive_passes + .25 long_balls_completed`; Aerial: `.55 aerials_won + .20 headed_goals + .25 headed_shots` |
| **Defensive Fullback** (DL/DR/WBL/WBR) | Defending: `.30 tackles_won + .25 interceptions + .25 ball_recoveries + .20 clearances`; Wide progression: `.35 progressive_passes + .30 dribbles_completed + .35 passes_final_third`; Crossing: `.65 crosses_completed + .35 key_passes`; Reliability: `1.00 pass_pct` |
| **Ball-Playing Centre Back** (DC/DCL/DCR) | Defending: `.25 tackles_won + .25 interceptions + .25 clearances + .25 ball_recoveries`; Progressive build-up: `.40 progressive_passes + .25 passes_final_third + .20 long_balls_completed + .15 through_balls_completed`; Reliability: `1.00 pass_pct`; Aerial: `.70 aerials_won + .15 headed_goals + .15 headed_shots` |
| **Holding Midfielder** (DMC/DML/DMR/MC) | Recovery: `.30 tackles_won + .30 interceptions + .40 ball_recoveries`; Build-up: `.40 passes + .30 pass_pct + .30 progressive_passes`; Progression: `.40 passes_final_third + .25 dribbles_completed + .35 passes_into_box` |
| **Box-to-Box Midfielder** (DMC/DML/DMR/MC/ML/MR) | Defence: `.30 tackles_won + .25 interceptions + .45 ball_recoveries`; Progression: `.35 progressive_passes + .30 dribbles_completed + .35 passes_final_third`; Chance: `.40 key_passes + .35 xa + .25 assists`; Goal threat: `.40 xg + .35 goals + .25 shots_inside_box` |
| **Advanced Playmaker** (AMC/MC/ML/MR) | Chance: `.40 key_passes + .35 xa + .25 assists`; Progressive passing: `.35 through_balls_completed + .35 passes_into_box + .30 passes_final_third`; Carrying: `.60 dribbles_completed + .40 fouls_won`; Goal threat: `.50 xg + .30 goals + .20 shots_on_target` |
| **Attacking Midfielder** (AMC/AML/AMR) | Chance: `.35 key_passes + .30 xa + .20 assists + .15 big_chances_created`; Goal threat: `.35 xg + .25 npxg + .25 goals + .15 shots_inside_box`; Progression: `.40 dribbles_completed + .35 passes_into_box + .25 through_balls_completed` |
| **Winger** (AML/AMR/FWL/FWR) | Wide creation: `.35 crosses_completed + .30 key_passes + .20 xa + .15 assists`; 1v1: `.60 dribbles_completed + .40 fouls_won`; Goal threat: `.35 xg + .25 goals + .20 shots_inside_box + .20 big_chances` |
| **Inside Forward** (AML/AMR/FWL/FWR) | Goal threat: `.30 xg + .25 npxg + .25 goals + .20 shots_inside_box`; Carrying: `.60 dribbles_completed + .40 fouls_won`; Chance: `.35 key_passes + .35 xa + .30 assists` |
| **Target Forward** (FW/FWL/FWR) | Aerial: `.45 aerials_won + .30 headed_shots + .25 headed_goals`; Box threat: `.30 xg + .25 npxg + .25 shots_inside_box + .20 big_chances`; Link: `.25 assists + .25 xa + .20 key_passes + .30 passes_into_box` |
| **Pressing Forward** (FW/FWL/FWR) | Defence: `.30 tackles_won + .25 interceptions + .45 ball_recoveries`; Attack: `.30 xg + .25 npxg + .25 goals + .20 shots_on_target`; Link/carry: `.35 dribbles_completed + .25 fouls_won + .20 key_passes + .20 assists` |
| **Goalkeeper** (GK) | Shot stopping: `.55 saves + .20 claims + .15 smothers + .10 punches`; Sweeping: `.65 keeper_sweeper + .35 interceptions`; Distribution: `.30 passes + .25 pass_pct + .30 long_balls_completed + .15 keeper_throws` |

คะแนน Role ใช้สถิติรวมตาม performance window และยุโรปที่จับคู่ได้ ผลอันดับเป็นการเทียบใน cohort ปัจจุบัน ไม่ใช่ probability of success

## CatEye Estimate: Transfermarkt × สถิติ

นี่เป็น **Rule-based Heuristic Valuation** ไม่ใช่ regression ที่ฝึกจากค่าตัวซื้อขาย

### 1) สร้าง peer cohort

- ต้องเป็น position family เดียวกัน, มี Transfermarkt value และลงเล่นอย่างน้อย 450 นาที
- เมื่อมี peer อายุห่างไม่เกิน 4 ปีอย่างน้อย 5 คน จะใช้ age-matched cohort; ถ้าไม่ถึง 5 จะใช้ cohort ตำแหน่งเดียวกันทั้งหมด
- เลือก peer ที่ Stats score ใกล้ผู้เล่นเป้าหมายที่สุดสูงสุด 15 คน โดยเรียงจาก `abs(peer_score − player_score)`
- ถ้า profile เป็น Reference จะเทียบลีก/ฤดูกาลเดียวกัน; Candidate ใช้ league และ performance window ที่เลือกโดยรวมทุกทีม

### 2) คำนวณ Stats score 0–100

ใช้ตัวชี้วัดจาก `positionProfiles` ของ family นั้น ค่า percentile ต่อ feature ใช้สูตร midrank ในส่วน Player Profile; กลับทิศรายการใน `negativeStats` แล้วหาเฉลี่ยเลขคณิต:

`StatsScore = Σ adjusted_percentile_j / จำนวน_features`

feature ที่ค่าน้อยดีกว่า ได้แก่ `miscontrols`, `dispossessed`, `errors`, `errors_leading_to_shot`, `errors_leading_to_goal`, `claims_failed`, `dribbled_past`, `offsides`, `big_chances_missed`

### 3) เลือกราคาฐาน

`Base = Transfermarkt[player_id]` เมื่อมีข้อมูลของผู้เล่นนั้น; หากไม่มีใช้ค่ากลางของ Transfermarkt values ใน 15 peers ที่ใกล้ Stats score ที่สุด โดย sort ราคาแล้วเลือกตำแหน่ง `round((n−1)×0.5)` (กรณีจำนวนคู่จะเลือกค่ากลางด้านบน) ค่าเป็นสกุล EUR จาก snapshot 6 ก.ค. 2026

### 4) ปรับราคากลางด้วยฟอร์ม

`PerformanceFactor = 1 + (StatsScore − 50) / 250`

`EstimateMid = Base × PerformanceFactor`

เมื่อ `StatsScore=50` จะไม่ปรับฐาน; เมื่อคะแนน 0 ตัวคูณ 0.80; เมื่อคะแนน 100 ตัวคูณ 1.20

### 5) สร้างช่วงราคา

| เงื่อนไขจำนวน peer และนาทีผู้เล่น | ความกว้าง `w` |
|---|---:|
| peer ≥ 12 และนาที ≥ 1,800 | 12% |
| peer ≥ 8 และนาที ≥ 900 | 20% |
| เงื่อนไขอื่น | 30% |

ถ้าทราบอายุแต่หา age-matched peer ไม่ได้ จะบวกความกว้าง 5 จุดเปอร์เซ็นต์ สูงสุด 35%

`EstimateLow = EstimateMid × (1 − w)`

`EstimateHigh = EstimateMid × (1 + w)`

ระดับ “ข้อมูลมาก/ปานกลาง/จำกัด” มาจากจำนวน peer และนาทีตามเกณฑ์เดียวกัน เป็นป้ายความครอบคลุมข้อมูล ไม่ใช่ความน่าจะเป็นหรือ confidence interval ช่วงราคานี้ไม่ได้ใช้สัญญานักเตะ, ค่าจ้าง, อาการบาดเจ็บ, ค่าตัวซื้อขายจริง หรือกำลังซื้อของสโมสร จึงใช้ช่วยคัดกรองเท่านั้น

## Heatmap และสูตร Prob/Stat ที่ใช้จริง

`build_heatmaps.py` อ่าน 60 Event Parquet ของ Big Five แล้วแบ่งพิกัดสนามเป็น **spatial histogram** 10×10:

`zone_x = min(9, floor(x/10))`; `zone_y = min(9, floor(y/10))`

นับจำนวน event ต่อ player/zone แยกเป็น All events, Touches (`is_touch=true`), Shots (`is_shot=true`) และ Passes (`type='Pass'`)

เปรียบเทียบเวกเตอร์จำนวน event 100 โซนด้วย Cosine Similarity:

`HeatmapScore = 100 × (A · B) / (||A||₂ × ||B||₂)`

คะแนนนี้วัดความคล้ายของทิศทาง/สัดส่วนการกระจาย event ไม่ได้วัดคุณภาพผู้เล่น ถ้าฝั่งใดไม่มี event ที่มีพิกัด จะคำนวณไม่ได้

สีแผนที่ normalize ต่อผู้เล่นด้วย `t = zone_count / max_zone_count`; ความทึบ `0.18 + 0.72√t`; สีเขียวเมื่อ `t > .72`, สีเหลืองเมื่อ `t > .42`, นอกนั้นสีแดง การแปลงรากที่สองเป็นเพียง visual scaling ไม่เปลี่ยนค่า HeatmapScore

### มีทฤษฎีความน่าจะเป็นหรือไม่

ใน Feature ปัจจุบัน **ไม่มี probability model**: ไม่ได้คำนวณ event probability, p-value, logistic regression, Bayesian posterior หรือ confidence interval ทางสถิติ ช่วง CatEye Estimate เป็นกฎกำหนดความกว้างตาม sample size/นาที ส่วนเปอร์เซ็นไทล์, z-score, ค่าเฉลี่ย, อัตราส่วน และ cosine เป็นสถิติเชิงพรรณนา/การจัดอันดับ

## ข้อมูลและข้อจำกัด

- `openplay_player_season_extended.json.gz`: summary ผู้เล่นรายฤดูกาลที่เตรียมจาก Openplay รวมรายการยุโรปตามชุดข้อมูล
- `player_birthdays.json`: วันเกิดที่จับคู่กับผู้เล่นเพื่อคำนวณอายุปัจจุบัน
- `player_market_values.json`: ค่าอ้างอิง Transfermarkt ใน EUR, snapshot 6 ก.ค. 2026
- `heatmap_{eng|esp|fra|ger|ita}_{season}.json.gz`: 60 Heatmap สำหรับ 5 ลีก × 12 ฤดูกาล
- Render DB มี asset สำหรับ Demo 63 ไฟล์: summary 3 ไฟล์ + Heatmap 60 ไฟล์ รวมประมาณ 21.9 MB
- Openplay ไม่มี tracking สำหรับระยะวิ่งและ Top Speed; Team Clean Sheets อาจไม่เท่ากับ Clean Sheet รายบุคคล
- Parquet ต้นฉบับอยู่ที่ `D:\Projects\SF250project\Openplay\Openplay_Event`; หน้า Demo ใช้ summary/Heatmap จาก DB จึงไม่ต้องอัปโหลด CSV
- `import_data.py --event-dir <Openplay_Event-folder>` รองรับเก็บ Parquet ดิบใน `openplay_event_files` แต่ Event ทั้งชุดประมาณ 868 MB ก่อน PostgreSQL/WAL; ต้องเพิ่มพื้นที่ DB ก่อนใช้

แหล่งข้อมูลการแข่งขัน: [Openplay](https://github.com/nlbair/openplay), CC BY 4.0. ค่าอ้างอิงตลาด: [Transfermarkt datasets](https://github.com/dcaribou/transfermarkt-datasets)

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|---|---|
| `index.html` | UI, filters, profile, similarity, role ranking, heatmap และ valuation |
| `app.py` | Flask routes และอ่าน asset จาก PostgreSQL |
| `build_heatmaps.py` | สร้าง Heatmap gzip JSON จาก Event Parquet |
| `import_data.py` | สร้างตารางและนำเข้า summary/Heatmap; ตรวจ SHA-256 และข้ามไฟล์ที่เหมือนเดิม |
| `requirements.txt` | Flask, python-dotenv, Gunicorn, psycopg |
| `.gitignore` | ป้องกัน `.env` และไฟล์ข้อมูลท้องถิ่นไม่ให้ถูก commit |

## รันในเครื่อง

สร้าง `.env` ในโฟลเดอร์โปรเจกต์:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

ติดตั้งและเปิดเว็บด้วย PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app run
```

เปิด `http://127.0.0.1:5000/` ค่า `.env` ถูกโหลดโดย `python-dotenv` และถูก ignore โดย Git ห้ามนำไฟล์นี้ขึ้น repository

## Deploy บน Render

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`
- ตั้ง `DATABASE_URL` ใน Environment ของ Web Service ให้เป็น Internal Database URL
- วาง Web Service กับ PostgreSQL ใน region เดียวกัน

`.env` ใช้เฉพาะเครื่อง local; Render ต้องตั้ง `DATABASE_URL` ใน Service Environment โดยตรง

## สร้างและนำเข้าข้อมูลใหม่

ติดตั้ง DuckDB และสร้าง Heatmap จากโฟลเดอร์ที่มี Event Parquet Big Five 60 ไฟล์:

```powershell
pip install duckdb
python build_heatmaps.py <Openplay_Event-folder> <heatmap-output-folder>
```

ตั้ง `DATABASE_URL` เป็น External Database URL ใน environment ของเครื่อง แล้วนำเข้า:

```powershell
python import_data.py <summary-folder> <heatmap-output-folder>
```

โฟลเดอร์ summary ต้องมี `openplay_player_season_extended.json.gz`, `player_birthdays.json`, `player_market_values.json` ตัวนำเข้ารันซ้ำได้และข้ามไฟล์ checksum ตรงกัน
