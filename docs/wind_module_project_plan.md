# 🌬️ Detaljerad Projektplan - Wind Module för E-Paper Väderstation

## 📊 Vindstyrka Konverteringstabell

**Svenska benämningar för vindstyrka (från användarens bild):**

| M/S        | Benämning på land |
|------------|-------------------|
| 0-0.2      | Lugnt            |
| 0.3-1.5    | Svag vind        |
| 1.6-3.3    | Svag vind        |
| 3.4-5.4    | Måttlig vind     |
| 5.5-7.9    | Måttlig vind     |
| 8.0-10.7   | Frisk vind       |
| 10.8-13.8  | Frisk vind       |
| 13.9-17.1  | Hård vind        |
| 17.2-20.7  | Hård vind        |
| 20.8-24.4  | Hård vind        |
| 24.5-28.4  | Storm            |
| 28.5-32.6  | Storm            |
| 32.7+      | Orkan            |

**Implementation i kod:**
```python
def get_wind_description_swedish(self, speed_ms):
    if speed_ms < 0.2: return "Lugnt"
    elif speed_ms < 1.5: return "Svag vind"  
    elif speed_ms < 3.3: return "Svag vind"
    elif speed_ms < 5.4: return "Måttlig vind"
    elif speed_ms < 7.9: return "Måttlig vind"
    elif speed_ms < 10.7: return "Frisk vind"
    elif speed_ms < 13.8: return "Frisk vind"
    elif speed_ms < 17.1: return "Hård vind"
    elif speed_ms < 20.7: return "Hård vind"
    elif speed_ms < 24.4: return "Hård vind"
    elif speed_ms < 28.4: return "Storm"
    elif speed_ms < 32.6: return "Storm"
    else: return "Orkan"
```

**Mål**: Skapa en wind-modul som ersätter barometer-modulen med vindstyrka + vindriktning  
**Komplexitet**: Låg (inga vindvarningar, inga Beaufort-konverteringar)  
**Antal faser**: 4 separata chattar  
**Estimerad total tid**: ~1.5 timmar över 4 chattar

### 🎯 Slutresultat
Wind-modul som visar:
- **Cykel-fokuserad layout**: M/s-värdet prominant för snabba cykel-beslut
- **Generell vind-ikon**: `wi-strong-wind.png` från `icons/system/` som allmän vind-indikator
- **Vindstyrka**: "4.8 m/s" stort och tydligt, "Måttlig vind" mindre under
- **Vindriktning**: Svenska kort-förkortningar (SV, NO, etc.) med pil-ikon
- **Layout**: Centrerad, cykel-optimerad, ersätter barometer-modulen (position MEDIUM 1)

---

## 🏗️ Fas 1: API-utökning för Vindriktning
**Estimerad tid**: 15 minuter  
**Chatt-start**: "Vi har nu gjort klart fas 0 (planering) och nu ska vi börja med fas 1"

### 🎯 **Fas 1 Syfte och Resonemang**

**VARFÖR denna fas behövs:**
- SMHI API:et levererar redan vindstyrka (`ws` parameter) men projektet hämtar inte vindriktning (`wd` parameter)
- Wind-modulen behöver BÅDE vindstyrka OCH vindriktning för komplett cykel-information
- Vindriktning är kritisk för cykling (motvind vs medvind påverkar ansträngning drastiskt)

**VAD denna fas skapar:**
- Utökar befintlig `parse_smhi_forecast()` metod i `weather_client.py`
- Lägger till `wind_direction` i weather_data (grader 0-360°)
- Bygger på befintlig SMHI-integration utan att störa andra funktioner

**HUR det passar in i arkitekturen:**
- Använder samma API-anrop som redan finns (ingen ny endpoint)
- Följer samma pattern som vindstyrka-parsningen
- Förbereder data för nästa fas (mappning till svenska riktningar)

**VAD nästa fas kan bygga på:**
- Efter denna fas finns `wind_direction` tillgänglig i all weather_data
- Fas 2 kan fokusera på att konvertera grader (270°) till svenska förkortningar ("V")
- Inga fler API-ändringar behövs för resten av projektet

### 📁 Filer att modifiera
- `modules/weather_client.py` (1 fil)

### 🔧 Specifika ändringar

#### I `parse_smhi_forecast()` metoden:
**HITTA denna kod** (ca rad 550):
```python
elif param['name'] == 'ws':  # Vindstyrka
    data['wind_speed'] = param['values'][0]
```

**LÄGG TILL direkt efter**:
```python
elif param['name'] == 'wd':  # Vindriktning
    data['wind_direction'] = param['values'][0]
```

