# E-Paper Väderapp - Komplett Projekt med Dynamic Module System
**Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480px)**

> Det här är ett personligt hobbyprojekt som jag byggt för eget bruk och lagt upp ifall det är till nytta för någon annan. Jag jobbar på det på fritiden, så issues och PR:ar är välkomna men svar kan dröja. Använd på egen risk.

## 🏆 Projektöversikt

Avancerad väderstation med E-Paper display som kombinerar lokala Netatmo-sensorer med SMHI väderdata, **SMHI Observations från Observatorielunden** och exakta soltider. Systemet använder ett **Dynamic Module System** med trigger-baserade moduler, högkvalitativa Weather Icons och intelligent rendering pipeline för professionell presentation.

**🚀 NYTT: Villkorsbaserade moduler** som automatiskt aktiveras baserat på väderförhållanden (t.ex. nederbörd-varningar för cykling).
**🆕 NYTT: SMHI Observations** för exakt "regnar just nu"-logik från station 98230 (Stockholm-Observatoriekullen).

## 🔧 Hårdvarukrav

### Huvudkomponenter
- **Raspberry Pi 3B** (eller nyare)
- **Waveshare 4.26" E-Paper HAT** (800×480px, svartvit)
- **SPI aktiverat** (`lsmod | grep spi` ska visa spi-moduler)
- **Internet-anslutning** för API-anrop

### E-Paper Specifikationer
- **Upplösning**: 800×480 pixlar
- **Färger**: 1-bit svartvit (optimerat för E-Paper)
- **Uppdateringstid**: ~10 sekunder per rendering
- **Strömförbrukning**: Mycket låg (E-Paper behåller bild utan ström)

## 📊 Funktionalitet och Datakällor

### Intelligenta Datakällor
**NETATMO** (prioriterat för lokala mätningar):
- 🌡️ **Utomhustemperatur** (från utomhusmodul)
- 📊 **Lufttryck** (från inomhusmodul, mer exakt än SMHI)
- 💨 **Luftfuktighet** (utomhus + inomhus)
- 📈 **3-timmars trycktrend** (meteorologisk standard)

**SMHI PROGNOSER** (för prognoser och väderdata):
- 🌤️ **Aktuellt väder** (27 SMHI-symboler med dag/natt-varianter)
- 🌦️ **Morgondagens prognos** (temperatur + väder)
- 💨 **Vind och nederbörd** (inklusive cykel-väder analys)
- 📍 **Exakta geografiska data**

**🆕 SMHI OBSERVATIONS** (för exakt "regnar just nu"):
- 🌧️ **Aktuell nederbörd** (senaste timmen från Observatorielunden)
- 📊 **Station 98230** (Stockholm-Observatoriekullen A)
- ✅ **Kvalitetskoder** (G=Godkänt, Y=Preliminärt, R=Dåligt)
- ⏰ **Timmesdata** (uppdateras varje hel timme)
- 🔄 **Fallback till Arlanda** (station 97390) vid fel

**ipgeolocation.io API** (exakta soltider):
- ☀️ **Soluppgång/solnedgång** (exakt tid för koordinater)
- ⏰ **Dagsljuslängd** (automatisk beräkning)
- 🌅 **Dag/natt-logik** för väderikoner

### Smart Datakombination med Prioritering
Appen använder **intelligent prioritering** med ny observations-logik:
1. **Netatmo** för lokala mätningar (temperatur, tryck)
2. **🆕 SMHI Observations** för nederbörd (prioriterat över prognoser)
3. **SMHI Prognoser** för väderprognos och meteorologi (fallback för nederbörd)
4. **API soltider** för exakt sol-information
5. **Fallback-system** vid API-fel

#### Nederbörd-prioritering:
```
PRIORITERING: SMHI Observations > SMHI Prognoser > Fallback
- observations > 0 → använd observations-värde
- observations = 0 → använd prognos-värde  
- båda saknas → fallback till 0mm/h
```

## 🔄 Dynamic Module System

### **Revolutionerande arkitektur för villkorsbaserade moduler**

Systemet kan automatiskt växla mellan olika moduler baserat på:
- 🌧️ **Väderförhållanden** (nederbörd aktiverar cykel-väder varningar)
- 👤 **Användarinställningar** (växla mellan barometer/sol-modul)
- ⏰ **Tid/säsong** (UV-index sommartid, mörka månader)
- 🎯 **Trigger-conditions** (anpassningsbara villkor)

### **Trigger-baserade Moduler med SMHI Observations**

