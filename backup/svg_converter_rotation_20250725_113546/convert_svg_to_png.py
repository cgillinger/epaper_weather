#!/usr/bin/env python3
"""
Weather Icons SVG → PNG Konvertering - MED HÖGRE UPPLÖSNINGAR
Ersätter befintliga felkonverterade PNG-filer med korrekta SVG-baserade versioner
Skapar även nya högre upplösningar (64x64, 80x80, 120x120) för bättre kvalitet
Löser pixling-problemet genom att använda SVG-källor direkt
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
    """Konverterar SVG till PNG med exakt överskrivning av befintliga filer PLUS högre upplösningar"""
    
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
            'new_created': 0,
            'skipped': 0,
            'failed': 0,
            'backed_up': 0
        }
        
        print(f"🎨 Weather Icons SVG→PNG Converter - HÖGRE UPPLÖSNINGAR")
        print(f"📁 SVG källa: {self.svg_base_dir}")
        print(f"📁 PNG mål: {self.icons_dir}")
        print(f"💾 Backup: {self.backup_dir}")
        print(f"🚀 Skapar även nya storlekar: 64x64, 80x80, 96x96, 120x120")
    
    def get_conversion_mapping(self):
        """
        Definiera mappning från SVG till PNG-filer - NU MED HÖGRE UPPLÖSNINGAR
        Inkluderar befintliga storlekar + nya större varianter
        """
        return {
            # KRITISKA PRESSURE-PILAR (löser avklippning + högre upplösning)
            'pressure': {
                'wi-direction-up': [
                    # Befintliga
                    (56, 56, ''), (20, 20, '_20'),
                    # NYA högre upplösningar
                    (96, 96, '_96'), (120, 120, '_120')
                ],
                'wi-direction-down': [
                    (56, 56, ''), (20, 20, '_20'),
                    (96, 96, '_96'), (120, 120, '_120')
                ],
                'wi-direction-right': [
                    (56, 56, ''), (20, 20, '_20'),
                    (96, 96, '_96'), (120, 120, '_120')
                ]
            },
            
            # SYSTEM-IKONER - UTÖKADE STORLEKAR
            'system': {
                'wi-barometer': [
                    # Befintliga
                    (48, 48, ''), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (64, 64, '_64'),
                    # NYA storlekar
                    (80, 80, '_80'), (96, 96, '_96')
                ],
                'wi-refresh': [
                    (24, 24, ''), (16, 16, '_16'), (12, 12, '_12'),
                    # NYA storlekar
                    (32, 32, '_32'), (48, 48, '_48')
                ],
                'wi-strong-wind': [
                    (24, 24, ''), (16, 16, '_16'), (12, 12, '_12'),
                    (32, 32, '_32'), (48, 48, '_48')
                ],
                'wi-na': [
                    (24, 24, ''), (16, 16, '_16'), (12, 12, '_12'),
                    (32, 32, '_32'), (48, 48, '_48')
                ],
                'wi-day-sunny': [
                    (24, 24, ''), (16, 16, '_16'), (12, 12, '_12'),
                    (32, 32, '_32'), (48, 48, '_48')
                ],
                
                # TID-IKONER (12 stycken, utökade storlekar)
                'wi-time-1': [
                    (64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'),
                    # NYA storlekar
                    (80, 80, '_80'), (96, 96, '_96')
                ],
                'wi-time-2': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-3': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-4': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-5': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-6': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-7': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-8': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-9': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-10': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-11': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')],
                'wi-time-12': [(64, 64, '_64'), (48, 48, '_48'), (32, 32, '_32'), (24, 24, '_24'), (16, 16, '_16'), (12, 12, '_12'), (80, 80, '_80'), (96, 96, '_96')]
            },
            
            # SOL-IKONER - STÖRRE STORLEKAR
            'sun': {
                'wi-sunrise': [
                    # Befintliga
                    (40, 40, ''), (24, 24, '_24'),
                    # NYA storlekar för bättre kvalitet
                    (56, 56, '_56'), (80, 80, '_80')
                ],
                'wi-sunset': [
                    (40, 40, ''), (24, 24, '_24'),
                    (56, 56, '_56'), (80, 80, '_80')
                ],
                'wi-day-sunny': [
                    (40, 40, ''), (24, 24, '_24'),
                    (56, 56, '_56'), (80, 80, '_80')
                ]
            },
            
            # WEATHER-IKONER - HÖGRE UPPLÖSNINGAR FÖR HERO-MODULEN
            'weather': {
                'wi-cloud': [
                    # Befintliga
                    (48, 48, ''), (32, 32, '_32'),
                    # NYA storlekar för hero-modulen och bättre kvalitet
                    (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')
                ],
                'wi-cloudy': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-cloudy': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-cloudy-high': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-rain': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-rain-mix': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-showers': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-sleet': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-snow': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-sunny': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-sunny-overcast': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-day-thunderstorm': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-fog': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-alt-cloudy': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-clear': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-cloudy-high': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-partly-cloudy': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-rain': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-rain-mix': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-showers': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-sleet': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-snow': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-night-thunderstorm': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-rain': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-rain-mix': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-sleet': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-snow': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-thunderstorm': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')],
                'wi-na': [(48, 48, ''), (32, 32, '_32'), (64, 64, '_64'), (80, 80, '_80'), (96, 96, '_96'), (120, 120, '_120')]
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
    
    def convert_svg_to_png(self, svg_path, png_path, width, height, is_new_size=False):
        """
        Konvertera SVG till PNG med given storlek
        
        Args:
            svg_path: Sökväg till SVG-fil
            png_path: Sökväg för PNG-utdata
            width, height: Mål-storlek
            is_new_size: Om detta är en ny storlek (inte ersättning)
            
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
            
            status = "🆕 SKAPAD" if is_new_size else "✅ KONVERTERAD"
            self.logger.debug(f"{status}: {svg_path.name} → {png_path.name} ({width}×{height})")
            
            if is_new_size:
                self.stats['new_created'] += 1
            else:
                self.stats['converted'] += 1
                
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
        FÖRBÄTTRAD för högre upplösningar
        
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
            
            # E-Paper optimering - FÖRBÄTTRAD för högre upplösningar
            # Dynamisk kontrast baserat på storlek
            size = max(image.size)
            if size >= 96:
                # Högre upplösning: mindre aggressiv kontrast för att bevara detaljer
                contrast_factor = 2.0
                sharpness_factor = 1.3
            elif size >= 64:
                # Medium upplösning
                contrast_factor = 2.1
                sharpness_factor = 1.4
            else:
                # Låg upplösning: mer aggressiv för tydlighet
                contrast_factor = 2.3
                sharpness_factor = 1.5
            
            # Öka kontrast
            contrast_enhancer = ImageEnhance.Contrast(image)
            image = contrast_enhancer.enhance(contrast_factor)
            
            # Förbättra skärpa
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(sharpness_factor)
            
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
        category_stats = {'converted': 0, 'new_created': 0, 'skipped': 0, 'failed': 0}
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
                
                # Kontrollera om detta är en befintlig eller ny storlek
                is_new_size = not png_path.exists()
                
                if not is_new_size:
                    # Backup befintlig PNG
                    if not self.backup_existing_png(png_path):
                        category_stats['failed'] += 1
                        continue
                
                # Konvertera SVG → PNG
                if self.convert_svg_to_png(svg_path, png_path, width, height, is_new_size):
                    if is_new_size:
                        category_stats['new_created'] += 1
                        print(f"  🆕 {icon_name}{suffix}.png ({width}×{height}) - NY STORLEK")
                    else:
                        category_stats['converted'] += 1
                        print(f"  ✅ {icon_name}{suffix}.png ({width}×{height}) - FÖRBÄTTRAD")
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
        self.stats = {'converted': 0, 'new_created': 0, 'skipped': 0, 'failed': 0, 'backed_up': 0}
        
        print(f"🚀 Startar SVG→PNG konvertering MED HÖGRE UPPLÖSNINGAR")
        print(f"📂 Kategorier: {', '.join(categories)}")
        print(f"🎯 Nya storlekar: 64x64, 80x80, 96x96, 120x120")
        
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
        print(f"🎨 SVG→PNG KONVERTERING MED HÖGRE UPPLÖSNINGAR SLUTFÖRD!")
        print(f"📂 Kategorier: {', '.join(categories)}")
        print(f"⏱️ Tid: {duration.total_seconds():.1f} sekunder")
        print(f"")
        print(f"📊 RESULTAT:")
        print(f"  ✅ Förbättrade: {self.stats['converted']} PNG-filer")
        print(f"  🆕 Nya storlekar: {self.stats['new_created']} PNG-filer")
        print(f"  ⏭️ Hoppade över: {self.stats['skipped']} filer")
        print(f"  ❌ Misslyckades: {self.stats['failed']} filer")
        print(f"  💾 Backup: {self.stats['backed_up']} filer")
        print(f"")
        print(f"🎯 NYA STORLEKAR SKAPADE:")
        
        if 'weather' in categories:
            print(f"  🌤️ Weather-ikoner: Nu tillgängliga i 32, 48, 64, 80, 96, 120px")
        if 'pressure' in categories:
            print(f"  ↗️ Pressure-pilar: Nu tillgängliga i 20, 56, 96, 120px")
        if 'system' in categories:
            print(f"  📊 System-ikoner: Barometer tillgänglig i upp till 96px")
        if 'sun' in categories:
            print(f"  ☀️ Sol-ikoner: Nu tillgängliga i 24, 40, 56, 80px")
        
        print(f"")
        print(f"📁 Backup sparad i: {self.backup_dir}")
        
        if self.stats['converted'] + self.stats['new_created'] > 0:
            print(f"")
            print(f"🔧 NÄSTA STEG:")
            print(f"1. Testa: cd ~/epaper_weather && python3 main.py")
            print(f"2. Nu kan main.py använda högre upplösningar:")
            print(f"   - HERO väderikon: 96x96 eller 120x120 (ej pixlig!)")
            print(f"   - Prognos väderikon: 64x64 eller 80x80")
            print(f"   - Barometer: 80x80 eller 96x96")
            print(f"   - Trycktrend-pil: 96x96 eller 120x120")
            print(f"")
            print(f"💡 PERFEKT KVALITET: Alla ikoner från SVG-källor!")
        
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
    print("🎨 Weather Icons SVG→PNG Converter - HÖGRE UPPLÖSNINGAR")
    print("Skapar nya storlekar: 64x64, 80x80, 96x96, 120x120 från SVG-källor\n")
    
    try:
        # Skapa konverterare
        converter = WeatherIconsSVGConverter()
        
        # Fråga användaren om vad som ska konverteras
        print("TILLGÄNGLIGA KONVERTERINGAR:")
        print("1. 🌤️ Weather-ikoner (~30 ikoner × 6 storlekar = ~180 filer)")
        print("2. ↗️ Pressure-pilar (3 ikoner × 4 storlekar = 12 filer)")
        print("3. 📊 System-ikoner (~85 ikoner, utökade storlekar)")
        print("4. ☀️ Sol-ikoner (3 ikoner × 4 storlekar = 12 filer)")
        print("5. 🌍 ALLA kategorier (alla nya storlekar)")
        print("6. 🎯 BARA HERO-IKONER (weather + pressure för HERO-modulen)")
        
        while True:
            choice = input("\nVälj (1-6): ").strip().lower()
            
            if choice in ['1', 'weather', 'väder']:
                print("🌤️ Startar konvertering av weather-ikoner med högre upplösningar...")
                converter.run_conversion(categories=['weather'])
                break
            elif choice in ['2', 'pressure', 'tryck']:
                print("↗️ Startar konvertering av pressure-pilar med högre upplösningar...")
                converter.run_conversion(categories=['pressure'])
                break
            elif choice in ['3', 'system']:
                print("📊 Startar konvertering av system-ikoner med utökade storlekar...")
                converter.run_conversion(categories=['system'])
                break
            elif choice in ['4', 'sol', 'sun']:
                print("☀️ Startar konvertering av sol-ikoner med högre upplösningar...")
                converter.run_conversion(categories=['sun'])
                break
            elif choice in ['5', 'alla', 'all', 'allt']:
                print("🌍 Startar konvertering av ALLA kategorier med högre upplösningar...")
                converter.run_conversion(categories=['weather', 'pressure', 'system', 'sun'])
                break
            elif choice in ['6', 'hero']:
                print("🎯 Startar konvertering av HERO-ikoner (weather + pressure)...")
                converter.run_conversion(categories=['weather', 'pressure'])
                break
            else:
                print(f"❌ Ogiltigt val: '{choice}'")
                print("💡 Ange 1-6 eller weather/pressure/system/sun/alla/hero")
    
    except KeyboardInterrupt:
        print("\n⚠️ Konvertering avbruten av användare")
    except Exception as e:
        print(f"❌ Kritiskt fel: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
