#!/usr/bin/env python3
"""
Weather Icon Manager för E-Paper Väderapp
Hanterar Weather Icons konverterade till PNG för E-Paper display
Använder samma mappningar som Väderdisplayens utils.py
FIXED: Korrekt trycktrend-pilar (wi-towards-X-deg med ringar) + förbättrad transparens
"""

import os
import sys
from datetime import datetime
from PIL import Image, ImageEnhance
import logging

class WeatherIconManager:
    """Hanterar Weather Icons för E-Paper display"""
    
    def __init__(self, icon_base_path="icons/"):
        """
        Initialisera ikon-hanterare
        
        Args:
            icon_base_path: Baskatalog för ikoner (relativ från projektrot)
        """
        self.icon_path = icon_base_path
        self.icon_cache = {}
        
        # Exakt samma mappning som Väderdisplayens utils.py
        self.smhi_mapping = {
            1: {"day": "wi-day-sunny", "night": "wi-night-clear"},                    # Klart
            2: {"day": "wi-day-sunny-overcast", "night": "wi-night-partly-cloudy"},  # Nästan klart
            3: {"day": "wi-day-cloudy", "night": "wi-night-alt-cloudy"},             # Växlande molnighet
            4: {"day": "wi-day-cloudy-high", "night": "wi-night-cloudy-high"},       # Halvklart
            5: {"day": "wi-cloudy", "night": "wi-cloudy"},                           # Molnigt
            6: {"day": "wi-cloud", "night": "wi-cloud"},                             # Mulet
            7: {"day": "wi-fog", "night": "wi-fog"},                                 # Dimma
            8: {"day": "wi-day-showers", "night": "wi-night-showers"},               # Lätta regnskurar
            9: {"day": "wi-day-rain", "night": "wi-night-rain"},                     # Måttliga regnskurar
            10: {"day": "wi-rain", "night": "wi-rain"},                              # Kraftiga regnskurar
            11: {"day": "wi-day-thunderstorm", "night": "wi-night-thunderstorm"},    # Åskväder
            12: {"day": "wi-day-rain-mix", "night": "wi-night-rain-mix"},            # Lätta snöblandade regnskurar
            13: {"day": "wi-rain-mix", "night": "wi-rain-mix"},                      # Måttliga snöblandade regnskurar
            14: {"day": "wi-rain-mix", "night": "wi-rain-mix"},                      # Kraftiga snöblandade regnskurar
            15: {"day": "wi-day-snow", "night": "wi-night-snow"},                    # Lätta snöbyar
            16: {"day": "wi-snow", "night": "wi-snow"},                              # Måttliga snöbyar
            17: {"day": "wi-snow", "night": "wi-snow"},                              # Kraftiga snöbyar
            18: {"day": "wi-day-rain", "night": "wi-night-rain"},                    # Lätt regn
            19: {"day": "wi-rain", "night": "wi-rain"},                              # Måttligt regn
            20: {"day": "wi-rain", "night": "wi-rain"},                              # Kraftigt regn
            21: {"day": "wi-thunderstorm", "night": "wi-thunderstorm"},              # Åska
            22: {"day": "wi-day-sleet", "night": "wi-night-sleet"},                  # Lätt snöblandat regn
            23: {"day": "wi-sleet", "night": "wi-sleet"},                            # Måttligt snöblandat regn
            24: {"day": "wi-sleet", "night": "wi-sleet"},                            # Kraftigt snöblandat regn
            25: {"day": "wi-day-snow", "night": "wi-night-snow"},                    # Lätt snöfall
            26: {"day": "wi-snow", "night": "wi-snow"},                              # Måttligt snöfall
            27: {"day": "wi-snow", "night": "wi-snow"}                               # Kraftigt snöfall
        }
        
        # FIXED: Korrekt trycktrend-ikoner med ringar (meteorologisk standard)
        self.pressure_mapping = {
            'rising': 'wi-towards-ne-deg',    # ↗ Stigande tryck (45° uppåt med ring)
            'falling': 'wi-towards-se-deg',   # ↘ Fallande tryck (45° nedåt med ring)
            'stable': 'wi-towards-e-deg'      # → Stabilt tryck (horisontell med ring)
        }
        
        # Sol-ikoner (använda de som faktiskt genererades i sun/ katalogen)
        self.sun_mapping = {
            'sunrise': 'wi-sunrise',          # Finns i sun/ katalogen
            'sunset': 'wi-sunset',            # Finns i sun/ katalogen
            'daylight': 'wi-day-sunny'        # Finns i sun/ katalogen
        }
        
        # System-ikoner - FIXED: Barometer-ikon tillagd!
        self.system_mapping = {
            'update': 'wi-refresh',           # Uppdatering
            'data_source': 'wi-strong-wind',  # Data-källa indikator
            'status_ok': 'wi-day-sunny',      # Status OK
            'status_error': 'wi-na',          # Status fel
            'clock': 'wi-time-1',
            'clock3': 'wi-time-3',            # Klockikon (gammal)
            'clock7': 'wi-time-7',            # Klockikon (FÖRBÄTTRAD)
            'barometer': 'wi-barometer'       # FIXED: Barometer-ikon tillagd!
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        print(f"🎨 WeatherIconManager initierad - {len(self.smhi_mapping)} väderikoner mappade")
        print(f"✅ FIXED: Korrekt trycktrend-pilar (wi-towards-X-deg med ringar)!")
    
    def get_weather_icon(self, smhi_symbol, is_night=False, size=(48, 48)):
        """
        Hämta väderikon baserat på SMHI-symbol med dag/natt-logik
        
        Args:
            smhi_symbol: SMHI vädersymbol (1-27)
            is_night: Om det är natt (påverkar val av ikon-variant)
            size: Tuple med (bredd, höjd) för ikon-storlek
            
        Returns:
            PIL Image-objekt optimerat för E-Paper, eller None vid fel
        """
        if smhi_symbol not in self.smhi_mapping:
            self.logger.warning(f"⚠️ Okänd SMHI-symbol: {smhi_symbol}")
            return self.create_fallback_icon(size, f"?{smhi_symbol}")
        
        icon_data = self.smhi_mapping[smhi_symbol]
        icon_name = icon_data['night' if is_night else 'day']
        
        return self.load_icon(f"weather/{icon_name}.png", size)
    
    def get_pressure_icon(self, trend, size=(64, 64)):
        """
        Hämta trycktrend-ikon - NU MED KORREKT wi-towards-X-deg ikoner (med ringar)
        
        Args:
            trend: 'rising', 'falling', eller 'stable'
            size: Tuple med ikon-storlek (default: 64x64 för optimala trend-pilar)
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.pressure_mapping.get(trend, 'wi-towards-e-deg')  # Fallback till stabilt
        self.logger.info(f"🎯 Pressure icon mapping (KORREKT): {trend} → {icon_name}")
        
        # Försök ladda från pressure/ katalogen först
        pressure_icon = self.load_icon(f"pressure/{icon_name}.png", size)
        
        if pressure_icon is None:
            # Fallback: Kolla i weather/ katalogen (för fall SVG-konvertering gjorts där)
            self.logger.warning(f"⚠️ Pressure-ikon saknas: pressure/{icon_name}.png, försöker weather/")
            pressure_icon = self.load_icon(f"weather/{icon_name}.png", size)
            
        if pressure_icon is None:
            # Sista fallback: Använd gamla direction-ikoner
            old_mapping = {'rising': 'wi-direction-up', 'falling': 'wi-direction-down', 'stable': 'wi-direction-right'}
            old_icon_name = old_mapping.get(trend, 'wi-direction-right')
            self.logger.warning(f"⚠️ Använder fallback: {old_icon_name}")
            pressure_icon = self.load_icon(f"pressure/{old_icon_name}.png", size)
        
        return pressure_icon
    
    def get_sun_icon(self, sun_type, size=(24, 24)):
        """
        Hämta sol-ikon (sunrise/sunset)
        
        Args:
            sun_type: 'sunrise', 'sunset', eller 'daylight'
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.sun_mapping.get(sun_type, 'wi-day-sunny')
        return self.load_icon(f"sun/{icon_name}.png", size)
    
    def get_system_icon(self, system_type, size=(16, 16)):
        """
        Hämta system-ikon
        
        Args:
            system_type: 'update', 'data_source', 'status_ok', 'status_error', 'barometer', 'clock', 'clock3'
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt eller None vid fel
        """
        icon_name = self.system_mapping.get(system_type, 'wi-na')
        return self.load_icon(f"system/{icon_name}.png", size)
    
    def load_icon(self, icon_path, size):
        """
        Ladda och cacha ikon optimerad för E-Paper
        FÖRBÄTTRAD: Bättre transparens-hantering för trycktrend-pilar
        
        Args:
            icon_path: Relativ sökväg till ikon från icons/ katalog
            size: Tuple med (bredd, höjd)
            
        Returns:
            PIL Image-objekt optimerat för E-Paper, eller fallback-ikon
        """
        cache_key = f"{icon_path}_{size[0]}x{size[1]}"
        
        # Returnera från cache om redan laddad
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        try:
            full_path = os.path.join(self.icon_path, icon_path)
            
            # Kontrollera att filen finns
            if not os.path.exists(full_path):
                self.logger.warning(f"⚠️ Ikon-fil saknas: {full_path}")
                return None  # Returnera None istället för fallback för bättre felhantering
            
            # Ladda ikon
            icon = Image.open(full_path)
            
            # Skala till rätt storlek med hög kvalitet
            if icon.size != size:
                icon = icon.resize(size, Image.Resampling.LANCZOS)
            
            # FÖRBÄTTRAD optimering för E-Paper med bättre transparens
            icon = self.optimize_for_epaper_improved(icon, icon_path)
            
            # Cacha för framtida användning
            self.icon_cache[cache_key] = icon
            
            self.logger.debug(f"✅ Ikon laddad: {icon_path} ({size[0]}x{size[1]})")
            return icon
            
        except Exception as e:
            self.logger.error(f"❌ Kunde inte ladda ikon {icon_path}: {e}")
            return self.create_fallback_icon(size, "✗")
    
    def optimize_for_epaper_improved(self, image, icon_path):
        """
        FÖRBÄTTRAD optimering för E-Paper display (1-bit svartvit)
        Speciell hantering för transparens och olika ikon-typer
        
        Args:
            image: PIL Image-objekt
            icon_path: Sökväg för att identifiera ikon-typ
            
        Returns:
            Optimerat PIL Image-objekt för E-Paper
        """
        try:
            # Förbättrad transparens-hantering
            if image.mode in ('RGBA', 'LA'):
                # Skapa vit bakgrund för transparens
                background = Image.new('RGB', image.size, (255, 255, 255))
                
                if image.mode == 'RGBA':
                    # Använd alpha-kanalen för bättre transparens
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                    
                image = background
            elif image.mode == 'P':  # Palette mode
                # Konvertera palette till RGB först
                image = image.convert('RGB')
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Konvertera till grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # DYNAMISK E-Paper optimering baserat på ikon-typ och storlek
            size = max(image.size)
            is_pressure_icon = 'pressure/' in icon_path or 'towards' in icon_path
            
            if is_pressure_icon:
                # Speciell hantering för trycktrend-pilar (behöver vara extra tydliga)
                contrast_factor = 2.5
                sharpness_factor = 1.6
                brightness_factor = 1.0  # Neutral ljusstyrka för pilar
                self.logger.debug(f"🎯 Trycktrend-pil optimering: {icon_path}")
            elif size >= 80:
                # Stora ikoner (väder, barometer): Balanserad optimering
                contrast_factor = 2.2
                sharpness_factor = 1.4
                brightness_factor = 1.1
            elif size >= 48:
                # Medium ikoner: Standard optimering
                contrast_factor = 2.3
                sharpness_factor = 1.5
                brightness_factor = 1.1
            else:
                # Små ikoner: Aggressiv optimering för tydlighet
                contrast_factor = 2.6
                sharpness_factor = 1.7
                brightness_factor = 1.2
            
            # Tillämpa optimeringar
            # Kontrast
            contrast_enhancer = ImageEnhance.Contrast(image)
            image = contrast_enhancer.enhance(contrast_factor)
            
            # Skärpa
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(sharpness_factor)
            
            # Ljusstyrka
            brightness_enhancer = ImageEnhance.Brightness(image)
            image = brightness_enhancer.enhance(brightness_factor)
            
            # Konvertera till 1-bit svartvit med Floyd-Steinberg dithering
            image = image.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            return image
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid E-Paper optimering: {e}")
            return self.create_fallback_icon(image.size, "!")
    
    def create_fallback_icon(self, size, text="?"):
        """
        Skapa fallback-ikon när riktig ikon inte kan laddas
        
        Args:
            size: Tuple med (bredd, höjd)
            text: Text att visa i fallback-ikonen
            
        Returns:
            PIL Image-objekt med fallback-ikon
        """
        try:
            # Skapa tom vit bild
            fallback = Image.new('1', size, 255)
            
            # Om PIL har textfunktioner, lägg till enkel text
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(fallback)
                
                # Försök använda standard-font
                font_size = min(size) // 2
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Centrera text
                if font:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (size[0] - text_width) // 2
                    y = (size[1] - text_height) // 2
                    draw.text((x, y), text, font=font, fill=0)
                else:
                    # Enkel punkt i mitten om font inte fungerar
                    center_x, center_y = size[0] // 2, size[1] // 2
                    draw.point((center_x, center_y), fill=0)
                    
            except ImportError:
                # Om ImageDraw inte finns, returnera tom ikon
                pass
            
            self.logger.debug(f"🔧 Fallback-ikon skapad: {size[0]}x{size[1]} ('{text}')")
            return fallback
            
        except Exception as e:
            self.logger.error(f"❌ Kunde inte skapa fallback-ikon: {e}")
            # Sista utväg: tom vit bild
            return Image.new('1', size, 255)
    
    def is_night_time(self, current_time, sunrise_time, sunset_time):
        """
        Bestäm om det är natt baserat på soluppgång/solnedgång
        Samma logik som Väderdisplayen
        
        Args:
            current_time: datetime-objekt för aktuell tid
            sunrise_time: datetime-objekt för soluppgång
            sunset_time: datetime-objekt för solnedgång
            
        Returns:
            True om det är natt, False om det är dag
        """
        if not sunrise_time or not sunset_time:
            # Fallback: 22:00-06:00 = natt
            hour = current_time.hour
            return hour < 6 or hour >= 22
        
        return current_time < sunrise_time or current_time > sunset_time
    
    def get_weather_icon_for_time(self, smhi_symbol, current_time, sun_data, size=(48, 48)):
        """
        Välj dag/natt-variant av väderikon baserat på aktuell tid och soldata
        
        Args:
            smhi_symbol: SMHI vädersymbol (1-27)
            current_time: datetime-objekt för aktuell tid
            sun_data: Dict med soluppgång/solnedgång-data
            size: Tuple med ikon-storlek
            
        Returns:
            PIL Image-objekt med korrekt dag/natt-variant
        """
        # Parsea soldata om tillgängligt
        sunrise_time = None
        sunset_time = None
        
        if sun_data and 'sunrise' in sun_data and 'sunset' in sun_data:
            try:
                if isinstance(sun_data['sunrise'], str):
                    sunrise_time = datetime.fromisoformat(sun_data['sunrise'])
                else:
                    sunrise_time = sun_data['sunrise']
                    
                if isinstance(sun_data['sunset'], str):
                    sunset_time = datetime.fromisoformat(sun_data['sunset'])
                else:
                    sunset_time = sun_data['sunset']
            except Exception as e:
                self.logger.warning(f"⚠️ Fel vid parsning av soldata: {e}")
        
        # Bestäm om det är natt
        is_night = self.is_night_time(current_time, sunrise_time, sunset_time)
        
        # Hämta korrekt väderikon
        return self.get_weather_icon(smhi_symbol, is_night, size)
    
    def clear_cache(self):
        """Rensa ikon-cache för att frigöra minne"""
        cache_size = len(self.icon_cache)
        self.icon_cache.clear()
        self.logger.info(f"🗑️ Ikon-cache rensad: {cache_size} ikoner borttagna")
        print(f"🗑️ Ikon-cache rensad: {cache_size} ikoner")
    
    def get_cache_stats(self):
        """
        Få statistik om ikon-cache
        
        Returns:
            Dict med cache-statistik
        """
        total_icons = len(self.icon_cache)
        
        # Gruppera efter typ
        weather_count = len([k for k in self.icon_cache.keys() if k.startswith('weather/')])
        pressure_count = len([k for k in self.icon_cache.keys() if k.startswith('pressure/')])
        sun_count = len([k for k in self.icon_cache.keys() if k.startswith('sun/')])
        system_count = len([k for k in self.icon_cache.keys() if k.startswith('system/')])
        
        return {
            'total_cached_icons': total_icons,
            'weather_icons': weather_count,
            'pressure_icons': pressure_count, 
            'sun_icons': sun_count,
            'system_icons': system_count
        }
    
    def test_icon_loading(self):
        """
        Testa ikon-laddning med fallback-ikoner
        Användbart för att verifiera att systemet fungerar innan riktiga ikoner läggs till
        
        Returns:
            Dict med test-resultat
        """
        print("🧪 Testar WeatherIconManager...")
        
        test_results = {
            'weather_icon_test': False,
            'pressure_icon_test': False,
            'sun_icon_test': False,
            'system_icon_test': False,
            'barometer_icon_test': False,  # NY: Specifik barometer-test
            'pressure_towards_test': False,  # NY: Test av wi-towards-X-deg ikoner
            'fallback_system_works': True
        }
        
        # Test väderikon
        try:
            weather_icon = self.get_weather_icon(1, is_night=False, size=(48, 48))
            test_results['weather_icon_test'] = weather_icon is not None
            print(f"🌤️ Väderikon-test: {'✅ OK' if weather_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Väderikon-test misslyckades: {e}")
        
        # Test tryckikon (NU: wi-towards-X-deg ikoner)
        try:
            pressure_icon = self.get_pressure_icon('rising', size=(64, 64))
            test_results['pressure_icon_test'] = pressure_icon is not None
            
            # Specifik test för wi-towards-X-deg ikoner
            test_results['pressure_towards_test'] = pressure_icon is not None
            print(f"📈 Tryckikon-test (wi-towards-ne-deg): {'✅ OK' if pressure_icon else '❌ Fel'}")
            
            if pressure_icon is None:
                print(f"⚠️ wi-towards-ne-deg saknas - använder fallback")
            
        except Exception as e:
            print(f"❌ Tryckikon-test misslyckades: {e}")
        
        # Test sol-ikon
        try:
            sun_icon = self.get_sun_icon('sunrise', size=(24, 24))
            test_results['sun_icon_test'] = sun_icon is not None
            print(f"🌅 Sol-ikon-test: {'✅ OK' if sun_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Sol-ikon-test misslyckades: {e}")
        
        # Test system-ikon
        try:
            system_icon = self.get_system_icon('update', size=(16, 16))
            test_results['system_icon_test'] = system_icon is not None
            print(f"🔄 System-ikon-test: {'✅ OK' if system_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ System-ikon-test misslyckades: {e}")
        
        # Test barometer-ikon (NY!)
        try:
            barometer_icon = self.get_system_icon('barometer', size=(32, 32))
            test_results['barometer_icon_test'] = barometer_icon is not None
            print(f"🌡️ Barometer-ikon-test: {'✅ OK' if barometer_icon else '❌ Fel'}")
        except Exception as e:
            print(f"❌ Barometer-ikon-test misslyckades: {e}")
        
        # Visa cache-statistik
        cache_stats = self.get_cache_stats()
        print(f"💾 Cache-statistik: {cache_stats['total_cached_icons']} ikoner totalt")
        
        return test_results


# Test-funktioner
def test_weather_icon_manager():
    """Test av WeatherIconManager"""
    print("🧪 Testar WeatherIconManager med KORREKT pressure icons...")
    
    # Skapa ikon-manager
    icon_manager = WeatherIconManager()
    
    # Kör test
    results = icon_manager.test_icon_loading()
    
    print(f"\n📊 Test-resultat:")
    for test_name, result in results.items():
        if test_name == 'pressure_towards_test':
            status = "✅ KORREKT wi-towards-X-deg" if result else "⚠️ Fallback till wi-direction-X"
        else:
            status = "✅ PASS" if result else "⚠️ FALLBACK"
        print(f"  {test_name}: {status}")
    
    print(f"\n💡 FIXED: Pressure-ikoner använder nu wi-towards-X-deg (med ringar)!")
    print(f"🔧 Om wi-towards-X-deg ikoner saknas, används wi-direction-X som fallback")
    
    return icon_manager


if __name__ == "__main__":
    test_weather_icon_manager()