```json
{
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_precipitation_2h > 0.2",
      "target_section": "bottom_section",
      "activate_group": "precipitation_active",
      "priority": 100,
      "description": "Aktivera nederbörd-modul vid regn eller kommande regn - NU MED OBSERVATIONS!"
    }
  }
}
```

**🆕 Exempel på dynamisk växling med observations:**
- **Normal layout**: Klocka + Status i botten
- **Observations: regnar nu (>0mm/h)**: Automatisk växling till nederbörd-varning
- **Observations: 0mm/h, men prognos >0.2mm/h**: Växling till prognos-varning
- **Efter regn**: Automatisk återgång till normal layout

## 🏗️ Arkitektur och Moduler

### Katalogstruktur
```
~/epaper_weather/
├── main_daemon.py            # Huvuddaemon + Dynamic Module System
├── config.json               # Modulkonfiguration + Triggers + API-nycklar + OBSERVATIONS
├── modules/
│   ├── weather_client.py     # SMHI + Netatmo + SunCalculator + OBSERVATIONS + Cykel-väder
│   ├── icon_manager.py       # Weather Icons hantering
│   ├── sun_calculator.py     # Exakta soltider (ipgeolocation.io)
│   └── renderers/            # Rendering Pipeline
│       ├── base_renderer.py       # Abstrakt baseklass
│       ├── module_factory.py      # Factory för renderer-skapande
│       └── precipitation_renderer.py  # Nederbörd-modul renderer
├── icons/                    # Weather Icons PNG-bibliotek
│   ├── weather/              # 54 väderikoner (27×2 dag/natt)
│   ├── pressure/             # Compass-pilar (wi-direction-X med ringar)
│   ├── sun/                  # Sol-ikoner (sunrise/sunset)
│   └── system/               # System-ikoner (barometer, klocka, kalender)
├── screenshots/              # Automatiska PNG-screenshots
├── logs/                     # System-logging + daemon-loggar
├── cache/                    # API-cache + tryckhistorik + test-data + OBSERVATIONS
├── backup/                   # Automatiska säkerhetskopior
└── tools/                    # 🆕 UPPDATERAT: Test-verktyg
    ├── test_precipitation_trigger.py  # 🆕 OBSERVATIONS-stöd + Prioriteringstest
    └── restart.py                     # Daemon restart-script
```

### **Dynamic Module System Komponenter**

#### **DynamicModuleManager**
```python
# Hanterar trigger-baserade moduler med OBSERVATIONS-stöd
class DynamicModuleManager:
    def evaluate_triggers(self, context_data: Dict) -> Dict[str, str]
    def get_active_modules(self, context_data: Dict) -> List[str]
    def should_layout_update(self, context_data: Dict) -> tuple
    # 🆕 NYT: Hanterar observations + prognos-data i trigger-context
```

#### **TriggerEvaluator**
```python
# Säker evaluering av villkor med OBSERVATIONS-prioritering
class TriggerEvaluator:
    def evaluate_condition(self, condition: str, context: Dict) -> bool
    # Stöder: precipitation (observations>prognoser), temperature, wind_speed, time_hour, etc.
```

#### **ModuleFactory + Rendering Pipeline**
```python
# Skapar rätt renderer för varje modul
class ModuleFactory:
    def create_renderer(self, module_name: str) -> ModuleRenderer
    
# Specifika renderers för olika modultyper
class PrecipitationRenderer(ModuleRenderer):
    def render(self, x, y, width, height, weather_data, context_data)
    # 🆕 NYT: Hanterar både observations och prognos-data
```

### Layout - DYNAMISK (Implementerad med OBSERVATIONS)
**Trigger-baserad layout som ändras automatiskt baserat på observations:**

#### **Normal Layout:**
```
┌─────────────────────────┬─────────────┐
│ Stockholm               │ 1007 ↗️     │
│ 25.1°C ⛅              │ hPa         │
│ Lätta regnskurar       │ Stigande    │
│ (NETATMO)              │ (Netatmo)   │
│ 🌅 04:16  🌇 21:30    ├─────────────┤
│ Sol: API ✓             │ Imorgon ⛅  │
├─────────┬──────────────┤ 25.4°C      │
│ 📅 25/7 │ Pipeline: ✓  │ Halvklart   │
│ Fredag  │ Update: 12:07│ (SMHI)      │
│         │ 5 moduler    │             │
└─────────┴──────────────┴─────────────┘
```

