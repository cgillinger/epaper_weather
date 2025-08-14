#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Kontinuerlig väderstation med DYNAMIC MODULE SYSTEM
Raspberry Pi 3B + Waveshare 4.26" E-Paper HAT (800×480)

NYT: DYNAMIC MODULE SYSTEM (Fas 1)
- DynamicModuleManager: Trigger-baserad modulhantering
- TriggerEvaluator: Säker condition evaluation
- Module Groups: Villkorsbaserade layout-ändringar
- Generell arkitektur för framtida moduler

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
from typing import Dict, Optional, List, Any
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


class TriggerEvaluator:
    """
    Säker evaluering av trigger-conditions för Dynamic Module System
    
    Stöder conditions som: "precipitation > 0 OR forecast_precipitation_2h > 0.2"
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TriggerEvaluator")
        
        # Whitelisted functions för säker evaluation
        self.safe_functions = {
            'precipitation': self._get_precipitation,
            'forecast_precipitation_2h': self._get_forecast_precipitation_2h,
            'temperature': self._get_temperature,
            'wind_speed': self._get_wind_speed,
            'pressure_trend': self._get_pressure_trend,
            'time_hour': self._get_current_hour,
            'time_month': self._get_current_month,
            'user_preference': self._get_user_preference,
            'is_daylight': self._get_is_daylight
        }
    
    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Säkert evaluera trigger-condition med whitelisted functions
        
        Args:
            condition: Condition string (t.ex. "precipitation > 0 OR temperature < 5")
            context: Context data för evaluation
            
        Returns:
            True om condition är uppfylld, False annars
        """
        try:
            if not condition or not isinstance(condition, str):
                return False
            
            # Ersätt function calls med värden
            evaluated_condition = self._replace_functions_with_values(condition, context)
            
            # Säker evaluation av logisk expression
            result = self._safe_eval_logic(evaluated_condition)
            
            self.logger.debug(f"🎯 Trigger condition: '{condition}' → '{evaluated_condition}' → {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid trigger evaluation: {condition} - {e}")
            return False
    
    def _replace_functions_with_values(self, condition: str, context: Dict) -> str:
        """Ersätt function calls med faktiska värden"""
        import re
        result = condition
        
        # Sortera functions efter längd (längsta först) för att undvika partiella ersättningar
        sorted_functions = sorted(self.safe_functions.items(), key=lambda x: len(x[0]), reverse=True)
        
        for func_name, func in sorted_functions:
            # Använd word boundaries för exakt matchning
            pattern = r'\b' + re.escape(func_name) + r'\b'
            if re.search(pattern, result):
                try:
                    value = func(context)
                    # Ersätt HELA function name med värdet
                    result = re.sub(pattern, str(value), result)
                    self.logger.debug(f"🔄 Replaced {func_name} → {value}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Function {func_name} fel: {e}")
                    result = re.sub(pattern, "0", result)  # Fallback
        
        return result
    
    def _safe_eval_logic(self, expression: str) -> bool:
        """
        Säker evaluation av logisk expression
        Endast tillåter: numbers, operators (>, <, >=, <=, ==, !=), AND, OR, NOT, ()
        """
        try:
            # Whitelist för tillåtna tokens
            allowed_chars = set('0123456789.<>=!() ')
            allowed_words = {'AND', 'OR', 'NOT', 'True', 'False'}
            
            # Ersätt logiska operatorer med Python syntax
            expression = expression.replace(' AND ', ' and ')
            expression = expression.replace(' OR ', ' or ')
            expression = expression.replace(' NOT ', ' not ')
            
            # Kontrollera att endast säkra tokens används
            tokens = expression.split()
            for token in tokens:
                if not (all(c in allowed_chars for c in token) or token in allowed_words or token in ['and', 'or', 'not']):
                    self.logger.warning(f"⚠️ Osäker token i expression: {token}")
                    return False
            
            # Evaluera expression
            result = eval(expression)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid logic evaluation: {expression} - {e}")
            return False
    
    # Whitelisted functions för context data
    def _get_precipitation(self, context: Dict) -> float:
        """Hämta aktuell nederbörd från context"""
        return float(context.get('precipitation', 0.0))
    
    def _get_forecast_precipitation_2h(self, context: Dict) -> float:
        """Hämta prognostiserad nederbörd kommande 2h"""
        return float(context.get('forecast_precipitation_2h', 0.0))
    
    def _get_temperature(self, context: Dict) -> float:
        """Hämta temperatur från context"""
        return float(context.get('temperature', 20.0))
    
    def _get_wind_speed(self, context: Dict) -> float:
        """Hämta vindstyrka från context"""
        return float(context.get('wind_speed', 0.0))
    
    def _get_pressure_trend(self, context: Dict) -> str:
        """Hämta trycktrend från context"""
        return str(context.get('pressure_trend_arrow', 'stable'))
    
    def _get_current_hour(self, context: Dict) -> int:
        """Hämta aktuell timme"""
        return datetime.now().hour
    
    def _get_current_month(self, context: Dict) -> int:
        """Hämta aktuell månad"""
        return datetime.now().month
    
    def _get_user_preference(self, context: Dict) -> str:
        """Hämta användarpreferens från context"""
        return str(context.get('user_preferences', {}).get('module_preference', 'normal'))
    
    def _get_is_daylight(self, context: Dict) -> bool:
        """Kontrollera om det är dagsljus"""
        return bool(context.get('is_daylight', True))


