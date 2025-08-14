#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Kontinuerlig väderstation
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)

DAEMON VERSION baserad på avancerad main.py:
- Kontinuerlig process istället för cron
- State i minnet för perfekt jämförelse  
- Minimal E-Paper slitage
- Robust felhantering
- Samma smarta uppdateringslogik som main.py
- Alla avancerade funktioner: Netatmo + SMHI + Smart caching + Watchdog
"""

import sys
import os
import json
import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont

# Lägg till projektets moduler
sys.path.append('modules')
sys.path.append(os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

from weather_client import WeatherClient
from icon_manager import WeatherIconManager

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    sys.exit(1)

class EPaperWeatherDaemon:
    """E-Paper Weather Daemon - Kontinuerlig väderstation med smart state-hantering"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera daemon"""
        print("🌤️ E-Paper Weather Daemon - Startar kontinuerlig väderstation...")
        
        # Daemon control
        self.running = True
        self.update_interval = 60  # 1 minut mellan kontroller
        self.watchdog_interval = 30 * 60  # 30 minuter watchdog
        
        # STATE I MINNET (ersätter fil-cache)
        self.current_display_state = None  # Perfekt state-hantering!
        self.last_update_time = 0
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
        
        # Setup logging för daemon
        self.setup_logging()
        
        # Initialisera komponenter
        self.weather_client = WeatherClient(self.config)
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")
        
        # Initialisera E-Paper display
        self.epd = None
        self.init_display()
        
        # Canvas setup
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)
        
        # Ladda typsnitt
        self.fonts = self.load_fonts()
        
        # Setup signal handlers för graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.logger.info("🌤️ E-Paper Weather Daemon initialiserad med smart state-hantering")
    
    def signal_handler(self, signum, frame):
        """Hantera shutdown signals"""
        self.logger.info(f"📶 Signal {signum} mottagen - avslutar daemon...")
        self.running = False
    
    def load_config(self, config_path):
        """Ladda JSON-konfiguration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None
    
    def setup_logging(self):
        """Konfigurera logging för daemon"""
        log_level = getattr(logging, self.config['debug']['log_level'], logging.INFO)
        
        # Skapa logs-mapp om den inte finns
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/weather_daemon.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_display(self):
        """Initialisera E-Paper display"""
        try:
            self.logger.info("📱 Initialiserar E-Paper display för daemon...")
            self.epd = epd4in26.EPD()
            self.epd.init()
            self.epd.Clear()
            self.logger.info("✅ E-Paper display redo för daemon")
        except Exception as e:
            self.logger.error(f"❌ E-Paper display-fel: {e}")
            if not self.config['debug']['test_mode']:
                sys.exit(1)
    
    def load_fonts(self):
        """Ladda typsnitt"""
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']
        
        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(font_path, size)
            self.logger.info(f"✅ {len(fonts)} typsnitt laddade")
        except Exception as e:
            self.logger.warning(f"⚠️ Typsnitt-fel: {e}, använder default")
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()
        
        return fonts
    
    def should_update_display(self, weather_data: Dict) -> tuple:
        """
        DAEMON STATE JÄMFÖRELSE - i minnet, inte fil!
        Samma logik som main.py men med in-memory state
        
        Args:
            weather_data: Ny väderdata
            
        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            # FÖRSTA KÖRNINGEN: Alltid uppdatera
            if self.current_display_state is None:
                return True, "Daemon första körning"
            
            # WATCHDOG: 30-minuters säkerhetsuppdatering
            time_since_last = time.time() - self.last_update_time
            if time_since_last > self.watchdog_interval:
                return True, f"30-min watchdog ({time_since_last/60:.1f} min)"
            
            # DATUM-ÄNDRING: Uppdatera vid midnatt
            current_date = datetime.now().strftime('%Y-%m-%d')
            last_date = self.current_display_state.get('date', '')
            if current_date != last_date:
                return True, f"Nytt datum: {last_date} → {current_date}"
            
            # JÄMFÖR VIKTIGA VÄDERDATA (exakt som main.py)
            comparisons = [
                ('temperature', weather_data.get('temperature'), 'Temperatur'),
                ('weather_symbol', weather_data.get('weather_symbol'), 'Väderikon'),
                ('weather_description', weather_data.get('weather_description'), 'Väderbeskrivning'),
                ('pressure', weather_data.get('pressure'), 'Lufttryck'),
                ('pressure_trend_text', weather_data.get('pressure_trend_text'), 'Trycktrend text'),
                ('pressure_trend_arrow', weather_data.get('pressure_trend_arrow'), 'Trycktrend pil'),
                ('tomorrow_temp', weather_data.get('tomorrow', {}).get('temperature'), 'Imorgon temperatur'),
                ('tomorrow_symbol', weather_data.get('tomorrow', {}).get('weather_symbol'), 'Imorgon väderikon'),
                ('tomorrow_desc', weather_data.get('tomorrow', {}).get('weather_description'), 'Imorgon beskrivning'),
                ('sunrise', weather_data.get('sun_data', {}).get('sunrise'), 'Soluppgång'),
                ('sunset', weather_data.get('sun_data', {}).get('sunset'), 'Solnedgång'),
            ]
            
            for key, current_value, description in comparisons:
                last_value = self.current_display_state.get(key)
                
                # Numeriska värden med tolerans
                if key in ['temperature', 'pressure', 'tomorrow_temp']:
                    if current_value is not None and last_value is not None:
                        if abs(float(current_value) - float(last_value)) >= 0.1:
                            return True, f"{description}: {last_value} → {current_value}"
                else:
                    # Exakt jämförelse för strängar och heltal
                    if current_value != last_value:
                        return True, f"{description}: {last_value} → {current_value}"
            
            # INGEN FÖRÄNDRING
            return False, "Inga förändringar"
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid jämförelse: {e}")
            return True, f"Fel vid jämförelse: {e}"
    
    def fetch_weather_data(self) -> Dict:
        """Hämta väderdata (samma som main.py)"""
        try:
            self.logger.debug("🌐 Hämtar väderdata från Netatmo + SMHI + exakta soltider...")
            
            # Hämta riktiga väderdata INKLUSIVE Netatmo sensorer
            weather_data = self.weather_client.get_current_weather()
            
            # Parsea exakta soltider från weather_client
            sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
            
            # Lägg till parsade soltider i weather_data
            weather_data['parsed_sunrise'] = sunrise
            weather_data['parsed_sunset'] = sunset
            weather_data['parsed_sun_data'] = sun_data
            
            return weather_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            # Returnera fallback-data
            return {
                'temperature': 20.0,
                'weather_description': 'Data ej tillgänglig',
                'pressure': 1013,
                'location': 'Okänd plats',
                'data_sources': ['fallback']
            }
    
    def parse_sun_data_from_weather(self, weather_data: Dict) -> tuple:
        """Parsea soldata (kopierat från main.py)"""
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
    
    def render_and_display(self, weather_data: Dict):
        """Rendera och visa på E-Paper display"""
        try:
            self.logger.info("🎨 Renderar ny layout...")
            
            # FULLSTÄNDIG RENDERING - kopierat från main.py
            self.clear_canvas()
            
            # Hämta parsade soltider från weather_data
            sunrise = weather_data.get('parsed_sunrise')
            sunset = weather_data.get('parsed_sunset')
            sun_data = weather_data.get('parsed_sun_data', {})
            
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
                        
                        # VÄDERIKON med exakt dag/natt-logik - VERKLIG HÖGUPPLÖST STORLEK (96x96)
                        weather_icon = self.icon_manager.get_weather_icon_for_time(
                            smhi_symbol, current_time, sun_data, size=(96, 96)
                        )
                        if weather_icon:
                            # Placera ikon till höger om temperaturen - justerad position för 96x96
                            icon_x = x + 320
                            icon_y = y + 50
                            self.paste_icon_on_canvas(weather_icon, icon_x, icon_y)
                            self.logger.info(f"🎨 HERO väderikon: 96x96 SVG-baserad (symbol {smhi_symbol})")
                        
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
                        
                        # EXAKTA SOL-IKONER + tider - HÖGUPPLÖST STORLEK (56x56)
                        if sunrise and sunset:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                            
                            # Soluppgång - ikon + exakt tid
                            sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(56, 56))
                            if sunrise_icon:
                                self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 200)
                                self.draw.text((x + 80, y + 215), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                                self.logger.debug(f"🌅 Sol-ikon: 56x56 SVG-baserad")
                            else:
                                # Fallback utan ikon
                                self.draw.text((x + 20, y + 215), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)
                            
                            # Solnedgång - ikon + exakt tid  
                            sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(56, 56))
                            if sunset_icon:
                                self.paste_icon_on_canvas(sunset_icon, x + 180, y + 200)
                                self.draw.text((x + 240, y + 215), sunset_str, font=self.fonts['medium_desc'], fill=0)
                                self.logger.debug(f"🌇 Sol-ikon: 56x56 SVG-baserad")
                            else:
                                # Fallback utan ikon
                                self.draw.text((x + 180, y + 215), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)
                        
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
                        
                        # Barometer-ikon - HÖGUPPLÖST STORLEK (80x80)
                        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
                        if barometer_icon:
                            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
                            # Tryck-värde bredvid ikon (justerad position för större ikon)
                            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                            self.logger.info(f"📊 Barometer-ikon: 80x80 SVG-baserad")
                        else:
                            # Fallback utan ikon
                            self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                        
                        # hPa-text
                        self.draw.text((x + 100, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                        
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
                        
                        # TREND-PIL från Weather Icons - OPTIMERAD STORLEK (64x64)
                        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
                        if trend_icon:
                            # Höger sida av modulen, optimerad position för 64x64
                            trend_x = x + width - 75  # 75px från höger kant för 64px ikon
                            trend_y = y + 100  # Centrerad vertikalt
                            self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)
                            self.logger.info(f"↗️ Trycktrend-pil: 64x64 SVG-baserad ({trend_arrow})")
                        
                        # NYTT: Visa tryck-källa (diskret)
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
                        
                        # Imorgon väderikon - HÖGUPPLÖST STORLEK (80x80)
                        tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(80, 80))
                        if tomorrow_icon:
                            self.paste_icon_on_canvas(tomorrow_icon, x + 140, y + 20)
                            self.logger.debug(f"🌦️ Prognos-ikon: 80x80 SVG-baserad (symbol {tomorrow_symbol})")
                        
                        # Temperatur (alltid från SMHI-prognos)
                        self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)
                        
                        # Väderbeskrivning
                        desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
                        self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)
                        
                        # NYTT: Visa att det är SMHI-prognos
                        self.draw.text((x + 20, y + 155), "(SMHI prognos)", font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'clock_module':
                        # OMVANDLAD TILL ELEGANT DATUMMODUL - INGEN KLOCKA LÄNGRE
                        now = datetime.now()
                        
                        # Hämta svenska datum-komponenter
                        swedish_weekday, swedish_date = self.get_swedish_date(now)
                        
                        # Kalenderdakts-ikon för modern utseende
                        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
                        if calendar_icon:
                            # Placera ikon till vänster
                            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 20)
                            text_start_x = x + 65  # Text börjar efter ikon
                        else:
                            # Fallback: ingen ikon, text börjar tidigare
                            text_start_x = x + 15
                        
                        # VECKODAG (stor och tydlig)
                        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['small_main'], width - 80)
                        self.draw.text((text_start_x, y + 20), weekday_truncated, font=self.fonts['small_main'], fill=0)
                        
                        # DATUM (elegant under veckodagen)
                        date_truncated = self.truncate_text(swedish_date, self.fonts['small_desc'], width - 80)
                        self.draw.text((text_start_x, y + 55), date_truncated, font=self.fonts['small_desc'], fill=0)
                        
                        # Dekorativ linje för elegans
                        line_start_x = text_start_x
                        line_end_x = min(x + width - 20, text_start_x + 150)
                        self.draw.line([(line_start_x, y + 80), (line_end_x, y + 80)], fill=0, width=1)
                    
                    elif module_name == 'status_module':
                        update_time = datetime.now().strftime('%H:%M')
                        
                        # FIXED: Status med enkla prickar - PERFEKT LINJERING med text
                        dot_x = x + 10
                        dot_size = 3  # 3px prick
                        
                        # Status prick + text (perfekt centrerad)
                        self.draw.ellipse([
                            (dot_x, y + 28), 
                            (dot_x + dot_size, y + 28 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 20), "Daemon: ✓", font=self.fonts['small_desc'], fill=0)
                        
                        # Update prick + text (perfekt centrerad)
                        self.draw.ellipse([
                            (dot_x, y + 53), 
                            (dot_x + dot_size, y + 53 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
                        
                        # Data-källor prick + text (perfekt centrerad)
                        data_sources = self.format_data_sources(weather_data)
                        self.draw.ellipse([
                            (dot_x, y + 78), 
                            (dot_x + dot_size, y + 78 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 70), f"Data: {data_sources}", font=self.fonts['small_desc'], fill=0)
            
            # Visa på display
            if self.epd and not self.config['debug']['test_mode']:
                self.epd.display(self.epd.getbuffer(self.canvas))
                self.logger.info("✅ E-Paper display uppdaterad")
            else:
                self.logger.info("🧪 Test-läge: Display simulering")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering: {e}")
            raise
    
    # ALLA HJÄLPMETODER från main.py (kopierade exakt)
    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)
    
    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar som inte dubbleras (kopierat från main.py)"""
        if module_name == 'main_weather':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'barometer_module':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'tomorrow_forecast':
            self.draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=2)
            self.draw.rectangle([(x + 2, y + 2), (x + width - 2, y + height - 2)], outline=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'clock_module':
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
        elif module_name == 'status_module':
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 20, y + 8)], fill=0, width=1)
            self.draw.line([(x + 8, y + 8), (x + 8, y + 20)], fill=0, width=1)
    
    def get_swedish_date(self, date_obj):
        """Konvertera datum till svenska veckodagar och månader (kopierat från main.py)"""
        swedish_days = {
            'Monday': 'Måndag', 'Tuesday': 'Tisdag', 'Wednesday': 'Onsdag', 
            'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lördag', 'Sunday': 'Söndag'
        }
        
        swedish_months = {
            1: 'Januari', 2: 'Februari', 3: 'Mars', 4: 'April', 5: 'Maj', 6: 'Juni',
            7: 'Juli', 8: 'Augusti', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'December'
        }
        
        english_day = date_obj.strftime('%A')
        swedish_day = swedish_days.get(english_day, english_day)
        
        day_num = date_obj.day
        month_num = date_obj.month
        swedish_month = swedish_months.get(month_num, str(month_num))
        
        return swedish_day, f"{day_num} {swedish_month}"
    
    def truncate_text(self, text, font, max_width):
        """Korta text så den får plats inom given bredd (kopierat från main.py)"""
        if not text:
            return text
            
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        words = text.split()
        for i in range(len(words), 0, -1):
            truncated = ' '.join(words[:i])
            bbox = self.draw.textbbox((0, 0), truncated, font=font)
            truncated_width = bbox[2] - bbox[0]
            
            if truncated_width <= max_width:
                return truncated
        
        return words[0] if words else text
    
    def paste_icon_on_canvas(self, icon, x, y):
        """Sätt in ikon på canvas (kopierat från main.py)"""
        if icon is None:
            return
        
        try:
            self.canvas.paste(icon, (x, y))
        except Exception as e:
            self.logger.error(f"❌ Fel vid ikon-inplacering: {e}")
    
    def format_data_sources(self, weather_data: Dict) -> str:
        """Formatera datakällor för status-modulen (kopierat från main.py)"""
        try:
            sources = []
            
            temp_source = weather_data.get('temperature_source', '')
            if temp_source == 'netatmo':
                sources.append("Netatmo")
            elif temp_source == 'smhi':
                sources.append("SMHI")
            
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
    
    def update_state(self, weather_data: Dict):
        """Uppdatera daemon state i minnet"""
        self.current_display_state = {
            'temperature': weather_data.get('temperature'),
            'weather_symbol': weather_data.get('weather_symbol'),
            'weather_description': weather_data.get('weather_description'),
            'pressure': weather_data.get('pressure'),
            'pressure_trend_text': weather_data.get('pressure_trend_text'),
            'pressure_trend_arrow': weather_data.get('pressure_trend_arrow'),
            'tomorrow_temp': weather_data.get('tomorrow', {}).get('temperature'),
            'tomorrow_symbol': weather_data.get('tomorrow', {}).get('weather_symbol'),
            'tomorrow_desc': weather_data.get('tomorrow', {}).get('weather_description'),
            'sunrise': weather_data.get('sun_data', {}).get('sunrise'),
            'sunset': weather_data.get('sun_data', {}).get('sunset'),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'last_update': time.time()
        }
        self.last_update_time = time.time()
    
    def run_daemon(self):
        """Huvudloop för daemon"""
        self.logger.info("🚀 Startar E-Paper Weather Daemon...")
        print("🚀 E-Paper Weather Daemon startad - kontinuerlig väderstation!")
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                self.logger.debug(f"🔄 Daemon iteration #{iteration}")
                
                try:
                    # Hämta väderdata
                    weather_data = self.fetch_weather_data()
                    
                    if weather_data:
                        # Avgör om uppdatering behövs
                        should_update, reason = self.should_update_display(weather_data)
                        
                        if should_update:
                            self.logger.info(f"🔄 UPPDATERAR E-Paper: {reason}")
                            
                            # Rendera och visa
                            self.render_and_display(weather_data)
                            
                            # Uppdatera state i minnet
                            self.update_state(weather_data)
                            
                            print(f"🔄 E-Paper uppdaterad: {reason}")
                            
                        else:
                            self.logger.info(f"💤 BEHÅLLER skärm: {reason}")
                            print(f"💤 E-Paper behålls: {reason}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Fel i daemon iteration #{iteration}: {e}")
                
                # Vänta till nästa iteration
                if self.running:
                    time.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            self.logger.info("⚠️ Daemon avbruten av användare")
            print("\n⚠️ Daemon stoppad")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup vid shutdown"""
        try:
            if self.epd:
                self.epd.sleep()
            
            if hasattr(self, 'icon_manager'):
                self.icon_manager.clear_cache()
            
            self.logger.info("🧹 Daemon cleanup genomförd")
            print("🧹 Daemon cleanup genomförd")
        except Exception as e:
            self.logger.error(f"⚠️ Cleanup-fel: {e}")

def main():
    """Huvudfunktion för daemon"""
    daemon = None
    try:
        daemon = EPaperWeatherDaemon()
        daemon.run_daemon()
    except Exception as e:
        print(f"❌ Kritiskt daemon-fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if daemon:
            daemon.cleanup()

if __name__ == "__main__":
    main()