#### **🆕 Nederbörd-aktiv Layout (OBSERVATIONS-baserad):**
```
┌─────────────────────────┬─────────────┐
│ Stockholm               │ 1007 ↗️     │
│ 25.1°C ⛅              │ hPa         │
│ Lätta regnskurar       │ Stigande    │
│ (NETATMO)              │ (Netatmo)   │
│ 🌅 04:16  🌇 21:30    ├─────────────┤
│ Sol: API ✓             │ Imorgon ⛅  │
├─────────────────────────┤ 25.4°C      │
│ ⚠️  REGNAR NU: MÅTTLIGT │ Halvklart   │
│     (Observatorielunden)│ (SMHI)      │
│     2.5mm senaste timmen│             │
└─────────────────────────┴─────────────┘
```

**Moduler:**
- **HERO** (480×300px): Huvudtemperatur + väder + soltider
- **MEDIUM 1** (240×200px): Barometer + 3h-trycktrend
- **MEDIUM 2** (240×200px): Morgondagens väderprognos
- **DYNAMIC BOTTOM** (480×100px): **Klocka+Status** ELLER **Nederbörd-varning med OBSERVATIONS**

## 🎨 Ikonsystem - Weather Icons Integration

### SVG→PNG Konverteringssystem
Appen använder **högkvalitativa PNG-ikoner** konverterade från Weather Icons SVG-källor med E-Paper optimering.

**📁 IKON-KÄLLOR:**
- **SVG-källa**: `\\EINK-WEATHER\downloads\weather-icons-master\svg\` (Windows-delning)
- **PNG-destination**: `~/epaper_weather/icons/` (Raspberry Pi)
- **Konvertering**: Via `convert_svg_to_png.py` i virtuell miljö med cairosvg

#### Ikon-kategorier och Storlekar

**🌤️ WEATHER-IKONER (54 stycken)**
- **Källa**: Erik Flowers Weather Icons
- **Mappning**: Exakt SMHI-symbol → Weather Icons (samma som Väderdisplayens utils.py)
- **Dag/Natt**: Automatisk väljning baserat på soltider
- **Storlekar**: 32×32 (prognos), 48×48 (standard), 96×96 (HERO)

**🧭 PRESSURE-PILAR (Befintliga wi-direction-X)**
- **Källa**: wi-direction-up/down/right.png (befintliga med ringar)
- **Storlekar**: 20×20, 56×56, 64×64 (optimal), 96×96, 120×120
- **Användning**: 3-timmars trycktrend enligt meteorologisk standard

**☀️ SOL-IKONER**
- **Källa**: wi-sunrise.svg, wi-sunset.svg
- **Storlekar**: 24×24, 40×40 (standard), 56×56, 80×80
- **Användning**: Exakta soltider i HERO-modulen

**📊 SYSTEM-IKONER**
- **Barometer**: wi-barometer.svg → olika storlekar (12-96px)
- **Klocka**: wi-time-7.svg → 32×32 (optimal synlighet)
- **Kalender**: wi-calendar.svg → 40×40 (för datummodulen)
- **Status**: wi-day-sunny.svg (OK), wi-refresh.svg (update)

## ⚙️ Konfiguration (config.json)

### **🆕 SMHI Observations Konfiguration**

```json
{
  "stockholm_stations": {
    "observations_station_id": "98230",
    "observations_station_name": "Stockholm-Observatoriekullen A",
    "alternative_station_id": "97390", 
    "alternative_station_name": "Stockholm-Arlanda",
    "comment": "KORRIGERAD: Station 98230 för Observatorielunden fungerar med parameter 7!",
    "usage_note": "observations_station_id används för 'regnar just nu'-logik från senaste timmen"
  }
}
```

### **Dynamic Module System Konfiguration**

```json
{
  "_comment_dynamic_system": "=== DYNAMIC MODULE SYSTEM MED OBSERVATIONS ===",
  "module_groups": {
    "bottom_section": {
      "_comment": "Nederst: Normal = klocka+status, Precipitation = nederbörd", 
      "normal": ["clock_module", "status_module"],
      "precipitation_active": ["precipitation_module"]
    }
  },
  "triggers": {
    "precipitation_trigger": {
      "condition": "precipitation > 0 OR forecast_precipitation_2h > 0.2",
      "target_section": "bottom_section",
      "activate_group": "precipitation_active", 
      "priority": 100,
      "description": "Aktivera nederbörd-modul vid regn eller kommande regn - NU MED OBSERVATIONS från Observatorielunden!"
    }
  }
}
```

### API-nycklar
```json
{
  "api_keys": {
    "netatmo": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET", 
      "refresh_token": "YOUR_REFRESH_TOKEN"
    }
  }
}
```

### **🆕 Uppdateringsintervaller med OBSERVATIONS**
```json
{
  "update_intervals": {
    "netatmo_seconds": 600,
    "smhi_seconds": 1800,
    "smhi_observations_seconds": 900,
    "display_seconds": 300,
    "clock_seconds": 60,
    "_comment_observations": "SMHI observations uppdateras varje 15 min (data kommer varje timme från Observatorielunden)"
  }
}
```

### Debug och Test-konfiguration
```json
{
  "debug": {
    "enabled": true,
    "log_level": "INFO",
    "allow_test_data": true,
    "test_timeout_hours": 1,
    "_comment_test_safety": "allow_test_data måste vara true för test-data injection. Sätt till false i produktion!"
  }
}
```

## 🚀 Installation och Användning

### Förutsättningar
```bash
# SPI aktiverat för E-Paper
sudo raspi-config
# → Interfacing Options → SPI → Enable

