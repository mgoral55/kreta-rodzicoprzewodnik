import pandas as pd
import json
import os
import re
import time

CACHE_BUSTER = int(time.time())

print("Wczytuję dane z plików CSV...")

# --- 1. WCZYTANIE PLIKU MIEJSCA.CSV ---
try:
    df_places = pd.read_csv("miejsca.csv", encoding="utf-8-sig")
except:
    df_places = pd.read_csv("miejsca.csv", encoding="cp1250")

df_places.columns = df_places.columns.str.strip()

def clean_text(val):
    if pd.isna(val): return ""
    return str(val).strip()

def format_tasks(text):
    if not text: return ""
    lines = text.split(" 2. ")
    if len(lines) > 1:
        tasks = []
        t1 = lines[0].replace("1. ", "")
        tasks.append(f"- {t1.strip()}")
        rest = "2. " + " 2. ".join(lines[1:])
        parts = re.split(r'\s(?=\d+\.)', rest)
        for p in parts:
            p = re.sub(r'^\d+\.\s*', '', p)
            tasks.append(f"- {p.strip()}")
        return "<br/>".join(tasks)
    return text.replace("\n", "<br/>")

COLORS = {
    'must have': '#E83E8C',
    'nice to have': '#FD7E14',
    'others': '#007BFF',
    'activity': '#FFC107',
    'shop': '#28A745',
    'plaża': '#00BFFF'
}
DEFAULT_COLOR = '#DC3545'

locations = []
place_color_map = {}

for idx, row in df_places.iterrows():
    try:
        num = int(row['numer miejsca'])
    except:
        num = str(row['numer miejsca']).strip()
        
    name = str(row['nazwa']).strip()
    typ_raw = str(row.get('typ', '')).strip().lower()
    bg_color = COLORS.get(typ_raw, DEFAULT_COLOR)
    text_color = "black" if typ_raw == 'activity' else "white"
    place_color_map[str(num)] = {"bg": bg_color, "text": text_color}
    
    coords_raw = str(row.get('współrzędne', '')).strip()
    lat, lon = None, None
    if coords_raw and coords_raw != 'nan':
        try:
            parts = coords_raw.replace(';', ',').split(',')
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
        except:
            pass

    opis_val, ile_jedzenia_val, potencjal_val, strategie_val, sun_val, adhd_val = "", "", "", "", "", ""
    
    for col in df_places.columns:
        col_lower = col.lower().replace(" ", "").replace("_", "")
        if col_lower == 'opis':
            opis_val = clean_text(row[col])
        elif 'jedzeni' in col_lower:
            ile_jedzenia_val = clean_text(row[col])
        elif 'potencja' in col_lower or 'meltdown' in col_lower and 'strateg' not in col_lower:
            potencjal_val = clean_text(row[col])
        elif 'strategi' in col_lower:
            strategie_val = clean_text(row[col])
        elif 'słońc' in col_lower or 'slonc' in col_lower:
            sun_val = clean_text(row[col])
        elif 'adhd' in col_lower:
            adhd_val = clean_text(row[col])

    locations.append({
        "id": num,
        "lat": lat,
        "lon": lon,
        "name": name,
        "opis": opis_val,
        "ile_jedzenia": ile_jedzenia_val,
        "potencjal_meltdownu": potencjal_val,
        "strategie_meltdown": strategie_val,
        "sun": sun_val,
        "adhd": adhd_val,
        "color": bg_color,
        "textColor": text_color,
        "typ": clean_text(row.get('typ', '')),
        "czas_dojazdu": clean_text(row.get('czas dojazdu ze Stravros', '')),
        "godziny": clean_text(row.get('godziny otwarcia', '')),
        "pora": clean_text(row.get('najlepsza pora zwiedzania', '')),
        "czas_zwiedzania": clean_text(row.get('orientacyjny czas zwiedzania', '')),
        "koszt": clean_text(row.get('koszt zwiedzania dla rodziny 2+2', '')),
        "akcja": clean_text(row.get('Konieczna akcja', '')),
        "gastro": clean_text(row.get('Zaplecze gastronomiczne', '')),
        "z_czym": clean_text(row.get('Najlepiej połączyć z', '')),
        "zadania": format_tasks(clean_text(row.get('Zadania dla dzieci', '')))
    })

