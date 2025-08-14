#!/usr/bin/env python3
"""
E-Paper Väderapp - Med riktiga väderdata från SMHI + Weather Icons
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)
STEG 14: Weather Icons integration med fallback-ikoner
"""

import sys
import os
import json
import time
import math
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import logging

# Lägg till Waveshare biblioteket i path
sys.path.append(os.path.join(os.path.dirname(__file__), 'e-Paper', 'RaspberryPi_JetsonNano', 'python', 'lib'))

# Lägg till modules-mappen
sys.path.append('modules')
from weather_client import WeatherClient
from icon_manager import WeatherIconManager  # NY: Weather Icons integration

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    print("🔧 Kontrollera att E-Paper biblioteket är installerat korrekt")
    sys.exit(1)

class EPaperWeatherApp:
    """Huvudklass för E-Paper väderapp med Weather Icons"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera appen med konfiguration och ikon-hantering"""
        print("🌤️ E-Paper Väderapp med Weather Icons - Startar...")
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
            
        # Setup logging
        self.setup_logging()
        
        # Initialisera weather client
        self.weather_client = WeatherClient(self.config)
        
        # NY: Initialisera ikon-hanterare
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
        
        print("✅ E-Paper Väderapp med ikoner initialiserad!")
    
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
    
    def calculate_sun_times(self, latitude, longitude, date=None):
        """Beräkna soluppgång och solnedgång (förenklad algoritm)"""
        if date is None:
            date = datetime.now().date()
        
        # Förenklad solberäkning (ungefärlig)
        day_of_year = date.timetuple().tm_yday
        
        # Solens deklination
        P = math.asin(0.39795 * math.cos(0.01723 * (day_of_year - 173)))
        
        # Latitud i radianer
        lat_rad = math.radians(latitude)
        
        # Timvinkel för soluppgång/nedgång
        try:
            argument = -math.tan(lat_rad) * math.tan(P)
            # Begränsa argument till [-1, 1] för att undvika domain error
            argument = max(-0.99, min(0.99, argument))
            H = math.acos(argument)
        except:
            H = 0  # Fallback
        
        # Lokal tid för soluppgång och solnedgång
        sunrise_hour = 12 - (H * 12 / math.pi)
        sunset_hour = 12 + (H * 12 / math.pi)
        
        # Konvertera till datetime objekt (ungefärligt, ignorerar tidszoner)
        sunrise = datetime.combine(date, datetime.min.time()) + timedelta(hours=sunrise_hour)
        sunset = datetime.combine(date, datetime.min.time()) + timedelta(hours=sunset_hour)
        
        return sunrise, sunset
    
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
    
    def render_weather_layout(self):
        """Rendera layout med riktiga väderdata OCH ikoner"""
        self.clear_canvas()
        
        # Hämta riktiga väderdata
        self.logger.info("🌐 Hämtar aktuella väderdata...")
        weather_data = self.weather_client.get_current_weather()
        
        # Beräkna soluppgång/nedgång
        latitude = self.config['location']['latitude']
        longitude = self.config['location']['longitude']
        sunrise, sunset = self.calculate_sun_times(latitude, longitude)
        
        # Skapa soldata för ikon-manager
        current_time = datetime.now()
        sun_data = {
            'sunrise': sunrise.isoformat(),
            'sunset': sunset.isoformat()
        }
        
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
                
                # Rita innehåll för varje modul MED IKONER
                if module_name == 'main_weather':
                    temp = weather_data.get('temperature', 20.0)
                    desc = weather_data.get('weather_description', 'Okänt väder')
                    source = weather_data.get('temperature_source', 'fallback')
                    location = weather_data.get('location', 'Okänd plats')
                    smhi_symbol = weather_data.get('weather_symbol', 1)  # SMHI väder-symbol
                    
                    # Plats överst i hero-modulen
                    self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)
                    
                    # VÄDERIKON (större för bättre synlighet) 
                    weather_icon = self.icon_manager.get_weather_icon_for_time(
                        smhi_symbol, current_time, sun_data, size=(80, 80)
                    )
                    if weather_icon:
                        # Placera ikon till höger om temperaturen med bättre alignment
                        icon_x = x + 320  # Mer space från temperatur-text
                        icon_y = y + 50   # Justerad höjd för bättre balans
                        self.paste_icon_on_canvas(weather_icon, icon_x, icon_y)
                    
                    # Temperatur (utan °C - redundant)
                    self.draw.text((x + 20, y + 60), f"{temp:.1f}°", font=self.fonts['hero_temp'], fill=0)
                    
                    # Beskrivning (trunka om nödvändigt)
                    desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
                    self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)
                    
                    # Källa (mindre framträdande)
                    self.draw.text((x + 20, y + 185), f"({source.upper()})", font=self.fonts['tiny'], fill=0)
                    
                    # SOL-IKONER + tider (större ikoner, bättre alignment)
                    sunrise_str = sunrise.strftime('%H:%M')
                    sunset_str = sunset.strftime('%H:%M')
                    
                    # Soluppgång - ikon + tid
                    sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(40, 40))
                    if sunrise_icon:
                        self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 210)
                        self.draw.text((x + 65, y + 220), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                    else:
                        # Fallback utan ikon
                        self.draw.text((x + 20, y + 220), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)
                    
                    # Solnedgång - ikon + tid  
                    sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(40, 40))
                    if sunset_icon:
                        self.paste_icon_on_canvas(sunset_icon, x + 160, y + 210)
                        self.draw.text((x + 205, y + 220), sunset_str, font=self.fonts['medium_desc'], fill=0)
                    else:
                        # Fallback utan ikon
                        self.draw.text((x + 160, y + 220), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)
                
                elif module_name == 'barometer_module':
                    pressure = weather_data.get('pressure', 1013)
                    
                    # Tryck-värde
                    self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                    self.draw.text((x + 20, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                    
                    # Trycktrend med ikon (nu med faktiska ikoner som existerar)
                    if pressure > 1020:
                        trend = "rising"
                        trend_text = "Högtryck"
                    elif pressure < 1000:
                        trend = "falling"
                        trend_text = "Lågtryck"
                    else:
                        trend = "stable"
                        trend_text = "Stabilt"
                    
                    # Trycktrend-ikon (använder wi-direction-* som faktiskt existerar)
                    pressure_icon = self.icon_manager.get_pressure_icon(trend, size=(24, 24))
                    if pressure_icon:
                        # Placera pilen till höger om trend-texten
                        self.paste_icon_on_canvas(pressure_icon, x + 180, y + 130)
                        self.draw.text((x + 20, y + 130), trend_text, font=self.fonts['medium_desc'], fill=0)
                    else:
                        # Fallback med emoji
                        arrow = "↗" if trend == "rising" else "↘" if trend == "falling" else "→"
                        self.draw.text((x + 20, y + 130), f"{trend_text} {arrow}", font=self.fonts['medium_desc'], fill=0)
                
                elif module_name == 'tomorrow_forecast':
                    tomorrow = weather_data.get('tomorrow', {})
                    tomorrow_temp = tomorrow.get('temperature', 18.0)
                    tomorrow_desc = tomorrow.get('weather_description', 'Okänt')
                    tomorrow_symbol = tomorrow.get('weather_symbol', 3)  # Fallback: växlande molnighet
                    
                    self.draw.text((x + 20, y + 30), "Imorgon", font=self.fonts['medium_desc'], fill=0)
                    
                    # Temperatur (utan °C) - samma x-koordinat som "Imorgon" för alignment
                    self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)
                    
                    # Imorgon väderikon (optimerad positionering - undviker temperatur)
                    tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(32, 32))
                    if tomorrow_icon:
                        # Placera ikonen längst upp till höger för att undvika all text
                        self.paste_icon_on_canvas(tomorrow_icon, x + 180, y + 30)
                    
                    # Bättre texthantering för beskrivning
                    desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 20)
                    self.draw.text((x + 10, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)
                    
                    # Om texten trunkerats mycket, visa på två rader
                    if len(desc_truncated) < len(tomorrow_desc) / 2:
                        remaining = tomorrow_desc[len(desc_truncated):].strip()
                        if remaining:
                            remaining_truncated = self.truncate_text(remaining, self.fonts['small_desc'], width - 20)
                            self.draw.text((x + 10, y + 150), remaining_truncated, font=self.fonts['small_desc'], fill=0)
                
                elif module_name == 'clock_module':
                    now = datetime.now()
                    
                    # Tid och datum med bättre alignment (ingen klockikon)
                    self.draw.text((x + 10, y + 20), now.strftime('%H:%M'), font=self.fonts['small_main'], fill=0)
                    
                    # Svenska datum - samma x-koordinat för alignment
                    swedish_date = self.get_swedish_date(now)
                    self.draw.text((x + 10, y + 60), swedish_date, font=self.fonts['small_desc'], fill=0)
                
                elif module_name == 'status_module':
                    update_time = datetime.now().strftime('%H:%M')
                    data_source = weather_data.get('temperature_source', 'fallback')
                    
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
                    
                    self.draw.text((x + 10, y + 70), f"Data: {data_source}", font=self.fonts['small_desc'], fill=0)
        
        self.logger.info("🎨 Layout renderad med Weather Icons")
        
        # Debug: Visa cache-statistik med mer detaljer
        cache_stats = self.icon_manager.get_cache_stats()
        self.logger.info(f"💾 Ikon-cache: {cache_stats['total_cached_icons']} ikoner totalt")
        for category, count in cache_stats.items():
            if category != 'total_cached_icons' and count > 0:
                self.logger.info(f"  📊 {category}: {count} ikoner")
    
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
        """Kör väderapp med riktiga data OCH ikoner"""
        try:
            self.logger.info("🌤️ Startar E-Paper väderapp med Weather Icons...")
            
            # Rendera väder-layout med ikoner
            self.render_weather_layout()
            
            # Visa på display
            self.display_canvas()
            
            print("\n" + "="*60)
            print("✅ E-PAPER VÄDERAPP MED WEATHER ICONS!")
            print("📱 Kontrollera E-Paper display för väderdata + ikoner")
            print("📁 Loggar: logs/weather.log")
            print("📸 Screenshots: screenshots/epaper_*.png")
            print("🌡️ Visar aktuell temperatur och väder från SMHI")
            print("🎨 Weather Icons med fallback-system (tills PNG-filer läggs till)")
            print("🌙 Dag/natt-ikoner baserat på soluppgång/solnedgång")
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
        # Skapa och kör väderapp med ikoner
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