# Waveshare E-Paper bibliotek installerat
# (specifik för Waveshare 4.26" HAT)
```

### **Daemon-baserad körning**
```bash
# Huvudsystem - kontinuerlig daemon
sudo systemctl start epaper-weather
sudo systemctl enable epaper-weather

# Restart daemon
python3 restart.py

# Live-loggar
sudo journalctl -u epaper-weather -f
```

### **Test och utveckling**
```bash
# Testa nederbörd-modul med OBSERVATIONS-stöd
python3 test_precipitation_trigger.py

# Ta screenshots för verifiering  
python3 screenshot.py --output test_layout

# Visa system-status
sudo systemctl status epaper-weather
```

## 🧪 **🆕 UPPDATERAT: Test-system för Dynamiska Moduler med SMHI Observations**

### **Avancerat Test-system för Nederbörd-trigger**

Det uppdaterade test-systemet stöder nu **både SMHI Observations och prognoser** för komplett testning av prioriteringslogiken:

```bash
# Aktivera avancerat test-läge
python3 test_precipitation_trigger.py
```

### **🆕 Nya Test-scenarion med OBSERVATIONS:**

#### **📊 Klassiska scenarion (uppdaterade med observations):**
```bash
# 1. Lätt regn (observations + prognoser konsistenta)
# Data: obs=0.8mm/h, prog=0.8mm/h, forecast=0mm/h
# Trigger: precipitation > 0 (observations prioriterat)

# 2. Måttligt regn (observations + prognoser konsistenta)  
# Data: obs=2.5mm/h, prog=2.5mm/h, forecast=0mm/h
# Trigger: precipitation > 0 (observations prioriterat)

# 3. Kraftigt regn (observations + prognoser + forecast)
# Data: obs=8.0mm/h, prog=8.0mm/h, forecast=1.2mm/h
# Trigger: precipitation > 0 (observations prioriterat)

# 4. Regn väntat (observations=0, använder prognoser)
# Data: obs=0mm/h, prog=1.5mm/h, forecast=1.5mm/h
# Trigger: forecast_precipitation_2h > 0.2 (fallback till prognos)

# 5. Cykel-varning (minimal nederbörd förväntat)
# Data: obs=0mm/h, prog=0mm/h, forecast=0.3mm/h  
# Trigger: forecast_precipitation_2h > 0.2
```

#### **🆕 Nya OBSERVATIONS-specifika scenarion:**
```bash
# 6. OBSERVATIONS-ONLY: Regnar enligt Observatorielunden
# Data: obs=1.8mm/h, prog=0mm/h, forecast=0mm/h
# Trigger: precipitation > 0 (observations visar regn, prognoser visar 0)
# Test: python3 test_precipitation_trigger.py → välj "6"

# 7. FORECAST-ONLY: Regn förväntat, regnar inte nu  
# Data: obs=0mm/h, prog=2.2mm/h, forecast=1.8mm/h
# Trigger: forecast_precipitation_2h > 0.2 (fallback till prognos)
# Test: python3 test_precipitation_trigger.py → välj "7"

# 8. KONFLIKT-SCENARIO: Observations vs Prognoser
# Data: obs=0.2mm/h, prog=3.5mm/h, forecast=0.8mm/h  
# Trigger: precipitation > 0 (observations 0.2mm/h prioriteras över prognos 3.5mm/h)
# Test: python3 test_precipitation_trigger.py → välj "8"

# 9. KVALITETSTEST: Observations opålitlig
# Data: obs=0mm/h, prog=2.0mm/h, forecast=1.2mm/h
# Trigger: forecast_precipitation_2h > 0.2 (fallback till prognos när observations=0)
# Test: python3 test_precipitation_trigger.py → välj "9"