### 🧪 Test-instruktioner för Fas 1
```bash
# Testa att vindriktning hämtas
cd ~/epaper_weather
python3 -c "
from modules.weather_client import WeatherClient
import json
with open('config.json', 'r') as f:
    config = json.load(f)
client = WeatherClient(config)
data = client.get_current_weather()
print(f'Vindstyrka: {data.get(\"wind_speed\", \"SAKNAS\")} m/s')
print(f'Vindriktning: {data.get(\"wind_direction\", \"SAKNAS\")} grader')
"
```

### ✅ Success-kriterier Fas 1
- [ ] `wind_direction` finns i weather_data (värde 0-360)
- [ ] `wind_speed` fortfarande fungerar (befintlig funktionalitet)
- [ ] Inga fel i loggarna
- [ ] Test-script visar både vindstyrka och vindriktning

### 💾 Backup-instruktioner Fas 1
```bash
# Backup weather_client.py
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/ORIGINAL_wind_module_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp modules/weather_client.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/weather_client.py"
```

---

## 🏗️ Fas 2: Wind Mappnings och Ikon-system
**Estimerad tid**: 20 minuter  
**Chatt-start**: "Vi har nu gjort klart fas 1 och nu ska vi börja med fas 2"

### 🎯 **Fas 2 Syfte och Resonemang**

**VARFÖR denna fas behövs:**
- API:et ger rå data (4.8 m/s, 270°) men användaren behöver cykel-relevant information
- Grader (270°) är meningslösa för cykling - "V" (västlig) är intuitivt för vindriktning
- M/s-värden behöver översättas till svenska benämningar ("Måttlig vind") för snabb förståelse
- Projektets ikon-system behöver utökas för wind-kategori

**VAD denna fas skapar:**
- **Vindstyrka-mappning**: M/s → svenska benämningar enligt konverteringstabellen
- **Vindriktnings-mappning**: Grader → korta svenska förkortningar (N, SV, ONO, etc.)
- **Ikon-integration**: Utökar `icon_manager.py` med wind-kategorin
- **Cykel-optimerade förkortningar**: 16 kardinalpunkter med korta svenska namn

**HUR det passar in i arkitekturen:**
- Bygger på `icon_manager.py` som redan hanterar weather/system/pressure ikoner  
- Följer samma pattern som befintliga mappningsfunktioner
- Använder befintligt ikon-system från `icons/wind/` och `icons/system/`
- Förbereder data för rendering-fasen

**VAD nästa fas kan bygga på:**
- Efter denna fas kan renderer kalla `get_wind_description_swedish(4.8)` → "Måttlig vind"
- Vindriktning kan konverteras från `270°` → `("V", "w")` för text + ikon
- Alla mappningar är klara så Fas 3 kan fokusera på layout och rendering
- Icon-system är komplett för både generell vind-ikon och kardinal-pilar

### 📁 Filer att modifiera
- `modules/icon_manager.py` (1 fil)

### 🔧 Specifika ändringar

#### 1. Lägg till wind-kategori i `__init__()`
**HITTA denna kod** (ca rad 40):
```python
# System-ikoner - FIXED: Barometer-ikon tillagd! + NYTT: Kalender-ikon!
self.system_mapping = {
```

**LÄGG TILL före system_mapping**:
```python
# Wind-ikoner för 16 kardinalpunkter
self.wind_mapping = {
    'n': 'wi-wind-n',         # Nord (0°/360°)
    'nne': 'wi-wind-nne',     # Nord-nordost (22.5°)
    'ne': 'wi-wind-ne',       # Nordost (45°)
    'ene': 'wi-wind-ene',     # Ost-nordost (67.5°)
    'e': 'wi-wind-e',         # Ost (90°)
    'ese': 'wi-wind-ese',     # Ost-sydost (112.5°)
    'se': 'wi-wind-se',       # Sydost (135°)
    'sse': 'wi-wind-sse',     # Syd-sydost (157.5°)
    's': 'wi-wind-s',         # Syd (180°)
    'ssw': 'wi-wind-ssw',     # Syd-sydväst (202.5°)
    'sw': 'wi-wind-sw',       # Sydväst (225°)
    'wsw': 'wi-wind-wsw',     # Väst-sydväst (247.5°)
    'w': 'wi-wind-w',         # Väst (270°)
    'wnw': 'wi-wind-wnw',     # Väst-nordväst (292.5°)
    'nw': 'wi-wind-nw',       # Nordväst (315°)
    'nnw': 'wi-wind-nnw'      # Nord-nordväst (337.5°)
}
```

