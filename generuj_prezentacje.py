import pandas as pd
from weasyprint import HTML
import os
import base64

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
        import re
        parts = re.split(r'\s(?=\d+\.)', rest)
        for p in parts:
            p = re.sub(r'^\d+\.\s*', '', p)
            tasks.append(f"- {p.strip()}")
        return "<br/>".join(tasks)
    return text.replace("\n", "<br/>")

# Określenie ścieżki (gdzie jesteśmy)
BASE_DIR = os.getcwd()

# ---------------------------------------------------------
# 1. PANCERNE ODCZYTYWANIE CSV Z POLSKIMI ZNAKAMI
# ---------------------------------------------------------
csv_path = os.path.join(BASE_DIR, "waypoints-v14.csv")
df = None
# Próbujemy różnych systemowych kodowań, żeby uniknąć krzaczków
for enc in ['utf-8-sig', 'utf-8', 'cp1250', 'windows-1250', 'latin1']:
    try:
        df = pd.read_csv(csv_path, encoding=enc)
        print(f"Sukces: Wczytano CSV używając kodowania: {enc}")
        break
    except UnicodeDecodeError:
        continue
    except Exception as e:
        print(f"Inny błąd przy wczytywaniu: {e}")

if df is None:
    print("KRYTYCZNY BŁĄD: Nie udało się wczytać pliku CSV.")
    exit()

# ---------------------------------------------------------
# 2. PANCERNY WYSZUKIWACZ ZDJĘĆ
# ---------------------------------------------------------
img_dir = os.path.join(BASE_DIR, "zdjecia")
if not os.path.exists(img_dir):
    print(f"UWAGA: Nie znaleziono folderu ze zdjęciami: {img_dir}")
    os.makedirs(img_dir, exist_ok=True)

def find_image_for_num(num):
    """Szuka pliku dla danego numeru ignorując rozszerzenia i błędy typu 1.jpg.jpg"""
    if not os.path.exists(img_dir): return None
    
    num_str = str(num).strip()
    
    # Przeszukujemy wszystkie pliki w folderze "zdjecia"
    for filename in os.listdir(img_dir):
        # Oddzielamy nazwę od rozszerzenia (np. '1' i '.jpg')
        name, ext = os.path.splitext(filename)
        # Bierzemy pod uwagę też błędy Windowsa typu '1.jpg.jpg' -> nazwa to '1.jpg'
        if name == num_str or name == f"{num_str}.jpg" or name == f"{num_str}.jpeg":
            if ext.lower() in ['.jpg', '.jpeg', '.png']:
                return os.path.join(img_dir, filename)
    return None

css = """
@page { size: A4 portrait; margin: 10mm; background-color: #f6efe8; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1a110b; }
.slide { width: 100%; min-height: 277mm; page-break-inside: avoid; display: block; position: relative; padding-bottom: 5mm; }
.title-bar { text-align: center; font-size: 24pt; font-weight: 900; text-transform: uppercase; margin-bottom: 10px; padding: 10px; border-top: 4px solid #b89b82; border-bottom: 4px solid #b89b82; background-color: #e6ded1; }
.image-placeholder { width: 100%; height: 220px; background-color: #d6e2e1; border-radius: 10px; border: 2px solid #aebac1; margin-bottom: 10px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.image-placeholder img { width: 100%; height: 100%; object-fit: cover; }
.info-bar { display: table; width: 100%; background-color: #e6ded1; border-radius: 10px; margin-bottom: 10px; padding: 8px; table-layout: fixed; }
.info-col { display: table-cell; text-align: center; vertical-align: top; padding: 0 5px; border-right: 1px solid #ccc1b5; }
.info-col:last-child { border-right: none; }
.info-col .label { font-size: 9pt; font-weight: 900; text-transform: uppercase; margin-bottom: 3px; }
.info-col .val { font-size: 11pt; }
.cost-box { background-color: #e6ded1; border-radius: 10px; padding: 10px; margin-bottom: 10px; }
.cost-label { font-weight: 900; font-size: 12pt; text-transform: uppercase; margin-bottom: 3px; }
.cost-val { font-size: 12pt; }
.action-gastro { display: table; width: 100%; margin-bottom: 10px; table-layout: fixed; }
.action-box { display: table-cell; width: 48%; background-color: #f1dfd1; border: 3px solid #663223; border-radius: 15px; padding: 12px; vertical-align: top; }
.gastro-box { display: table-cell; width: 48%; background-color: #aeb5b8; border-radius: 15px; padding: 12px; vertical-align: top; }
.gap { display: table-cell; width: 4%; }
.box-title { font-weight: 900; font-size: 12pt; text-transform: uppercase; margin-bottom: 5px; display: inline-block; }
.box-text { font-size: 10.5pt; line-height: 1.3; }
.challenges-header { text-align: center; font-weight: 900; font-size: 16pt; text-transform: uppercase; margin: 15px 0 10px 0; letter-spacing: 1px; }
.adhd-sun { display: table; width: 100%; margin-bottom: 10px; table-layout: fixed; }
.adhd-col, .sun-col { display: table-cell; width: 48%; vertical-align: top; padding: 0 5px; }
.tasks-box { background-color: #eee1d5; border: 3px solid #663223; border-radius: 15px; padding: 12px; margin-bottom: 10px; }
.combine-box { background-color: #aeb5b8; border-radius: 10px; padding: 12px; }
"""

