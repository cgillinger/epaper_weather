#!/usr/bin/env python3
"""
Weather Icons PNG Generator för E-Paper Väderapp
Konverterar Weather Icons TTF-font till PNG-filer optimerade för E-Paper
Använder samma mappningar som utils.py från Väderdisplayen
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import json

# Lägg till modules för att kunna importera utils
sys.path.append('modules')

class WeatherIconsPNGGenerator:
    """Genererar PNG-ikoner från Weather Icons TTF-font"""
    
    def __init__(self, font_path="assets/fonts/weathericons-regular-webfont.ttf"):
        """
        Initialisera PNG-generator
        
        Args:
            font_path: Sökväg till Weather Icons TTF-font
        """
        self.font_path = font_path
        self.output_base = "icons"
        
        # Weather Icons Unicode mappningar (från utils.py)
        self.weather_icons_unicode = {
            # Dag-ikoner
            "wi-day-sunny": "\uf00d",
            "wi-day-cloudy": "\uf002",
            "wi-day-cloudy-gusts": "\uf000",
            "wi-day-cloudy-windy": "\uf001",
            "wi-day-fog": "\uf003",
            "wi-day-hail": "\uf004",
            "wi-day-haze": "\uf0b6",
            "wi-day-lightning": "\uf005",
            "wi-day-rain": "\uf008",
            "wi-day-rain-mix": "\uf006",
            "wi-day-rain-wind": "\uf007",
            "wi-day-showers": "\uf009",
            "wi-day-sleet": "\uf0b2",
            "wi-day-sleet-storm": "\uf068",
            "wi-day-snow": "\uf00a",
            "wi-day-snow-thunderstorm": "\uf06b",
            "wi-day-snow-wind": "\uf065",
            "wi-day-sprinkle": "\uf00b",
            "wi-day-storm-showers": "\uf00e",
            "wi-day-sunny-overcast": "\uf00c",
            "wi-day-thunderstorm": "\uf010",
            "wi-day-windy": "\uf085",
            "wi-day-cloudy-high": "\uf07d",
            
            # Natt-ikoner
            "wi-night-clear": "\uf02e",
            "wi-night-cloudy": "\uf031",
            "wi-night-cloudy-gusts": "\uf02d",
            "wi-night-cloudy-windy": "\uf02c",
            "wi-night-fog": "\uf04a",
            "wi-night-hail": "\uf026",
            "wi-night-lightning": "\uf025",
            "wi-night-partly-cloudy": "\uf083",
            "wi-night-rain": "\uf036",
            "wi-night-rain-mix": "\uf034",
            "wi-night-rain-wind": "\uf035",
            "wi-night-showers": "\uf037",
            "wi-night-sleet": "\uf0b4",
            "wi-night-sleet-storm": "\uf069",
            "wi-night-snow": "\uf038",
            "wi-night-snow-thunderstorm": "\uf06c",
            "wi-night-snow-wind": "\uf066",
            "wi-night-sprinkle": "\uf039",
            "wi-night-storm-showers": "\uf03a",
            "wi-night-thunderstorm": "\uf03b",
            "wi-night-cloudy-high": "\uf07e",
            "wi-night-alt-cloudy": "\uf086",
            
            # Allmänna ikoner
            "wi-cloudy": "\uf013",
            "wi-cloud": "\uf041",
            "wi-fog": "\uf014",
            "wi-rain": "\uf019",
            "wi-rain-mix": "\uf017",
            "wi-sleet": "\uf0b5",
            "wi-snow": "\uf01b",
            "wi-thunderstorm": "\uf01e",
            "wi-windy": "\uf021",
            
            # Riktning-ikoner
            "wi-direction-up": "\uf058",
            "wi-direction-down": "\uf044",
            "wi-direction-right": "\uf04d",  # Lägg till denna för stabilt tryck
            "wi-minus": "\uf056",
            
            # Sol-ikoner
            "wi-sunrise": "\uf051",
            "wi-sunset": "\uf053",
            
            # System-ikoner
            "wi-refresh": "\uf04c",
            "wi-strong-wind": "\uf050",
            
            # Fallback
            "wi-na": "\uf07b"
        }
        
        # SMHI mappningar (från utils.py)
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
        
        # Andra mappningar
        self.pressure_mapping = {
            'rising': 'wi-direction-up',
            'falling': 'wi-direction-down',
            'stable': 'wi-direction-right'
        }
        
        self.sun_mapping = {
            'sunrise': 'wi-sunrise',
            'sunset': 'wi-sunset',
            'daylight': 'wi-day-sunny'
        }
        
        self.system_mapping = {
            'update': 'wi-refresh',
            'data_source': 'wi-strong-wind',
            'status_ok': 'wi-day-sunny',
            'status_error': 'wi-na'
        }
        
        # Storlekskonfiguration för olika ikon-typer
        self.size_config = {
            'weather': [64, 48, 32],      # Väderikoner (stor, medium, liten)
            'pressure': [20, 16],         # Tryckikoner (liten)
            'sun': [24, 20],              # Sol-ikoner (medium)
            'system': [16, 12]            # System-ikoner (mycket liten)
        }
        
        print(f"🎨 Weather Icons PNG Generator initierad")
        print(f"📁 Font: {font_path}")
        print(f"📊 Unicode mappningar: {len(self.weather_icons_unicode)} ikoner")
        
    def verify_font(self):
        """Verifiera att Weather Icons font finns och kan laddas"""
        if not os.path.exists(self.font_path):
            print(f"❌ Font saknas: {self.font_path}")
            return False
        
        try:
            # Testa att ladda font
            test_font = ImageFont.truetype(self.font_path, 32)
            print(f"✅ Font verifierad: {self.font_path}")
            return True
        except Exception as e:
            print(f"❌ Kan inte ladda font: {e}")
            return False
    
    def create_output_directories(self):
        """Skapa output-kataloger för olika ikon-typer"""
        directories = ['weather', 'pressure', 'sun', 'system']
        
        for dir_name in directories:
            dir_path = os.path.join(self.output_base, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            print(f"📁 Katalog säkerställd: {dir_path}/")
    
    def generate_png_icon(self, icon_name, unicode_char, size, output_path):
        """
        Generera en PNG-ikon från Unicode-tecken
        
        Args:
            icon_name: Namn på ikon (t.ex. "wi-day-sunny")
            unicode_char: Unicode-tecken från font
            size: Storlek på ikon (pixlar)
            output_path: Sökväg där PNG ska sparas
            
        Returns:
            True om lyckad, False vid fel
        """
        try:
            # Ladda font med rätt storlek
            font = ImageFont.truetype(self.font_path, size)
            
            # Skapa tom bild med vit bakgrund
            image = Image.new('RGB', (size, size), 'white')
            draw = ImageDraw.Draw(image)
            
            # Hämta text-dimensioner för centrering
            bbox = draw.textbbox((0, 0), unicode_char, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Centrera ikon
            x = (size - text_width) // 2
            y = (size - text_height) // 2
            
            # Rita ikon (svart på vit bakgrund)
            draw.text((x, y), unicode_char, font=font, fill='black')
            
            # Optimera för E-Paper
            optimized_image = self.optimize_for_epaper(image)
            
            # Spara PNG
            optimized_image.save(output_path, 'PNG')
            
            return True
            
        except Exception as e:
            print(f"❌ Fel vid generering av {icon_name}: {e}")
            return False
    
    def optimize_for_epaper(self, image):
        """
        Optimera bild för E-Paper display
        
        Args:
            image: PIL Image-objekt (RGB)
            
        Returns:
            Optimerad PIL Image-objekt (1-bit)
        """
        # Konvertera till grayscale
        gray_image = image.convert('L')
        
        # Förbättra kontrast för E-Paper
        enhancer = ImageEnhance.Contrast(gray_image)
        contrasted = enhancer.enhance(2.0)  # Hög kontrast
        
        # Förbättra skärpa
        sharpness_enhancer = ImageEnhance.Sharpness(contrasted)
        sharpened = sharpness_enhancer.enhance(1.5)
        
        # Konvertera till 1-bit svartvit med Floyd-Steinberg dithering
        bw_image = sharpened.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        
        return bw_image
    
    def collect_all_needed_icons(self):
        """
        Samla alla unika ikon-namn som behövs baserat på mappningar
        
        Returns:
            Dict med ikon-kategorier och lista av ikon-namn
        """
        needed_icons = {
            'weather': set(),
            'pressure': set(),
            'sun': set(),
            'system': set()
        }
        
        # Samla väderikoner från SMHI-mappning
        for symbol_data in self.smhi_mapping.values():
            needed_icons['weather'].add(symbol_data['day'])
            needed_icons['weather'].add(symbol_data['night'])
        
        # Samla tryckikoner
        for icon_name in self.pressure_mapping.values():
            needed_icons['pressure'].add(icon_name)
        
        # Samla sol-ikoner
        for icon_name in self.sun_mapping.values():
            needed_icons['sun'].add(icon_name)
        
        # Samla system-ikoner
        for icon_name in self.system_mapping.values():
            needed_icons['system'].add(icon_name)
        
        # Konvertera sets till lists och sortera
        for category in needed_icons:
            needed_icons[category] = sorted(list(needed_icons[category]))
        
        return needed_icons
    
    def generate_all_icons(self):
        """Generera alla PNG-ikoner som behövs"""
        print("\n🎨 Startar PNG-generering för alla Weather Icons...")
        
        # Verifiera font
        if not self.verify_font():
            return False
        
        # Skapa output-kataloger
        self.create_output_directories()
        
        # Samla alla behövda ikoner
        needed_icons = self.collect_all_needed_icons()
        
        total_generated = 0
        total_failed = 0
        
        # Generera ikoner för varje kategori
        for category, icon_names in needed_icons.items():
            print(f"\n📁 Genererar {category}-ikoner ({len(icon_names)} unika)...")
            
            for icon_name in icon_names:
                # Kontrollera om ikon finns i Unicode-mappning
                if icon_name not in self.weather_icons_unicode:
                    print(f"⚠️ Unicode saknas för: {icon_name}")
                    total_failed += 1
                    continue
                
                unicode_char = self.weather_icons_unicode[icon_name]
                
                # Generera i alla storlekar för denna kategori
                sizes = self.size_config.get(category, [32])  # Default 32px
                
                for size in sizes:
                    output_filename = f"{icon_name}.png"
                    output_path = os.path.join(self.output_base, category, output_filename)
                    
                    if self.generate_png_icon(icon_name, unicode_char, size, output_path):
                        total_generated += 1
                        print(f"  ✅ {icon_name}.png ({size}×{size})")
                    else:
                        total_failed += 1
                        print(f"  ❌ {icon_name}.png ({size}×{size})")
                    
                    # För weather-ikoner, skapa även andra storlekar
                    if category == 'weather' and size == 64:  
                        # Skapa även 48×48 och 32×32 versioner
                        for alt_size in [48, 32]:
                            alt_output_path = output_path.replace('.png', f'_{alt_size}.png')
                            if self.generate_png_icon(icon_name, unicode_char, alt_size, alt_output_path):
                                total_generated += 1
                                print(f"  ✅ {icon_name}_{alt_size}.png")
        
        print(f"\n📊 PNG-generering slutförd:")
        print(f"  ✅ Genererade: {total_generated} PNG-filer")
        print(f"  ❌ Misslyckade: {total_failed}")
        
        return total_failed == 0
    
    def create_icon_summary(self):
        """Skapa sammanfattning av genererade ikoner"""
        summary = {
            'generated_icons': {},
            'file_count': 0,
            'total_size_kb': 0
        }
        
        categories = ['weather', 'pressure', 'sun', 'system']
        
        for category in categories:
            category_path = os.path.join(self.output_base, category)
            if not os.path.exists(category_path):
                continue
            
            png_files = [f for f in os.listdir(category_path) if f.endswith('.png')]
            summary['generated_icons'][category] = len(png_files)
            summary['file_count'] += len(png_files)
            
            # Beräkna total storlek
            for png_file in png_files:
                file_path = os.path.join(category_path, png_file)
                file_size = os.path.getsize(file_path)
                summary['total_size_kb'] += file_size / 1024
        
        return summary
    
    def test_generated_icons(self):
        """Testa att viktiga ikoner genererats korrekt"""
        print("\n🧪 Testar genererade ikoner...")
        
        # Viktiga ikoner som ska finnas (baserat på main.py terminal-output)
        critical_icons = [
            ('weather', 'wi-day-cloudy.png'),
            ('sun', 'wi-sunrise.png'),
            ('sun', 'wi-sunset.png'),
            ('pressure', 'wi-direction-right.png'),
            ('weather', 'wi-day-sunny-overcast.png'),
            ('system', 'wi-day-sunny.png'),
            ('system', 'wi-refresh.png')
        ]
        
        all_found = True
        
        for category, filename in critical_icons:
            file_path = os.path.join(self.output_base, category, filename)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ {category}/{filename} ({file_size} bytes)")
            else:
                print(f"  ❌ {category}/{filename} SAKNAS!")
                all_found = False
        
        return all_found


def main():
    """Huvudfunktion för PNG-generering"""
    print("🎨 Weather Icons → PNG Converter för E-Paper")
    print("=" * 50)
    
    # Skapa generator
    generator = WeatherIconsPNGGenerator()
    
    # Generera alla ikoner
    success = generator.generate_all_icons()
    
    if success:
        print(f"\n🎉 PNG-generering slutförd framgångsrikt!")
        
        # Skapa sammanfattning
        summary = generator.create_icon_summary()
        print(f"\n📊 Sammanfattning:")
        print(f"  📁 Totalt: {summary['file_count']} PNG-filer")
        print(f"  💾 Storlek: {summary['total_size_kb']:.1f} KB")
        
        for category, count in summary['generated_icons'].items():
            print(f"  🎨 {category}: {count} ikoner")
        
        # Testa kritiska ikoner
        if generator.test_generated_icons():
            print(f"\n✅ Alla kritiska ikoner genererade!")
            print(f"🚀 Redo att testa med main.py!")
        else:
            print(f"\n⚠️ Vissa kritiska ikoner saknas - kontrollera output")
    
    else:
        print(f"\n❌ PNG-generering misslyckades")
        print(f"🔧 Kontrollera font-sökväg och Unicode-mappningar")
    
    return success


if __name__ == "__main__":
    main()