#### 2. Lägg till wind description funktion
**LÄGG TILL som ny metod** (efter befintliga metoder):
```python
def get_wind_description_swedish(self, speed_ms):
    """
    Konvertera vindstyrka (m/s) till svenska benämningar enligt "Benämning på land"
    Från användarens konverteringstabell för cykel-relevant wind-information
    
    Args:
        speed_ms: Vindstyrka i m/s
        
    Returns:
        Svensk vindbenämning enligt Beaufort-skala "Benämning på land"
    """
    if speed_ms < 0.2:
        return "Lugnt"
    elif speed_ms < 1.5:
        return "Svag vind"
    elif speed_ms < 3.3:
        return "Svag vind"
    elif speed_ms < 5.4:
        return "Måttlig vind"
    elif speed_ms < 7.9:
        return "Måttlig vind"
    elif speed_ms < 10.7:
        return "Frisk vind"
    elif speed_ms < 13.8:
        return "Frisk vind"
    elif speed_ms < 17.1:
        return "Hård vind"
    elif speed_ms < 20.7:
        return "Hård vind"
    elif speed_ms < 24.4:
        return "Hård vind"
    elif speed_ms < 28.4:
        return "Storm"
    elif speed_ms < 32.6:
        return "Storm"
    else:
        return "Orkan"

def get_wind_direction_info(self, degrees):
    """
    Konvertera grader till kort svensk vindförkortning och kardinal-kod
    Cykel-optimerat för snabb avläsning (SV istället för "Sydvästlig vind")
    
    Args:
        degrees: Vindriktning i grader (0-360)
        
    Returns:
        Tuple (kort_svensk_förkortning, kardinal_kod)
    """
    if degrees < 0 or degrees > 360:
        return "?", "n"
    
    # 16 sektorer à 22.5 grader med KORTA svenska förkortningar
    sectors = [
        (348.75, 360, "N", "n"), (0, 11.25, "N", "n"),
        (11.25, 33.75, "NNO", "nne"),
        (33.75, 56.25, "NO", "ne"),
        (56.25, 78.75, "ONO", "ene"),
        (78.75, 101.25, "O", "e"),
        (101.25, 123.75, "OSO", "ese"),
        (123.75, 146.25, "SO", "se"),
        (146.25, 168.75, "SSO", "sse"),
        (168.75, 191.25, "S", "s"),
        (191.25, 213.75, "SSV", "ssw"),
        (213.75, 236.25, "SV", "sw"),
        (236.25, 258.75, "VSV", "wsw"),
        (258.75, 281.25, "V", "w"),
        (281.25, 303.75, "VNV", "wnw"),
        (303.75, 326.25, "NV", "nw"),
        (326.25, 348.75, "NNV", "nnw")
    ]
    
    for start, end, kort_svensk, code in sectors:
        if start <= degrees < end:
            return kort_svensk, code
    
    # Fallback
    return "N", "n"

def get_wind_icon(self, cardinal_direction, size=(32, 32)):
    """
    Hämta wind-ikon baserat på kardinal-riktning
    
    Args:
        cardinal_direction: Kardinal-kod (t.ex. 'nw', 'se')
        size: Tuple med ikon-storlek
        
    Returns:
        PIL Image-objekt eller None vid fel
    """
    icon_name = self.wind_mapping.get(cardinal_direction, 'wi-wind-n')
    return self.load_icon(f"wind/{icon_name}.png", size)
```

### 🧪 Test-instruktioner Fas 2
```bash
# Testa wind mappnings + system ikoner + KORTA förkortningar
cd ~/epaper_weather
python3 -c "
from modules.icon_manager import WeatherIconManager
mgr = WeatherIconManager()

# Testa beskrivningar
print('4.8 m/s:', mgr.get_wind_description_swedish(4.8))
print('15.5 m/s:', mgr.get_wind_description_swedish(15.5))

# Testa KORTA riktningar (cykel-optimerat)
print('270°:', mgr.get_wind_direction_info(270))  # Förväntat: ('V', 'w')
print('225°:', mgr.get_wind_direction_info(225))  # Förväntat: ('SV', 'sw')
print('45°:', mgr.get_wind_direction_info(45))    # Förväntat: ('NO', 'ne')

# Testa kardinal wind-ikon
wind_icon = mgr.get_wind_icon('w', (32, 32))
print('Väst kardinal-ikon laddad:', wind_icon is not None)

# Testa generell wind-ikon från system
general_wind_icon = mgr.get_system_icon('strong-wind', (48, 48))
print('Generell wind-ikon (strong-wind) laddad:', general_wind_icon is not None)
"
```

### ✅ Success-kriterier Fas 2
- [ ] Wind description fungerar (4.8 m/s → "Måttlig vind")
- [ ] Direction mapping fungerar med KORTA förkortningar (270° → "V", "w")
- [ ] Cykel-optimerade riktningar (225° → "SV", 45° → "NO")
- [ ] Kardinal wind-ikon kan laddas (även om filen saknas, ingen crash)
- [ ] Generell wind-ikon (strong-wind) kan laddas från system
- [ ] Inga import-fel eller syntax-fel

### 💾 Backup-instruktioner Fas 2
```bash
# Backup icon_manager.py
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/wind_mappings_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp modules/icon_manager.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/icon_manager.py"
```

