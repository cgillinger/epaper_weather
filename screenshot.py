#!/usr/bin/env python3
"""
E-Paper Live Screenshots - Exakt kopia av aktuell skärm
Samma rendering-logik som main_daemon.py men sparar PNG istället för E-Paper

ANVÄNDNING:
python3 screenshot.py                    # Standard screenshot
python3 screenshot.py --timestamp       # Med timestamp i filnamn  
python3 screenshot.py --output myshot   # Anpassat filnamn
python3 screenshot.py --debug          # Debug-utskrifter
"""

import sys
import os
import json
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Lägg till projektets moduler (samma som daemon)
sys.path.append('modules')

# Importera samma moduler som daemonen använder
from weather_client import WeatherClient
from icon_manager import WeatherIconManager

class EPaperScreenshotGenerator:
    """Genererar exakt kopia av vad som visas på E-Paper skärmen"""
    
    def __init__(self, config_path="config.json", debug=False):
        """Initialisera screenshot-generator"""
        self.debug = debug
        
        if self.debug:
            print("📸 E-Paper Screenshot Generator - Exakt kopia av live skärm")
        
        # Ladda samma konfiguration som daemonen
        self.config = self.load_config(config_path)
        if not self.config:
            print("❌ Kunde inte ladda konfiguration")
            sys.exit(1)
        
        # Samma komponenter som daemonen
        self.weather_client = WeatherClient(self.config)
        self.icon_manager = WeatherIconManager(icon_base_path="icons/")
        
        # Samma canvas-setup som daemonen
        self.width = self.config['layout']['screen_width']
        self.height = self.config['layout']['screen_height']
        self.canvas = Image.new('1', (self.width, self.height), 255)
        self.draw = ImageDraw.Draw(self.canvas)
        
        # Samma typsnitt som daemonen
        self.fonts = self.load_fonts()
        
        if self.debug:
            print(f"✅ Initialiserad för {self.width}×{self.height} E-Paper layout")
    
    def load_config(self, config_path):
        """Ladda JSON-konfiguration (samma som daemon)"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Kan inte ladda konfiguration: {e}")
            return None
    
    def load_fonts(self):
        """Ladda typsnitt (samma som daemon)"""
        fonts = {}
        font_path = self.config['display']['font_path']
        font_sizes = self.config['fonts']
        
        try:
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.truetype(font_path, size)
            if self.debug:
                print(f"✅ {len(fonts)} typsnitt laddade")
        except Exception as e:
            if self.debug:
                print(f"⚠️ Typsnitt-fel: {e}, använder default")
            for name, size in font_sizes.items():
                fonts[name] = ImageFont.load_default()
        
        return fonts
    
    def fetch_live_weather_data(self):
        """Hämta EXAKT samma väderdata som daemonen använder"""
        try:
            if self.debug:
                print("🌐 Hämtar live väderdata (samma som daemon)...")
            
            # Samma API-anrop som daemonen
            weather_data = self.weather_client.get_current_weather()
            
            # Samma soldata-parsning som daemonen
            sunrise, sunset, sun_data = self.parse_sun_data_from_weather(weather_data)
            
            # Lägg till parsade soltider (samma som daemon)
            weather_data['parsed_sunrise'] = sunrise
            weather_data['parsed_sunset'] = sunset
            weather_data['parsed_sun_data'] = sun_data
            
            if self.debug:
                temp = weather_data.get('temperature', 'N/A')
                temp_source = weather_data.get('temperature_source', 'unknown')
                pressure = weather_data.get('pressure', 'N/A')
                pressure_source = weather_data.get('pressure_source', 'unknown')
                print(f"🌡️ Temperatur: {temp}°C från {temp_source}")
                print(f"📊 Tryck: {pressure} hPa från {pressure_source}")
                
                if sunrise and sunset:
                    print(f"☀️ Soltider: {sunrise.strftime('%H:%M')} - {sunset.strftime('%H:%M')}")
            
            return weather_data
            
        except Exception as e:
            print(f"❌ Fel vid hämtning av väderdata: {e}")
            return self.get_fallback_data()
    
    def parse_sun_data_from_weather(self, weather_data):
        """Parsea soldata (kopierat exakt från daemon)"""
        try:
            # Hämta soldata från weather_client
            sun_data = weather_data.get('sun_data', {})
            
            if not sun_data:
                if self.debug:
                    print("⚠️ Ingen soldata från WeatherClient, använder fallback")
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
            
            return sunrise_time, sunset_time, parsed_sun_data
            
        except Exception as e:
            if self.debug:
                print(f"❌ Fel vid parsning av soldata: {e}")
            # Fallback
            now = datetime.now()
            sunrise = now.replace(hour=6, minute=0, second=0)
            sunset = now.replace(hour=18, minute=0, second=0)
            return sunrise, sunset, {'sunrise': sunrise.isoformat(), 'sunset': sunset.isoformat(), 'source': 'error_fallback'}
    
    def get_fallback_data(self):
        """Fallback-data vid API-fel (samma som daemon)"""
        return {
            'timestamp': datetime.now().isoformat(),
            'location': self.config['location']['name'],
            'temperature': 20.0,
            'weather_description': 'Data ej tillgänglig',
            'weather_symbol': 1,
            'pressure': 1013,
            'temperature_source': 'fallback',
            'pressure_source': 'fallback',
            'tomorrow': {
                'temperature': 18.0,
                'weather_description': 'Okänt'
            },
            'sun_data': {
                'sunrise': datetime.now().replace(hour=6, minute=0).isoformat(),
                'sunset': datetime.now().replace(hour=18, minute=0).isoformat(),
                'daylight_duration': '12h 0m',
                'sun_source': 'fallback'
            },
            'data_sources': ['fallback']
        }
    
    def render_exact_display(self, weather_data):
        """EXAKT samma rendering som main_daemon.py"""
        try:
            if self.debug:
                print("🎨 Renderar exakt E-Paper layout...")
            
            # Rensa canvas (vit bakgrund)
            self.clear_canvas()
            
            # Hämta parsade soltider från weather_data
            sunrise = weather_data.get('parsed_sunrise')
            sunset = weather_data.get('parsed_sunset')
            sun_data = weather_data.get('parsed_sun_data', {})
            
            # Aktuell tid för dag/natt-bestämning
            current_time = datetime.now()
            
            # Rita alla moduler enligt konfiguration (EXAKT som daemon)
            modules = self.config['modules']
            
            for module_name, module_config in modules.items():
                if module_config['enabled']:
                    x = module_config['coords']['x']
                    y = module_config['coords']['y'] 
                    width = module_config['size']['width']
                    height = module_config['size']['height']
                    
                    # Rita smarta modulramar (samma som daemon)
                    self.draw_module_border(x, y, width, height, module_name)
                    
                    # Rita innehåll för varje modul (EXAKT som daemon)
                    if module_name == 'main_weather':
                        temp = weather_data.get('temperature', 20.0)
                        desc = weather_data.get('weather_description', 'Okänt väder')
                        temp_source = weather_data.get('temperature_source', 'fallback')
                        location = weather_data.get('location', 'Okänd plats')
                        smhi_symbol = weather_data.get('weather_symbol', 1)
                        
                        # Plats överst i hero-modulen
                        self.draw.text((x + 20, y + 15), location, font=self.fonts['medium_desc'], fill=0)
                        
                        # VÄDERIKON med exakt dag/natt-logik (96x96)
                        weather_icon = self.icon_manager.get_weather_icon_for_time(
                            smhi_symbol, current_time, sun_data, size=(96, 96)
                        )
                        if weather_icon:
                            icon_x = x + 320
                            icon_y = y + 50
                            self.paste_icon_on_canvas(weather_icon, icon_x, icon_y)
                        
                        # TEMPERATUR (prioriterat från Netatmo!)
                        self.draw.text((x + 20, y + 60), f"{temp:.1f}°", font=self.fonts['hero_temp'], fill=0)
                        
                        # Beskrivning (från SMHI meteorologi)
                        desc_truncated = self.truncate_text(desc, self.fonts['hero_desc'], width - 40)
                        self.draw.text((x + 20, y + 150), desc_truncated, font=self.fonts['hero_desc'], fill=0)
                        
                        # Visa temperatur-källa
                        if temp_source == 'netatmo':
                            source_text = "(NETATMO)"
                        elif temp_source == 'smhi':
                            source_text = "(SMHI)"
                        else:
                            source_text = f"({temp_source.upper()})"
                        
                        self.draw.text((x + 20, y + 185), source_text, font=self.fonts['tiny'], fill=0)
                        
                        # EXAKTA SOL-IKONER + tider (56x56)
                        if sunrise and sunset:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                            
                            # Soluppgång - ikon + exakt tid
                            sunrise_icon = self.icon_manager.get_sun_icon('sunrise', size=(56, 56))
                            if sunrise_icon:
                                self.paste_icon_on_canvas(sunrise_icon, x + 20, y + 200)
                                self.draw.text((x + 80, y + 215), sunrise_str, font=self.fonts['medium_desc'], fill=0)
                            else:
                                self.draw.text((x + 20, y + 215), f"🌅 {sunrise_str}", font=self.fonts['medium_desc'], fill=0)
                            
                            # Solnedgång - ikon + exakt tid  
                            sunset_icon = self.icon_manager.get_sun_icon('sunset', size=(56, 56))
                            if sunset_icon:
                                self.paste_icon_on_canvas(sunset_icon, x + 180, y + 200)
                                self.draw.text((x + 240, y + 215), sunset_str, font=self.fonts['medium_desc'], fill=0)
                            else:
                                self.draw.text((x + 180, y + 215), f"🌇 {sunset_str}", font=self.fonts['medium_desc'], fill=0)
                        
                        # Visa soldata-källa
                        sun_source = sun_data.get('source', 'unknown')
                        if sun_source != 'unknown':
                            source_text = f"Sol: {sun_source}"
                            if sun_source == 'ipgeolocation.io':
                                source_text = "Sol: API ✓"
                            elif sun_source == 'fallback':
                                source_text = "Sol: approx"
                            self.draw.text((x + 20, y + 250), source_text, font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'barometer_module':
                        # EXAKT samma trycktrend-logik som daemon
                        pressure = weather_data.get('pressure', 1013)
                        pressure_source = weather_data.get('pressure_source', 'unknown')
                        
                        # Riktiga trend-data från weather_client
                        pressure_trend = weather_data.get('pressure_trend', {})
                        trend_text = weather_data.get('pressure_trend_text', 'Samlar data')
                        trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')
                        
                        # Barometer-ikon (80x80)
                        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
                        if barometer_icon:
                            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
                            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                        else:
                            self.draw.text((x + 20, y + 50), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
                        
                        # hPa-text
                        self.draw.text((x + 100, y + 100), "hPa", font=self.fonts['medium_desc'], fill=0)
                        
                        # Trend-text med radbrytning för "Samlar data"
                        if trend_text == 'Samlar data':
                            self.draw.text((x + 20, y + 125), "Samlar", font=self.fonts['medium_desc'], fill=0)
                            self.draw.text((x + 20, y + 150), "data", font=self.fonts['medium_desc'], fill=0)
                        else:
                            self.draw.text((x + 20, y + 125), trend_text, font=self.fonts['medium_desc'], fill=0)
                        
                        # Numerisk 3h-förändring
                        if pressure_trend.get('change_3h') is not None and pressure_trend.get('trend') != 'insufficient_data':
                            change_3h = pressure_trend['change_3h']
                            change_text = f"{change_3h:+.1f} hPa/3h"
                            change_y = y + 175 if trend_text == 'Samlar data' else y + 150
                            self.draw.text((x + 20, change_y), change_text, font=self.fonts['small_desc'], fill=0)
                        
                        # Trend-pil (64x64)
                        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
                        if trend_icon:
                            trend_x = x + width - 75
                            trend_y = y + 100
                            self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)
                        
                        # Tryck-källa
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
                        
                        # Imorgon väderikon (80x80)
                        tomorrow_icon = self.icon_manager.get_weather_icon(tomorrow_symbol, is_night=False, size=(80, 80))
                        if tomorrow_icon:
                            self.paste_icon_on_canvas(tomorrow_icon, x + 140, y + 20)
                        
                        # Temperatur
                        self.draw.text((x + 20, y + 80), f"{tomorrow_temp:.1f}°", font=self.fonts['medium_main'], fill=0)
                        
                        # Väderbeskrivning
                        desc_truncated = self.truncate_text(tomorrow_desc, self.fonts['small_desc'], width - 60)
                        self.draw.text((x + 20, y + 130), desc_truncated, font=self.fonts['small_desc'], fill=0)
                        
                        # SMHI-prognos märkning
                        self.draw.text((x + 20, y + 155), "(SMHI prognos)", font=self.fonts['tiny'], fill=0)
                    
                    elif module_name == 'clock_module':
                        # FIXAD DATUMMODUL - Justerad storlek för bättre läsbarhet (samma som daemon)
                        now = datetime.now()
                        
                        # Svenska datum-komponenter
                        swedish_weekday, swedish_date = self.get_swedish_date(now)
                        
                        # Kalender-ikon (40x40)
                        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
                        if calendar_icon:
                            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 15)
                            text_start_x = x + 65
                        else:
                            text_start_x = x + 15
                        
                        # DATUM FÖRST I BRA STORLEK (small_main = 32px - samma som daemon)
                        date_truncated = self.truncate_text(swedish_date, self.fonts['small_main'], width - 80)
                        self.draw.text((text_start_x, y + 15), date_truncated, font=self.fonts['small_main'], fill=0)
                        
                        # VECKODAG UNDER I BRA STORLEK (medium_desc = 24px - samma som daemon)
                        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['medium_desc'], width - 80)
                        self.draw.text((text_start_x, y + 50), weekday_truncated, font=self.fonts['medium_desc'], fill=0)
                        
                        # BORTTAGET: Dekorativ linje (samma som daemon - inga linjer)
                    
                    elif module_name == 'status_module':
                        update_time = datetime.now().strftime('%H:%M')
                        
                        # Status med prickar (samma som daemon)
                        dot_x = x + 10
                        dot_size = 3
                        
                        # Status prick + text
                        self.draw.ellipse([
                            (dot_x, y + 28), 
                            (dot_x + dot_size, y + 28 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 20), "Screenshot: ✓", font=self.fonts['small_desc'], fill=0)
                        
                        # Update prick + text
                        self.draw.ellipse([
                            (dot_x, y + 53), 
                            (dot_x + dot_size, y + 53 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 45), f"Tagen: {update_time}", font=self.fonts['small_desc'], fill=0)
                        
                        # Data-källor prick + text
                        data_sources = self.format_data_sources(weather_data)
                        self.draw.ellipse([
                            (dot_x, y + 78), 
                            (dot_x + dot_size, y + 78 + dot_size)
                        ], fill=0)
                        self.draw.text((dot_x + 10, y + 70), f"Data: {data_sources}", font=self.fonts['small_desc'], fill=0)
            
            if self.debug:
                print("✅ Rendering komplett - exakt som daemon")
            
        except Exception as e:
            print(f"❌ Fel vid rendering: {e}")
            raise
    
    # === HJÄLPMETODER (kopierade exakt från daemon) ===
    
    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)
    
    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar (exakt som daemon)"""
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
        """Svenska veckodagar och månader (exakt som daemon)"""
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
        """Korta text så den får plats (exakt som daemon)"""
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
        """Sätt in ikon på canvas (exakt som daemon)"""
        if icon is None:
            return
        
        try:
            self.canvas.paste(icon, (x, y))
        except Exception as e:
            if self.debug:
                print(f"❌ Fel vid ikon-inplacering: {e}")
    
    def format_data_sources(self, weather_data):
        """Formatera datakällor (exakt som daemon)"""
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
            if self.debug:
                print(f"❌ Fel vid formatering av datakällor: {e}")
            return "unknown"
    
    def save_screenshot(self, output_filename=None, add_timestamp=False):
        """Spara screenshot som PNG"""
        try:
            # Generera filnamn
            if output_filename is None:
                if add_timestamp:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_filename = f"epaper_live_{timestamp}.png"
                else:
                    output_filename = "epaper_live.png"
            
            # Säkerställ att screenshots-mappen finns
            screenshots_dir = "screenshots"
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
                if self.debug:
                    print(f"📁 Skapade {screenshots_dir} mapp")
            
            # Spara både 1-bit (exakt E-Paper format) och RGB (för visning)
            # 1-bit version (exakt E-Paper)
            oneBit_filename = f"1bit_{output_filename}"
            oneBit_path = os.path.join(screenshots_dir, oneBit_filename)
            self.canvas.save(oneBit_path)
            
            # RGB version (för enkel visning)
            rgb_canvas = self.canvas.convert('RGB')
            rgb_path = os.path.join(screenshots_dir, output_filename)
            rgb_canvas.save(rgb_path)
            
            print(f"📸 Screenshot sparad:")
            print(f"   🖼️ Visning: {rgb_path}")
            print(f"   📱 E-Paper: {oneBit_path}")
            print(f"   📐 Storlek: {self.width}×{self.height}px")
            
            return rgb_path, oneBit_path
            
        except Exception as e:
            print(f"❌ Fel vid sparande: {e}")
            return None, None
    
    def generate_live_screenshot(self, output_filename=None, add_timestamp=False):
        """Huvud-funktion: Generera exakt kopia av live E-Paper skärm"""
        try:
            print("📸 Genererar exakt kopia av live E-Paper skärm...")
            
            # Hämta live väderdata (samma som daemon)
            weather_data = self.fetch_live_weather_data()
            
            # Rendera exakt samma layout som daemon
            self.render_exact_display(weather_data)
            
            # Spara screenshot
            rgb_path, oneBit_path = self.save_screenshot(output_filename, add_timestamp)
            
            if rgb_path:
                print("✅ Live screenshot genererad - exakt som E-Paper skärmen!")
                return rgb_path, oneBit_path
            else:
                print("❌ Kunde inte spara screenshot")
                return None, None
            
        except Exception as e:
            print(f"❌ Fel vid generering av live screenshot: {e}")
            import traceback
            traceback.print_exc()
            return None, None


def main():
    """Huvudfunktion med kommandoradsargument"""
    parser = argparse.ArgumentParser(description='E-Paper Live Screenshot - Exakt kopia av aktuell skärm')
    parser.add_argument('--output', '-o', 
                        help='Filnamn för screenshot (utan .png)')
    parser.add_argument('--timestamp', '-t', action='store_true',
                        help='Lägg till timestamp i filnamnet')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Visa debug-information')
    
    args = parser.parse_args()
    
    try:
        # Skapa screenshot-generator
        generator = EPaperScreenshotGenerator(debug=args.debug)
        
        # Generera live screenshot
        rgb_path, oneBit_path = generator.generate_live_screenshot(
            output_filename=args.output,
            add_timestamp=args.timestamp
        )
        
        if rgb_path:
            print(f"\n🎯 RESULTAT: Exakt kopia av E-Paper skärmen sparad!")
            if args.debug:
                print(f"📂 Öppna {rgb_path} för att se resultatet")
        
    except KeyboardInterrupt:
        print("\n⚠️ Screenshot avbruten av användare")
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()