html_parts = [f'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>{css}</style></head><body>']

for idx, row in df.iterrows():
    # Zabezpieczenie przed liczbami z przecinkiem (np. 1.0)
    try:
        num = int(row['numer miejsca'])
    except ValueError:
        num = str(row['numer miejsca']).strip()
        
    title_raw = str(row['nazwa']).strip()
    
    # Wyszukiwanie obrazka na dysku
    img_path = find_image_for_num(num)
    
    # ---------------------------------------------------------
    # 3. PANCERNE WSTAWIANIE OBRAZÓW (Base64)
    # ---------------------------------------------------------
    if img_path:
        try:
            with open(img_path, "rb") as image_file:
                # Zamieniamy zdjęcie na ciąg znaków, WeasyPrint to uwielbia i nigdy nie odrzuca
                ext = os.path.splitext(img_path)[1].lower()
                mime = "image/png" if ext == ".png" else "image/jpeg"
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                img_html = f'<img src="data:{mime};base64,{encoded_string}" />'
                print(f"Dodano zdjęcie dla: {title_raw} (plik: {os.path.basename(img_path)})")
        except Exception as e:
            img_html = f'<div style="padding-top: 80px; text-align: center; color: #657b85; font-weight: bold; font-size: 14pt;">BŁĄD PLIKU ZDJĘCIA</div>'
    else:
        img_html = f'<div style="padding-top: 80px; text-align: center; color: #657b85; font-weight: bold; font-size: 14pt;">BRAK ZDJĘCIA {num}</div>'
        print(f"Brak pliku dla numeru {num}: {title_raw}")

    title = f"{num}. {title_raw}".upper()
    typ = clean_text(row.get('typ', ''))
    czas_dojazdu = clean_text(row.get('czas dojazdu ze Stravros', ''))
    godziny = clean_text(row.get('godziny otwarcia', ''))
    pora = clean_text(row.get('najlepsza pora zwiedzania', ''))
    czas_zwiedzania = clean_text(row.get('orientacyjny czas zwiedzania', ''))
    koszt = clean_text(row.get('koszt zwiedzania dla rodziny 2+2', ''))
    akcja = clean_text(row.get('Konieczna akcja', ''))
    gastro = clean_text(row.get('Zaplecze gastronomiczne', ''))
    adhd = clean_text(row.get('Poziom trudności ADHD', ''))
    sun = clean_text(row.get('Ochrona przed słońcem', ''))
    z_czym = clean_text(row.get('Najlepiej połączyć z', ''))
    zadania = format_tasks(clean_text(row.get('Zadania dla dzieci', '')))

    slide = f"""
    <div class="slide">
        <div class="title-bar">{title}</div>
        <div class="image-placeholder">{img_html}</div>
        
        <div class="info-bar">
            <div class="info-col"><div class="label">Typ:</div><div class="val">{typ}</div></div>
            <div class="info-col"><div class="label">Czas dojazdu<br/>ze Stavros:</div><div class="val">{czas_dojazdu}</div></div>
            <div class="info-col"><div class="label">Godziny<br/>otwarcia:</div><div class="val">{godziny}</div></div>
            <div class="info-col"><div class="label">Najlepsza pora<br/>zwiedzania:</div><div class="val">{pora}</div></div>
            <div class="info-col"><div class="label">Orientacyjny czas<br/>zwiedzania:</div><div class="val">{czas_zwiedzania}</div></div>
        </div>
        
        <div class="cost-box">
            <div style="display: table; width: 100%;">
                <div style="display: table-cell; vertical-align: middle;">
                    <div class="cost-label">Koszt dla rodziny 2+2:</div>
                    <div class="cost-val">{koszt}</div>
                </div>
            </div>
        </div>
        
        <div class="action-gastro">
            <div class="action-box">
                <div class="box-title">Konieczna akcja:</div>
                <div class="box-text">{akcja}</div>
            </div>
            <div class="gap"></div>
            <div class="gastro-box">
                <div class="box-title">Zaplecze gastronomiczne:</div>
                <div class="box-text">{gastro}</div>
            </div>
        </div>
        
        <div class="challenges-header">🐂 Wyzwania & Rady dla rodziców</div>
        
        <div class="adhd-sun">
            <div class="adhd-col">
                <div class="box-title">🧠 Poziom trudności ADHD:</div>
                <div class="box-text">{adhd}</div>
            </div>
            <div class="sun-col">
                <div class="box-title">☀️ Ochrona przed słońcem:</div>
                <div class="box-text">{sun}</div>
            </div>
        </div>
        
        <div class="tasks-box">
            <div class="box-title">Zadania dla dzieci:</div>
            <div class="box-text">{zadania}</div>
        </div>
        
        <div class="combine-box">
            <div class="combine-title">Najlepiej połączyć z:</div>
            <div class="combine-text">{z_czym}</div>
        </div>
    </div>
    """
    html_parts.append(slide)

html_parts.append("</body></html>")
html_str = "\n".join(html_parts)

output_pdf = os.path.join(BASE_DIR, "Kreta_Idealna_Prezentacja.pdf")
print("Generuję ostateczny plik PDF (to może potrwać kilkanaście sekund)...")

# Przekazujemy kod bezpośrednio w pamięci do WeasyPrint (żeby uniknąć błędów zapisu do pliku)
HTML(string=html_str).write_pdf(output_pdf)

print(f"Gotowe! Plik zapisano jako: {output_pdf}")