---

## 🏗️ Fas 3: WindRenderer Implementation
**Estimerad tid**: 30 minuter  
**Chatt-start**: "Vi har nu gjort klart fas 2 och nu ska vi börja med fas 3"

### 🎯 **Fas 3 Syfte och Resonemang**

**VARFÖR denna fas behövs:**
- Projektets Dynamic Module System kräver att varje modul har sin egen renderer-klass
- Wind-modulen behöver specialiserad layout för cykel-användning (ikke bara kopiera barometer-layout)
- E-Paper har begränsat utrymme (240×200px) som måste optimeras för snabb wind-avläsning
- Systemet följer rendering pipeline-arkitektur med ModuleRenderer som bas

**VAD denna fas skapar:**
- **WindRenderer klass**: Ärver från ModuleRenderer, följer projektets renderer-pattern
- **Cykel-fokuserad layout**: M/s-värde prominent, centrerad design, korta riktningar
- **Dubbel-ikon system**: Generell wind-ikon + specifik kardinal-pil för komplett information
- **Robust rendering**: Graceful fallback vid ikon-fel, smart positionering, E-Paper-optimerad

**HUR det passar in i arkitekturen:**
- Följer samma pattern som `PrecipitationRenderer` i projektets renderer-system
- Använder ModuleRenderer som bas för konsekvent interface
- Integrerar med befintlig icon_manager och font-system
- Förbereder för registrering i ModuleFactory (Fas 4)

**CYKEL-OPTIMERAD DESIGN-BESLUT:**
- **4.8 m/s PROMINENT**: Huvuddata för cykel-beslut (hero_temp font)
- **Centrerad layout**: Optimal användning av E-Paper utrymme
- **Korta riktningar**: "SV" istället för "Sydvästlig vind" sparar plats
- **Ingen teknisk data**: Borttaget grader/datakälla för fokus på praktisk info

**VAD nästa fas kan bygga på:**
- Efter denna fas finns en komplett, testbar WindRenderer
- Fas 4 kan registrera den i ModuleFactory utan att behöva ändra rendering-logik
- Layout är färdig-optimerad för cykel-användning
- All rendering-logik är isolerad och testbar

### 📁 Filer att skapa/modifiera
- `modules/renderers/wind_renderer.py` (NY FIL)

### 🔧 Specifika ändringar