class DynamicModuleManager:
    """
    Hanterar dynamiska moduler baserat på triggers och module groups
    
    Kärnkomponent i Dynamic Module System för villkorsbaserade layout-ändringar
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DynamicModuleManager")
        
        # Läs ny config-struktur med fallback till legacy
        self.module_groups = config.get('module_groups', {})
        self.triggers = config.get('triggers', {})
        self.legacy_modules = config.get('modules', {})
        
        # Trigger evaluator för condition evaluation
        self.trigger_evaluator = TriggerEvaluator()
        
        # State tracking för layout-ändringar
        self.current_active_groups = {}
        self.last_trigger_evaluation = 0
        
        self.logger.info(f"🔄 DynamicModuleManager initierad")
        self.logger.info(f"   📊 Module groups: {len(self.module_groups)}")
        self.logger.info(f"   🎯 Triggers: {len(self.triggers)}")
        
        # Log loaded triggers för debugging (skippa kommentarer)
        for trigger_name, trigger_config in self.triggers.items():
            # Skippa kommentarer som börjar med "_"
            if trigger_name.startswith('_') or not isinstance(trigger_config, dict):
                continue
            condition = trigger_config.get('condition', 'N/A')
            self.logger.info(f"   🎯 {trigger_name}: '{condition}'")
    
    def evaluate_triggers(self, context_data: Dict) -> Dict[str, str]:
        """
        Evaluera alla triggers och returnera aktiva module groups
        
        Args:
            context_data: Väderdata, användarpref, tid, etc.
            
        Returns:
            Dict med section → active group mapping
            Exempel: {"bottom_section": "precipitation_active", "side_panel": "normal"}
        """
        try:
            active_groups = {}
            
            # Börja med default groups (normal för alla sections)
            for section_name, groups in self.module_groups.items():
                if 'normal' in groups:
                    active_groups[section_name] = 'normal'
                else:
                    # Använd första tillgängliga group som default
                    first_group = list(groups.keys())[0] if groups else None
                    if first_group:
                        active_groups[section_name] = first_group
            
            # Evaluera triggers med priority-ordning (skippa kommentarer)
            triggers_by_priority = sorted(
                [(name, config) for name, config in self.triggers.items() 
                 if not name.startswith('_') and isinstance(config, dict)],
                key=lambda x: x[1].get('priority', 50),
                reverse=True  # Högsta priority först
            )
            
            for trigger_name, trigger_config in triggers_by_priority:
                try:
                    condition = trigger_config.get('condition', '')
                    target_section = trigger_config.get('target_section', '')
                    activate_group = trigger_config.get('activate_group', '')
                    
                    if not all([condition, target_section, activate_group]):
                        self.logger.warning(f"⚠️ Ofullständig trigger config: {trigger_name}")
                        continue
                    
                    # Evaluera condition
                    if self.trigger_evaluator.evaluate_condition(condition, context_data):
                        # Trigger är aktiv → aktivera group
                        active_groups[target_section] = activate_group
                        self.logger.info(f"🎯 Trigger aktiverad: {trigger_name} → {target_section}.{activate_group}")
                    else:
                        self.logger.debug(f"🎯 Trigger inaktiv: {trigger_name}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Fel vid trigger evaluation: {trigger_name} - {e}")
                    continue
            
            self.current_active_groups = active_groups
            self.last_trigger_evaluation = time.time()
            
            return active_groups
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid trigger evaluation: {e}")
            # Fallback: alla sections till normal
            return {section: 'normal' for section in self.module_groups.keys()}
    
    def get_active_modules(self, context_data: Dict) -> List[str]:
        """
        Returnera lista av moduler som ska renderas baserat på aktiva groups
        
        Args:
            context_data: Context data för trigger evaluation
            
        Returns:
            Lista av modulnamn som ska renderas
        """
        try:
            # Evaluera triggers för att få aktiva groups
            active_groups = self.evaluate_triggers(context_data)
            
            active_modules = []
            
            # Samla moduler från aktiva groups
            for section_name, active_group in active_groups.items():
                if section_name in self.module_groups:
                    section_groups = self.module_groups[section_name]
                    if active_group in section_groups:
                        group_modules = section_groups[active_group]
                        active_modules.extend(group_modules)
                        self.logger.debug(f"📊 Section {section_name}: {active_group} → {group_modules}")
            
            # Fallback: använd legacy modules om inga groups är definierade
            if not active_modules and self.legacy_modules:
                active_modules = [name for name, config in self.legacy_modules.items() if config.get('enabled', False)]
                self.logger.info("🔄 Använder legacy modules (inga groups definierade)")
            
            self.logger.info(f"🎯 Aktiva moduler: {active_modules}")
            return active_modules
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av aktiva moduler: {e}")
            # Fallback: legacy modules
            return [name for name, config in self.legacy_modules.items() if config.get('enabled', False)]
    
    def get_current_layout_state(self, context_data: Dict) -> Dict[str, Any]:
        """
        Få aktuellt layout-state för change detection
        
        Args:
            context_data: Context data för trigger evaluation
            
        Returns:
            Dict med layout state information
        """
        active_groups = self.evaluate_triggers(context_data)
        active_modules = self.get_active_modules(context_data)
        
        return {
            'active_groups': active_groups,
            'active_modules': active_modules,
            'trigger_evaluation_time': self.last_trigger_evaluation
        }
    
    def should_layout_update(self, context_data: Dict, last_layout_state: Dict) -> tuple:
        """
        Kontrollera om layout har ändrats sedan senast
        
        Args:
            context_data: Aktuell context data
            last_layout_state: Tidigare layout state
            
        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            current_layout_state = self.get_current_layout_state(context_data)
            
            if not last_layout_state:
                return True, "Första layout evaluation"
            
            # Jämför aktiva groups
            last_groups = last_layout_state.get('active_groups', {})
            current_groups = current_layout_state.get('active_groups', {})
            
            if last_groups != current_groups:
                changes = []
                for section in set(list(last_groups.keys()) + list(current_groups.keys())):
                    last_group = last_groups.get(section, 'none')
                    current_group = current_groups.get(section, 'none')
                    if last_group != current_group:
                        changes.append(f"{section}: {last_group}→{current_group}")
                
                return True, f"Layout-ändring: {', '.join(changes)}"
            
            # Jämför aktiva moduler
            last_modules = set(last_layout_state.get('active_modules', []))
            current_modules = set(current_layout_state.get('active_modules', []))
            
            if last_modules != current_modules:
                added = current_modules - last_modules
                removed = last_modules - current_modules
                changes = []
                if added:
                    changes.append(f"Tillagda: {', '.join(added)}")
                if removed:
                    changes.append(f"Borttagna: {', '.join(removed)}")
                
                return True, f"Modul-ändring: {'; '.join(changes)}"
            
            return False, "Ingen layout-ändring"
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid layout change detection: {e}")
            return True, f"Fel vid layout-kontroll: {e}"
    
    def build_trigger_context(self, weather_data: Dict) -> Dict[str, Any]:
        """
        Bygg komplett context för trigger evaluation
        
        Args:
            weather_data: Väderdata från weather_client
            
        Returns:
            Dict med all context data för triggers
        """
        try:
            now = datetime.now()
            
            # Extrahera cykel-väder data om tillgängligt
            cycling_weather = weather_data.get('cycling_weather', {})
            
            context = {
                # Väderdata
                'precipitation': weather_data.get('precipitation', 0.0),
                'forecast_precipitation_2h': cycling_weather.get('precipitation_mm', 0.0),  # Från cykel-väder analys
                'temperature': weather_data.get('temperature', 20.0),
                'wind_speed': weather_data.get('wind_speed', 0.0),
                'pressure_trend_arrow': weather_data.get('pressure_trend_arrow', 'stable'),
                
                # Temporal context  
                'time_hour': now.hour,
                'time_month': now.month,
                'time_weekday': now.weekday(),
                'is_daylight': self._determine_daylight(weather_data),
                
                # User context (från config)
                'user_preferences': self.config.get('user_preferences', {}),
                
                # System context
                'display_mode': self.config.get('display_mode', 'normal'),
                'debug_mode': self.config.get('debug', {}).get('enabled', False)
            }
            
            self.logger.debug(f"🌐 Trigger context: precipitation={context['precipitation']}, forecast_2h={context['forecast_precipitation_2h']}")
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid context building: {e}")
            return {}
    
    def _determine_daylight(self, weather_data: Dict) -> bool:
        """Bestäm om det är dagsljus baserat på soldata"""
        try:
            sun_data = weather_data.get('sun_data', {})
            sunrise_time = weather_data.get('parsed_sunrise')
            sunset_time = weather_data.get('parsed_sunset')
            
            if sunrise_time and sunset_time:
                now = datetime.now()
                return sunrise_time <= now <= sunset_time
            else:
                # Fallback: 06:00-18:00 = dagsljus
                hour = datetime.now().hour
                return 6 <= hour <= 18
                
        except Exception as e:
            self.logger.warning(f"⚠️ Fel vid dagsljus-bestämning: {e}")
            return True  # Default till dagsljus


