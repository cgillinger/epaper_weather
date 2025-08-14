#!/usr/bin/env python3
"""
E-Paper Väderapp - Med riktiga väderdata från SMHI + Weather Icons + Exakta soltider + NETATMO
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)
KOMPLETT: Netatmo lokala sensorer + SMHI prognoser + exakta soltider
FIXED: Korrekt 3-timmars trycktrend med meteorologisk standard
"""

import sys
import os
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict
from PIL import Image, ImageDraw, ImageFont
import logging

# Lägg till Waveshare biblioteket i path
sys.path.append(os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

# Lägg till modules-mappen
sys.path.append('modules')
from weather_client import WeatherClient
from icon_manager import WeatherIconManager

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    print("🔧 Kontrollera att E-Paper biblioteket är installerat korrekt")
    sys.exit(1)

class EPaperWeatherApp:
    """Huvudklass för E-Paper väderapp med Netatmo + SMHI + Weather Icons + exakta soltider"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera appen med konfiguration och ikon-hantering"""
        print("🌤️ E-Paper Väderapp med Netatmo + SMHI + Exakta soltider - Startar...")
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
            
        # Setup logging
        self.setup_logging()
        
        # Initialisera weather client (nu med full Netatmo + SunCalculator)
        self.weather_client = WeatherClient(self.config)
        
        # Initialisera ikon-hanterare
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")
        
        # Initialisera E-Paper display
        self.epd = None
        self.init_display()
        
        # Skapa canvas för rendering
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)  # Vit bakgrund
        self.draw = ImageDraw.Draw(self.canvas)
        
        # Ladda typsnitt
        self.fonts = self.load_fonts()
        
        print("✅ E-Paper Väderapp med Netatmo + exakta soltider initialiserad!")
    
    def load_config(self, config_path):
        """Ladda JSON-konfiguration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ Konfiguration laddad från {config_path}")
            return config
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None
    
    def setup_logging(self):
        """Konfigurera logging"""
        log_level = getattr(logging, self.config['debug']['log_level'], logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/weather.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔧 Logging konfigurerat")
    
    def init_display(self):
        """Initialisera E-Paper display"""
        try:
            self.logger.info("📱 Initialiserar E-Paper display...")
            self.epd = epd4in26.EPD()
            self.epd.init()
            self.epd.Clear()
            self.logger.info("✅ E-Paper display redo")
        except Exception as e:
            self.logger.error(f"❌ E-Paper display-fel: {e}")
            if not self.config['debug']['test_mode']:
                sys.exit(1)
    
    def load_fonts(self):
        """Ladda typsnitt för olika moduler"""
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']
        
        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(font_path, size)
            self.logger.info(f"✅ {len(fonts)} typsnitt laddade")
        except Exception as e:
            self.logger.warning(f"⚠️ Typsnitt-fel: {e}, använder default")
            # Fallback till default font
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()
        
        return fonts
    
    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)
    
    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar som inte dubbleras"""
        # Bara rita vissa sidor för att undvika dubblering
        if module_name == 'main_weather':
            # HERO: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'barometer_module':
            # MEDIUM 1: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'tomorrow_forecast':
            # MEDIUM 2: Rita alla sidor
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'clock_module':
            # SMALL 1: Rita alla sidor utom höger (för att undvika dubblering med status_module)
            # Topp, vänster, botten
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)  # Topp
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)  # Vänster
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)  # Botten
            # Höger sida - tunnare för att inte konflikta
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=1)  # Höger (tunn)
            
            # Inre ram
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)  # Topp
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)  # Vänster
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Botten
            
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        
        elif module_name == 'status_module':
            # SMALL 2: Rita alla sidor utom vänster (för att undvika dubblering med clock_module)
            # Topp, höger, botten
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)  # Topp
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)  # Höger
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)  # Botten
            # Vänster sida - tunnare för att inte konflikta
            self.draw.line([(x, y), (x, y + height)], fill=0, width=1)  # Vänster (tunn)
            
            # Inre ram
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)  # Topp
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Höger
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)  # Botten
            
            # Dekorativ linje
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
    
    def get_swedish_date(self, date_obj):
        """
        Konvertera datum till svenska veckodagar och månader
        
        Args:
            date_obj: datetime-objekt
            
        Returns:
            Formaterad svensk datumsträng
        """
        swedish_days = {
            'Monday': 'Mån', 'Tuesday': 'Tis', 'Wednesday': 'Ons', 
            'Thursday': 'Tor', 'Friday': 'Fre', 'Saturday': 'Lör', 'Sunday': 'Sön'
        }
        
        swedish_months = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Maj', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dec'
        }
        
        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days.get(english_day, english_day[:3])
        
        day_num = date_obj.day
        month_num = date_obj.month
        swedish_month = swedish_months.get(month_num, str(month_num))
        
        return f"{swedish_day} {day_num}/{month_num}"
    
    def truncate_text(self, text, font, max_width):
        """Korta text så den får plats inom given bredd"""
        if not text:
            return text
            
        # Kontrollera om texten får plats som den är
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        # Förkorta ord för ord tills den får plats
        words = text.split()
        for i in range(len(words), 0, -1):
            truncated = ' '.join(words[:i])
            bbox = self.draw.textbbox((0, 0), truncated, font=font)
            truncated_width = bbox[2] - bbox[0]
            
            if truncated_width <= max_width:
                return truncated
        
        # Som sista utväg, returnera första ordet
        return words[0] if words else text
    
    def paste_icon_on_canvas(self, icon, x, y):
        """
        Sätt in ikon på canvas på given position
        
        Args:
            icon: PIL Image-objekt (1-bit) från icon_manager
            x, y: Position där ikon ska placeras
        """
        if icon is None:
            return
        
        try:
            # Sätt in ikon på canvas
            # För 1-bit bilder används paste med mask för transparens
            self.canvas.paste(icon, (x, y))
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid ikon-inplacering: {e}")
    
    def parse_sun_data_from_weather(self, weather_data: Dict) -> tuple:
        """
        Parsea soldata från weather_client och skapa soldata för ikon-manager
        
        Args:
            weather_data: Komplett väderdata från WeatherClient
            
        Returns:
            Tuple med (sunrise_datetime, sunset_datetime, sun_data_dict)
        """
        try:
            # Hämta soldata från weather_client
            sun_data = weather_data.get('sun_data', {})
            
            if not sun_data:
                self.logger.warning("⚠️ Ingen soldata från WeatherClient, använder fallback")
                # Fallback till nuvarande tid
                now = datetime.now()
                sunrise = now.replace(hour=6, minute=0, second=0)
                sunset = now.replace(hour=18, minute=0, second=0)
                return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat()}
            
            # Parsea datetime-objekt eller ISO-strängar
            sunrise_time = sun_data.get('sunrise_time')
            sunset_time = sun_data.get('sunset_time')
            
            if not sunrise_time or not sunset_time:
                # Försök parsea från ISO-strängar
                sunrise_str = sun_data.get('sunrise')
                sunset_str = sun_data.get('sunset')
                
                if sunrise_str and sunset_str:
                    try:
                        sunrise_time = datetime.fromisoformat(sunrise_str.replace('Z', '+00:00'))
                        sunset_time = datetime.fromisoformat(sunset_str.replace('Z', '+00:00'))
                    except:
                        # Fallback
                        now = datetime.now()
                        sunrise_time = now.replace(hour=6, minute=0, second=0)
                        sunset_time = now.replace(hour=18, minute=0, second=0)
                else:
                    # Sista fallback
                    now = datetime.now()
                    sunrise_time = now.replace(hour=6, minute=0, second=0)
                    sunset_time = now.replace(hour=18, minute=0, second=0)
            
            # Skapa soldata-dict för ikon-manager
            parsed_sun_data = {
                'sunrise': sunrise_time.isoformat(),
                'sunset': sunset_time.isoformat(),
                'daylight_duration': sun_data.get('daylight_duration', 'N/A'),
                'source': sun_data.get('sun_source', 'unknown')
            }
            
            self.logger.info(f"☀️ Soldata parsead: {sunrise_time.strftime('%H:%M')} - {sunset_time.strftime('%H:%M')} (källa: {parsed_sun_data['source']})")
            
            return sunrise_time, sunset_time, parsed_sun_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av soldata: {e}")
            # Fallback
            now = datetime.now()
            sunrise = now.replace(hour=6, minute=0, second=0)
            sunset = now.replace(hour=18, minute=0, second=0)
            return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat(), 'source': 'error_fallback'}
    
    def format_data_sources(self, weather_data: Dict) -> str:
        """
        NYTT: Formatera datakällor för status-modulen
        
        Args:
            weather_data: Väderdata med källor
            
        Returns:
            Formaterad sträng med datakällor
        """
        try:
            sources = []
            
            # Temperatur-källa
            temp_source = weather_data.get('temperature_source', '')
            if temp_source == 'netatmo':
                sources.append("Netatmo")
            elif temp_source == 'smhi':
                sources.append("SMHI")
            
            # Tryck-källa (om olika från temperatur)
            pressure_source = weather_data.get('pressure_source', '')
            if pressure_source == 'netatmo' and temp_source != 'netatmo':
                if 'Netatmo' not in sources:
                    sources.append("Netatmo")
            elif pressure_source == 'smhi' and temp_source != 'smhi':
                if 'SMHI' not in sources:
                    sources.append("SMHI")
            
            if not sources:
                return "fallback"
            
            return " + ".join(sources)
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid formatering av datakällor: {e}")
            return "unknown"
    
    def render_weather_layout(self):
        """Rendera layout med Netatmo + SMHI + ikoner + exakta soltider"""
        self.clear_canvas()
        
        # Hämta riktiga väderdata INKLUSIVE Netatmo sensorer
        self.logger.info("🌐 Hämtar väderdata från Netatmo + SMHI + exakta soltider...")
        weather_data = self.weather_client.get_current_weather()
        
        # Parsea exakta soltider från weather_client
        sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
        
        # Aktuell tid för dag/natt-bestämning
        current_time = datetime.now()
        
        # Rita alla moduler enligt konfiguration
        modules = self.config['modules']
        
        for module_name, module_config in modules.items():
            if module_config['enabled']:
                x = module_config['coords']['x']
                y = module_config['coords']['y'] 
                width = module_config['size']['width']
                height = module_config['size']['height']
                
                # Rita smarta modulramar
                self.draw_module_border(x, y, width, height, module_name)
                
                # Rita innehåll för varje modul MED NETATMO + SMHI DATA
                if module_name == 'main_weather':
                    temp = weather_data.get('temperature', 20.0)
                    desc = weather_data.get('weather_description', 'Okänt väder')
                    temp_source = weather_data.get('temperature_source', 'fallback')
                    location = weather_data.get('location', 'Okänd plats')
                    smhi_symbol = weather_data.get('weather_symbol', 1)  # SMHI väder-symbol
                    
                    # Plats överst i hero-modulen
                    self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)
                    
                    # VÄDERIKON med exakt dag/natt-logik
                    weather_icon = self.icon_manager.get_weather_icon_for_time(
                        smhi_symbol, current_time, sun_data, size=(80, 80)
                    )
                    if weather_icon:
                        # Placera ikon till höger om temperaturen
                        icon_x = x + 320
                        icon_y = y + 50
                        self.paste_icon_on_canvas(weather_icon, icon_x, icon_y)
                    
                    # TEMPERATUR (prioriterat från Netatmo!)
                    self.draw.text((x + 20, y + 60), f"{temp:.1f}°", font=self.fonts['hero_temp'], fill=0)
                    
                    # Beskrivning (från SMHI meteorologi)
                    desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
                    self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)
                    
                    # NYTT: Visa temperatur-källa
                    if temp_source == 'netatmo':
                        source_text = "(NETATMO)"
                    elif temp_source == 'smhi':
                        source_text = "(SMHI)"
                    else:
                        source_text = f"({temp_source.upper()})"
                    
                    self.draw.text((x + 20, y + 185), source_text, font=self.fonts['tiny'], fill=0)
                    
                    # EXAKTA SOL-IKONER + tider
                    sunrise_str = sunrise.strftime('%H:%M')
                    sunset_str = sunset.strftime('%H:%M')
                    
                    # Soluppgång - ikon + exakt tid
                    sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(40, 40))
                    if sunrise_icon:
                        self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 210)
                        self.draw.text((x + 65, y + 220), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                    else:
                        # Fallback utan ikon
                        self.draw.text((x + 20, y + 220), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)
                    
                    # Solnedgång - ikon + exakt tid  
                    sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(40, 40))
                    if sunset_icon:
                        self.paste_icon_on_canvas(sunset_icon, x + 160, y + 210)
                        self.draw.text((x + 205, y + 220), sunset_str, font=self.fonts['medium_desc'], fill=0)
                    else:
                        # Fallback utan ikon
                        self.draw.text((x + 160, y + 220), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)
                    
                    # NYTT: Visa soldata-källa (diskret)
                    sun_source = sun_data.get('source', 'unknown')
                    if sun_source != 'unknown':
                        source_text = f"Sol: {sun_source}"
                        if sun_source == 'ipgeolocation.io':
                            source_text = "Sol: API ✓"
                        elif sun_source == 'fallback':
                            source_text = "Sol: approx"
                        self.draw.text((x + 20, y + 250), source_text, font=self.fonts['tiny'], fill=0)
                
                elif module_name == 'barometer_module':
                    # 🚨 FIXED: Använd RIKTIGA trycktrend-data från weather_client
                    pressure = weather_data.get('pressure', 1013)
                    pressure_source = weather_data.get('pressure_source', 'unknown')
                    
                    # ANVÄND RIKTIGA TREND-DATA från weather_client.py
                    pressure_trend = weather_data.get('pressure_trend', {})
                    trend_text = weather_data.get('pressure_trend_text', 'Samlar data')
                    trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')
                    
                    # 🎯 LOGGA VAD VI FAKTISKT FÅR
                    self.logger.info(f"🔍 BAROMETER DEBUG:")
                    self.logger.info(f"  pressure_trend: {pressure_trend}")
                    self.logger.info(f"  trend_text: {trend_text}")
                    self.logger.info(f"  trend_arrow: {trend_arrow}")
                    
                    # Barometer-ikon
                    barometer_icon = self.icon_manager.get_system_icon('barometer', size=(32, 32))
                    if barometer_icon:
                        self.paste_icon_on_canvas(barometer_icon, x + 20, y + 30)
                        # Tryck-värde bredvid ikon (FIXAD position - inte längre överlappande med pil)
                        self.draw.text((x + 60, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                    else:
                        # Fallback utan ikon
                        self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                    
                    # hPa-text (FIXAD: Flyttad längre ner för att inte kollidera med siffran)
                    self.draw.text((x + 60, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                    
                    # RIKTIGA TREND-TEXT (från 3h-analys) - RADBRYTS OM DET ÄR "Samlar data"
                    if trend_text == 'Samlar data':
                        self.draw.text((x + 20, y + 125), "Samlar", font=self.fonts['medium_desc'], fill=0)
                        self.draw.text((x + 20, y + 150), "data", font=self.fonts['medium_desc'], fill=0)
                    else:
                        self.draw.text((x + 20, y + 125), trend_text, font=self.fonts['medium_desc'], fill=0)
                    
                    # BONUS: Visa numerisk 3h-förändring om tillgänglig
                    if pressure_trend.get('change_3h') is not None and pressure_trend.get('trend') != 'insufficient_data':
                        change_3h = pressure_trend['change_3h']
                        change_text = f"{change_3h:+.1f} hPa/3h"
                        # Placera under trend-text, anpassat för radbrytsning
                        change_y = y + 175 if trend_text == 'Samlar data' else y + 150
                        self.draw.text((x + 20, change_y), change_text, font=self.fonts['small_desc'], fill=0)
                    
                    # TREND-PIL från Weather Icons - FIXAD position för att undvika avklippning
                    trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(56, 56))  # Optimal storlek för tydlighet
                    if trend_icon:
                        # Höger sida av modulen, men högre upp för att undvika avklippning
                        trend_x = x + width - 65  # 65px från höger kant
                        trend_y = y + 100  # Högre upp för att ge utrymme för hela pilen (56px hög)
                        self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)
                    
                    # NYTT: Visa tryck-källa (diskret) - FLYTTAD FÖR ATT INTE KOLLIDERA MED PIL
                    if pressure_source == 'netatmo':
                        self.draw.text((x + 20, y + height - 20), "(Netatmo)", font=self.fonts['tiny'], fill=0)
                    elif pressure_source == 'smhi':
                        self.draw.text((x + 20, y + height - 20), "(SMHI)", font=self.fonts['tiny'], fill=0)
                
                elif module_name == 'tomorrow_forecast':
                    tomorrow = weather_data.get('tomorrow', {})
                    tomorrow_temp = tomorrow.get('temperature', 18.0)
                    tomorrow_desc = tomorrow.get('weather_description', 'Okänt')
                    tomorrow_symbol = tomorrow.get('weather_symbol', 3)
                    
                    # "Imorgon" titel
                    self.draw.text((x + 20, y + 30), "Imorgon", font=self.fonts['medium_desc'], fill=0)
                    
                    # Imorgon väderikon
                    tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(32, 32))
                    if tomorrow_icon:
                        self.paste_icon_on_canvas(tomorrow_icon, x + 180, y + 30)
                    
                    # Temperatur (alltid från SMHI-prognos)
                    self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)
                    
                    # Väderbeskrivning
                    desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
                    self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)
                    
                    # NYTT: Visa att det är SMHI-prognos
                    self.draw.text((x + 20, y + 155), "(SMHI prognos)", font=self.fonts['tiny'], fill=0)
                
                elif module_name == 'clock_module':
                    now = datetime.now()
                    
                    # Klockikon
                    clock_icon = self.icon_manager.get_system_icon('clock3', size=(24, 24))
                    if clock_icon:
                        self.paste_icon_on_canvas(clock_icon, x + 10, y + 18)
                        self.draw.text((x + 40, y + 20), now.strftime('%H:%M'), font=self.fonts['small_main'], fill=0)
                    else:
                        self.draw.text((x + 10, y + 20), now.strftime('%H:%M'), font=self.fonts['small_main'], fill=0)
                    
                    # Svenska datum
                    swedish_date = self.get_swedish_date(now)
                    self.draw.text((x + 10, y + 60), swedish_date, font=self.fonts['small_desc'], fill=0)
                
                elif module_name == 'status_module':
                    update_time = datetime.now().strftime('%H:%M')
                    
                    # Status med ikon
                    status_icon = self.icon_manager.get_system_icon('status_ok', size=(12, 12))
                    if status_icon:
                        self.paste_icon_on_canvas(status_icon, x + 10, y + 18)
                        self.draw.text((x + 25, y + 20), "Status: OK", font=self.fonts['small_desc'], fill=0)
                    else:
                        self.draw.text((x + 10, y + 20), "Status: ✓ OK", font=self.fonts['small_desc'], fill=0)
                    
                    # Update-ikon
                    update_icon = self.icon_manager.get_system_icon('update', size=(12, 12))
                    if update_icon:
                        self.paste_icon_on_canvas(update_icon, x + 10, y + 43)
                        self.draw.text((x + 25, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
                    else:
                        self.draw.text((x + 10, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
                    
                    # UPPDATERAD: Visa intelligenta datakällor
                    data_sources = self.format_data_sources(weather_data)
                    self.draw.text((x + 10, y + 70), f"Data: {data_sources}", font=self.fonts['small_desc'], fill=0)
        
        self.logger.info("🎨 Layout renderad med Netatmo + SMHI + Weather Icons + exakta soltider")
        
        # Debug: Visa datakällor i log
        temp_source = weather_data.get('temperature_source', 'unknown')
        pressure_source = weather_data.get('pressure_source', 'unknown')
        sources = weather_data.get('data_sources', [])
        
        # NYTT: Logga trycktrend-information MED DETALJERAD DEBUG
        pressure_trend = weather_data.get('pressure_trend', {})
        if pressure_trend:
            self.logger.info(f"📊 KOMPLETT pressure_trend data: {pressure_trend}")
            
            if pressure_trend.get('trend') not in ['unknown', 'insufficient_data', 'error']:
                trend_info = f"{pressure_trend.get('change_3h', 0.0):+.1f} hPa/3h → {pressure_trend.get('trend', 'unknown')}"
                self.logger.info(f"📊 3h-Trycktrend: {trend_info}")
            else:
                self.logger.info(f"📊 Trycktrend inte tillgänglig: {pressure_trend.get('trend', 'unknown')} (data: {pressure_trend.get('data_hours', 0.0):.1f}h)")
        
        self.logger.info(f"📊 Datakällor - Temp: {temp_source}, Tryck: {pressure_source}, Alla: {sources}")
        
        if 'sun_data' in weather_data:
            sun_info = weather_data['sun_data']
            self.logger.info(f"☀️ Soldata: {sunrise.strftime('%H:%M')}-{sunset.strftime('%H:%M')} ({sun_info.get('daylight_duration', 'N/A')}) från {sun_info.get('sun_source', 'unknown')}")
    
    def display_canvas(self):
        """Visa canvas på E-Paper display"""
        try:
            if self.epd and not self.config['debug']['test_mode']:
                self.logger.info("📱 Uppdaterar E-Paper display...")
                self.epd.display(self.epd.getbuffer(self.canvas))
                self.logger.info("✅ E-Paper display uppdaterad")
            else:
                self.logger.info("🧪 Test-läge: Sparar bild istället för display")
                
            # ALLTID spara screenshot för visning
            self.save_screenshot()
                
        except Exception as e:
            self.logger.error(f"❌ Display-fel: {e}")
    
    def save_screenshot(self):
        """Spara screenshot av aktuell rendering"""
        try:
            # Skapa screenshots-mapp om den inte finns
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Spara original 1-bit format
            original_filename = f"{screenshot_dir}/1bit_epaper_{timestamp}.png"
            self.canvas.save(original_filename)
            
            # Konvertera till RGB för bättre visning
            rgb_canvas = self.canvas.convert('RGB')
            rgb_filename = f"{screenshot_dir}/epaper_{timestamp}.png"
            rgb_canvas.save(rgb_filename)
            
            self.logger.info(f"📸 Screenshot sparad: {rgb_filename}")
            print(f"📸 Screenshot: {rgb_filename}")
            
        except Exception as e:
            self.logger.error(f"⚠️ Screenshot-fel: {e}")
    
    def run_weather_app(self):
        """Kör väderapp med Netatmo + SMHI + ikoner + exakta soltider"""
        try:
            self.logger.info("🌤️ Startar E-Paper väderapp med Netatmo integration...")
            
            # Rendera väder-layout med alla datakällor
            self.render_weather_layout()
            
            # Visa på display
            self.display_canvas()
            
            print("\n" + "="*60)
            print("✅ E-PAPER VÄDERAPP MED NETATMO INTEGRATION!")
            print("📱 Kontrollera E-Paper display för komplett väderdata")
            print("📁 Loggar: logs/weather.log")
            print("📸 Screenshots: screenshots/epaper_*.png")
            print("🏠 Netatmo: Temperatur (utomhus) + Lufttryck (inomhus)")
            print("🌤️ SMHI: Väder, prognoser, vind, nederbörd")
            print("☀️ Exakta soltider från ipgeolocation.io API")
            print("🎨 Weather Icons med fallback-system")
            print("🧠 Intelligent datakombination: Lokalt + Prognoser")
            print("📊 FIXED: 3-timmars trycktrend med meteorologisk standard")
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"❌ Väderapp misslyckades: {e}")
            raise
    
    def cleanup(self):
        """Städa upp resurser"""
        try:
            if self.epd:
                self.epd.sleep()
            
            # Rensa ikon-cache
            if hasattr(self, 'icon_manager'):
                self.icon_manager.clear_cache()
                
            self.logger.info("🧹 Cleanup genomförd")
        except Exception as e:
            self.logger.error(f"⚠️ Cleanup-fel: {e}")

def main():
    """Huvudfunktion"""
    app = None
    try:
        # Skapa och kör väderapp med Netatmo + alla funktioner
        app = EPaperWeatherApp()
        app.run_weather_app()
        
    except KeyboardInterrupt:
        print("\n⚠️ Avbruten av användare")
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if app:
            app.cleanup()

if __name__ == "__main__":
    main()