#### Skapa ny fil: `modules/renderers/wind_renderer.py`
**KOMPLETT fil-innehåll**:
```python
#!/usr/bin/env python3
"""
Wind Module Renderer för E-Paper Väderstation - CYKEL-OPTIMERAD LAYOUT
Visar vindstyrka + vindriktning med fokus på snabba cykel-beslut

Cykel-fokuserad layout:
🌪️       4.8 m/s
      Måttlig vind
      
         ↙️ SV

Ikoner:
- wi-strong-wind.png (generell vind-ikon från system/, centrerad överst)
- wi-wind-[direction].png (pil-ikon från wind/, med kort svenska förkortningar)
"""

from typing import Dict, List
from .base_renderer import ModuleRenderer

class WindRenderer(ModuleRenderer):
    """
    Renderer för wind-modul med CYKEL-FOKUSERAD layout
    
    Visar:
    - Generell vind-ikon (wi-strong-wind.png från system/, centrerad överst)
    - M/S-värde PROMINENT för snabba cykel-beslut
    - Svensk vindbenämning (mindre, under m/s-värdet)
    - Kort vindriktning (SV, NO, etc.) med pil-ikon från wind/
    - Centrerad layout optimerad för cykling (240×200px)
    """
    
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Rendera wind-modul
        
        Args:
            x, y: Position på canvas
            width, height: Modulens storlek (240×200px för MEDIUM 1)
            weather_data: Väderdata från weather_client
            context_data: Trigger context data
            
        Returns:
            True om rendering lyckades
        """
        try:
            self.logger.info(f"🌬️ Renderar wind-modul ({width}×{height})")
            
            # Hämta vinddata med säker fallback
            wind_speed = self.safe_get_value(weather_data, 'wind_speed', 0.0, float)
            wind_direction = self.safe_get_value(weather_data, 'wind_direction', 0.0, float)
            
            # Konvertera till svenska beskrivningar
            speed_description = self.icon_manager.get_wind_description_swedish(wind_speed)
            direction_short, cardinal_code = self.icon_manager.get_wind_direction_info(wind_direction)
            
            # === CYKEL-FOKUSERAD CENTRERAD LAYOUT ===
            
            # 1. Generell vind-ikon (centrerad överst)
            general_wind_icon = self.icon_manager.get_system_icon('strong-wind', size=(48, 48))
            icon_center_x = x + (width // 2) - 24  # Centrera ikon (48px bred)
            if general_wind_icon:
                self.paste_icon_on_canvas(general_wind_icon, icon_center_x, y + 15)
            
            # 2. M/S-värde (STORT, prominent, centrerat under ikon)
            ms_text = f"{wind_speed:.1f} m/s"
            ms_center_x = x + (width // 2)  # Centrera text
            self.draw_text_with_fallback(
                (ms_center_x - 50, y + 75),  # Justera X för att centrera (ungefär)
                ms_text,
                self.fonts.get('hero_temp', self.fonts.get('small_main')),  # STOR font!
                fill=0
            )
            
            # 3. Vindbenämning (mindre, centrerad under m/s)
            desc_center_x = x + (width // 2)
            self.draw_text_with_fallback(
                (desc_center_x - 40, y + 115),  # Justera X för att centrera
                speed_description,
                self.fonts.get('medium_desc', self.fonts.get('small_desc')),
                fill=0
            )
            
            # 4. Pil-ikon för riktning (centrerad, under beskrivning)
            cardinal_icon = self.icon_manager.get_wind_icon(cardinal_code, size=(32, 32))
            cardinal_center_x = x + (width // 2) - 16  # Centrera ikon (32px bred)
            if cardinal_icon:
                self.paste_icon_on_canvas(cardinal_icon, cardinal_center_x, y + 150)
            
            # 5. Kort vindriktning (bredvid pil-ikon)
            direction_x = cardinal_center_x + 40  # Till höger om pil-ikon
            self.draw_text_with_fallback(
                (direction_x, y + 155),
                direction_short,
                self.fonts.get('medium_desc', self.fonts.get('small_desc')),
                fill=0
            )
            
            self.logger.info(f"✅ Cykel-optimerad wind-modul rendered: {wind_speed:.1f}m/s {speed_description}, {direction_short}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid wind rendering: {e}")
            return self.render_fallback_content(
                x, y, width, height, 
                "Wind-data ej tillgänglig"
            )
    
    def get_required_data_sources(self) -> List[str]:
        """Wind-modul behöver SMHI prognosdata för vindstyrka och vindriktning"""
        return ['smhi']
    
    def get_module_info(self) -> Dict:
        """Metadata för wind-modul"""
        info = super().get_module_info()
        info.update({
            'purpose': 'Visa vindstyrka och vindriktning med svenska benämningar',
            'data_sources': ['SMHI vindprognoser (ws + wd parametrar)'],
            'layout': 'Ersätter barometer-modulen (MEDIUM 1 position)',
            'features': [
                'CYKEL-FOKUSERAD layout för snabba wind-beslut',
                'M/S-värde PROMINENT (hero_temp font) - huvuddata',
                'Generell vind-ikon (wi-strong-wind.png) centrerad överst',
                'Korta svenska vindförkortningar (SV, NO, etc.) från kompass',
                'Pil-ikon för exakt vindriktning från wind-biblioteket',
                'Centrerad layout utan tekniska detaljer (inga grader/datakälla)',
                'Optimal utnyttjande av E-Paper skärmyta (240×200px)',
                'Vindstyrka enligt "Benämning på land" för kontext'
            ]
        })
        return info
```