# --- 2. GENEROWANIE INDEX.HTML (ZWYKŁY STRING BEZ F-STRING) ---
index_html = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>Kreta - Przewodnik Rodzinny</title>
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body, html { height: 100%; width: 100%; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f6efe8; color: #1a110b; overflow: hidden; }
        
        #map { height: 100%; width: 100%; position: absolute; top: 0; left: 0; z-index: 1; }

        .filter-container {
            position: absolute; top: 10px; left: 10px; right: 10px; max-width: 480px;
            background: rgba(255, 255, 255, 0.96); padding: 8px 10px; border-radius: 12px;
            z-index: 1000; box-shadow: 0 3px 10px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 5px;
        }
        .filter-row {
            display: flex; gap: 4px; overflow-x: auto; white-space: nowrap; align-items: center; padding-bottom: 2px;
        }
        .filter-row::-webkit-scrollbar { height: 2px; }
        .filter-row::-webkit-scrollbar-thumb { background: #b89b82; border-radius: 2px; }
        
        .filter-label { font-size: 9px; font-weight: 900; text-transform: uppercase; color: #663223; min-width: 55px; }
        .filter-btn {
            background: #f1dfd1; border: 1px solid #d5cbc0; padding: 3px 8px; border-radius: 5px;
            font-size: 9.5px; font-weight: bold; cursor: pointer; color: #1a110b; flex-shrink: 0;
            transition: all 0.2s;
        }
        .filter-btn.active {
            background: #663223; color: white; border-color: #663223;
        }

        .bottom-left-dock {
            position: absolute; bottom: 20px; left: 10px; z-index: 1500;
            display: flex; flex-direction: column; gap: 6px; width: 140px;
            transition: opacity 0.2s ease-in-out;
        }
        .bottom-left-dock.hidden {
            opacity: 0; pointer-events: none;
        }

        .panel-toggle-btn {
            background: #663223; color: white; border: none; border-radius: 8px;
            padding: 8px 10px; font-size: 11px; font-weight: 900; text-transform: uppercase;
            cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.3); display: flex;
            align-items: center; justify-content: center; gap: 6px; width: 100%; pointer-events: auto;
        }
        .panel-toggle-btn:active { background: #4a2419; transform: scale(0.96); }

        .quick-nav-row {
            display: flex; gap: 6px; width: 100%; pointer-events: auto;
        }
        .quick-nav-btn {
            background: #e6ded1; color: #1a110b; border: 1px solid #b89b82; border-radius: 8px;
            padding: 6px 0; font-size: 14px; font-weight: bold; cursor: pointer;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;
            flex: 1;
        }
        .quick-nav-btn:active { background: #d5cbc0; transform: scale(0.96); }

        .map-legend {
            background: white; padding: 8px 10px; border-radius: 8px;
            font-size: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); pointer-events: none;
            width: 100%;
        }
        .legend-row { display: flex; align-items: center; margin-bottom: 3px; }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; border: 1px solid #aaa; flex-shrink: 0; }

        .trip-btn {
            position: absolute; bottom: 20px; right: 10px; z-index: 1500;
            background: #663223; color: white;
            padding: 10px 18px; border-radius: 30px; font-size: 11pt; font-weight: 900;
            text-decoration: none; text-transform: uppercase; letter-spacing: 0.5px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; align-items: center; gap: 6px;
            border: 2px solid #b89b82; transition: transform 0.2s;
        }
        .trip-btn:active { transform: scale(0.95); background: #4a2419; }

        #side-panel {
            position: fixed; top: 0; left: -100%; width: 85%; max-width: 340px; height: 100%;
            background: #f6efe8; z-index: 9998; box-shadow: 4px 0 15px rgba(0,0,0,0.2);
            transition: left 0.3s ease-in-out; display: flex; flex-direction: column;
        }
        #side-panel.active { left: 0; }
        
        .panel-header {
            background: #663223; color: white; padding: 15px; display: flex;
            justify-content: space-between; align-items: center; font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 2;
        }
        .panel-close { cursor: pointer; font-size: 16pt; }
        
        .panel-list {
            flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px;
        }
        .list-item {
            background: white; border-radius: 8px; padding: 10px; display: flex; align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer; gap: 12px; transition: background 0.2s;
        }
        .list-item:active { background: #e6ded1; }
        .list-icon {
            width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
            justify-content: center; color: white; font-weight: bold; font-size: 12px;
            border: 2px solid #ddd; box-shadow: 0 1px 3px rgba(0,0,0,0.2); flex-shrink: 0;
        }
        .list-name { font-size: 11pt; font-weight: 600; color: #1a110b; line-height: 1.2; }

        #mini-popup {
            position: fixed; bottom: -150px; left: 50%; transform: translateX(-50%);
            width: 90%; max-width: 400px; background-color: #663223; color: white;
            text-align: center; padding: 15px; border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 3000;
            transition: bottom 0.3s ease-in-out; cursor: pointer;
        }
        #mini-popup.active { bottom: 30px; }
        .popup-title { font-weight: 900; font-size: 13pt; text-transform: uppercase; margin-bottom: 5px; }
        .popup-hint { font-size: 9pt; opacity: 0.8; }

        #details-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: #f6efe8; z-index: 9999;
            transform: translateX(100%); transition: transform 0.3s ease-in-out;
            overflow-y: auto; display: flex; flex-direction: column;
        }
        #details-overlay.active { transform: translateX(0); }

        .back-btn {
            position: sticky; top: 0; background-color: #663223; color: white;
            text-align: center; padding: 15px; font-weight: bold; font-size: 15px;
            cursor: pointer; z-index: 10000; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .back-btn:active { background-color: #4a2419; }

        .content-container { padding: 15px; padding-bottom: 30px; }
        
        .title-bar { 
            text-align: center; font-size: 18pt; font-weight: 900; text-transform: uppercase; 
            margin-bottom: 10px; padding: 10px; border-top: 3px solid #b89b82; border-bottom: 3px solid #b89b82; 
            background-color: #e6ded1; 
        }
        .title-bar a { color: #1a110b; text-decoration: none; display: block; }
        .title-bar a:hover { color: #663223; }
        .title-bar a::after { content: " 🔍"; font-size: 14pt; }
        
        .image-placeholder { width: 100%; height: 220px; background-color: #d6e2e1; border-radius: 10px; border: 2px solid #aebac1; overflow: hidden; display: flex; align-items: center; justify-content: center; }
        .image-placeholder img { width: 100%; height: 100%; object-fit: cover; }
        .missing-img { text-align: center; color: #657b85; font-weight: bold; font-size: 12pt; }

        .description-box {
            background-color: rgba(230, 222, 209, 0.95); border: 2px solid #8b6b55; border-radius: 12px;
            padding: 12px 15px; text-align: center; font-size: 10.5pt; line-height: 1.3;
            margin: -25px 10px 15px 10px; position: relative; z-index: 10;
        }

        .logistics-card {
            background-color: #e6ded1; border-radius: 12px; margin-bottom: 15px; overflow: hidden;
            border: 1px solid #d5cbc0; box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }
        
        .gps-strip {
            background-color: #f1dfd1; border-bottom: 1px solid #d5cbc0; padding: 12px 15px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .gps-strip-left { display: flex; align-items: center; gap: 10px; }
        .gps-icon-badge {
            background-color: #663223; color: white; width: 32px; height: 32px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 14pt;
        }
        .gps-strip-label { font-weight: 900; font-size: 10pt; text-transform: uppercase; color: #663223; letter-spacing: 0.5px; }
        .gps-nav-btn {
            background-color: #663223; color: white; padding: 6px 14px; border-radius: 20px;
            text-decoration: none; font-size: 9pt; font-weight: bold; text-transform: uppercase;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }
        .gps-nav-btn:active { transform: scale(0.95); }

        .logistics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background-color: #d5cbc0; }
        .logistics-cell { background-color: #e6ded1; padding: 10px 12px; text-align: left; }
        .logistics-cell .label { font-size: 7.5pt; font-weight: 900; text-transform: uppercase; color: #7a6b5d; margin-bottom: 2px; letter-spacing: 0.5px; }
        .logistics-cell .val { font-size: 10pt; font-weight: 600; color: #1a110b; }

        .cost-box { background-color: #e6ded1; border-radius: 10px; padding: 12px; margin-bottom: 15px; display: flex; align-items: center; border: 1px solid #d5cbc0; }
        .cost-icon { font-size: 24pt; font-weight: bold; color: #627278; margin-right: 15px; }
        .cost-label { font-weight: 900; font-size: 11pt; text-transform: uppercase; margin-bottom: 2px; }
        .cost-val { font-size: 11pt; }

        .action-gastro { display: flex; flex-direction: column; gap: 10px; margin-bottom: 15px; }
        .action-box { background-color: #f1dfd1; border: 3px solid #663223; border-radius: 15px; padding: 12px; }
        .gastro-box { background-color: #aeb5b8; border-radius: 15px; padding: 12px; }
        .food-box { background-color: #d6e2e1; border: 2px solid #657b85; border-radius: 15px; padding: 12px; }

        .box-header { display: flex; align-items: center; margin-bottom: 5px; }
        .box-icon { font-size: 16pt; font-weight: 900; color: #663223; width: 30px; text-align: center; margin-right: 10px; }
        .box-title { font-weight: 900; font-size: 11pt; text-transform: uppercase; }
        .box-text { font-size: 10pt; line-height: 1.4; }

        .sun-box { background-color: #f9ecdc; border: 2px solid #d99b43; border-radius: 15px; padding: 12px; margin-bottom: 15px; }

        .challenges-box {
            background-color: #e6ded1; border: 3px solid #8b6b55; border-radius: 15px; padding: 15px; margin-bottom: 15px;
        }
        .challenges-header { text-align: center; font-weight: 900; font-size: 14pt; text-transform: uppercase; margin: 0 0 15px 0; letter-spacing: 1px; color: #1a110b; }
        .challenges-stack { display: flex; flex-direction: column; gap: 12px; }
        
        .tasks-box { background-color: #eee1d5; border: 3px solid #663223; border-radius: 15px; padding: 12px; margin-bottom: 15px; }
        
        .combine-box { background-color: #aeb5b8; border-radius: 10px; padding: 12px; }
        .combine-title { font-weight: 900; font-size: 11pt; text-transform: uppercase; margin-bottom: 5px; }
        
        .place-link {
            color: #663223; font-weight: 900; text-decoration: underline; cursor: pointer;
            padding: 2px 4px; background-color: rgba(102, 50, 35, 0.1); border-radius: 4px; transition: background-color 0.2s;
        }
        .place-link:active { background-color: rgba(102, 50, 35, 0.3); }

    </style>
</head>
<body>

    <div class="filter-container">
        <div class="filter-row" id="filter-row-meltdown">
            <span class="filter-label">Meltdown:</span>
            <button class="filter-btn active" onclick="setFilter('meltdown', 'all', this)">Wszystkie</button>
            <button class="filter-btn" onclick="setFilter('meltdown', 'niski', this)">Niski</button>
            <button class="filter-btn" onclick="setFilter('meltdown', 'średni', this)">Średni</button>
            <button class="filter-btn" onclick="setFilter('meltdown', 'wysoki', this)">Wysoki</button>
        </div>
        <div class="filter-row" id="filter-row-typ">
            <span class="filter-label">Typ:</span>
            <button class="filter-btn active" onclick="setFilter('typ', 'all', this)">Wszystkie</button>
            <button class="filter-btn" onclick="setFilter('typ', 'must have', this)">Must have</button>
            <button class="filter-btn" onclick="setFilter('typ', 'nice to have', this)">Nice to have</button>
            <button class="filter-btn" onclick="setFilter('typ', 'others', this)">Others</button>
            <button class="filter-btn" onclick="setFilter('typ', 'activity', this)">Activity</button>
            <button class="filter-btn" onclick="setFilter('typ', 'shop', this)">Shop</button>
            <button class="filter-btn" onclick="setFilter('typ', 'plaża', this)">Plaża</button>
        </div>
    </div>

    <div class="bottom-left-dock" id="bottom-dock">
        <button class="panel-toggle-btn" onclick="toggleSidePanel()">➡ Lista</button>
        <div class="quick-nav-row">
            <button class="quick-nav-btn" onclick="navigateHome()" title="Nawiguj do domu">🏠</button>
            <button class="quick-nav-btn" onclick="navigateShop()" title="Nawiguj do sklepu">🛒</button>
        </div>
        <div class="map-legend">
            <b>Typy miejsc:</b>
            <div class="legend-row" style="margin-top:4px;"><div class="legend-dot" style="background:#E83E8C;"></div>Must have</div>
            <div class="legend-row"><div class="legend-dot" style="background:#FD7E14;"></div>Nice to have</div>
            <div class="legend-row"><div class="legend-dot" style="background:#007BFF;"></div>Others</div>
            <div class="legend-row"><div class="legend-dot" style="background:#FFC107;"></div>Activity</div>
            <div class="legend-row"><div class="legend-dot" style="background:#28A745;"></div>Shop</div>
            <div class="legend-row"><div class="legend-dot" style="background:#00BFFF;"></div>Plaża</div>
        </div>
    </div>

    <a href="wycieczka.html" class="trip-btn">🚗 Trip</a>

    <div id="side-panel">
        <div class="panel-header">
            <h3>Lista miejsc</h3>
            <span class="panel-close" onclick="toggleSidePanel()">✖</span>
        </div>
        <div class="panel-list" id="panel-list"></div>
    </div>

    <div id="map"></div>

    <div id="mini-popup" onclick="openSelectedDetails()">
        <div class="popup-title" id="mini-title">Nazwa</div>
        <div class="popup-hint">Kliknij, aby zobaczyć szczegóły ➔</div>
    </div>

    <div id="details-overlay">
        <div class="back-btn" id="top-back-btn" onclick="goBack()">⬅ Wróć do mapy</div>
        
        <div class="content-container">
            <div class="title-bar">
                <a id="d-title-link" href="#" target="_blank"><span id="d-title"></span></a>
            </div>
            
            <div class="image-placeholder" id="d-image"></div>
            
            <div class="description-box" id="d-opis-container">
                <span id="d-opis"></span>
            </div>
            
            <div class="logistics-card">
                <div class="gps-strip">
                    <div class="gps-strip-left">
                        <div class="gps-icon-badge">📍</div>
                        <div class="gps-strip-label">Lokalizacja GPS</div>
                    </div>
                    <div id="d-gps-action"></div>
                </div>
                <div class="logistics-grid">
                    <div class="logistics-cell">
                        <div class="label">Czas dojazdu (Stavros)</div>
                        <div class="val" id="d-dojazd">-</div>
                    </div>
                    <div class="logistics-cell">
                        <div class="label">Godziny otwarcia</div>
                        <div class="val" id="d-godziny">-</div>
                    </div>
                    <div class="logistics-cell">
                        <div class="label">Najlepsza pora</div>
                        <div class="val" id="d-pora">-</div>
                    </div>
                    <div class="logistics-cell">
                        <div class="label">Czas zwiedzania</div>
                        <div class="val" id="d-czas">-</div>
                    </div>
                </div>
            </div>
            
            <div class="cost-box">
                <div class="cost-icon">€👪</div>
                <div>
                    <div class="cost-label">Koszt dla rodziny 2+2:</div>
                    <div class="cost-val" id="d-koszt"></div>
                </div>
            </div>
            
            <div class="action-gastro">
                <div class="action-box" id="d-akcja-container">
                    <div class="box-header">
                        <div class="box-icon" style="border:2px solid #663223; border-radius:50%; width:26px; height:26px; line-height:22px; font-size:14pt;">!</div>
                        <div class="box-title">Konieczna akcja</div>
                    </div>
                    <div class="box-text" id="d-akcja"></div>
                </div>
                <div class="gastro-box">
                    <div class="box-header">
                        <div class="box-icon" style="font-size:16pt;">🍽️</div>
                        <div class="box-title">Zaplecze Gastronomiczne</div>
                    </div>
                    <div class="box-text" id="d-gastro"></div>
                </div>
                <div class="food-box" id="d-jedzenie-container">
                    <div class="box-header">
                        <div class="box-icon" style="font-size:16pt;">🥪</div>
                        <div class="box-title" style="color:#2c4a52;">Ile jedzenia</div>
                    </div>
                    <div class="box-text" id="d-jedzenie"></div>
                </div>
            </div>
            
            <div class="sun-box" id="d-sun-container">
                <div class="box-header">
                    <div class="box-icon" style="font-size:16pt;">☀️</div>
                    <div class="box-title" style="color:#b26310;">Ile słońca</div>
                </div>
                <div class="box-text" id="d-sun"></div>
            </div>
            
            <div class="challenges-box">
                <div class="challenges-header">🐂 Wyzwania & Rady</div>
                <div class="challenges-stack">
                    <div>
                        <div class="box-title" style="color:#663223;">🧠 Trudności ADHD:</div>
                        <div class="box-text" id="d-adhd"></div>
                    </div>
                    <div id="d-potencjal-container" style="display:none;">
                        <div class="box-title" style="color:#663223;">⚡ Potencjał meltdownu:</div>
                        <div class="box-text" id="d-potencjal"></div>
                    </div>
                    <div id="d-strategie-container" style="display:none;">
                        <div class="box-title" style="color:#663223;">🛡️ Strategie na meltdown:</div>
                        <div class="box-text" id="d-strategie"></div>
                    </div>
                </div>
            </div>
            
            <div class="tasks-box">
                <div class="box-title">Zadania dla dzieci:</div>
                <div class="box-text" id="d-zadania"></div>
            </div>
            
            <div class="combine-box">
                <div class="combine-title">Najlepiej połączyć z:</div>
                <div class="box-text" id="d-lacz"></div>
            </div>
        </div>
    </div>

    <script>
        const locations = /*LOCATIONS_PLACEHOLDER*/;
        let selectedLoc = null;
        let historyStack = [];
        let markersList = [];
        
        let activeFilters = {
            meltdown: 'all',
            typ: 'all'
        };
        
        var map = L.map('map').setView([35.2401, 24.8093], 9);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CARTO',
            maxZoom: 19
        }).addTo(map);

        const homeLat = 35.591389;
        const homeLon = 24.091750;
        const shopLat = 35.5862494;
        const shopLon = 24.0918753;

        function navigateHome() {
            window.open('https://www.google.com/maps/dir/?api=1&destination=' + homeLat + ',' + homeLon, '_blank');
        }

        function navigateShop() {
            window.open('https://www.google.com/maps/dir/?api=1&destination=' + shopLat + ',' + shopLon, '_blank');
        }

        let homeHtml = '<div style="background-color:#1a110b;color:white;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.5);">🏠</div>';
        let homeIcon = L.divIcon({ html: homeHtml, className: '', iconSize: [30,30], iconAnchor: [15,15] });
        let homeMarker = L.marker([homeLat, homeLon], { icon: homeIcon }).addTo(map);
        
        homeMarker.on('click', function(e) {
            L.DomEvent.stopPropagation(e);
            navigateHome();
        });

        map.on('click', function() {
            document.getElementById('mini-popup').classList.remove('active');
            document.getElementById('bottom-dock').classList.remove('hidden');
            selectedLoc = null;
        });

        let listHtml = "";
        
        locations.forEach(loc => {
            listHtml += `
                <div class="list-item" onclick="openFromList('${loc.id}')">
                    <div class="list-icon" style="background-color:${loc.color}; color:${loc.textColor};">${loc.id}</div>
                    <div class="list-name">${loc.name}</div>
                </div>
            `;
            
            if(loc.lat && loc.lon) {
                let html = `<div style="background-color:${loc.color};color:${loc.textColor};border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-family:Arial;font-size:12px;font-weight:bold;border:2px solid white;box-shadow:0 2px 5px rgba(0,0,0,0.4);">${loc.id}</div>`;
                let icon = L.divIcon({ html: html, className: '', iconSize: [26,26], iconAnchor: [13,13] });
                
                let marker = L.marker([loc.lat, loc.lon], { icon: icon }).addTo(map);
                
                marker.on('click', function(e) {
                    L.DomEvent.stopPropagation(e);
                    selectedLoc = loc;
                    document.getElementById('mini-title').innerText = loc.id + ". " + loc.name;
                    document.getElementById('mini-popup').classList.add('active');
                    document.getElementById('bottom-dock').classList.add('hidden');
                });

                markersList.push({
                    marker: marker,
                    meltdown: (loc.potencjal_meltdownu || "").toLowerCase(),
                    typ: (loc.typ || "").toLowerCase()
                });
            }
        });

        document.getElementById('panel-list').innerHTML = listHtml;

        function toggleSidePanel() {
            document.getElementById('side-panel').classList.toggle('active');
            document.getElementById('mini-popup').classList.remove('active');
            document.getElementById('bottom-dock').classList.remove('hidden');
        }

        function openFromList(id) {
            const newLoc = locations.find(l => l.id == id);
            if (newLoc) {
                document.getElementById('side-panel').classList.remove('active');
                historyStack = []; 
                selectedLoc = newLoc;
                showDetails(newLoc);
                
                if(newLoc.lat && newLoc.lon) {
                    map.setView([newLoc.lat, newLoc.lon], 11);
                }
            }
        }

        function setFilter(category, value, btnElement) {
            activeFilters[category] = value;

            let rowContainer = document.getElementById('filter-row-' + category);
            rowContainer.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btnElement.classList.add('active');

            markersList.forEach(item => {
                let matchMeltdown = (activeFilters.meltdown === 'all' || item.meltdown.includes(activeFilters.meltdown));
                let matchTyp = (activeFilters.typ === 'all' || item.typ === activeFilters.typ);

                if (matchMeltdown && matchTyp) {
                    if (!map.hasLayer(item.marker)) {
                        item.marker.addTo(map);
                    }
                } else {
                    if (map.hasLayer(item.marker)) {
                        map.removeLayer(item.marker);
                    }
                }
            });

            document.getElementById('mini-popup').classList.remove('active');
            document.getElementById('bottom-dock').classList.remove('hidden');
            selectedLoc = null;
        }

        function openSelectedDetails() {
            if(selectedLoc) {
                historyStack = []; 
                showDetails(selectedLoc);
                document.getElementById('mini-popup').classList.remove('active');
                document.getElementById('bottom-dock').classList.remove('hidden');
            }
        }

        function jumpToPlace(id) {
            const newLoc = locations.find(l => l.id == id);
            if (newLoc && selectedLoc) {
                historyStack.push(selectedLoc); 
                selectedLoc = newLoc;
                showDetails(newLoc);
                
                if(newLoc.lat && newLoc.lon) {
                    map.setView([newLoc.lat, newLoc.lon], 11);
                }
            }
        }

        function goBack() {
            if (historyStack.length > 0) {
                const prevLoc = historyStack.pop();
                selectedLoc = prevLoc;
                showDetails(prevLoc);
            } else {
                document.getElementById('details-overlay').classList.remove('active');
                if(selectedLoc) {
                    document.getElementById('mini-popup').classList.add('active');
                    document.getElementById('bottom-dock').classList.add('hidden');
                } else {
                    document.getElementById('bottom-dock').classList.remove('hidden');
                }
            }
        }

        function showDetails(loc) {
            let backBtn = document.getElementById('top-back-btn');
            if (historyStack.length > 0) {
                let prevLoc = historyStack[historyStack.length - 1];
                let shortName = prevLoc.name.length > 15 ? prevLoc.name.substring(0, 15) + "..." : prevLoc.name;
                backBtn.innerText = "⬅ Wróć do: " + shortName;
            } else {
                backBtn.innerText = "⬅ Wróć do mapy";
            }

            let fullTitle = loc.id + ". " + loc.name;
            document.getElementById('d-title').innerText = fullTitle.toUpperCase();
            
            let searchUrl = "https://www.google.com/search?q=" + encodeURIComponent(loc.name + " Kreta");
            document.getElementById('d-title-link').href = searchUrl;

            let imgStr = '<img src="zdjecia/' + loc.id + '.jpg" onerror="this.outerHTML=\\'<div class=\\\\\\'missing-img\\\\\\'>BRAK ZDJĘCIA</div>\\'" />';
            document.getElementById('d-image').innerHTML = imgStr;
            
            let opisBox = document.getElementById('d-opis-container');
            if(loc.opis && loc.opis.trim() !== "") {
                document.getElementById('d-opis').innerText = loc.opis;
                opisBox.style.display = "block";
            } else {
                opisBox.style.display = "none";
            }
            
            let gpsAction = document.getElementById('d-gps-action');
            if(loc.lat && loc.lon) {
                gpsAction.innerHTML = '<a href="https://www.google.com/maps/dir/?api=1&destination=' + loc.lat + ',' + loc.lon + '" target="_blank" class="gps-nav-btn">Nawiguj ➔</a>';
            } else {
                gpsAction.innerHTML = '<span style="font-size:9pt; color:#888;">Brak współrzędnych</span>';
            }
            
            document.getElementById('d-dojazd').innerText = loc.czas_dojazdu || "-";
            document.getElementById('d-godziny').innerText = loc.godziny || "-";
            document.getElementById('d-pora').innerText = loc.pora || "-";
            document.getElementById('d-czas').innerText = loc.czas_zwiedzania || "-";
            
            document.getElementById('d-koszt').innerText = loc.koszt || "Brak danych";
            
            let akcjaText = (loc.akcja || "").trim();
            let akcjaLower = akcjaText.toLowerCase().replace(".", ""); 
            let akcjaContainer = document.getElementById('d-akcja-container');
            
            if (!akcjaText || akcjaLower === "brak") {
                akcjaContainer.style.display = "none";
            } else {
                document.getElementById('d-akcja').innerText = akcjaText;
                akcjaContainer.style.display = "block";
            }

            document.getElementById('d-gastro').innerText = loc.gastro || "-";
            
            let jedzenieContainer = document.getElementById('d-jedzenie-container');
            let jedzenieText = (loc.ile_jedzenia || "").trim();
            if (!jedzenieText || jedzenieText.toLowerCase() === "brak") {
                jedzenieContainer.style.display = "none";
            } else {
                document.getElementById('d-jedzenie').innerText = jedzenieText;
                jedzenieContainer.style.display = "block";
            }
            
            let sunContainer = document.getElementById('d-sun-container');
            let sunText = (loc.sun || "").trim();
            if (!sunText || sunText.toLowerCase() === "brak") {
                sunContainer.style.display = "none";
            } else {
                document.getElementById('d-sun').innerText = sunText;
                sunContainer.style.display = "block";
            }

            document.getElementById('d-adhd').innerText = loc.adhd || "-";
            
            let potencjalContainer = document.getElementById('d-potencjal-container');
            let potencjalText = (loc.potencjal_meltdownu || "").trim();
            if (!potencjalText || potencjalText.toLowerCase() === "brak") {
                potencjalContainer.style.display = "none";
            } else {
                document.getElementById('d-potencjal').innerText = potencjalText;
                potencjalContainer.style.display = "block";
            }

            let strategieContainer = document.getElementById('d-strategie-container');
            let strategieText = (loc.strategie_meltdown || "").trim();
            if (!strategieText || strategieText.toLowerCase() === "brak") {
                strategieContainer.style.display = "none";
            } else {
                document.getElementById('d-strategie').innerText = strategieText;
                strategieContainer.style.display = "block";
            }

            document.getElementById('d-zadania').innerHTML = loc.zadania || "Brak zadań.";
            
            let zCzymTxt = loc.z_czym || "-";
            if (zCzymTxt !== "-") {
                zCzymTxt = zCzymTxt.replace(/\\(?Miejsce\\s+(\\d+)\\)?/gi, function(match, id) {
                    return '<span class="place-link" onclick="jumpToPlace(\\'' + id + '\\')">' + match + '</span>';
                });
            }
            document.getElementById('d-lacz').innerHTML = zCzymTxt;

            let overlay = document.getElementById('details-overlay');
            overlay.classList.add('active');
            overlay.scrollTop = 0;
        }

    </script>
</body>
</html>"""

final_index_html = index_html.replace("/*LOCATIONS_PLACEHOLDER*/", json.dumps(locations, ensure_ascii=False))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(final_index_html)
print("-> Zapisano index.html")


# --- 3. GENEROWANIE PODSTRONY WYCIECZKA.HTML ---
pobudka_val = "05:00"
wyjazd_val = "05:30"
powrot_val = "17:00"
calkowity_czas_val = ""
opis_wycieczki_val = ""
ogolna_taktyka_val = ""
tytul_wycieczki_val = ""
first_place_id = "1"
cards_html = ""

trip_map_points = []
home_lat, home_lon = 35.591389, 24.091750
trip_map_points.append({"lat": home_lat, "lon": home_lon, "name": "Baza domowa (Stavros)", "is_home": True, "id": "0"})

trip_csv_name = "karta_wycieczki_4.csv" if os.path.exists("karta_wycieczki_4.csv") else ("karta_wycieczki_3.csv" if os.path.exists("karta_wycieczki_3.csv") else ("karta_wycieczki_2.csv" if os.path.exists("karta_wycieczki_2.csv") else "karta_wycieczki.csv"))

if os.path.exists(trip_csv_name):
    try:
        df_trip = pd.read_csv(trip_csv_name, encoding="utf-8-sig")
    except:
        df_trip = pd.read_csv(trip_csv_name, encoding="cp1250")
    
    df_trip.columns = df_trip.columns.str.strip()

    if not df_trip.empty:
        first_row = df_trip.iloc[0]
        for col in df_trip.columns:
            c_clean = col.lower().replace(" ", "").replace("_", "")
            if 'pobudka' in c_clean:
                v = clean_text(first_row[col])
                if v and v != '-': pobudka_val = v
            elif 'wyjazd' in c_clean:
                v = clean_text(first_row[col])
                if v and v != '-':
                    wyjazd_val = re.sub(r'\(ze\s*stra?vros\)', '', v, flags=re.IGNORECASE).strip()
            elif 'powrot' in c_clean or 'powrót' in c_clean:
                v = clean_text(first_row[col])
                if v and v != '-': powrot_val = v
            elif 'calkowityczas' in c_clean:
                v = clean_text(first_row[col])
                if v and v != '-':
                    try:
                        v_float = float(v)
                        calkowity_czas_val = f"{v_float:g} godz."
                    except:
                        calkowity_czas_val = v
            elif 'tytul' in c_clean:
                tytul_wycieczki_val = clean_text(first_row[col])
            elif 'opis' in c_clean and not opis_wycieczki_val:
                opis_wycieczki_val = clean_text(first_row[col])
            elif ('calosciowataktyka' in c_clean or 'taktyka' in c_clean) and not ogolna_taktyka_val:
                ogolna_taktyka_val = clean_text(first_row[col])
            elif ('oryginalne' in c_clean or 'idmiejsca' in c_clean):
                first_place_id = clean_text(first_row[col]).replace(".0", "")
    
    for idx, row in df_trip.iterrows():
        place_id = None
        step_num = None
        for col in df_trip.columns:
            c_clean = col.lower().replace(" ", "").replace("_", "")
            if 'oryginalne' in c_clean or 'idmiejsca' in c_clean or c_clean == 'numermiejsca':
                place_id = clean_text(row[col]).replace(".0", "")
            if 'krok' in c_clean:
                step_num = clean_text(row[col]).replace(".0", "")
                
        if not place_id:
            place_id = str(idx + 1)
        if not step_num:
            step_num = str(idx + 1)

        name = clean_text(row.get('nazwa', ''))
        clean_name = re.sub(r'^\d+\.\s*', '', name)
        
        coords = clean_text(row.get('wspolrzedne', ''))
        
        if coords:
            try:
                parts = coords.replace(';', ',').split(',')
                plat = float(parts[0].strip())
                plon = float(parts[1].strip())
                c_info = place_color_map.get(str(place_id), {"bg": "#663223", "text": "white"})
                trip_map_points.append({
                    "lat": plat,
                    "lon": plon,
                    "name": clean_name,
                    "id": str(place_id),
                    "is_home": False,
                    "bg": c_info["bg"],
                    "text": c_info["text"]
                })
            except:
                pass

        okienko = clean_text(row.get('okienko_zwiedzania', '-'))
        ewakuacja = clean_text(row.get('godzina_ewakuacji', '-'))
        taktyka = clean_text(row.get('podsumowanie_taktyki', ''))
        red_zone = clean_text(row.get('czerwona_strefa_ostrzezenie', ''))
        luz_zone = clean_text(row.get('strefa_luzu_i_regeneracji', ''))

        circle_style = place_color_map.get(str(place_id), {"bg": "#663223", "text": "white"})
        bg_col = circle_style["bg"]
        txt_col = circle_style["text"]

        if coords:
            name_link_html = f'<a href="https://www.google.com/maps/dir/?api=1&destination={coords.replace(" ", "")}" target="_blank" class="nav-name-link" title="Nawiguj">{clean_name}</a>'
        else:
            name_link_html = f'<span class="nav-name-text">{clean_name}</span>'

        tactic_box_html = f'''<div class="tile-subbox tactic-subbox"><div class="subbox-title">🎯 Taktyka</div><div class="subbox-text">{taktyka}</div></div>''' if taktyka and taktyka != '-' else ''
        regen_box_html = f'''<div class="tile-subbox regen-subbox"><div class="subbox-title">🌿 Strefa luzu i regeneracji</div><div class="subbox-text">{luz_zone}</div></div>''' if luz_zone and luz_zone != '-' and luz_zone.lower() != 'brak' else ''
        alert_box_html = f'''<div class="tile-subbox alert-subbox"><div class="subbox-title">⚠️ Ostrzeżenie</div><div class="subbox-text">{red_zone}</div></div>''' if red_zone and red_zone != '-' and red_zone.lower() != 'brak' else ''

        cards_html += f"""
        <div class="timeline-item">
            <div class="timeline-node">
                <a href="index.html?place={place_id}&from=wycieczka" class="place-circle" style="background-color:{bg_col}; color:{txt_col};" title="Zobacz kartę miejsca">{place_id}</a>
            </div>
            <div class="place-tile">
                <div class="tile-header-row">
                    <div class="tile-name">{name_link_html}</div>
                </div>
                
                <div class="tile-hours-grid">
                    <div class="hour-box">
                        <div class="h-label">🕐 Harmonogram</div>
                        <div class="h-val">{okienko}</div>
                    </div>
                    <div class="hour-box evac-box">
                        <div class="h-label">🚨 Ewakuacja</div>
                        <div class="h-val">{ewakuacja}</div>
                    </div>
                </div>

                {tactic_box_html}
                {regen_box_html}
                {alert_box_html}
            </div>
        </div>
        """

opis_box_html = ""
if opis_wycieczki_val and opis_wycieczki_val != '-':
    opis_box_html = f"""
    <div class="trip-description-card">
        <div class="desc-header">📝 Opis i cel wycieczki</div>
        <div class="desc-body">{opis_wycieczki_val}</div>
    </div>
    """

if ogolna_taktyka_val and ogolna_taktyka_val != '-':
    taktyki_final_html = f"<p style='line-height:1.45;'>{ogolna_taktyka_val}</p>"
else:
    taktyki_final_html = "<p>Standardowa realizacja trasy zgodnie z harmonogramem.</p>"

title_card_html = f"""
        <div class="title-banner-card">
            <div class="title-banner-text">{tytul_wycieczki_val}</div>
        </div>
""" if tytul_wycieczki_val else ""

wycieczka_html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>Aktualna Wycieczka</title>
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #f6efe8;
            color: #1a110b;
            padding: 12px;
            padding-bottom: 40px;
            font-size: 11pt;
        }}

        .page-container {{
            max-width: 680px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}

        .top-header {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 6px 0 10px 0;
            border-bottom: 2px solid #b89b82;
        }}
        .header-title {{
            font-size: 20pt;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-align: center;
            color: #1a110b;
        }}
        .back-nav {{
            text-decoration: none;
            color: #663223;
            font-weight: 900;
            font-size: 10.5pt;
            text-transform: uppercase;
            background: #e6ded1;
            padding: 6px 12px;
            border-radius: 8px;
            border: 1px solid #b89b82;
            display: inline-block;
            margin-bottom: 6px;
        }}
        .back-nav:active {{ background: #d5cbc0; }}

        .hero-image-card {{
            width: 100%;
            height: 220px;
            border-radius: 14px;
            overflow: hidden;
            border: 2px solid #8b6b55;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            background: #d6e2e1;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .hero-image-card img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}

        .title-banner-card {{
            background: #e6ded1;
            border: 2px solid #8b6b55;
            border-radius: 12px;
            padding: 12px 16px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }}
        .title-banner-text {{
            font-size: 12.5pt;
            font-weight: 900;
            color: #663223;
            letter-spacing: 0.4px;
            line-height: 1.35;
        }}

        .logistics-card {{
            background: #e6ded1;
            border-radius: 14px;
            padding: 14px 16px;
            border: 2px solid #b89b82;
            box-shadow: 0 3px 10px rgba(102, 50, 35, 0.08);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .logistics-title {{
            font-size: 14pt;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #663223;
            display: flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px solid #d5cbc0;
            padding-bottom: 8px;
        }}

        .logistics-metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        @media(min-width: 520px) {{
            .logistics-metrics-grid {{
                grid-template-columns: 1fr 1fr 1.2fr 1.1fr;
            }}
        }}

        .metric-cell {{
            background: #fdfbf9;
            border-radius: 10px;
            padding: 10px 12px;
            border: 1px solid #d5cbc0;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .metric-label {{
            font-size: 8.5pt;
            font-weight: 900;
            text-transform: uppercase;
            color: #7a6b5d;
            margin-bottom: 3px;
            letter-spacing: 0.3px;
        }}
        .metric-value {{
            font-size: 11pt;
            font-weight: 900;
            color: #1a110b;
            line-height: 1.25;
        }}

        .trip-description-card {{
            background: #f1dfd1;
            border: 2px solid #8b6b55;
            border-radius: 14px;
            padding: 12px 15px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        .desc-header {{
            font-weight: 900;
            font-size: 11pt;
            text-transform: uppercase;
            color: #663223;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }}
        .desc-body {{
            font-size: 10.5pt;
            line-height: 1.45;
            color: #1a110b;
        }}

        .trip-map-container {{
            width: 100%;
            height: 200px;
            border-radius: 14px;
            overflow: hidden;
            border: 2px solid #8b6b55;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            position: relative;
        }}
        #trip-map {{
            width: 100%;
            height: 100%;
        }}

        .timeline-container {{
            display: flex;
            flex-direction: column;
            gap: 16px;
            position: relative;
        }}

        .timeline-item {{
            display: flex;
            gap: 12px;
            align-items: stretch;
            position: relative;
        }}

        .timeline-node {{
            width: 36px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            padding-top: 12px;
            position: relative;
            flex-shrink: 0;
        }}

        .timeline-item::before {{
            content: "";
            position: absolute;
            left: 17px;
            top: 0;
            bottom: 0;
            width: 3px;
            background-color: #8b6b55;
            z-index: 1;
        }}
        .timeline-item:first-child::before {{
            top: 25px;
        }}
        .timeline-item:last-child::before {{
            bottom: calc(100% - 25px);
        }}

        .place-circle {{
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 12.5pt;
            text-decoration: none;
            border: 2.5px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            z-index: 2;
            cursor: pointer;
            transition: transform 0.2s;
            flex-shrink: 0;
        }}
        .place-circle:active {{
            transform: scale(0.9);
        }}

        .place-tile {{
            background: #ede4d8;
            border-radius: 14px;
            border: 1.5px solid #b89b82;
            padding: 14px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
            box-shadow: 0 3px 8px rgba(0,0,0,0.06);
            z-index: 2;
        }}

        .tile-header-row {{
            border-bottom: 1.5px solid #d5cbc0;
            padding-bottom: 8px;
        }}

        .nav-name-link {{
            font-weight: 900;
            font-size: 12pt;
            color: #663223;
            text-decoration: underline;
            line-height: 1.3;
            display: inline-block;
        }}
        .nav-name-link:active {{
            color: #1a110b;
        }}

        .tile-hours-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}

        .hour-box {{
            background: #fdfbf9;
            border-radius: 10px;
            padding: 8px 10px;
            border: 1px solid #d5cbc0;
        }}
        .evac-box {{
            background: #fae8e8;
            border-color: #dca7a7;
        }}
        .h-label {{
            font-size: 7.5pt;
            font-weight: 900;
            text-transform: uppercase;
            color: #7a6b5d;
            margin-bottom: 2px;
            letter-spacing: 0.3px;
        }}
        .evac-box .h-label {{
            color: #9c2c2c;
        }}
        .h-val {{
            font-size: 10pt;
            font-weight: 900;
            color: #1a110b;
            line-height: 1.3;
        }}

        .tile-subbox {{
            border-radius: 10px;
            padding: 9px 12px;
            font-size: 10pt;
            line-height: 1.4;
        }}
        .subbox-title {{
            font-weight: 900;
            font-size: 8.5pt;
            text-transform: uppercase;
            margin-bottom: 3px;
            letter-spacing: 0.4px;
        }}
        .subbox-text {{
            font-size: 10pt;
        }}

        .tactic-subbox {{
            background: #dfd8cf;
            border: 1px solid #c9bea8;
            color: #1a110b;
        }}
        .tactic-subbox .subbox-title {{
            color: #663223;
        }}

        .regen-subbox {{
            background: #eafaf1;
            border: 1px solid #a2d9bc;
            color: #0f5132;
        }}
        .regen-subbox .subbox-title {{
            color: #198754;
        }}

        .alert-subbox {{
            background: #fde8e8;
            border: 1px solid #e07171;
            color: #842029;
        }}
        .alert-subbox .subbox-title {{
            color: #b02a37;
        }}

        .tactic-box {{
            background: #c3cbcf;
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 10.5pt;
            line-height: 1.45;
            color: #1a110b;
            border: 1.5px solid #aeb5b8;
            margin-top: 6px;
        }}
        .tactic-title {{
            text-align: center;
            font-weight: 900;
            font-size: 12pt;
            text-transform: uppercase;
            margin-bottom: 8px;
            color: #1a110b;
            letter-spacing: 0.5px;
        }}
    </style>
</head>
<body>

    <div class="page-container">
        <div>
            <a href="index.html" class="back-nav">⬅ Wróć do mapy</a>
        </div>

        <div class="top-header">
            <div class="header-title">AKTUALNA WYCIECZKA</div>
        </div>

        <!-- ZDJĘCIE PIERWSZEGO MIEJSCA -->
        <div class="hero-image-card">
            <img src="zdjecia/{first_place_id}.jpg?v={CACHE_BUSTER}" onerror="this.outerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;font-size:10pt;color:#666;font-weight:bold;\\'>Kreta</div>'" />
        </div>

        <!-- STYLOWA RAMKA TYTUŁU POD ZDJĘCIEM -->
        {title_card_html}

        <!-- LOGISTYKA DNIA -->
        <div class="logistics-card">
            <div class="logistics-title">🧭 Logistyka dnia</div>
            <div class="logistics-metrics-grid">
                <div class="metric-cell">
                    <div class="metric-label">⏰ Pobudka</div>
                    <div class="metric-value">{pobudka_val}</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">🚗 Wyjazd</div>
                    <div class="metric-value">{wyjazd_val}</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">🏠 Powrót</div>
                    <div class="metric-value">{powrot_val}</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">⏱️ Całkowity czas</div>
                    <div class="metric-value">{calkowity_czas_val if calkowity_czas_val else "Wg planu"}</div>
                </div>
            </div>
        </div>

        <!-- OPIS WYCIECZKI -->
        {opis_box_html}

        <!-- MAPA TRASY WYCIECZKI -->
        <div class="trip-map-container">
            <div id="trip-map"></div>
        </div>

        <!-- KAFELKOWY UKŁAD MIEJSC -->
        <div class="timeline-container">
            {cards_html}
        </div>

        <!-- PODSUMOWANIE TAKTYKI CAŁEGO DNIA -->
        <div class="tactic-box">
            <div class="tactic-title">PODSUMOWANIE TAKTYKI</div>
            {taktyki_final_html}
        </div>
    </div>

    <script>
        const tripPoints = {json.dumps(trip_map_points, ensure_ascii=False)};
        
        var tripMap = L.map('trip-map', {{ zoomControl: false }}).setView([35.3, 24.5], 9);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CARTO',
            maxZoom: 19
        }}).addTo(tripMap);

        const latLngs = [];

        tripPoints.forEach((pt) => {{
            latLngs.push([pt.lat, pt.lon]);
            
            let iconHtml = '';
            if (pt.is_home) {{
                iconHtml = `<div style="background-color:#1a110b;color:white;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-size:13px;border:2px solid white;box-shadow:0 2px 5px rgba(0,0,0,0.4);">🏠</div>`;
            }} else {{
                iconHtml = `<div style="background-color:${{pt.bg}};color:${{pt.text}};border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-family:Arial;font-size:12px;font-weight:bold;border:2px solid white;box-shadow:0 2px 5px rgba(0,0,0,0.4);">${{pt.id}}</div>`;
            }}
            
            let customIcon = L.divIcon({{ html: iconHtml, className: '', iconSize: [26,26], iconAnchor: [13,13] }});
            let marker = L.marker([pt.lat, pt.lon], {{ icon: customIcon }}).addTo(tripMap);
            marker.bindPopup(`<b>${{pt.name}}</b>`);
        }});

        if (latLngs.length > 1) {{
            L.polyline(latLngs, {{
                color: '#663223',
                weight: 3.5,
                opacity: 0.8,
                dashArray: '6, 6'
            }}).addTo(tripMap);
            
            tripMap.fitBounds(latLngs, {{ padding: [20, 20] }});
        }}
    </script>
</body>
</html>"""

with open("wycieczka.html", "w", encoding="utf-8") as f:
    f.write(wycieczka_html)
print(f"-> Zapisano wycieczka.html z tytułem w ramce pod zdjęciem.")

print("Gotowe!")