class EPaperWeatherDaemon:
    """E-Paper Weather Daemon - Kontinuerlig väderstation med DYNAMIC MODULE SYSTEM + smart state-hantering"""
    
    def __init__(self, config_path="config.json"):
        """Initialisera daemon med Dynamic Module System"""
        print("🌤️ E-Paper Weather Daemon - Startar med DYNAMIC MODULE SYSTEM...")
        
        # Daemon control
        self.running = True
        self.update_interval = 60  # 1 minut mellan kontroller
        self.watchdog_interval = 30 * 60  # 30 minuter watchdog
        
        # STATE I MINNET (utökat med layout state)
        self.current_display_state = None  # Perfekt state-hantering!
        self.current_layout_state = None   # NYT: Layout state tracking
        self.last_update_time = 0
        
        # Ladda konfiguration
        self.config = self.load_config(config_path)
        if not self.config:
            sys.exit(1)
        
        # Setup logging för daemon
        self.setup_logging()
        
        # NYT: Dynamic Module Manager
        self.module_manager = DynamicModuleManager(self.config)
        
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
        
        self.logger.info("🌤️ E-Paper Weather Daemon initialiserad med DYNAMIC MODULE SYSTEM")
        self.logger.info("🔄 Nya funktioner: Trigger-baserade moduler, Layout change detection")
    
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
        DAEMON STATE JÄMFÖRELSE + LAYOUT CHANGE DETECTION
        Samma logik som original men UTÖKAT med Dynamic Module System
        
        Args:
            weather_data: Ny väderdata
            
        Returns:
            Tuple (should_update: bool, reason: str)
        """
        try:
            # NYT: Kontrollera layout-ändringar FÖRST (högsta prioritet)
            trigger_context = self.module_manager.build_trigger_context(weather_data)
            layout_changed, layout_reason = self.module_manager.should_layout_update(
                trigger_context, self.current_layout_state
            )
            
            if layout_changed:
                return True, f"LAYOUT: {layout_reason}"
            
            # BEFINTLIG LOGIK: Första körningen
            if self.current_display_state is None:
                return True, "Daemon första körning"
            
            # BEFINTLIG LOGIK: Watchdog
            time_since_last = time.time() - self.last_update_time
            if time_since_last > self.watchdog_interval:
                return True, f"30-min watchdog ({time_since_last/60:.1f} min)"
            
            # BEFINTLIG LOGIK: Datum-ändring
            current_date = datetime.now().strftime('%Y-%m-%d')
            last_date = self.current_display_state.get('date', '')
            if current_date != last_date:
                return True, f"Nytt datum: {last_date} → {current_date}"
            
            # BEFINTLIG LOGIK: Väderdata-jämförelse
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
        """Hämta väderdata (samma som original)"""
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
        """Parsea soldata (kopierat från original)"""
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
        """Rendera och visa på E-Paper display med DYNAMIC MODULE SYSTEM"""
        try:
            self.logger.info("🎨 Renderar ny layout med Dynamic Module System...")
            
            # NYT: Bygg trigger context
            trigger_context = self.module_manager.build_trigger_context(weather_data)
            
            # NYT: Hämta aktiva moduler från Dynamic Module Manager
            active_modules = self.module_manager.get_active_modules(trigger_context)
            
            # FULLSTÄNDIG RENDERING - kopierat från original MEN med dynamiska moduler
            self.clear_canvas()
            
            # Hämta parsade soltider från weather_data
            sunrise = weather_data.get('parsed_sunrise')
            sunset = weather_data.get('parsed_sunset')
            sun_data = weather_data.get('parsed_sun_data', {})
            
            # Aktuell tid för dag/natt-bestämning
            current_time = datetime.now()
            
            # NYT: Rita ENDAST aktiva moduler (istället för alla enabled modules)
            for module_name in active_modules:
                if module_name not in self.config['modules']:
                    self.logger.warning(f"⚠️ Okänd modul: {module_name}")
                    continue
                
                module_config = self.config['modules'][module_name]
                x = module_config['coords']['x']
                y = module_config['coords']['y'] 
                width = module_config['size']['width']
                height = module_config['size']['height']
                
                # Rita modulram
                self.draw_module_border(x, y, width, height, module_name)
                
                # NYT: Modulspecifik rendering med stöd för nya modultyper
                if module_name == 'precipitation_module':
                    # NYT: Nederbörd-modul rendering
                    self.render_precipitation_module(x, y, width, height, weather_data, trigger_context)
                
                elif module_name == 'main_weather':
                    # BEFINTLIG: Hero-modul (oförändrad)
                    self.render_main_weather_module(x, y, width, height, weather_data, sun_data, current_time)
                
                elif module_name == 'barometer_module':
                    # BEFINTLIG: Barometer-modul (oförändrad)
                    self.render_barometer_module(x, y, width, height, weather_data)
                
                elif module_name == 'tomorrow_forecast':
                    # BEFINTLIG: Prognos-modul (oförändrad)
                    self.render_tomorrow_forecast_module(x, y, width, height, weather_data)
                
                elif module_name == 'clock_module':
                    # BEFINTLIG: Klock-modul (oförändrad)
                    self.render_clock_module(x, y, width, height)
                
                elif module_name == 'status_module':
                    # BEFINTLIG: Status-modul (modifierad för dynamic status)
                    self.render_status_module(x, y, width, height, weather_data, active_modules)
                
                else:
                    # NYT: Okänd modul → fallback rendering
                    self.render_unknown_module(x, y, width, height, module_name)
            
            # Visa på display
            if self.epd and not self.config['debug']['test_mode']:
                self.epd.display(self.epd.getbuffer(self.canvas))
                self.logger.info("✅ E-Paper display uppdaterad med Dynamic Module System")
            else:
                self.logger.info("🧪 Test-läge: Display simulering")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid rendering: {e}")
            raise
    
    def render_precipitation_module(self, x, y, width, height, weather_data, trigger_context):
        """
        NYT: Rendera nederbörd-modul
        Första implementation av Dynamic Module System
        """
        try:
            # Hämta nederbörd-data
            precipitation = trigger_context.get('precipitation', 0.0)
            forecast_2h = trigger_context.get('forecast_precipitation_2h', 0.0)
            cycling_weather = weather_data.get('cycling_weather', {})
            
            # Varningsikon (!) för nederbörd
            self.draw.text((x + 15, y + 15), "⚠️", font=self.fonts['medium_main'], fill=0)
            
            # Huvudtext baserat på timing
            if precipitation > 0:
                main_text = f"Regnar nu: {precipitation:.1f}mm/h"
                status_text = "Vänta med cykling"
            elif forecast_2h > 0:
                main_text = f"Regn väntat: {forecast_2h:.1f}mm/h"
                
                # Timing från cykel-väder analys
                forecast_time = cycling_weather.get('forecast_time', 'snart')
                status_text = f"Startar kl {forecast_time}"
            else:
                main_text = "Nederbörd detekterad"
                status_text = "Kontrollera prognos"
            
            # Rita huvudtext
            main_text_truncated = self.truncate_text(main_text, self.fonts['small_main'], width - 80)
            self.draw.text((x + 60, y + 20), main_text_truncated, font=self.fonts['small_main'], fill=0)
            
            # Rita status/timing
            status_text_truncated = self.truncate_text(status_text, self.fonts['small_desc'], width - 40)
            self.draw.text((x + 20, y + 50), status_text_truncated, font=self.fonts['small_desc'], fill=0)
            
            # Intensitet/typ-beskrivning (om tillgänglig)
            precip_description = cycling_weather.get('precipitation_description', '')
            if precip_description and precip_description != 'Inget regn':
                desc_truncated = self.truncate_text(precip_description, self.fonts['tiny'], width - 40)
                self.draw.text((x + 20, y + 70), desc_truncated, font=self.fonts['tiny'], fill=0)
            
            self.logger.info(f"🌧️ Nederbörd-modul renderad: {main_text}")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid nederbörd-modul rendering: {e}")
            # Fallback: visa bara text
            self.draw.text((x + 20, y + 30), "Nederbörd-info", font=self.fonts['small_main'], fill=0)
            self.draw.text((x + 20, y + 60), "Fel vid datahämtning", font=self.fonts['small_desc'], fill=0)
    
    def render_main_weather_module(self, x, y, width, height, weather_data, sun_data, current_time):
        """BEFINTLIG: Hero-modul rendering (oförändrad från original)"""
        temp = weather_data.get('temperature', 20.0)
        desc = weather_data.get('weather_description', 'Okänt väder')
        temp_source = weather_data.get('temperature_source', 'fallback')
        location = weather_data.get('location', 'Okänd plats')
        smhi_symbol = weather_data.get('weather_symbol', 1)
        
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
        sunrise = weather_data.get('parsed_sunrise')
        sunset = weather_data.get('parsed_sunset')
        
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
    
    def render_barometer_module(self, x, y, width, height, weather_data):
        """BEFINTLIG: Barometer-modul rendering (oförändrad från original)"""
        pressure = weather_data.get('pressure', 1013)
        pressure_source = weather_data.get('pressure_source', 'unknown')
        pressure_trend = weather_data.get('pressure_trend', {})
        trend_text = weather_data.get('pressure_trend_text', 'Samlar data')
        trend_arrow = weather_data.get('pressure_trend_arrow', 'stable')
        
        # Barometer-ikon - HÖGUPPLÖST STORLEK (80x80)
        barometer_icon = self.icon_manager.get_system_icon('barometer', size=(80, 80))
        if barometer_icon:
            self.paste_icon_on_canvas(barometer_icon, x + 15, y + 20)
            self.draw.text((x + 100, y + 40), f"{int(pressure)}", font=self.fonts['medium_main'], fill=0)
            self.logger.info(f"📊 Barometer-ikon: 80x80 SVG-baserad")
        else:
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
            change_y = y + 175 if trend_text == 'Samlar data' else y + 150
            self.draw.text((x + 20, change_y), change_text, font=self.fonts['small_desc'], fill=0)
        
        # TREND-PIL från Weather Icons - OPTIMERAD STORLEK (64x64)
        trend_icon = self.icon_manager.get_pressure_icon(trend_arrow, size=(64, 64))
        if trend_icon:
            trend_x = x + width - 75
            trend_y = y + 100
            self.paste_icon_on_canvas(trend_icon, trend_x, trend_y)
            self.logger.info(f"↗️ Trycktrend-pil: 64x64 SVG-baserad ({trend_arrow})")
        
        # NYTT: Visa tryck-källa (diskret)
        if pressure_source == 'netatmo':
            self.draw.text((x + 20, y + height - 20), "(Netatmo)", font=self.fonts['tiny'], fill=0)
        elif pressure_source == 'smhi':
            self.draw.text((x + 20, y + height - 20), "(SMHI)", font=self.fonts['tiny'], fill=0)
    
    def render_tomorrow_forecast_module(self, x, y, width, height, weather_data):
        """BEFINTLIG: Prognos-modul rendering (oförändrad från original)"""
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
    
    def render_clock_module(self, x, y, width, height):
        """BEFINTLIG: Klock-modul rendering (oförändrad från original)"""
        now = datetime.now()
        
        # Hämta svenska datum-komponenter
        swedish_weekday, swedish_date = self.get_swedish_date(now)
        
        # Kalender-ikon för modern utseende (samma storlek)
        calendar_icon = self.icon_manager.get_system_icon('calendar', size=(40, 40))
        if calendar_icon:
            # Placera ikon till vänster
            self.paste_icon_on_canvas(calendar_icon, x + 15, y + 15)
            text_start_x = x + 65  # Text börjar efter ikon
        else:
            # Fallback: ingen ikon, text börjar tidigare
            text_start_x = x + 15
        
        # DATUM FÖRST I BRA STORLEK (small_main = 32px - lagom större än förut)
        date_truncated = self.truncate_text(swedish_date, self.fonts['small_main'], width - 80)
        self.draw.text((text_start_x, y + 15), date_truncated, font=self.fonts['small_main'], fill=0)
        
        # VECKODAG UNDER I BRA STORLEK (medium_desc = 24px - större men fortfarande mindre än datum)  
        weekday_truncated = self.truncate_text(swedish_weekday, self.fonts['medium_desc'], width - 80)
        self.draw.text((text_start_x, y + 50), weekday_truncated, font=self.fonts['medium_desc'], fill=0)
    
    def render_status_module(self, x, y, width, height, weather_data, active_modules):
        """MODIFIERAD: Status-modul med Dynamic Module System info"""
        update_time = datetime.now().strftime('%H:%M')
        
        # Status med enkla prickar
        dot_x = x + 10
        dot_size = 3
        
        # Status prick + text
        self.draw.ellipse([
            (dot_x, y + 28), 
            (dot_x + dot_size, y + 28 + dot_size)
        ], fill=0)
        self.draw.text((dot_x + 10, y + 20), "Dynamic: ✓", font=self.fonts['small_desc'], fill=0)
        
        # Update prick + text
        self.draw.ellipse([
            (dot_x, y + 53), 
            (dot_x + dot_size, y + 53 + dot_size)
        ], fill=0)
        self.draw.text((dot_x + 10, y + 45), f"Update: {update_time}", font=self.fonts['small_desc'], fill=0)
        
        # NYT: Visa aktiva moduler istället för bara datakällor
        modules_text = f"{len(active_modules)} moduler"
        self.draw.ellipse([
            (dot_x, y + 78), 
            (dot_x + dot_size, y + 78 + dot_size)
        ], fill=0)
        self.draw.text((dot_x + 10, y + 70), f"Layout: {modules_text}", font=self.fonts['small_desc'], fill=0)
    
    def render_unknown_module(self, x, y, width, height, module_name):
        """NYT: Fallback rendering för okända moduler"""
        self.logger.warning(f"⚠️ Okänd modul: {module_name} - använder fallback rendering")
        
        # Enkel fallback-rendering
        self.draw.text((x + 20, y + 30), f"Modul: {module_name}", font=self.fonts['small_main'], fill=0)
        self.draw.text((x + 20, y + 60), "Konfiguration saknas", font=self.fonts['small_desc'], fill=0)
    
    # === BEFINTLIGA HJÄLPMETODER (oförändrade från original) ===
    
    def clear_canvas(self):
        """Rensa canvas (vit bakgrund)"""
        self.draw.rectangle([(0, 0), (self.width, self.height)], fill=255)
    
    def draw_module_border(self, x, y, width, height, module_name):
        """Rita smarta modulramar som inte dubbleras (kopierat från original)"""
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
        elif module_name == 'precipitation_module':
            # NYT: Samma stil som clock/status moduler
            self.draw.line([(x, y), (x + width, y)], fill=0, width=2)
            self.draw.line([(x, y), (x, y + height)], fill=0, width=2)
            self.draw.line([(x, y + height), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + width, y), (x + width, y + height)], fill=0, width=2)
            self.draw.line([(x + 2, y + 2), (x + width - 2, y + 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + 2), (x + 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + 2, y + height - 2), (x + width - 2, y + height - 2)], fill=0, width=1)
            self.draw.line([(x + width - 2, y + 2), (x + width - 2, y + height - 2)], fill=0, width=1)
    
    def get_swedish_date(self, date_obj):
        """Konvertera datum till svenska veckodagar och månader (kopierat från original)"""
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
        """Korta text så den får plats inom given bredd (kopierat från original)"""
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
        """Sätt in ikon på canvas (kopierat från original)"""
        if icon is None:
            return
        
        try:
            self.canvas.paste(icon, (x, y))
        except Exception as e:
            self.logger.error(f"❌ Fel vid ikon-inplacering: {e}")
    
    def format_data_sources(self, weather_data: Dict) -> str:
        """Formatera datakällor för status-modulen (kopierat från original)"""
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
        """Uppdatera daemon state i minnet + LAYOUT STATE"""
        # BEFINTLIG state (oförändrad)
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
        
        # NYT: Layout state tracking
        trigger_context = self.module_manager.build_trigger_context(weather_data)
        self.current_layout_state = self.module_manager.get_current_layout_state(trigger_context)
        
        self.last_update_time = time.time()
    
    def run_daemon(self):
        """Huvudloop för daemon"""
        self.logger.info("🚀 Startar E-Paper Weather Daemon med DYNAMIC MODULE SYSTEM...")
        print("🚀 E-Paper Weather Daemon startad - Dynamic Module System aktiverat!")
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                self.logger.debug(f"🔄 Daemon iteration #{iteration}")
                
                try:
                    # Hämta väderdata
                    weather_data = self.fetch_weather_data()
                    
                    if weather_data:
                        # Avgör om uppdatering behövs (nu med layout change detection)
                        should_update, reason = self.should_update_display(weather_data)
                        
                        if should_update:
                            self.logger.info(f"🔄 UPPDATERAR E-Paper: {reason}")
                            
                            # Rendera och visa (nu med Dynamic Module System)
                            self.render_and_display(weather_data)
                            
                            # Uppdatera state i minnet (nu med layout state)
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