### 🧪 Test-instruktioner Fas 3
```bash
# Testa WindRenderer med CYKEL-FOKUSERAD layout
cd ~/epaper_weather
python3 -c "
from modules.renderers.wind_renderer import WindRenderer
from modules.icon_manager import WeatherIconManager
import json

# Mock setup
with open('config.json', 'r') as f:
    config = json.load(f)
fonts = {'small_main': None, 'medium_desc': None, 'hero_temp': None, 'tiny': None}
icon_mgr = WeatherIconManager()

# Skapa renderer
renderer = WindRenderer(icon_mgr, fonts)

# Test data
weather_data = {
    'wind_speed': 4.8,
    'wind_direction': 225.0  # Sydväst
}

# Simulera rendering (utan canvas)
try:
    # Test metoder direkt
    speed_desc = icon_mgr.get_wind_description_swedish(4.8)
    dir_short, cardinal = icon_mgr.get_wind_direction_info(225.0)  # Förväntat: 'SV'
    
    # Testa båda ikon-typerna
    general_icon = icon_mgr.get_system_icon('strong-wind', (48, 48))
    cardinal_icon = icon_mgr.get_wind_icon(cardinal, (32, 32))
    
    print(f'✅ WindRenderer kan skapas')
    print(f'✅ Speed: {speed_desc}')
    print(f'✅ Direction: {dir_short} ({cardinal}) - KORT förkortning!')
    print(f'✅ Generell wind-ikon: {general_icon is not None}')
    print(f'✅ Kardinal wind-ikon: {cardinal_icon is not None}')
    print(f'✅ Required sources: {renderer.get_required_data_sources()}')
    print(f'✅ CYKEL-LAYOUT: 4.8 m/s prominant, {dir_short} kort!')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### ✅ Success-kriterier Fas 3
- [ ] `WindRenderer` kan importeras utan fel
- [ ] Renderer kan skapas med icon_manager + fonts
- [ ] `get_required_data_sources()` returnerar ['smhi']
- [ ] Mock-test visar CYKEL-OPTIMERAD data (4.8 m/s prominant, "SV" kort)
- [ ] Både generell wind-ikon och kardinal-ikon kan testas
- [ ] Centrerad layout-logik utan tekniska detaljer
- [ ] Inga syntax-fel eller import-fel

### 💾 Backup-instruktioner Fas 3
```bash
# Ny fil - ingen backup behövs för skapande
# Verifiera att filen skapats korrekt:
ls -la modules/renderers/wind_renderer.py
echo "✅ WindRenderer fil skapad"
```

---

## 🏗️ Fas 4: Integration och Konfiguration
**Estimerad tid**: 15 minuter  
**Chatt-start**: "Vi har nu gjort klart fas 3 och nu ska vi börja med fas 4"

### 🎯 **Fas 4 Syfte och Resonemang**

**VARFÖR denna fas behövs:**
- Wind-modulen existerar men är inte "synlig" för systemets Dynamic Module System
- ModuleFactory måste veta att WindRenderer finns för att kunna skapa den
- Konfigurationssystemet behöver wind_module definierad för layout-hantering
- Trigger-systemet behöver wind_trigger för automatisk aktivering vid hård vind
- Vi har inte löst hur flaggan i config.json ska implementeras så att det går att ställa in manuellt där. 

**VAD denna fas skapar:**
- **Factory-registrering**: WindRenderer blir tillgänglig via `factory.create_renderer('wind_module')`
- **Import-chain**: Uppdaterar `__init__.py` så WindRenderer kan importeras korrekt
- **Modul-konfiguration**: Definierar wind_module i config.json med position/storlek
- **Trigger-system**: Aktiverar wind-modul automatiskt vid vindstyrka >10 m/s
- **Layout-grupper**: Skapar medium_right_section för dynamisk växling barometer↔wind

**HUR det passar in i arkitekturen:**
- Följer projektets Dynamic Module System med module_groups och triggers
- Integrerar med befintliga renderer-registrering (samma pattern som PrecipitationRenderer)
- Använder trigger-systemet för intelligent växling (som precipitation_trigger)
- Bevarar barometer som default, wind aktiveras endast vid behov

**TRIGGER-LOGIK RESONEMANG:**
- **wind_speed > 10.0**: Aktiverar vid "Frisk vind" (cykel-relevant tröskelvärde)
- **Priority 80**: Lägre än precipitation (100) - nederbörd viktigare än vind
- **Target medium_right_section**: Ersätter barometer-position intelligent
- **Automatisk återgång**: När vind lugnar sig (<10 m/s) återgår systemet till barometer

**VAD denna fas slutför:**
- Efter denna fas är wind-modulen KOMPLETT och ANVÄNDBAR
- Systemet kan växla automatiskt mellan barometer och wind baserat på vindförhållanden
- Manuell aktivering möjlig via config.json för permanent wind-modul
- All integration med befintlig arkitektur är klar

### 📁 Filer att modifiera
- `modules/renderers/module_factory.py` (1 fil)
- `modules/renderers/__init__.py` (1 fil) 
- `config.json` (1 fil)

### 🔧 Specifika ändringar

#### 1. Registrera i `modules/renderers/module_factory.py`
**HITTA denna kod** (ca rad 25):
```python
from .precipitation_renderer import PrecipitationRenderer
```

**LÄGG TILL efter**:
```python
from .wind_renderer import WindRenderer
```

**HITTA denna kod** (ca rad 35):
```python
self._renderer_registry = {
    'precipitation_module': PrecipitationRenderer,
    # Framtida moduler läggs till här:
```

**ÄNDRA till**:
```python
self._renderer_registry = {
    'precipitation_module': PrecipitationRenderer,
    'wind_module': WindRenderer,
    # Framtida moduler läggs till här:
```

#### 2. Uppdatera `modules/renderers/__init__.py`
**HITTA denna kod**:
```python
from .precipitation_renderer import PrecipitationRenderer
```

**LÄGG TILL efter**:
```python
from .wind_renderer import WindRenderer
```

**HITTA denna kod**:
```python
__all__ = [
    'ModuleRenderer',
    'LegacyModuleRenderer', 
    'PrecipitationRenderer',
    'ModuleFactory'
]
```

**ÄNDRA till**:
```python
__all__ = [
    'ModuleRenderer',
    'LegacyModuleRenderer', 
    'PrecipitationRenderer',
    'WindRenderer',
    'ModuleFactory'
]
```

#### 3. Konfigurera `config.json`
**HITTA denna sektion** (ca rad 50):
```json
"modules": {
    "main_weather": {
      "enabled": true,
      "coords": {"x": 10, "y": 10},
      "size": {"width": 480, "height": 300}
    },
    "barometer_module": {
      "enabled": true,
      "coords": {"x": 500, "y": 10},
      "size": {"width": 240, "height": 200}
    },
```

**LÄGG TILL efter barometer_module**:
```json
    "wind_module": {
      "enabled": false,
      "coords": {"x": 500, "y": 10},
      "size": {"width": 240, "height": 200},
      "description": "Vindstyrka och vindriktning med svenska benämningar"
    },
```

**HITTA denna sektion** (ca rad 110):
```json
"module_groups": {
    "bottom_section": {
      "_comment": "Nederst: Normal = klocka+status, Precipitation = nederbörd", 
      "normal": ["clock_module", "status_module"],
      "precipitation_active": ["precipitation_module"]
    }
```

**LÄGG TILL efter bottom_section**:
```json
    "medium_right_section": {
      "_comment": "Höger sida: Normal = barometer, Wind = vindmodul",
      "normal": ["barometer_module"],
      "wind_active": ["wind_module"]
    }
```

**HITTA denna sektion** (ca rad 125):
```json
"triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_precipitation_2h > 0.2",
      "target_section": "bottom_section",
      "activate_group": "precipitation_active",
      "priority": 100,
      "description": "Aktivera nederbörd-modul vid regn eller kommande regn"
    }
```

**LÄGG TILL efter precipitation_trigger**:
```json
    "wind_trigger": {
      "condition": "wind_speed > 10.0",
      "target_section": "medium_right_section", 
      "activate_group": "wind_active",
      "priority": 80,
      "description": "Aktivera wind-modul vid vindstyrka över 10 m/s (frisk vind)"
    }
```

### 🧪 Test-instruktioner Fas 4
```bash
# Testa komplett integration
cd ~/epaper_weather

# 1. Testa import av alla renderer-komponenter
python3 -c "
from modules.renderers import WindRenderer, ModuleFactory
from modules.icon_manager import WeatherIconManager
import json

print('✅ WindRenderer import fungerar')

# 2. Testa factory registration
with open('config.json', 'r') as f:
    config = json.load(f)
fonts = {'small_main': None, 'medium_desc': None, 'tiny': None}
icon_mgr = WeatherIconManager()

factory = ModuleFactory(icon_mgr, fonts)
available = factory.get_available_renderers()
print(f'Available renderers: {available}')
print(f'✅ WindRenderer registrerad: {\"wind_module\" in available}')

# 3. Testa wind_module renderer-skapande
renderer = factory.create_renderer('wind_module')
print(f'✅ WindRenderer kan skapas via factory: {renderer.__class__.__name__}')
"

# 4. Validera config.json
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)

# Kontrollera wind_module finns
wind_module = config.get('modules', {}).get('wind_module', {})
print(f'✅ wind_module i config: {wind_module.get(\"enabled\", \"SAKNAS\")}')

# Kontrollera trigger finns  
wind_trigger = config.get('triggers', {}).get('wind_trigger', {})
print(f'✅ wind_trigger i config: {wind_trigger.get(\"condition\", \"SAKNAS\")}')

# Kontrollera module_groups
groups = config.get('module_groups', {}).get('medium_right_section', {})
print(f'✅ medium_right_section: {groups}')
"
```

### 🧪 Live-test (frivilligt)
```bash
# Aktivera wind-modul för test
# VARNING: Detta kommer ändra layout på E-Paper!

cd ~/epaper_weather

# Backup current config
cp config.json config.json.backup

# Temporärt aktivera wind-modul
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)

# Aktivera wind_module, inaktivera barometer_module
config['modules']['wind_module']['enabled'] = True
config['modules']['barometer_module']['enabled'] = False

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    
print('✅ Wind-modul aktiverad temporärt')
"

# Restart daemon för att testa
python3 restart.py

# Vänta 90 sekunder på uppdatering
echo "⏰ Väntar 90 sekunder på E-Paper uppdatering..."
sleep 90

# Ta screenshot
python3 screenshot.py --output wind_module_test

# Återställ config
cp config.json.backup config.json
python3 restart.py

echo "✅ Wind-modul test klar, config återställd"
```

### ✅ Success-kriterier Fas 4
- [ ] WindRenderer kan importeras via `from modules.renderers import WindRenderer`
- [ ] ModuleFactory kan skapa wind_module renderer
- [ ] `wind_module` finns i config.json med korrekt konfiguration
- [ ] `wind_trigger` finns med korrekt condition
- [ ] JSON-validering visar inga syntax-fel
- [ ] (Frivilligt) Live-test visar wind-modul på E-Paper

### 💾 Backup-instruktioner Fas 4
```bash
# Backup alla filer som modifieras
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/wind_integration_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp modules/renderers/module_factory.py "$BACKUP_DIR/"
cp modules/renderers/__init__.py "$BACKUP_DIR/"
cp config.json "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/ (3 filer)"
```

### 🔄 Återställning vid problem
```bash
# Om något går fel, återställ från backup:
cp backup/wind_integration_[TIMESTAMP]/module_factory.py modules/renderers/
cp backup/wind_integration_[TIMESTAMP]/__init__.py modules/renderers/
cp backup/wind_integration_[TIMESTAMP]/config.json .
python3 restart.py
echo "✅ Återställt från backup"
```

---

## 🎯 Slutgiltig Test-procedur (Efter Fas 4)

### Manual aktivering av wind-modul
```bash
cd ~/epaper_weather

# 1. Backup current config  
cp config.json config.json.before_wind

# 2. Aktivera wind-modul permanent
python3 -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)