# 10. CYKEL-TRÖSKELVÄRDE: Precis över gränsen
# Data: obs=0mm/h, prog=0mm/h, forecast=0.25mm/h
# Trigger: forecast_precipitation_2h > 0.2 (0.25 > 0.2)
# Test: python3 test_precipitation_trigger.py → välj "10"
```

### **🔍 Säkerhetsfeatures för test-systemet:**

- ✅ **Production-safe:** Kräver `debug.allow_test_data = true` i config
- ✅ **Automatisk timeout:** Test-data försvinner efter 1 timme  
- ✅ **Prioriteringslogik-test:** Simulerar exakt weather_client-beteende
- ✅ **Dual-source tracking:** Visar både observations och prognoser
- ✅ **Trigger-förklaring:** Visar vilken datakälla som aktiverade triggern
- ✅ **Reverterbart:** Kan stängas av utan restart

### **🎯 Praktisk användning av test-systemet - EXAKT TIMING:**

#### **⏱️ VIKTIGT: Timing-förväntningar**
- **Test-data aktiveras:** Omedelbart (json-fil skapas)
- **E-Paper ändring:** **60-90 sekunder** efter restart (daemon-intervall = 60s)
- **Test-data rensning:** **60-90 sekunder** efter rensning + restart
- **Auto-timeout:** 1 timme (test-data försvinner automatiskt)

```bash
# === KOMPLETT TEST-PROCEDUR MED EXAKT TIMING ===

# Steg 1: Ta screenshot av normal layout
python3 screenshot.py --output before_test
# ✅ Resultat: Omedelbart - screenshot sparas

# Steg 2: Aktivera test (t.ex. konflikt-scenario)  
python3 test_precipitation_trigger.py
# Välj: "8. Test konflikt-scenario"
# ✅ Resultat: Omedelbart - test-data sparas i cache/test_precipitation.json

# Steg 3: Restart daemon (OBLIGATORISKT för test-aktivering)
python3 restart.py
# ✅ Resultat: 20-30 sekunder - daemon startar om
# ⏰ VÄNTA: Daemon läser test-data vid första iteration

# Steg 4: VÄNTA på E-Paper uppdatering
echo "⏰ Väntar 90 sekunder på E-Paper uppdatering..."
sleep 90
# ✅ Resultat: E-Paper visar nederbörd-layout med test-data

# Steg 5: Ta screenshot av nederbörd-layout
python3 screenshot.py --output during_test
# ✅ Resultat: Omedelbart - visar test-layout

# Steg 6: Analysera vad som hände
python3 test_precipitation_trigger.py  
# Välj: "12. Analysera trigger-conditions"
# ✅ Resultat: Omedelbart - visar prioriteringslogik

# Steg 7: Rensa test-data (VIKTIGT: Måste göras manuellt!)
python3 test_precipitation_trigger.py
# Välj: "10. Rensa test-data"
# ✅ Resultat: Omedelbart - test-fil raderas

# Steg 8: Restart daemon igen för återställning
python3 restart.py
echo "⏰ Väntar 90 sekunder på återställning..."
sleep 90
# ✅ Resultat: E-Paper återgår till normal layout

# Steg 9: Bekräfta återställning
python3 screenshot.py --output after_test
# ✅ Resultat: Omedelbart - visar normal layout igen
```

#### **🚨 VIKTIGA DETALJER baserat på verklig erfarenhet:**

##### **⏰ Timing-problem att vara medveten om:**
```
PROBLEM: "Inget händer omedelbart efter test-aktivering"
ORSAK: Daemon läser bara test-data var 60:e sekund
LÖSNING: Vänta 60-90 sekunder efter restart

PROBLEM: "Rensning av test-data fungerar inte"  
ORSAK: cache/test_precipitation.json kan finnas kvar
LÖSNING: Kontrollera manuellt och radera vid behov

PROBLEM: "Test-data överlevde reboot"
ORSAK: JSON-filen sparas permanent i cache/
LÖSNING: Rensa ALLTID test-data innan shutdown
```

##### **🔧 Manual troubleshooting om test "fastnar":**
```bash
# Kontrollera om test-data finns kvar
ls -la cache/test_precipitation.json

# Visa innehåll i test-data  
cat cache/test_precipitation.json

# FORCE-rensa test-data om script inte fungerar
rm -f cache/test_precipitation.json
echo "🗑️ Test-data force-rensad"

# Restart daemon för säker återställning
python3 restart.py

# Vänta på återställning
echo "⏰ Väntar 90 sekunder på återställning..."
sleep 90

