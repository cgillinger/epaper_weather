#!/usr/bin/env python3
"""
Weather Icons SVG → PNG Konvertering
Ersätter befintliga felkonverterade PNG-filer med korrekta SVG-baserade versioner
Löser avklippning-problemet med pressure-pilar och förbättrar alla ikoner
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance
import logging

# Kontrollera att cairosvg finns i virtuell miljö
try:
    import cairosvg
    print("✅ cairosvg tillgängligt i virtuell miljö")
except ImportError:
    print("❌ cairosvg inte tillgängligt!")
    print("🔧 Aktivera virtuell miljö först: source .venv/bin/activate")
    sys.exit(1)

class WeatherIconsSVGConverter:
    """Konverterar SVG till PNG med exakt överskrivning av befintliga filer"""
    
    def __init__(self, svg_base_dir="weather-icons-master/svg", icons_dir="icons"):
        """
        Initialisera konverterare
        
        Args:
            svg_base_dir: Katalog med SVG-filer
            icons_dir: Målkatalog med befintliga PNG-filer
        """
        self.svg_base_dir = Path(svg_base_dir)
        self.icons_dir = Path(icons_dir)
        
        # Kontrollera att katalogerna finns
        if not self.svg_base_dir.exists():
            raise FileNotFoundError(f"SVG-katalog finns inte: {self.svg_base_dir}")
        if not self.icons_dir.exists():
            raise FileNotFoundError(f"Icons-katalog finns inte: {self.icons_dir}")
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Skapa backup-katalog
        self.backup_dir = Path(f"backup/svg_conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Räknare för statistik
        self.stats = {
            'converted': 0,
            'skipped': 0,
            'failed': 0,
            'backed_up': 0
        }
        
        print(f"🎨 Weather Icons SVG→PNG Converter")
        print(f"📁 SVG källa: {self.svg_base_dir}")
        print(f"📁 PNG mål: {self.icons_dir}")
        print(f"💾 Backup: {self.backup_dir}")
    
    def get_conversion_mapping(self):
        """
        Definiera exakt mappning från SVG till befintliga PNG-filer
        Baserat på din inventering och befintlig struktur
        """
        return {
            # KRITISKA PRESSURE-PILAR (löser avklippning)
            'pressure': {
                'wi-direction-up': [(56, 56, ''), (20, 20, '_20')],
                'wi-direction-down': [(56, 56, ''), (20, 20, '_20')],
                'wi-direction-right': [(56, 56, ''), (20, 20, '_20')]
            },
            
            # SYSTEM-IKONER
            'system': {
                'wi-barometer': [(48, 48, ''), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (64, 64, '_64')],
                'wi-refresh': [(24, 24, ''), (16, 16, '_16'), (12, 12, '_12')],
                'wi-strong-wind': [(24, 24, ''), (16, 16, '_16'), (12, 12, '_12')],
                'wi-na': [(24, 24, ''), (16, 16, '_16'), (12, 12, '_12')],
                'wi-day-sunny': [(24, 24, ''), (16, 16, '_16'), (12, 12, '_12')],
                
                # TID-IKONER (12 stycken, 6 storlekar vardera)
                'wi-time-1': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-2': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-3': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-4': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-5': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-6': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-7': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-8': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-9': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-10': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-11': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')],
                'wi-time-12': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12')]
            },
            
            # SOL-IKONER
            'sun': {
                'wi-sunrise': [(40, 40, ''), (24, 24, '_24')],
                'wi-sunset': [(40, 40, ''), (24, 24, '_24')],
                'wi-day-sunny': [(40, 40, ''), (24, 24, '_24')]
            },
            
            # WEATHER-IKONER (många, 3 storlekar vardera)
            'weather': {
                'wi-cloud': [(48, 48, ''), (32, 32, '_32')],
                'wi-cloudy': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-cloudy': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-cloudy-high': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-rain': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-rain-mix': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-showers': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-sleet': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-snow': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-sunny': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-sunny-overcast': [(48, 48, ''), (32, 32, '_32')],
                'wi-day-thunderstorm': [(48, 48, ''), (32, 32, '_32')],
                'wi-fog': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-alt-cloudy': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-clear': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-cloudy-high': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-partly-cloudy': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-rain': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-rain-mix': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-showers': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-sleet': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-snow': [(48, 48, ''), (32, 32, '_32')],
                'wi-night-thunderstorm': [(48, 48, ''), (32, 32, '_32')],
                'wi-rain': [(48, 48, ''), (32, 32, '_32')],
                'wi-rain-mix': [(48, 48, ''), (32, 32, '_32')],
                'wi-sleet': [(48, 48, ''), (32, 32, '_32')],
                'wi-snow': [(48, 48, ''), (32, 32, '_32')],
                'wi-thunderstorm': [(48, 48, ''), (32, 32, '_32')],
                'wi-na': [(48, 48, ''), (32, 32, '_32')]
            }
        }
    
    def backup_existing_png(self, png_path):
        """
        Säkerhetskopiera befintlig PNG-fil
        
        Args:
            png_path: Sökväg till PNG-fil
            
        Returns:
            True om backup lyckades
        """
        try:
            if png_path.exists():
                # Skapa samma katalogstruktur i backup
                relative_path = png_path.relative_to(self.icons_dir)
                backup_path = self.backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(png_path, backup_path)
                self.stats['backed_up'] += 1
                self.logger.debug(f"💾 Backup: {png_path} → {backup_path}")
                return True
            return True
        except Exception as e:
            self.logger.error(f"❌ Backup misslyckades för {png_path}: {e}")
            return False
    
    def convert_svg_to_png(self, svg_path, png_path, width, height):
        """
        Konvertera SVG till PNG med given storlek
        
        Args:
            svg_path: Sökväg till SVG-fil
            png_path: Sökväg för PNG-utdata
            width, height: Mål-storlek
            
        Returns:
            True om konvertering lyckades
        """
        try:
            # Skapa temp-fil för säker överskrivning
            temp_path = png_path.with_suffix('.tmp')
            
            # Konvertera SVG → PNG med cairosvg
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(temp_path),
                output_width=width,
                output_height=height,
                background_color='white'
            )
            
            # Optimera för E-Paper
            self.optimize_for_epaper(temp_path)
            
            # Atomisk överskrivning
            shutil.move(temp_path, png_path)
            
            self.logger.debug(f"✅ Konverterad: {svg_path.name} → {png_path.name} ({width}×{height})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Konvertering misslyckades {svg_path.name}: {e}")
            # Rensa temp-fil om den finns
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def optimize_for_epaper(self, png_path):
        """
        Optimera PNG för E-Paper display (1-bit svartvit)
        
        Args:
            png_path: Sökväg till PNG-fil att optimera
        """
        try:
            # Ladda bilden
            image = Image.open(png_path)
            
            # Konvertera till RGB om nödvändigt (hantera transparens)
            if image.mode in ('RGBA', 'LA'):
                # Skapa vit bakgrund för transparens
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Konvertera till grayscale
            image = image.convert('L')
            
            # E-Paper optimering
            # Öka kontrast rejält
            contrast_enhancer = ImageEnhance.Contrast(image)
            image = contrast_enhancer.enhance(2.2)
            
            # Förbättra skärpa
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(1.4)
            
            # Justera ljusstyrka
            brightness_enhancer = ImageEnhance.Brightness(image)
            image = brightness_enhancer.enhance(1.1)
            
            # Konvertera till 1-bit svartvit med Floyd-Steinberg dithering
            image = image.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            # Spara optimerad version
            image.save(png_path, 'PNG', optimize=True)
            
        except Exception as e:
            self.logger.error(f"❌ E-Paper optimering misslyckades för {png_path}: {e}")
    
    def convert_category(self, category, icon_mapping):
        """
        Konvertera en kategori av ikoner
        
        Args:
            category: Kategorinamn ('pressure', 'system', 'sun', 'weather')
            icon_mapping: Dict med ikon-mappningar
            
        Returns:
            Dict med resultat-statistik
        """
        category_stats = {'converted': 0, 'skipped': 0, 'failed': 0}
        category_dir = self.icons_dir / category
        
        print(f"\n🔄 Konverterar {category} ikoner...")
        print(f"📁 Mål: {category_dir}")
        
        for icon_name, size_specs in icon_mapping.items():
            svg_path = self.svg_base_dir / f"{icon_name}.svg"
            
            # Kontrollera att SVG finns
            if not svg_path.exists():
                self.logger.warning(f"⚠️ SVG saknas: {svg_path}")
                category_stats['failed'] += len(size_specs)
                continue
            
            # Konvertera alla storlekar för denna ikon
            for width, height, suffix in size_specs:
                png_name = f"{icon_name}{suffix}.png"
                png_path = category_dir / png_name
                
                # Kontrollera om PNG finns (ska ersättas)
                if not png_path.exists():
                    self.logger.warning(f"⚠️ PNG saknas (hoppar över): {png_path}")
                    category_stats['skipped'] += 1
                    continue
                
                # Backup befintlig PNG
                if not self.backup_existing_png(png_path):
                    category_stats['failed'] += 1
                    continue
                
                # Konvertera SVG → PNG
                if self.convert_svg_to_png(svg_path, png_path, width, height):
                    category_stats['converted'] += 1
                    print(f"  ✅ {icon_name}{suffix}.png ({width}×{height})")
                else:
                    category_stats['failed'] += 1
                    print(f"  ❌ {icon_name}{suffix}.png MISSLYCKADES")
        
        return category_stats
    
    def run_conversion(self, categories=None):
        """
        Kör konvertering av specificerade kategorier
        
        Args:
            categories: Lista med kategorier att konvertera ['pressure', 'system', 'sun', 'weather']
                       Om None, konvertera alla
        """
        if categories is None:
            categories = ['pressure', 'system', 'sun', 'weather']
        
        # Nollställ statistik för denna körning
        self.stats = {'converted': 0, 'skipped': 0, 'failed': 0, 'backed_up': 0}
        
        print(f"🚀 Startar SVG→PNG konvertering för: {', '.join(categories)}")
        
        conversion_mapping = self.get_conversion_mapping()
        
        total_start_time = datetime.now()
        
        for category in categories:
            if category in conversion_mapping:
                icon_mapping = conversion_mapping[category]
                category_stats = self.convert_category(category, icon_mapping)
                
                # Uppdatera total statistik
                for key in category_stats:
                    self.stats[key] += category_stats[key]
            else:
                print(f"⚠️ Okänd kategori: {category}")
        
        total_duration = datetime.now() - total_start_time
        
        # Sammanfattning
        self.print_summary(total_duration, categories)
    
    def print_summary(self, duration, categories):
        """Skriv ut sammanfattning av konvertering"""
        print(f"\n" + "="*60)
        print(f"🎨 SVG→PNG KONVERTERING SLUTFÖRD!")
        print(f"📂 Kategorier: {', '.join(categories)}")
        print(f"⏱️ Tid: {duration.total_seconds():.1f} sekunder")
        print(f"")
        print(f"📊 RESULTAT:")
        print(f"  ✅ Konverterade: {self.stats['converted']} PNG-filer")
        print(f"  ⏭️ Hoppade över: {self.stats['skipped']} filer")
        print(f"  ❌ Misslyckades: {self.stats['failed']} filer")
        print(f"  💾 Backup: {self.stats['backed_up']} filer")
        print(f"")
        print(f"📁 Backup sparad i: {self.backup_dir}")
        
        if 'system' in categories and self.stats['converted'] > 50:
            print(f"")
            print(f"🔧 SYSTEM-IKONER UPPDATERADE!")
            print(f"📊 Barometer, tid-ikoner och andra system-ikoner förbättrade")
        
        if 'weather' in categories and self.stats['converted'] > 20:
            print(f"")
            print(f"🌤️ WEATHER-IKONER UPPDATERADE!")
            print(f"☀️ Väder-ikoner nu med bättre kvalitet från SVG")
        
        if self.stats['converted'] > 0:
            print(f"")
            print(f"🔧 Testa nu: cd ~/epaper_weather && python3 main.py")
            print(f"📐 Alla ikoner ska nu ha bättre kvalitet utan avklippning!")
        
        if self.stats['failed'] > 0:
            print(f"")
            print(f"⚠️ Några konverteringar misslyckades.")
            print(f"🔍 Kontrollera log-meddelanden ovan för detaljer.")
        
        print(f"="*60)
    
    def restore_from_backup(self):
        """Återställ från senaste backup (för felsökning)"""
        print(f"🔄 Återställer från backup: {self.backup_dir}")
        
        try:
            restored = 0
            for backup_file in self.backup_dir.rglob('*.png'):
                # Räkna ut original-sökväg
                relative_path = backup_file.relative_to(self.backup_dir)
                original_path = self.icons_dir / relative_path
                
                if original_path.exists():
                    shutil.copy2(backup_file, original_path)
                    restored += 1
            
            print(f"✅ Återställde {restored} filer från backup")
            
        except Exception as e:
            print(f"❌ Återställning misslyckades: {e}")


def main():
    """Huvudfunktion"""
    print("🎨 Weather Icons SVG→PNG Converter")
    print("Ersätter felkonverterade PNG-filer med korrekta SVG-baserade versioner\n")
    
    try:
        # Skapa konverterare
        converter = WeatherIconsSVGConverter()
        
        # Fråga användaren om endast kritiska eller alla
        print("ÅTERSTÅENDE KONVERTERINGAR:")
        print("1. ⚠️ Pressure-pilar redan gjorda - hoppa över")
        print("2. System-ikoner (~85 filer: barometer, refresh, tid-ikoner)")
        print("3. Sol-ikoner (6 filer: sunrise, sunset)")
        print("4. Weather-ikoner (~78 filer: alla väder-PNG)")
        print("5. ALLA återstående (alternativ 2+3+4 = ~169 filer)")
        
        while True:
            choice = input("\nVälj (2/3/4/5): ").strip().lower()
            
            if choice in ['1', 'pressure']:
                print("⚠️ Pressure-pilar redan konverterade! Välj 2-5 för resten.")
                continue
            elif choice in ['2', 'system']:
                print("🔧 Startar konvertering av system-ikoner...")
                converter.run_conversion(categories=['system'])
                break
            elif choice in ['3', 'sol', 'sun']:
                print("☀️ Startar konvertering av sol-ikoner...")
                converter.run_conversion(categories=['sun'])
                break
            elif choice in ['4', 'weather', 'väder']:
                print("🌤️ Startar konvertering av weather-ikoner...")
                converter.run_conversion(categories=['weather'])
                break
            elif choice in ['5', 'alla', 'all', 'allt']:
                print("🌍 Startar konvertering av ALLA återstående ikoner...")
                converter.run_conversion(categories=['system', 'sun', 'weather'])
                break
            else:
                print(f"❌ Ogiltigt val: '{choice}'")
                print("💡 Ange 2 (system), 3 (sol), 4 (weather), eller 5 (alla återstående)")
    
    except KeyboardInterrupt:
        print("\n⚠️ Konvertering avbruten av användare")
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