# Ersätt barometer med wind
config['modules']['wind_module']['enabled'] = True
config['modules']['barometer_module']['enabled'] = False

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    
print('✅ Wind-modul aktiverad permanent')
"

# 3. Restart och vänta
python3 restart.py
echo "⏰ Väntar 90 sekunder på uppdatering..."
sleep 90

# 4. Verifiera resultat
python3 screenshot.py --output wind_module_final
echo "📸 Screenshot tagen: screenshots/wind_module_final_[timestamp].png"

# 5. För att återgå till barometer:
# cp config.json.before_wind config.json && python3 restart.py
```

### Förväntade resultat
**E-Paper ska visa på MEDIUM 1 position (höger övre, 240×200px):**
```
      🌪️
      
    4.8 m/s
  Måttlig vind
  
     ↙️ SV
```

**CYKEL-FOKUSERAD layout-förklaring:**
- **🌪️** = Generell vind-ikon (wi-strong-wind.png, 48×48px) - centrerad överst
- **4.8 m/s** = M/S-VÄRDE PROMINENT (hero_temp font) - huvuddata för cykling
- **Måttlig vind** = Svensk benämning (mindre font) - kontext under m/s
- **↙️ SV** = Pil-ikon + kort förkortning (32×32px ikon) - exakt riktning
- **Centrerat allt** = Optimal utnyttjande av 240×200px utan tekniska detaljer

---

## 📋 Projektsammanfattning

### ✅ Vad som har skapats - CYKEL-FOKUSERAD WIND-MODUL

#### **🚴‍♂️ Cykel-användning i fokus:**
Denna wind-modul är designad specifikt för SNABBA CYKEL-BESLUT:
- **"Ska jag cykla idag?"** → M/S-värdet prominent visar om det blåser för hårt
- **"Vilken väg ska jag ta?"** → Vindriktning visar om du får med/motvind på rutten
- **"Behöver jag förbereda mig?"** → Svenska benämningar ger direkt förståelse

#### **🎯 Designbeslut för cykel-optimering:**
1. **M/S-värdet STÖRST** - det du kollar först (hero_temp font)
2. **Korta riktningar** - "SV" istället av "Sydvästlig vind" (mer plats, snabbare läsning)
3. **Centrerad layout** - optimal för E-Paper:s begränsade yta (240×200px)
4. **Borttaget tekniska detaljer** - inga grader eller datakällor som stör

#### **📊 Teknisk implementation:**
1. **API-utökning**: `weather_client.py` hämtar nu vindriktning (wd parameter) från SMHI
2. **Mappningar**: `icon_manager.py` konverterar rådata till cykel-relevant information:
   - 4.8 m/s → "Måttlig vind" (enligt Beaufort "Benämning på land")
   - 225° → "SV" (kort svensk förkortning från kompass)
3. **Renderer**: `wind_renderer.py` - cykel-optimerad layout med dubbla ikoner
4. **Integration**: Registrerad i ModuleFactory + trigger-baserad aktivering

### 🎯 Användning för cykel-beslut
- **Automatisk**: Wind-modul aktiveras vid vindstyrka >10 m/s (frisk vind)
- **Manuell**: Sätt `wind_module.enabled = true` för permanent visning
- **Position**: Ersätter barometer-modulen (höger övre, MEDIUM 1)

### 🏗️ Arkitektonisk kvalitet
- ✅ **4 modulära faser**: Varje fas självständig och testbar
- ✅ **Cykel-fokuserad**: Designad för praktisk wind-användning, inte tekniska detaljer
- ✅ **Robust**: Graceful fallback, smart positionering, E-Paper-optimerad
- ✅ **Integrera**: Använder befintlig arkitektur utan att störa andra moduler

**🚴‍♂️ SLUTRESULTAT**: En wind-modul som gör cykel-vindsbeslut blixtnabba och intuitive!