# Bekräfta normal layout
python3 screenshot.py --output recovery_check
```

##### **📊 Hur du VET att test fungerar:**

**1. Innan test (normal layout):**
```bash
python3 screenshot.py --output before
# Förväntat: Klocka + Status i nedre delen
```

**2. Under test (nederbörd-layout):**
```bash
# Efter 90 sekunder från restart:
python3 screenshot.py --output during  
# Förväntat: Nederbörd-varning i nedre delen istället för klocka+status
```

**3. Daemon-loggar bekräftar test:**
```bash
sudo journalctl -u epaper-weather -f
# Leta efter: "🧪 TEST-DATA AKTIVT" och "🎯 TRIGGER AKTIVERAS"
```

**4. Efter rensning (återställd layout):**
```bash
# Efter rensning + restart + 90 sekunder:
python3 screenshot.py --output after
# Förväntat: Tillbaka till klocka + status (identisk med "before")
```

### **🧪 Vad du förväntar dig se med OBSERVATIONS - MED EXAKT TIMING:**

**📅 Omedelbart efter test-aktivering:**
1. **JSON-fil skapas:** `cache/test_precipitation.json` med test-data
2. **Skript bekräftar:** "✅ Säker test-data injicerad med OBSERVATIONS-stöd"  
3. **Prioriteringslogik visas:** "observations 0.2mm/h prioriteras över prognos 3.5mm/h"

**🔄 20-30 sekunder efter restart:**
4. **Daemon startar:** Loggar visar "🌤️ E-Paper Weather Daemon startar"
5. **Test-data detekteras:** "🧪 TEST-DATA AKTIVT: Test konflikt: obs=0.2mm/h..."

**📱 60-90 sekunder efter restart:**
6. **E-Paper uppdateras:** Nederbörd-modul ersätter klocka+status
7. **Daemon loggar:** "🎯 TRIGGER AKTIVERAS → bottom_section = precipitation_active"  
8. **Observations-prioritering:** "🎯 PRIORITERING: Nederbörd från observations (0.2mm/h) istället för prognoser"

**📊 Under test-perioden:**
9. **Layout kvarstår:** Nederbörd-layout visas konsekvent
10. **Status-analys:** "12. Analysera trigger-conditions" visar aktiv trigger

**🗑️ Omedelbart efter rensning:**
11. **Test-fil raderas:** `cache/test_precipitation.json` försvinner
12. **Skript bekräftar:** "🗑️ Test-data rensad"

**🔄 60-90 sekunder efter rensning + restart:**
13. **Layout återställs:** E-Paper visar klocka+status igen
14. **Daemon loggar:** "💤 Trigger aktiveras INTE → bottom_section = normal"
15. **Normal drift:** "✅ Normal drift (inget test aktivt)"

#### **⚠️ Felsökning om något går fel:**

**Problem: E-Paper ändras aldrig trots test**
```bash
# Kontrollera daemon-status
sudo systemctl status epaper-weather
# Kontrollera loggar  
sudo journalctl -u epaper-weather -n 20
# Kontrollera test-fil
cat cache/test_precipitation.json
```

**Problem: Test-data försvinner inte**
```bash
# Force-rensa + restart
rm -f cache/test_precipitation.json && python3 restart.py
```

**Problem: Layout "fastnar" i test-läge** 
```bash
# Dubbelkolla timeout
python3 test_precipitation_trigger.py
# Välj: "6. Visa test-status"
# Om "UTGÅNGEN" → restart daemon
```

## 📈 Prestanda och Optimering

### Prestanda-mål (Uppnådda med OBSERVATIONS)
- **Total rendering**: Under 5 sekunder (inklusive API-anrop + observations + trigger evaluation)
- **E-Paper uppdatering**: Under 10 sekunder total
- **Trigger evaluation**: Under 100ms (säker condition parsing med observations-prioritering)
- **Module switching**: Omedelbar (ingen extra fördröjning för observations)
- **Minnesanvändning**: Under 100MB RAM
- **API-anrop**: Cached (SMHI 30min, **OBSERVATIONS 15min**, Netatmo 10min, Soltider 4h)

### **🆕 OBSERVATIONS-optimeringar:**
- **15-minuters cache:** Observations uppdateras oftare än prognoser
- **Fallback-system:** Automatisk växling till Arlanda (97390) vid fel på Observatorielunden (98230)
- **Kvalitetskontroll:** Filtrerar dåliga mätningar (quality code R)
- **Ålderskontroll:** Varnar om observations-data är >90 minuter gammal

### **Intelligent Change Detection med OBSERVATIONS:**
- **Observations-baserad triggering** - Detekterar verklig nederbörd omedelbart
- **Prioriteringsbaserad change detection** - Rätt datakälla används för jämförelse  
- **Data source tracking** - Både observations och prognoser spåras separat
- **Smart state tracking** - Både väderdata och layout state cachas med observations-info

## 🛡️ Fel-hantering och Robusthet

### **🆕 OBSERVATIONS-specifik Robusthet**
- **Station 98230 fel**: Automatisk fallback till station 97390 (Arlanda)
- **Observations API-fel**: Fallback till SMHI prognoser för nederbörd
- **Gammal observations-data**: Använd prognoser om data >90 min gammal
- **Kvalitetskoder**: Filtrera bort dåliga mätningar (R-kod)
- **Cache-fel**: Fortsätt med prognos-baserade triggers

### **Dynamic Module System Robusthet (uppdaterad)**
- **Trigger evaluation fel**: Graceful fallback till normal layout
- **Observations prioriteringsfel**: Fallback till prognosdata
- **Configuration fel**: Validering + fallback till working config  
- **Context data fel**: Safe defaults för alla trigger-variabler (inklusive observations)

### API-fel Hantering (Befintlig + OBSERVATIONS)
- **Netatmo API-fel**: Fallback till SMHI-data + cached Netatmo
- **SMHI API-fel**: Använd cached data + grundläggande väderinfo
- **🆕 OBSERVATIONS API-fel**: Fallback till prognoser + cached observations
- **Soltider API-fel**: Förenklad solberäkning baserat på koordinater
- **Display-fel**: Fortsätt med screenshot-generering för debugging

### Data-validering (utökad)
- **🆕 Observations-validering**: Kontroll av kvalitetskoder och data-ålder
- **🆕 Prioriteringslogik**: Säkerställer korrekt val mellan observations och prognoser
- **3-timmars trycktrend**: Kräver minimum 1.5h data för giltighet
- **Sensor-ålder**: Varnar om Netatmo-data >30 min gammal
- **Trigger conditions**: Säker parsing utan kod-execution med observations-stöd
- **Module configuration**: Validering av storlekar och positioner

## 🔄 Uppdateringsintervaller

### API-anrop Frekvens (uppdaterad med OBSERVATIONS)
- **Netatmo**: Var 10:e minut (mer aktuell lokaldata)
- **SMHI Prognoser**: Var 30:e minut (prognosdata ändras sällan)
- **🆕 SMHI Observations**: Var 15:e minut (data kommer varje timme från Observatorielunden)
- **Soltider**: Var 4:e timme (ändras långsamt)
- **E-Paper**: Var 60 sekunder (trigger evaluation + change detection med observations)

### **🆕 Observations-specifik Cache-strategi**
- **Observations-cache**: 15 minuter (mer frekvent än prognoser)
- **Station-fallback**: Arlanda-data cachas separat om Observatorielunden misslyckas
- **Kvalitetshistorik**: Sparar senaste kvalitetskoder för trend-analys
- **Tryckhistorik**: 24h rullande för trend-analys (från Netatmo)
- **API-cache**: JSON-filer med timestamp-validering (inklusive observations)
- **Ikon-cache**: I minnet under körning
- **Backup-system**: Automatiska säkerhetskopior vid alla ändringar

### **Trigger Evaluation (uppdaterad)**
- **Context building**: Varje daemon-iteration (60s) med observations-data
- **Condition evaluation**: <100ms per trigger (inklusive observations-prioritering)
- **Layout switching**: Omedelbar när trigger aktiveras (observations eller prognoser)
- **🆕 Observations-analys**: Vid varje observations-uppdatering (15 min)
- **Cykel-väder analys**: Vid varje SMHI-uppdatering med observations-input

## 🎯 Framtida Förbättringar

### **🆕 OBSERVATIONS-baserade utbyggnader:**
- **Fler SMHI-stationer**: Stöd för flera observations-stationer (temperatur, vind, etc.)
- **Regional observations**: Automatisk val av närmaste station baserat på koordinater
- **Kvalitets-viktning**: Använd kvalitetskoder för viktning mellan källor
- **Historisk observations**: Trend-analys baserat på observations-historik
- **Real-time varningar**: Push-notiser vid plötsliga observations-förändringar

### **Enkla tillägg med befintlig arkitektur:**
- **Säsongsmoduler**: UV-index sommartid, mörka månader-fokus
- **Användarstyrda moduler**: Manuell växling mellan barometer/sol
- **Fler trigger-conditions**: Vindstyrka (observations), extremtemperatur, tidsbaserat
- **Nya renderers**: WindRenderer (observations-baserad), UVRenderer, AirQualityRenderer

### **Advanced Features:**
- **🆕 Observations-debugging interface**: Visualisera observations vs prognoser
- **Trigger debugging interface**: Visualisera aktiva triggers med observations-prioritering
- **Configuration hot-reload**: Ändra triggers utan restart
- **Multi-source triggers**: Komplexa villkor med observations + prognoser + Netatmo
- **User preference management**: Web-interface för inställningar

### Tekniska optimeringar
- **Partiell uppdatering**: Endast ändrade moduler (kräver avancerat E-Paper stöd)
- **🆕 Asynkrona observations-anrop**: Parallella calls för snabbare observations-data
- **Asynkrona API-anrop**: Parallella calls för snabbare data-hämtning
- **Compressed screenshots**: Mindre filstorlek för backup
- **Hot-swappable renderers**: Runtime loading av nya moduler

## 📚 Teknisk Dokumentation

### **🆕 SMHI Observations API Integration**

```python
# Endpoint för Observatorielunden (parameter 7 = nederbörd)
url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/98230/period/latest-hour/data.json"

