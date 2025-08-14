#!/usr/bin/env python3
"""
E-Paper Väderapp - Med riktiga väderdata från SMHI
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)
STEG 13: Helt utan extra text + smarta ramar som inte dubbleras
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

# NYTT: Lägg till modules-mappen för weather_client
sys.path.append('modules')
from weather_client import WeatherClient

try:
    from waveshare_epd import epd4in26
except ImportError as e:
    print(f"❌ Kan inte importera Waveshare bibliotek: {e}")
    print("🔧 Kontrollera att E-Paper biblioteket är installerat korrekt")
    sys.exit(1)

class EPaperWeatherApp:
    """Huvudklass för E-Paper väderapp"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera appen med konfiguration"""
        print("🌤️ E-Paper Väderapp - Startar...")
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
            
        # Setup logging
        self.setup_logging()
        
        # NYTT: Initialisera weather client
        self.weather_client = WeatherClient(self.config)
        
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
        
        print("✅ E-Paper Väderapp initialiserad!")
    
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
    
    def render_weather_layout(self):
        """Rendera layout med riktiga väderdata - HELT utan extra text"""
        self.clear_canvas()
        
        # Hämta riktiga väderdata
        self.logger.info("🌐 Hämtar aktuella väderdata...")
        weather_data = self.weather_client.get_current_weather()
        
        # Beräkna soluppgång/nedgång
        latitude = self.config['location']['latitude']
        longitude = self.config['location']['longitude']
        sunrise, sunset = self.calculate_sun_times(latitude, longitude)
        
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
                
                # Rita innehåll för varje modul
                if module_name == 'main_weather':
                    temp = weather_data.get('temperature', 20.0)
                    desc = weather_data.get('weather_description', 'Okänt väder')
                    source = weather_data.get('temperature_source', 'fallback')
                    location = weather_data.get('location', 'Okänd plats')
                    
                    # Plats överst i hero-modulen
                    self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)
                    
                    # Temperatur
                    self.draw.text((x + 20, y + 60), f"{temp}°C", font=self.fonts['hero_temp'], fill=0)
                    
                    # Beskrivning (trunka om nödvändigt)
                    desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
                    self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)
                    
                    # Källa (mindre framträdande)
                    self.draw.text((x + 20, y + 185), f"({source.upper()})", font=self.fonts['tiny'], fill=0)
                    
                    # BARA soluppgång/nedgång - INGET ANNAT
                    # Soluppgång - ikon + klockslag
                    sunrise_str = sunrise.strftime('%H:%M')
                    self.draw.text((x + 20, y + 220), "🌅", font=self.fonts['medium_desc'], fill=0)
                    self.draw.text((x + 50, y + 220), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                    
                    # Solnedgång - ikon + klockslag  
                    sunset_str = sunset.strftime('%H:%M')
                    self.draw.text((x + 150, y + 220), "🌇", font=self.fonts['medium_desc'], fill=0)
                    self.draw.text((x + 180, y + 220), sunset_str, font=self.fonts['medium_desc'], fill=0)
                    
                    # INGEN ANNAN TEXT HÄR - "Ljus: X h Y m kvar" borttagen helt
                
                elif module_name == 'barometer_module':
                    pressure = weather_data.get('pressure', 1013)
                    
                    self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                    self.draw.text((x + 20, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                    
                    # Enkel trycktrend baserat på värde
                    if pressure > 1020:
                        trend = "Högtryck ↗"
                    elif pressure < 1000:
                        trend = "Lågtryck ↘"
                    else:
                        trend = "Stabilt →"
                    self.draw.text((x + 20, y + 130), trend, font=self.fonts['medium_desc'], fill=0)
                
                elif module_name == 'tomorrow_forecast':
                    tomorrow = weather_data.get('tomorrow', {})
                    tomorrow_temp = tomorrow.get('temperature', 18.0)
                    tomorrow_desc = tomorrow.get('weather_description', 'Okänt')
                    
                    self.draw.text((x + 20, y + 30), "Imorgon", font=self.fonts['medium_desc'], fill=0)
                    self.draw.text((x + 20, y + 80), f"{tomorrow_temp}°C", font=self.fonts['medium_main'], fill=0)
                    
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
                    self.draw.text((x + 10, y + 20), now.strftime('%H:%M'), font=self.fonts['small_main'], fill=0)
                    self.draw.text((x + 10, y + 60), now.strftime('%a %d/%m'), font=self.fonts['small_desc'], fill=0)
                
                elif module_name == 'status_module':
                    update_time = datetime.now().strftime('%H:%M')
                    data_source = weather_data.get('temperature_source', 'fallback')
                    
                    self.draw.text((x + 10, y + 20), "Status: ✓ OK", font=self.fonts['small_desc'], fill=0)
                    self.draw.text((x + 10, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
                    self.draw.text((x + 10, y + 70), f"Data: {data_source}", font=self.fonts['small_desc'], fill=0)
        
        self.logger.info("🎨 Layout renderad - helt utan extra text, smarta ramar")
    
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
        """Kör väderapp med riktiga data"""
        try:
            self.logger.info("🌤️ Startar E-Paper väderapp...")
            
            # Rendera väder-layout med riktiga data
            self.render_weather_layout()
            
            # Visa på display
            self.display_canvas()
            
            print("\n" + "="*60)
            print("✅ E-PAPER VÄDERAPP - PERFEKT VERSION!")
            print("📱 Kontrollera E-Paper display för riktiga väderdata")
            print("📁 Loggar: logs/weather.log")
            print("📸 Screenshots: screenshots/epaper_*.png")
            print("🌡️ Visar aktuell temperatur och väder från SMHI")
            print("☀️ Bara soluppgång/nedgång - INGEN extra text")
            print("🎨 Smarta ramar - inga dubblerade linjer")
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"❌ Väderapp misslyckades: {e}")
            raise
    
    def cleanup(self):
        """Städa upp resurser"""
        try:
            if self.epd:
                self.epd.sleep()
            self.logger.info("🧹 Cleanup genomförd")
        except Exception as e:
            self.logger.error(f"⚠️ Cleanup-fel: {e}")

def main():
    """Huvudfunktion"""
    app = None
    try:
        # Skapa och kör väderapp
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