# Prioriteringslogik i weather_client.py
if observations_data and observations_data['precipitation_observed'] > 0:
    combined['precipitation'] = observations_data['precipitation_observed']
    combined['precipitation_source'] = 'smhi_observations'
else:
    combined['precipitation'] = smhi_data.get('precipitation', 0)
    combined['precipitation_source'] = 'smhi_forecast'
```

### **Kritiska filer för backup (uppdaterat)**
- **main_daemon.py**: Daemon + Dynamic Module System + Rendering Pipeline
- **config.json**: Komplett konfiguration + triggers + module groups + **OBSERVATIONS**
- **modules/weather_client.py**: API-integration + **OBSERVATIONS** + cykel-väder + test-data support
- **modules/renderers/**: Alla renderer-klasser + factory
- **tools/test_precipitation_trigger.py**: **🆕 OBSERVATIONS-test** + Prioriteringslogik-test
- **tools/restart.py**: Restart script

### **🆕 Nya beroenden för OBSERVATIONS**
- **PIL (Pillow)**: Bildbehandling + E-Paper rendering (befintlig)
- **requests**: API-anrop (SMHI, **OBSERVATIONS**, Netatmo, ipgeolocation.io) (utökad)
- **systemd**: Daemon-hantering för kontinuerlig körning
- **Dynamic imports**: Runtime loading av renderer-klasser

### **Utvecklingsverktyg (uppdaterat)**
- **🆕 test_precipitation_trigger.py**: Säker test-data injection för nederbörd MED OBSERVATIONS-stöd
- **restart.py**: Intelligent daemon restart med timeout-hantering
- **screenshot.py**: Debug-screenshots (kompatibel med observations-systemet)
- **backup-system**: Automatisk versionhantering + ORIGINAL-backups

---

## 🏆 Slutresultat

**Avancerad, intelligens väderstation** som kombinerar:
- 🏠 **Lokala sensorer** (Netatmo utomhus/inomhus)
- 🌍 **Meteorologisk data** (SMHI prognoser + cykel-väder analys)
- **🆕 Exakta observations** (SMHI Observatorielunden för "regnar just nu")
- ⭐ **Exakt astronomi** (API-baserade soltider)  
- 🎨 **Högkvalitativa ikoner** (Weather Icons SVG→PNG)
- 📱 **E-Paper optimering** (1-bit, kontrast, cache)
- 🔄 **Dynamic Module System** (trigger-baserade moduler med observations-prioritering)
- 🧪 **Robust test-system** (säker utveckling med observations + prognos-testning)

### **🆕 Revolutionary OBSERVATIONS Features:**
- **🌧️ Exakt nederbörd-medvetenhet**: Verklig nederbörd från Observatorielunden prioriterat över prognoser
- **🎯 Smart prioriteringslogik**: Observations > Prognoser > Fallback med intelligent växling
- **🔄 Trigger-driven layout**: Moduler aktiveras baserat på verkliga observations-förhållanden
- **🏭 Dual-source tracking**: Spårar både observations och prognoser separat
- **🔧 Production-ready**: Daemon + observations-logging + robust felhantering med station-fallback
- **📊 Intelligent caching**: Optimal cache-tider för olika datakällor (observations 15min, prognoser 30min)

### **🧪 Advanced Test-capabilities:**
- **Observations vs prognoser**: Testa prioriteringslogik mellan datakällor
- **Konflikt-scenarion**: Vad händer när observations och prognoser skiljer sig åt
- **Kvalitets-testning**: Simulera dålig observations-data för fallback-testning
- **Threshold-testning**: Precis testning av trigger-tröskelvärden (0.2mm/h för cykel-väder)

**Resultat**: Kristallklar, adaptiv väderstation med meteorologisk precision som automatiskt anpassar sig efter **verkliga väderförhållanden från Observatorielunden** och användarens behov, med komplett test-system för säker utveckling.
