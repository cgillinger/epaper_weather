#!/usr/bin/env python3
"""
Weather Client - API-anrop för SMHI och Netatmo + SunCalculator
Hämtar riktiga väderdata för E-Paper displayen
KOMPLETT NETATMO INTEGRATION: OAuth2 + Temperatur + Tryck + Luftfuktighet
NYTT: CYKEL-VÄDER INTEGRATION: Nederbörd-analys för cykling
SÄKER TEST-DATA INJECTION: Config-driven test-data för precipitation module
NYTT: SMHI OBSERVATIONS API: Exakt "regnar just nu" från senaste timmen
FIXAD: Test-funktion läser från config.json istället av hårdkodade värden
FIXAD: Test-data prioritering följer samma logik som riktiga väderdata
FIXAD: Cykel-väder bug - analyze_cycling_weather extraherar nu korrekt precipitation från SMHI forecast
FIXAD: Timezone bug - UTC-tider konverteras nu till lokal tid för visning (19:00 UTC → 21:00 CEST)
NYTT: SMHI-inkonsistens fix - synkroniserar weather description med observations för konsistent regnkläder-info
FAS 1: VINDRIKTNING API-UTÖKNING - Hämtar nu både vindstyrka (ws) och vindriktning (wd) från SMHI
🐛 BUGFIX: Vindriktning (wd) parameter nu korrekt extraherad från SMHI API - fixar "alltid nordlig vind" problemet
"""

import requests
import json
import time
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

# Importera SunCalculator (med fallback)
try:
    from sun_calculator import SunCalculator
    SUN_CALCULATOR_AVAILABLE = True
except ImportError:
    print("⚠️ SunCalculator ej tillgänglig - använder förenklad solberäkning")
    SUN_CALCULATOR_AVAILABLE = False

class WeatherClient:
    """Klient för att hämta väderdata från SMHI, Netatmo och exakta soltider + CYKEL-VÄDER + SÄKER TEST-DATA + SMHI OBSERVATIONS + VINDRIKTNING"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialisera med konfiguration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # SMHI konfiguration
        self.latitude = config['location']['latitude']
        self.longitude = config['location']['longitude']
        self.location_name = config['location']['name']
        
        # NYTT: SMHI Observations konfiguration
        self.stockholm_stations = config.get('stockholm_stations', {})
        self.observations_station_id = self.stockholm_stations.get('observations_station_id', '98230')
        self.alternative_station_id = self.stockholm_stations.get('alternative_station_id', '97390')
        
        # NETATMO konfiguration (nu fullt implementerad)
        self.netatmo_config = config.get('api_keys', {}).get('netatmo', {})
        self.netatmo_access_token = None
        self.netatmo_token_expires = 0
        
        # Netatmo API endpoints - UPPDATERAD DOMÄN
        self.netatmo_token_url = "https://api.netatmo.com/oauth2/token"
        self.netatmo_stations_url = "https://api.netatmo.com/api/getstationsdata"
        
        # SunCalculator för exakta soltider (om tillgänglig)
        if SUN_CALCULATOR_AVAILABLE:
            self.sun_calculator = SunCalculator()
        else:
            self.sun_calculator = None
        
        # Cache för API-anrop (Netatmo cache kortare - mer aktuell data)
        self.smhi_cache = {'data': None, 'timestamp': 0}
        self.netatmo_cache = {'data': None, 'timestamp': 0}  # 10 min cache för Netatmo
        self.sun_cache = {'data': None, 'timestamp': 0}
        
        # NYTT: Cache för SMHI observations (15 min - data kommer varje timme)
        self.observations_cache = {'data': None, 'timestamp': 0}
        
        # NYTT: Tryckhistorik för 3-timmars tendenser (meteorologisk standard)
        self.pressure_history_file = "cache/pressure_history.json"
        self.ensure_cache_directory()
        
        # NYTT: CYKEL-VÄDER konstanter
        self.CYCLING_PRECIPITATION_THRESHOLD = 0.2  # mm/h - Tröskelvärde för cykel-väder varning
        
        self.logger.info(f"🌍 WeatherClient initialiserad för {self.location_name}")
        self.logger.info(f"☀️ SunCalculator aktiverad för exakta soltider")
        self.logger.info(f"🚴‍♂️ Cykel-väder aktiverat (tröskelvärde: {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
        self.logger.info(f"🌬️ FAS 1: Vindriktning API-utökning aktiverad (ws + wd parametrar)")
        
        # NYTT: Logga observations-konfiguration
        station_name = self.stockholm_stations.get('observations_station_name', 'Okänd station')
        self.logger.info(f"📊 SMHI Observations aktiverat: Station {self.observations_station_id} ({station_name})")
        
        # Kontrollera Netatmo-konfiguration
        if self.netatmo_config.get('client_id') and self.netatmo_config.get('refresh_token'):
            self.logger.info(f"🏠 Netatmo-integration aktiverad")
        else:
            self.logger.warning(f"⚠️ Netatmo-credentials saknas - använder endast SMHI")
        
        # NYTT: Kontrollera test-data konfiguration
        debug_config = self.config.get('debug', {})
        if debug_config.get('enabled') and debug_config.get('allow_test_data'):
            self.logger.info(f"🧪 Test-data injection aktiverad (timeout: {debug_config.get('test_timeout_hours', 1)}h)")
        else:
            self.logger.debug(f"🔒 Test-data injection inaktiverad (production-safe)")
    
    def get_smhi_observations(self) -> Dict[str, Any]:
        """
        NYTT: Hämta SMHI observations data för exakt "regnar just nu"-logik
        
        Returns:
            Dict med observations data eller tom dict vid fel
        """
        # Kontrollera cache (15 min för observations)
        cache_timeout = self.config.get('update_intervals', {}).get('smhi_observations_seconds', 900)
        if time.time() - self.observations_cache['timestamp'] < cache_timeout:
            if self.observations_cache['data']:
                self.logger.info("📋 Använder cachad SMHI observations-data")
                return self.observations_cache['data']
        
        try:
            self.logger.info(f"🌧️ Hämtar SMHI observations från station {self.observations_station_id}...")
            
            # SMHI Observations API enligt handboken
            # Parameter 7 = Nederbördsmängd, summa 1 timme, 1 gång/tim, enhet: millimeter
            url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/{self.observations_station_id}/period/latest-hour/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parsea observations data
            observations_data = self.parse_smhi_observations(data)
            
            if observations_data:
                # Uppdatera cache
                self.observations_cache = {'data': observations_data, 'timestamp': time.time()}
                station_name = self.stockholm_stations.get('observations_station_name', 'Station')
                precipitation = observations_data.get('precipitation_observed', 0.0)
                self.logger.info(f"✅ SMHI Observations hämtad från {station_name}: {precipitation}mm/h")
            else:
                self.logger.warning("⚠️ Ingen giltig observations-data hittades")
            
            return observations_data
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ SMHI Observations API-fel: {e}")
            # Försök med alternativ station
            return self.try_alternative_station()
        except Exception as e:
            self.logger.error(f"❌ SMHI Observations parsningsfel: {e}")
            return {}
    
    def try_alternative_station(self) -> Dict[str, Any]:
        """
        Försök med alternativ station om huvudstationen misslyckas
        
        Returns:
            Dict med observations data från alternativ station eller tom dict
        """
        try:
            self.logger.info(f"🔄 Försöker alternativ station {self.alternative_station_id}...")
            
            url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/{self.alternative_station_id}/period/latest-hour/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            observations_data = self.parse_smhi_observations(data, station_source="alternative")
            
            if observations_data:
                # Uppdatera cache med alternativ data
                self.observations_cache = {'data': observations_data, 'timestamp': time.time()}
                alt_name = self.stockholm_stations.get('alternative_station_name', 'Alternativ station')
                precipitation = observations_data.get('precipitation_observed', 0.0)
                self.logger.info(f"✅ SMHI Observations från alternativ station {alt_name}: {precipitation}mm/h")
            
            return observations_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ Alternativ station misslyckades också: {e}")
            return {}
    
    def parse_smhi_observations(self, api_data: Dict, station_source: str = "primary") -> Dict[str, Any]:
        """
        Parsea SMHI observations API-svar
        
        Args:
            api_data: Rå API-data från SMHI observations
            station_source: "primary" eller "alternative"
            
        Returns:
            Dict med parsad observations data
        """
        try:
            if 'value' not in api_data:
                self.logger.warning("⚠️ Inget 'value' fält i observations API-svar")
                return {}
            
            values = api_data['value']
            if not values:
                self.logger.info("📊 Inga observations-värden tillgängliga (förmodligen 0mm nederbörd)")
                # Returnera 0-värde istället för tom dict - detta är giltigt data!
                return {
                    'source': 'smhi_observations', 
                    'precipitation_observed': 0.0,
                    'observation_time': datetime.now().isoformat(),
                    'station_id': self.observations_station_id if station_source == "primary" else self.alternative_station_id,
                    'station_source': station_source,
                    'quality': 'G',  # Antar godkänt om inga värden (= 0mm)
                    'data_age_minutes': 0
                }
            
            # Ta senaste värdet (borde bara vara ett för latest-hour)
            latest_value = values[-1]
            
            # Extrahera data enligt API-specifikation
            precipitation_mm = float(latest_value.get('value', 0.0))
            quality_code = latest_value.get('quality', 'U')  # U = Unknown om ej angivet
            
            # Konvertera Unix timestamp (millisekunder) till datetime
            timestamp_ms = latest_value.get('date', 0)
            if timestamp_ms:
                observation_time = datetime.fromtimestamp(timestamp_ms / 1000)
                data_age_minutes = (datetime.now() - observation_time).total_seconds() / 60
            else:
                observation_time = datetime.now()
                data_age_minutes = 0
            
            observations_data = {
                'source': 'smhi_observations',
                'precipitation_observed': precipitation_mm,
                'observation_time': observation_time.isoformat(),
                'station_id': self.observations_station_id if station_source == "primary" else self.alternative_station_id,
                'station_source': station_source,
                'quality': quality_code,
                'data_age_minutes': data_age_minutes
            }
            
            # Logga kvalitet och ålder
            quality_desc = {'G': 'Godkänt', 'Y': 'Preliminärt', 'R': 'Dåligt'}.get(quality_code, 'Okänd')
            self.logger.debug(f"📊 Observations kvalitet: {quality_desc}, ålder: {data_age_minutes:.1f} min")
            
            # Varna om data är gammal (över 90 minuter är ovanligt)
            if data_age_minutes > 90:
                self.logger.warning(f"⚠️ Observations-data är {data_age_minutes:.1f} min gammal - möjlig fördröjning")
            
            return observations_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av observations-data: {e}")
            return {}
    
    def _load_test_data_if_enabled(self) -> Optional[Dict]:
        """
        Ladda test-data endast om debug är aktiverat OCH test-fil finns
        SÄKER för produktion - kräver explicit aktivering
        """
        # Kontrollera att debug är aktiverat
        if not self.config.get('debug', {}).get('enabled', False):
            return None
        
        # Kontrollera att test-data är tillåtet
        if not self.config.get('debug', {}).get('allow_test_data', False):
            return None
        
        test_file = "cache/test_precipitation.json"
        if not os.path.exists(test_file):
            return None
        
        try:
            with open(test_file, 'r') as f:
                test_data = json.load(f)
            
            # Säkerhetscheck: endast om explicit enabled
            if not test_data.get('enabled', False):
                self.logger.debug("🧪 Test-data disabled i fil")
                return None
                
            # Timeout-check: test-data max 1 timme gammalt
            if 'created_at' in test_data:
                created = datetime.fromisoformat(test_data['created_at'])
                age_hours = (datetime.now() - created).total_seconds() / 3600
                
                if age_hours > self.config.get('debug', {}).get('test_timeout_hours', 1):
                    self.logger.warning(f"🧪 Test-data timeout ({age_hours:.1f}h) - ignorerar")
                    # Auto-cleanup
                    os.remove(test_file)
                    return None
            
            self.logger.info(f"🧪 TEST-DATA AKTIVT: {test_data.get('test_description', 'Okänd test')}")
            return test_data
            
        except Exception as e:
            self.logger.error(f"❌ Test-data läsningsfel: {e}")
            return None

    def _apply_test_overrides(self, combined_data: Dict, test_data: Dict) -> Dict:
        """
        FIXAD: Applicera test-data med korrekt prioriteringslogik
        Följer nu samma logik som riktiga väderdata där observations prioriteras
        """
        self.logger.info(f"🧪 Applicerar test-data med observations-prioritering...")
        
        # Hämta test-värden
        test_precipitation = test_data.get('precipitation', 0.0)
        test_precipitation_observed = test_data.get('precipitation_observed', 0.0)
        test_forecast_2h = test_data.get('forecast_precipitation_2h', 0.0)
        
        # FIXAD PRIORITERINGSLOGIK: Samma som production-kod
        # Om observations-data finns och > 0, använd det för huvudvärdet
        if test_precipitation_observed > 0:
            combined_data['precipitation'] = test_precipitation_observed
            combined_data['precipitation_source'] = 'smhi_observations_test'
            self.logger.info(f"🎯 TEST PRIORITERING: Observations ({test_precipitation_observed}mm/h) prioriteras över prognos ({test_precipitation}mm/h)")
        else:
            # Fallback till prognos om observations är 0
            combined_data['precipitation'] = test_precipitation
            combined_data['precipitation_source'] = 'smhi_forecast_test'
            self.logger.info(f"🔄 TEST FALLBACK: Observations är 0, använder prognos ({test_precipitation}mm/h)")
        
        # Sätt observations-värde för detaljerad info (alltid från test)
        combined_data['precipitation_observed'] = test_precipitation_observed
        
        # Override forecast-data för context_data
        if 'forecast_precipitation_2h' in test_data:
            combined_data['forecast_precipitation_2h'] = test_forecast_2h
            self.logger.info(f"🧪 Override forecast_precipitation_2h: {test_forecast_2h}mm/h")
        
        # Override cykel-väder data
        if 'cycling_weather' in test_data:
            combined_data['cycling_weather'] = test_data['cycling_weather']
            self.logger.info(f"🧪 Override cycling_weather: {test_data['cycling_weather']}")
        
        # Markera att test-data är aktivt
        combined_data['test_mode'] = True
        combined_data['test_description'] = test_data.get('test_description', 'Test-data aktivt')
        
        # DEBUGGING: Visa slutresultat
        self.logger.info(f"🎯 TEST SLUTRESULTAT: precipitation={combined_data['precipitation']}, precipitation_observed={combined_data['precipitation_observed']}")
        
        return combined_data
    
    def ensure_cache_directory(self):
        """Säkerställ att cache-mappen finns för tryckhistorik"""
        cache_dir = os.path.dirname(self.pressure_history_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            self.logger.info(f"📁 Skapade cache-mapp: {cache_dir}")
    
    def save_pressure_measurement(self, pressure: float, source: str = "netatmo"):
        """
        Spara tryck-mätning för 3-timmars trend-analys (meteorologisk standard)
        
        Args:
            pressure: Lufttryck i hPa
            source: Källa för mätningen
        """
        try:
            current_time = time.time()
            
            # Ladda befintlig historik
            history = self.load_pressure_history()
            
            # Lägg till ny mätning
            history['timestamps'].append(current_time)
            history['pressures'].append(pressure)
            history['sources'].append(source)
            
            # Ta bort mätningar äldre än 24 timmar (behåll längre för säkerhet)
            cutoff_time = current_time - (24 * 3600)
            valid_indices = [i for i, ts in enumerate(history['timestamps']) if ts >= cutoff_time]
            
            history['timestamps'] = [history['timestamps'][i] for i in valid_indices]
            history['pressures'] = [history['pressures'][i] for i in valid_indices]
            history['sources'] = [history['sources'][i] for i in valid_indices]
            
            # Spara uppdaterad historik
            with open(self.pressure_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
                
            self.logger.debug(f"💾 Tryck sparat: {pressure} hPa ({len(history['pressures'])} mätningar totalt)")
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid sparande av tryck: {e}")
    
    def load_pressure_history(self) -> Dict:
        """
        Ladda tryckhistorik från fil
        
        Returns:
            Dict med timestamps, pressures, sources
        """
        try:
            if os.path.exists(self.pressure_history_file):
                with open(self.pressure_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                # Säkerställ att alla nycklar finns
                if 'timestamps' not in history:
                    history['timestamps'] = []
                if 'pressures' not in history:
                    history['pressures'] = []
                if 'sources' not in history:
                    history['sources'] = []
                    
                return history
            else:
                return {'timestamps': [], 'pressures': [], 'sources': []}
                
        except Exception as e:
            self.logger.error(f"❌ Fel vid läsning av tryckhistorik: {e}")
            return {'timestamps': [], 'pressures': [], 'sources': []}
    
    def calculate_3h_pressure_trend(self) -> Dict[str, Any]:
        """
        Beräkna 3-timmars lufttryckstendensen enligt meteorologisk standard
        
        Returns:
            Dict med trend-information
        """
        try:
            history = self.load_pressure_history()
            
            if len(history['pressures']) < 2:
                self.logger.warning("⚠️ För lite tryckdata för trend-analys")
                return {
                    'trend': 'unknown',
                    'change_3h': 0.0,
                    'description': 'Inte tillräckligt med data',
                    'data_hours': 0.0
                }
            
            current_time = time.time()
            timestamps = history['timestamps']
            pressures = history['pressures']
            
            # Hitta mätning närmast 3 timmar bakåt (meteorologisk standard)
            target_time_3h = current_time - (3 * 3600)  # 3 timmar sedan
            
            # Hitta närmaste mätning till 3h-målet
            best_index = 0
            best_time_diff = abs(timestamps[0] - target_time_3h)
            
            for i, ts in enumerate(timestamps):
                time_diff = abs(ts - target_time_3h)
                if time_diff < best_time_diff:
                    best_time_diff = time_diff
                    best_index = i
            
            # Kontrollera att vi har rimlig data (inom 1 timme från 3h-målet)
            actual_hours_back = (current_time - timestamps[best_index]) / 3600
            
            if actual_hours_back < 1.5:  # Mindre än 1.5h data
                self.logger.warning(f"⚠️ För lite historik: {actual_hours_back:.1f}h")
                return {
                    'trend': 'insufficient_data',
                    'change_3h': 0.0,
                    'description': f'Bara {actual_hours_back:.1f}h data tillgänglig',
                    'data_hours': actual_hours_back
                }
            
            # Beräkna 3-timmars förändring
            pressure_3h_ago = pressures[best_index]
            current_pressure = pressures[-1]
            pressure_change_3h = current_pressure - pressure_3h_ago
            
            # Meteorologisk klassificering (officiell standard)
            if pressure_change_3h >= 1.5:
                trend = "rising"
                description = "Högtryck på ingång - bättre väder"
            elif pressure_change_3h <= -1.5:
                trend = "falling"
                description = "Lågtryck närmar sig - ostadigare väder"
            else:
                trend = "stable"
                description = "Oförändrat väderläge"
            
            self.logger.info(f"📊 3h-trycktrend: {pressure_change_3h:+.1f} hPa ({actual_hours_back:.1f}h) → {trend}")
            
            return {
                'trend': trend,
                'change_3h': pressure_change_3h,
                'description': description,
                'data_hours': actual_hours_back,
                'pressure_3h_ago': pressure_3h_ago,
                'pressure_now': current_pressure
            }
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid trend-beräkning: {e}")
            return {
                'trend': 'error',
                'change_3h': 0.0,
                'description': 'Fel vid beräkning',
                'data_hours': 0.0
            }
    
    def analyze_cycling_weather(self, smhi_forecast_data: Dict) -> Dict[str, Any]:
        """
        🚴‍♂️ FIXAD: Analysera väder för cykling kommande timmen - BUG FIXAD + TIMEZONE FIXAD
        
        PROBLEMET: Funktionen hittade inte nederbörd som faktiskt fanns i prognosen
        LÖSNINGEN: Förbättrad tidsfiltrering och precipitation extraction
        
        TIMEZONE-BUG FIXAD: UTC-tider konverteras nu till lokal tid för visning  
        19:00 UTC → 21:00 CEST (svensk sommartid)
        
        Args:
            smhi_forecast_data: Full SMHI forecast data med timeSeries
            
        Returns:
            Dict med cykel-väder analys (tider i lokal tid)
        """
        try:
            if not smhi_forecast_data or 'timeSeries' not in smhi_forecast_data:
                self.logger.warning("⚠️ Ingen SMHI forecast-data för cykel-analys")
                return {'cycling_warning': False, 'reason': 'No forecast data'}
            
            now = datetime.now(timezone.utc)
            
            # FIXAD: Mer generös tidsfiltrering för kommande 2 timmar (istället för bara 1h)
            next_hours_forecasts = []
            for forecast in smhi_forecast_data['timeSeries']:
                try:
                    forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                    
                    # FIXAD: Utökat till 2 timmar för bättre träffsäkerhet
                    if now <= forecast_time <= now + timedelta(hours=2):
                        next_hours_forecasts.append((forecast_time, forecast))
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Fel vid parsning av forecast tid: {e}")
                    continue
            
            if not next_hours_forecasts:
                self.logger.warning("⚠️ Ingen prognos för kommande 2 timmar")
                return {'cycling_warning': False, 'reason': 'No hourly forecast'}
            
            # FIXAD: Förbättrad precipitation extraction och analys
            cycling_analysis = {
                'cycling_warning': False,
                'precipitation_mm': 0.0,
                'precipitation_type': 'Ingen',
                'precipitation_description': '',
                'forecast_time': '',
                'reason': 'Inget regn förväntat'
            }
            
            max_precipitation = 0.0
            precipitation_type_code = 0
            warning_forecast_time = None
            
            # DEBUGGING: Logga vad vi faktiskt hittar
            self.logger.debug(f"🔍 CYKEL-VÄDER DEBUG: Analyserar {len(next_hours_forecasts)} prognoser")
            
            for forecast_time, forecast in next_hours_forecasts:
                # FIXAD: Säkrare parameter-extraktion
                precipitation = 0.0
                precip_type = 0
                
                try:
                    for param in forecast.get('parameters', []):
                        param_name = param.get('name', '')
                        param_values = param.get('values', [])
                        
                        if param_name == 'pmin' and param_values:  # Nederbörd mm/h
                            precipitation = float(param_values[0])
                        elif param_name == 'pcat' and param_values:  # Nederbörd-typ
                            precip_type = int(param_values[0])
                    
                    # DEBUGGING: Logga varje prognos
                    self.logger.debug(f"  {forecast_time.strftime('%H:%M')}: {precipitation}mm/h (typ: {precip_type})")
                    
                    # FIXAD: Kolla tröskelvärdet korrekt
                    if precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                        if precipitation > max_precipitation:
                            max_precipitation = precipitation
                            precipitation_type_code = precip_type
                            warning_forecast_time = forecast_time
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ Fel vid extraktion av forecast-parametrar: {e}")
                    continue
            
            # FIXAD: Korrekt result building
            if max_precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                cycling_analysis['cycling_warning'] = True
                cycling_analysis['precipitation_mm'] = max_precipitation
                cycling_analysis['precipitation_type'] = self.get_precipitation_type_description(precipitation_type_code)
                cycling_analysis['precipitation_description'] = self.get_precipitation_intensity_description(max_precipitation)
                
                # FIXAD TIMEZONE BUG: Konvertera UTC till lokal tid för visning
                if warning_forecast_time:
                    local_time = warning_forecast_time.astimezone()
                    cycling_analysis['forecast_time'] = local_time.strftime('%H:%M')
                else:
                    cycling_analysis['forecast_time'] = 'Okänd tid'
                    
                cycling_analysis['reason'] = f"Nederbörd förväntat: {max_precipitation:.1f}mm/h"
                
                # FIXAD TIMEZONE BUG: Logging med lokal tid
                local_time_str = local_time.strftime('%H:%M') if warning_forecast_time else 'Okänd tid'
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING: {cycling_analysis['precipitation_description']} {cycling_analysis['precipitation_type']} kl {local_time_str} (lokal tid)")
            else:
                cycling_analysis['precipitation_mm'] = max_precipitation  # FIXAD: Sätt även här för debug
                self.logger.info(f"🚴‍♂️ Cykel-väder OK: Max {max_precipitation:.1f}mm/h (under {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
            
            # DEBUGGING: Logga slutresultat
            self.logger.debug(f"🎯 CYKEL-VÄDER SLUTRESULTAT: warning={cycling_analysis['cycling_warning']}, max_precip={cycling_analysis['precipitation_mm']}")
            
            return cycling_analysis
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid cykel-väder analys: {e}")
            return {'cycling_warning': False, 'reason': f'Analysis error: {e}'}
    
    def get_precipitation_type_description(self, pcat_code: int) -> str:
        """
        Konvertera SMHI pcat-kod till läsbar beskrivning
        
        Args:
            pcat_code: SMHI precipitation category kod
            
        Returns:
            Läsbar beskrivning av nederbörd-typ
        """
        precipitation_types = {
            0: "Ingen nederbörd",
            1: "Snö", 
            2: "Snöblandat regn",
            3: "Regn",
            4: "Hagel",
            5: "Hagel + regn", 
            6: "Hagel + snö"
        }
        return precipitation_types.get(pcat_code, f"Okänd typ ({pcat_code})")
    
    def get_precipitation_intensity_description(self, mm_per_hour: float) -> str:
        """
        Konvertera mm/h till läsbar intensitetsbeskrivning
        
        Args:
            mm_per_hour: Nederbörd i mm per timme
            
        Returns:
            Beskrivning av nederbörd-intensitet
        """
        if mm_per_hour < 0.1:
            return "Inget regn"
        elif mm_per_hour < 0.5:
            return "Lätt duggregn"
        elif mm_per_hour < 1.0:
            return "Lätt regn"
        elif mm_per_hour < 2.5:
            return "Måttligt regn"
        elif mm_per_hour < 10.0:
            return "Kraftigt regn"
        else:
            return "Mycket kraftigt regn"
    
    def get_current_weather(self) -> Dict[str, Any]:
        """Hämta komplett väderdata från alla källor INKLUSIVE Netatmo lokala sensorer + CYKEL-VÄDER + OBSERVATIONS + VINDRIKTNING"""
        try:
            # Hämta SMHI-data
            smhi_data = self.get_smhi_data()
            
            # Hämta Netatmo-data (nu fullt implementerat!)
            netatmo_data = self.get_netatmo_data()
            
            # Hämta exakta soltider
            sun_data = self.get_sun_data()
            
            # NYTT: Hämta SMHI observations för "regnar just nu"
            observations_data = self.get_smhi_observations()
            
            # NYTT: Hämta full SMHI forecast för cykel-analys
            smhi_forecast_data = self.get_smhi_forecast_data()
            
            # NYTT: Analysera cykel-väder
            cycling_weather = self.analyze_cycling_weather(smhi_forecast_data)
            
            # Kombinera data intelligent (Netatmo prioriterat för lokala mätningar, Observations för nederbörd)
            combined_data = self.combine_weather_data(smhi_data, netatmo_data, sun_data, observations_data)
            
            # NYTT: Lägg till cykel-väder information
            combined_data['cycling_weather'] = cycling_weather
            
            # FIXAD: Lägg till forecast_precipitation_2h för trigger evaluation
            if cycling_weather:
                combined_data['forecast_precipitation_2h'] = cycling_weather.get('precipitation_mm', 0.0)
                self.logger.debug(f"🎯 TRIGGER DATA: forecast_precipitation_2h = {combined_data['forecast_precipitation_2h']}")
            
            sources = []
            if observations_data:
                sources.append("SMHI-Observations")
            if netatmo_data:
                sources.append("Netatmo")
            if smhi_data:
                sources.append("SMHI-Prognoser")
            
            # NYTT: Logga cykel-väder status
            if cycling_weather.get('cycling_warning'):
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING aktiv: {cycling_weather.get('reason')}")
            
            # NYTT: Logga observations status
            if observations_data:
                observed_precip = observations_data.get('precipitation_observed', 0.0)
                if observed_precip > 0:
                    self.logger.info(f"🌧️ OBSERVATIONS: Regnar just nu ({observed_precip}mm senaste timmen)")
                else:
                    self.logger.info(f"🌤️ OBSERVATIONS: Regnar inte just nu (0mm senaste timmen)")
            
            # FAS 1: Logga vinddata om tillgänglig
            if smhi_data and 'wind_speed' in smhi_data:
                wind_speed = smhi_data.get('wind_speed', 0.0)
                wind_direction = smhi_data.get('wind_direction', 'N/A')
                self.logger.info(f"🌬️ FAS 1: Vinddata hämtad - Styrka: {wind_speed} m/s, Riktning: {wind_direction}°")
            
            self.logger.info(f"✅ Väderdata hämtad från: {', '.join(sources) if sources else 'fallback'}")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            return self.get_fallback_data()
    
    def get_netatmo_access_token(self) -> Optional[str]:
        """
        Hämta giltig Netatmo access token via refresh token
        
        Returns:
            Access token eller None vid fel
        """
        # Kontrollera om befintlig token fortfarande är giltig
        if (self.netatmo_access_token and 
            time.time() < self.netatmo_token_expires - 300):  # 5 min marginal
            return self.netatmo_access_token
        
        try:
            self.logger.info("🔑 Förnyar Netatmo access token...")
            
            # OAuth2 refresh token request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.netatmo_config['refresh_token'],
                'client_id': self.netatmo_config['client_id'],
                'client_secret': self.netatmo_config['client_secret']
            }
            
            response = requests.post(self.netatmo_token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'access_token' in token_data:
                self.netatmo_access_token = token_data['access_token']
                # Access tokens brukar gälla 3 timmar
                expires_in = token_data.get('expires_in', 10800)  
                self.netatmo_token_expires = time.time() + expires_in
                
                self.logger.info(f"✅ Netatmo token förnyad (gäller {expires_in//3600}h)")
                return self.netatmo_access_token
            else:
                self.logger.error(f"❌ Ogiltigt token-svar: {token_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Netatmo token-fel: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Oväntat token-fel: {e}")
            return None
    
    def get_netatmo_data(self) -> Dict[str, Any]:
        """
        Hämta sensordata från Netatmo väderstation
        
        Returns:
            Dict med Netatmo sensordata eller tom dict vid fel
        """
        # Kontrollera om Netatmo är konfigurerat
        if not self.netatmo_config.get('client_id'):
            self.logger.debug("📋 Netatmo ej konfigurerat")
            return {}
        
        # Kontrollera cache (10 min för Netatmo - mer aktuell än SMHI)
        if time.time() - self.netatmo_cache['timestamp'] < 600:
            if self.netatmo_cache['data']:
                self.logger.info("📋 Använder cachad Netatmo-data")
                return self.netatmo_cache['data']
        
        try:
            self.logger.info("🏠 Hämtar Netatmo sensordata...")
            
            # Hämta access token
            access_token = self.get_netatmo_access_token()
            if not access_token:
                self.logger.error("❌ Kunde inte få Netatmo access token")
                return {}
            
            # Hämta stations-data
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(self.netatmo_stations_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            stations_data = response.json()
            
            # Parsea sensor-data
            netatmo_data = self.parse_netatmo_stations(stations_data)
            
            # NYTT: Spara tryck för 3-timmars trend-analys
            if netatmo_data and 'pressure' in netatmo_data:
                self.save_pressure_measurement(netatmo_data['pressure'], source="netatmo")
            
            if netatmo_data:
                # Uppdatera cache
                self.netatmo_cache = {'data': netatmo_data, 'timestamp': time.time()}
                self.logger.info("✅ Netatmo-data hämtad")
            else:
                self.logger.warning("⚠️ Ingen giltig Netatmo-data hittades")
            
            return netatmo_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Netatmo API-fel: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Netatmo parsningsfel: {e}")
            return {}
    
    def parse_netatmo_stations(self, stations_data: Dict) -> Dict[str, Any]:
        """
        Parsea Netatmo stations-data och extrahera sensorvärden
        
        Args:
            stations_data: Rå data från Netatmo stations API
            
        Returns:
            Dict med parsade sensorvärden
        """
        try:
            if 'body' not in stations_data or 'devices' not in stations_data['body']:
                self.logger.error("❌ Ogiltigt Netatmo stations-format")
                return {}
            
            devices = stations_data['body']['devices']
            if not devices:
                self.logger.error("❌ Inga Netatmo enheter hittades")
                return {}
            
            # Ta första station (användaren har antagligen bara en)
            station = devices[0]
            
            netatmo_data = {
                'source': 'netatmo',
                'station_name': station.get('station_name', 'Okänd station'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Hämta data från huvudmodul (inomhus)
            if 'dashboard_data' in station:
                indoor_data = station['dashboard_data']
                
                # LUFTTRYCK från inomhusmodul (mer exakt än SMHI!)
                if 'Pressure' in indoor_data:
                    netatmo_data['pressure'] = indoor_data['Pressure']
                    self.logger.debug(f"📊 Netatmo tryck: {indoor_data['Pressure']} hPa")
                
                # Inomhustemperatur (för framtida användning)
                if 'Temperature' in indoor_data:
                    netatmo_data['indoor_temperature'] = indoor_data['Temperature']
                
                # Luftfuktighet inomhus
                if 'Humidity' in indoor_data:
                    netatmo_data['indoor_humidity'] = indoor_data['Humidity']
                
                # CO2 och ljudnivå (bonus-data)
                if 'CO2' in indoor_data:
                    netatmo_data['co2'] = indoor_data['CO2']
                if 'Noise' in indoor_data:
                    netatmo_data['noise'] = indoor_data['Noise']
            
            # Hämta data från utomhusmodul(er)
            if 'modules' in station:
                for module in station['modules']:
                    module_type = module.get('type')
                    
                    # NAModule1 = Utomhusmodul
                    if module_type == 'NAModule1' and 'dashboard_data' in module:
                        outdoor_data = module['dashboard_data']
                        
                        # TEMPERATUR från utomhusmodul (huvudsensordata!)
                        if 'Temperature' in outdoor_data:
                            netatmo_data['temperature'] = outdoor_data['Temperature']
                            self.logger.debug(f"🌡️ Netatmo utomhustemp: {outdoor_data['Temperature']}°C")
                        
                        # Luftfuktighet utomhus
                        if 'Humidity' in outdoor_data:
                            netatmo_data['outdoor_humidity'] = outdoor_data['Humidity']
                        
                        # Tidsstämpel för senaste mätning
                        if 'time_utc' in outdoor_data:
                            last_seen = datetime.fromtimestamp(outdoor_data['time_utc'])
                            netatmo_data['last_measurement'] = last_seen.isoformat()
                            
                            # Kontrollera att data är färsk (senaste 30 min)
                            data_age_minutes = (datetime.now() - last_seen).total_seconds() / 60
                            if data_age_minutes > 30:
                                self.logger.warning(f"⚠️ Netatmo-data är {data_age_minutes:.1f} min gammal")
                            else:
                                self.logger.debug(f"✅ Netatmo-data är {data_age_minutes:.1f} min gammal")
            
            # Kontrollera att vi fick viktig data
            if 'temperature' not in netatmo_data and 'pressure' not in netatmo_data:
                self.logger.warning("⚠️ Varken temperatur eller tryck hittades i Netatmo-data")
                return {}
            
            # Logga vad vi faktiskt fick
            sensors_found = []
            if 'temperature' in netatmo_data:
                sensors_found.append(f"Temp: {netatmo_data['temperature']}°C")
            if 'pressure' in netatmo_data:
                sensors_found.append(f"Tryck: {netatmo_data['pressure']} hPa")
            if 'outdoor_humidity' in netatmo_data:
                sensors_found.append(f"Luftfuktighet: {netatmo_data['outdoor_humidity']}%")
            
            self.logger.info(f"🏠 Netatmo sensorer: {', '.join(sensors_found)}")
            
            return netatmo_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid parsning av Netatmo-data: {e}")
            return {}
    
    def get_smhi_forecast_data(self) -> Dict[str, Any]:
        """
        NYTT: Hämta full SMHI forecast data för cykel-analys
        (Separerat från get_smhi_data för att få full timeSeries)
        
        Returns:
            Full SMHI forecast data med timeSeries
        """
        try:
            self.logger.debug("🌐 Hämtar full SMHI forecast för cykel-analys...")
            
            # SMHI Meteorologiska prognoser API (samma som get_smhi_data)
            url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{self.longitude}/lat/{self.latitude}/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            self.logger.error(f"❌ SMHI forecast data-fel: {e}")
            return {}
    
    def get_smhi_data(self) -> Dict[str, Any]:
        """Hämta väderdata från SMHI API + FAS 1: VINDRIKTNING"""
        # Kontrollera cache (30 min)
        if time.time() - self.smhi_cache['timestamp'] < 1800:
            if self.smhi_cache['data']:
                self.logger.info("📋 Använder cachad SMHI-data")
                return self.smhi_cache['data']
        
        try:
            self.logger.info("🌐 Hämtar SMHI väderdata med VINDRIKTNING...")
            
            # SMHI Meteorologiska prognoser API
            url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{self.longitude}/lat/{self.latitude}/data.json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Hitta närmaste tidpunkt - FIX: Använd timezone-aware datetime
            now = datetime.now(timezone.utc)
            current_forecast = None
            tomorrow_forecast = None
            
            for forecast in data['timeSeries']:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                
                # Aktuell prognos (närmaste timme)
                if not current_forecast and forecast_time >= now:
                    current_forecast = forecast
                
                # Morgondagens prognos (nästa dag, mitt på dagen)
                tomorrow = now + timedelta(days=1)
                if (forecast_time.date() == tomorrow.date() and 
                    forecast_time.hour == 12):
                    tomorrow_forecast = forecast
                    break
            
            # Extrahera data - NU MED VINDRIKTNING!
            smhi_data = self.parse_smhi_forecast(current_forecast, tomorrow_forecast)
            
            # Uppdatera cache
            self.smhi_cache = {'data': smhi_data, 'timestamp': time.time()}
            
            self.logger.info("✅ SMHI-data hämtad MED VINDRIKTNING")
            return smhi_data
            
        except Exception as e:
            self.logger.error(f"❌ SMHI API-fel: {e}")
            return {}
    
    def get_sun_data(self) -> Dict[str, Any]:
        """
        Hämta exakta soltider med SunCalculator
        
        Returns:
            Dict med soldata eller tom dict vid fel
        """
        # Kontrollera cache (4 timmar för soltider)
        if time.time() - self.sun_cache['timestamp'] < 14400:
            if self.sun_cache['data']:
                self.logger.info("📋 Använder cachade soltider")
                return self.sun_cache['data']
        
        try:
            self.logger.info("☀️ Hämtar exakta soltider...")
            
            # Använd SunCalculator för exakta soltider (om tillgänglig)
            if self.sun_calculator:
                sun_data = self.sun_calculator.get_sun_times(
                    latitude=self.latitude,
                    longitude=self.longitude
                )
            else:
                # Fallback: förenklad beräkning
                self.logger.info("⚠️ SunCalculator ej tillgänglig - använder förenklad beräkning")
                return {}
            
            # Uppdatera cache
            self.sun_cache = {'data': sun_data, 'timestamp': time.time()}
            
            source = sun_data.get('source', 'unknown')
            cached = sun_data.get('cached', False)
            self.logger.info(f"✅ Soltider hämtade från {source} (cached: {cached})")
            
            return sun_data
            
        except Exception as e:
            self.logger.error(f"❌ Soldata-fel: {e}")
            return {}
    
    def parse_smhi_forecast(self, current: Dict, tomorrow: Dict) -> Dict[str, Any]:
        """🐛 BUGFIX: FAS 1: Parsa SMHI prognos-data - UTÖKAD MED VINDRIKTNING för cykel-väder + nederbörd"""
        data = {
            'source': 'smhi',
            'location': self.location_name,
            'timestamp': datetime.now().isoformat()
        }
        
        if current:
            # Aktuell väderdata
            for param in current['parameters']:
                if param['name'] == 't':  # Temperatur (kommer att överskrivas av Netatmo)
                    data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':  # Vädersymbol
                    data['weather_symbol'] = param['values'][0]
                    data['weather_description'] = self.get_weather_description(param['values'][0])
                elif param['name'] == 'ws':  # Vindstyrka
                    data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':  # 🐛 BUGFIX: VINDRIKTNING TILLAGD - fixar "alltid nordlig vind"
                    data['wind_direction'] = float(param['values'][0])
                elif param['name'] == 'msl':  # Lufttryck (kommer att överskrivas av Netatmo)
                    data['pressure'] = round(param['values'][0], 0)
                elif param['name'] == 'pmin':  # NYTT: Nederbörd mm/h
                    data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':  # NYTT: Nederbörd-typ
                    data['precipitation_type'] = param['values'][0]
        
        if tomorrow:
            # Morgondagens väder
            tomorrow_data = {}
            for param in tomorrow['parameters']:
                if param['name'] == 't':
                    tomorrow_data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':
                    tomorrow_data['weather_symbol'] = param['values'][0]
                    tomorrow_data['weather_description'] = self.get_weather_description(param['values'][0])
                # FAS 1: Lägg till vinddata för imorgon också
                elif param['name'] == 'ws':
                    tomorrow_data['wind_speed'] = param['values'][0]
                elif param['name'] == 'wd':  # 🐛 BUGFIX: VINDRIKTNING för imorgon också
                    tomorrow_data['wind_direction'] = float(param['values'][0])
                # NYTT: Lägg till nederbörd för imorgon också
                elif param['name'] == 'pmin':
                    tomorrow_data['precipitation'] = param['values'][0]
                elif param['name'] == 'pcat':
                    tomorrow_data['precipitation_type'] = param['values'][0]
            
            data['tomorrow'] = tomorrow_data
        
        return data
    
    def get_weather_description(self, symbol: int) -> str:
        """Konvertera SMHI vädersymbol till beskrivning"""
        descriptions = {
            1: "Klart", 2: "Mest klart", 3: "Växlande molnighet",
            4: "Halvklart", 5: "Molnigt", 6: "Mulet",
            7: "Dimma", 8: "Lätta regnskurar", 9: "Måttliga regnskurar",
            10: "Kraftiga regnskurar", 11: "Åskväder", 12: "Lätt snöblandad regn",
            13: "Måttlig snöblandad regn", 14: "Kraftig snöblandad regn",
            15: "Lätta snöbyar", 16: "Måttliga snöbyar", 17: "Kraftiga snöbyar",
            18: "Lätt regn", 19: "Måttligt regn", 20: "Kraftigt regn",
            21: "Åska", 22: "Lätt snöblandad regn", 23: "Måttlig snöblandad regn",
            24: "Kraftig snöblandad regn", 25: "Lätt snöfall", 26: "Måttligt snöfall",
            27: "Kraftigt snöfall"
        }
        return descriptions.get(symbol, "Okänt väder")
    
    def get_observations_synchronized_description(self, weather_symbol: int, observations_precipitation: float) -> str:
        """
        NYTT: Synkronisera weather description med observations för konsistent regnkläder-info
        
        Löser problemet: 
        - Weather symbol 18 = "Lätt regn" 
        - Men observations = 0mm/h (regnar inte faktiskt)
        - Ändra till "Regn väntat" istället för "Lätt regn"
        
        Args:
            weather_symbol: SMHI weather symbol (1-27)
            observations_precipitation: Verklig nederbörd från observations (mm/h)
            
        Returns:
            Synkroniserad weather description
        """
        try:
            # Hämta original beskrivning
            original_description = self.get_weather_description(weather_symbol)
            
            # Regn-symboler som kan behöva synkronisering
            rain_symbols = {
                8: "regnskurar",     # Lätta regnskurar
                9: "regnskurar",     # Måttliga regnskurar  
                10: "regnskurar",    # Kraftiga regnskurar
                18: "regn",          # Lätt regn
                19: "regn",          # Måttligt regn
                20: "regn",          # Kraftigt regn
                21: "åska",          # Åska
                22: "snöblandad regn", # Lätt snöblandad regn
                23: "snöblandad regn", # Måttlig snöblandad regn
                24: "snöblandad regn"  # Kraftig snöblandad regn
            }
            
            # Om weather symbol indikerar regn MEN observations visar 0mm/h
            if weather_symbol in rain_symbols and observations_precipitation == 0:
                rain_type = rain_symbols[weather_symbol]
                
                # Ändra från "regnar nu" till "regn väntat"
                synchronized_description = original_description.replace(
                    rain_type, f"{rain_type} väntat"
                ).replace(
                    "Lätta", "Lätta"  # Behåll intensitet
                ).replace(
                    "Måttliga", "Måttliga"  # Behåll intensitet
                ).replace(
                    "Kraftiga", "Kraftiga"  # Behåll intensitet
                )
                
                # Special case för åska
                if weather_symbol == 21:
                    synchronized_description = "Åska väntat"
                
                self.logger.info(f"🔄 SMHI-synkronisering: '{original_description}' → '{synchronized_description}' (observations: {observations_precipitation}mm/h)")
                return synchronized_description
            
            # Ingen synkronisering behövd - returnera original
            return original_description
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid weather description synkronisering: {e}")
            return self.get_weather_description(weather_symbol)  # Fallback till original
    
    def combine_weather_data(self, smhi_data: Dict, netatmo_data: Dict, sun_data: Dict, observations_data: Dict = None) -> Dict[str, Any]:
        """
        INTELLIGENT KOMBINERING: Netatmo lokala mätningar + SMHI prognoser + OBSERVATIONS prioriterat
        UTÖKAD: Med SMHI Observations prioritering för nederbörd + FAS 1: VINDRIKTNING
        NYTT: SMHI-inkonsistens fix - synkroniserar weather description med observations
        🐛 BUGFIX: Vinddata nu korrekt extraherad och kombinerad
        
        Args:
            smhi_data: SMHI väderdata (prognoser, vind, nederbörd, VINDRIKTNING)
            netatmo_data: Netatmo sensordata (temperatur, tryck)
            sun_data: Exakta soltider från SunCalculator
            observations_data: SMHI observations (senaste timmen)
            
        Returns:
            Optimalt kombinerad väderdata med observations-prioritering och synkroniserad description + VINDRIKTNING
        """
        combined = {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name
        }
        
        # PRIORITERING: Netatmo för lokala mätningar, OBSERVATIONS för nederbörd, SMHI för prognoser + VINDRIKTNING
        
        # TEMPERATUR: Netatmo utomhus > SMHI
        if netatmo_data and 'temperature' in netatmo_data:
            combined['temperature'] = netatmo_data['temperature']
            combined['temperature_source'] = 'netatmo'
        elif smhi_data and 'temperature' in smhi_data:
            combined['temperature'] = smhi_data['temperature']
            combined['temperature_source'] = 'smhi'
        
        # LUFTTRYCK: Netatmo inomhus > SMHI  
        if netatmo_data and 'pressure' in netatmo_data:
            combined['pressure'] = netatmo_data['pressure']
            combined['pressure_source'] = 'netatmo'
        elif smhi_data and 'pressure' in smhi_data:
            combined['pressure'] = smhi_data['pressure']
            combined['pressure_source'] = 'smhi'
        
        # NEDERBÖRD: OBSERVATIONS prioriterat över prognoser (exakt "regnar just nu")
        if observations_data and 'precipitation_observed' in observations_data:
            # Använd observations för huvudvärdet
            combined['precipitation'] = observations_data['precipitation_observed']
            combined['precipitation_source'] = 'smhi_observations'
            
            # Behåll observations-data för detaljerad info
            combined['precipitation_observed'] = observations_data['precipitation_observed']
            combined['observation_time'] = observations_data.get('observation_time')
            combined['observation_quality'] = observations_data.get('quality', 'U')
            combined['observation_station'] = observations_data.get('station_id')
            combined['observation_age_minutes'] = observations_data.get('data_age_minutes', 0)
            
            self.logger.info(f"🎯 PRIORITERING: Nederbörd från observations ({observations_data['precipitation_observed']}mm/h) iställetför prognoser")
            
        elif smhi_data and 'precipitation' in smhi_data:
            # Fallback till SMHI prognoser
            combined['precipitation'] = smhi_data['precipitation']
            combined['precipitation_source'] = 'smhi_forecast'
            self.logger.debug("🔄 Fallback: Nederbörd från SMHI prognoser (observations ej tillgänglig)")
        
        # 🐛 BUGFIX: FAS 1: VINDDATA från SMHI (nu både styrka och riktning!)
        if smhi_data:
            combined['wind_speed'] = smhi_data.get('wind_speed', 0.0)
            combined['wind_direction'] = smhi_data.get('wind_direction', 0.0)  # 🐛 BUGFIX: FAS 1: TILLAGT
            
            # Logga vinddata för debugging
            if 'wind_speed' in smhi_data and 'wind_direction' in smhi_data:
                self.logger.debug(f"🌬️ FAS 1: Komplett vinddata - {smhi_data['wind_speed']} m/s från {smhi_data['wind_direction']}°")
        
        # LUFTFUKTIGHET: Netatmo (bonus-data)
        if netatmo_data:
            if 'outdoor_humidity' in netatmo_data:
                combined['humidity'] = netatmo_data['outdoor_humidity']
                combined['humidity_source'] = 'netatmo_outdoor'
            elif 'indoor_humidity' in netatmo_data:
                combined['indoor_humidity'] = netatmo_data['indoor_humidity']
        
        # VÄDER OCH PROGNOSER: Alltid från SMHI
        if smhi_data:
            combined['weather_symbol'] = smhi_data.get('weather_symbol')
            
            # NYTT: Synkronisera weather description med observations
            if observations_data and combined.get('weather_symbol'):
                combined['weather_description'] = self.get_observations_synchronized_description(
                    combined['weather_symbol'],
                    observations_data.get('precipitation_observed', 0.0)
                )
            else:
                # Fallback till original description
                combined['weather_description'] = smhi_data.get('weather_description')
            
            # Nederbörd-typ från prognoser (observations har ingen typ-info)
            combined['precipitation_type'] = smhi_data.get('precipitation_type')  
            combined['tomorrow'] = smhi_data.get('tomorrow', {})
        
        # SOLTIDER: Exakta från SunCalculator
        if sun_data:
            combined['sun_data'] = {
                'sunrise': sun_data.get('sunrise'),
                'sunset': sun_data.get('sunset'),
                'sunrise_time': sun_data.get('sunrise_time'),
                'sunset_time': sun_data.get('sunset_time'),
                'daylight_duration': sun_data.get('daylight_duration'),
                'sun_source': sun_data.get('source', 'unknown')
            }
            
            # För bakåtkompatibilitet med main.py
            combined['sunrise'] = sun_data.get('sunrise')
            combined['sunset'] = sun_data.get('sunset')
        
        # BONUS NETATMO-DATA (för framtida användning)
        if netatmo_data:
            combined['netatmo_extras'] = {}
            for key in ['co2', 'noise', 'indoor_temperature', 'station_name', 'last_measurement']:
                if key in netatmo_data:
                    combined['netatmo_extras'][key] = netatmo_data[key]
        
        # NYTT: 3-TIMMARS TRYCKTREND (meteorologisk standard)
        pressure_trend = self.calculate_3h_pressure_trend()
        combined['pressure_trend'] = pressure_trend
        
        # DEBUG: Visa exakt vad vi får från trend-beräkningen
        self.logger.info(f"🔍 DEBUG pressure_trend: {pressure_trend}")
        
        # Lägg till trend-beskrivning för display
        if pressure_trend['trend'] in ['rising', 'falling', 'stable']:
            combined['pressure_trend_text'] = {
                'rising': 'Stigande',
                'falling': 'Fallande', 
                'stable': 'Stabilt'
            }[pressure_trend['trend']]
            combined['pressure_trend_arrow'] = pressure_trend['trend']
            self.logger.info(f"🎯 Använder verklig trend: {pressure_trend['trend']} → '{combined['pressure_trend_text']}'")
        else:
            # Fallback för otillräcklig data - TYDLIGT meddelande
            combined['pressure_trend_text'] = 'Samlar data'
            combined['pressure_trend_arrow'] = 'stable'  # Horisontell pil under uppbyggnad
            self.logger.info(f"🎯 Otillräcklig data: {pressure_trend['trend']} → 'Samlar data'")
        
        # DATAKÄLLA-SAMMANFATTNING + FAS 1: VINDRIKTNING
        sources = []
        if observations_data:
            sources.append("Observations")
        if netatmo_data:
            if 'temperature' in netatmo_data:
                sources.append("Netatmo-temp")
            if 'pressure' in netatmo_data:
                sources.append("Netatmo-tryck")
        if smhi_data:
            sources.append("SMHI-prognos")
            if 'wind_direction' in smhi_data:
                sources.append("SMHI-vindriktning")  # 🐛 BUGFIX: FAS 1: Tillagt
        
        combined['data_sources'] = sources
        
        # === SÄKER TEST-DATA OVERRIDE ===
        test_override = self._load_test_data_if_enabled()
        if test_override:
            combined = self._apply_test_overrides(combined, test_override)
        
        return combined
    
    def get_fallback_data(self) -> Dict[str, Any]:
        """Fallback-data vid API-fel - UTÖKAD MED CYKEL-VÄDER fallback + OBSERVATIONS + FAS 1: VINDRIKTNING"""
        return {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name,
            'temperature': 20.0,
            'weather_description': 'Data ej tillgänglig',
            'weather_symbol': 1,
            'pressure': 1013,
            'temperature_source': 'fallback',
            'pressure_source': 'fallback',
            'precipitation': 0.0,  # NYTT
            'precipitation_type': 0,  # NYTT
            'precipitation_source': 'fallback',
            'precipitation_observed': 0.0,  # NYTT: Observations fallback
            'forecast_precipitation_2h': 0.0,  # FIXAD: Lägg till för trigger
            # 🐛 BUGFIX: FAS 1: VINDRIKTNING fallback
            'wind_speed': 0.0,
            'wind_direction': 0.0,
            'tomorrow': {
                'temperature': 18.0,
                'weather_description': 'Okänt',
                'wind_speed': 0.0,        # 🐛 BUGFIX: FAS 1: Fallback vinddata
                'wind_direction': 0.0     # 🐛 BUGFIX: FAS 1: Fallback vindriktning
            },
            # Fallback soltider
            'sun_data': {
                'sunrise': datetime.now().replace(hour=6, minute=0).isoformat(),
                'sunset': datetime.now().replace(hour=18, minute=0).isoformat(),
                'daylight_duration': '12h 0m',
                'sun_source': 'fallback'
            },
            # NYTT: Fallback cykel-väder
            'cycling_weather': {
                'cycling_warning': False,
                'precipitation_mm': 0.0,
                'precipitation_type': 'Ingen',
                'reason': 'Fallback data - ingen nederbörd-info'
            },
            'data_sources': ['fallback']
        }


def test_weather_client():
    """
    🐛 BUGFIX: FAS 1: UPPDATERAD Test-funktion med VINDRIKTNING-verifiering
    
    Testar säkra test-data injection system och korrekt SMHI Observations integration + VINDRIKTNING
    """
    print("🧪 🐛 BUGFIX: FAS 1: Test av WeatherClient MED VINDRIKTNING + SMHI OBSERVATIONS + CYKEL-VÄDER + TEST-DATA")
    print("=" * 80)
    
    try:
        # FIXAD: Läs från samma config.json som produktionssystemet
        config_path = "config.json"  # Antaget från projektrot
        
        # Försök läsa från aktuell katalog först
        if not os.path.exists(config_path):
            # Om vi kör från modules/ katalog, gå upp en nivå
            config_path = "../config.json"
        
        if not os.path.exists(config_path):
            print("❌ Kunde inte hitta config.json - kör från rätt katalog!")
            return False
        
        # Läs konfiguration från fil
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Visa konfiguration som kommer användas
        stockholm_stations = config.get('stockholm_stations', {})
        print(f"📁 KONFIGURATION (från {config_path}):")
        print(f"   Station ID: {stockholm_stations.get('observations_station_id', 'Saknas')}")
        print(f"   Station namn: {stockholm_stations.get('observations_station_name', 'Saknas')}")
        print(f"   Debug aktiverat: {config.get('debug', {}).get('enabled', False)}")
        print(f"   Test-data tillåtet: {config.get('debug', {}).get('allow_test_data', False)}")
        
        print(f"\n🐛 BUGFIX: 🌬️ FAS 1: VINDRIKTNING API-UTÖKNING TEST:")
        print(f"   🎯 Målparameter: 'wd' (wind direction) från SMHI")
        print(f"   📊 Befintlig parameter: 'ws' (wind speed) ska fungera som vanligt")
        print(f"   🔄 Båda styrka och riktning ska finnas i weather_data")
        print(f"   🐛 BUGFIX: Fixar 'alltid nordlig vind' problemet")
        
        print(f"\n🚀 KÖR WEATHERCLIENT-TEST MED VINDRIKTNING:")
        print("-" * 50)
        
        # Setup logging för test
        logging.basicConfig(level=logging.INFO)
        
        # Skapa och testa klient
        client = WeatherClient(config)
        weather_data = client.get_current_weather()
        
        print(f"\n📊 🐛 BUGFIX: FAS 1: VINDRIKTNING TEST-RESULTAT:")
        print("-" * 40)
        
        # FAS 1: Specifika tester för vinddata
        wind_speed = weather_data.get('wind_speed', 'SAKNAS')
        wind_direction = weather_data.get('wind_direction', 'SAKNAS')
        
        print(f"🌬️ 🐛 BUGFIX: FAS 1: VINDDATA VERIFIERING:")
        print(f"   📊 Vindstyrka (ws): {wind_speed} m/s")
        print(f"   🧭 Vindriktning (wd): {wind_direction}° {'✅ FUNKAR' if wind_direction != 'SAKNAS' else '❌ SAKNAS'}")
        
        if wind_direction != 'SAKNAS' and wind_direction != 0.0:
            print(f"   🎯 🐛 BUGFIX FRAMGÅNG: Både vindparametrar hämtade från SMHI!")
            print(f"   🌬️ Wind direction bug FIXAD - inte längre alltid nordlig vind")
        elif wind_direction == 0.0:
            print(f"   ⚠️ 🐛 POTENTIELL BUG: Vindriktning är 0° (nord) - kan vara verkligt eller bug")
        else:
            print(f"   ❌ 🐛 FAS 1 PROBLEM: Vindriktning saknas - kontrollera parse_smhi_forecast()")
        
        # Visa även morgondagens vinddata om tillgängligt
        tomorrow = weather_data.get('tomorrow', {})
        if tomorrow.get('wind_speed') is not None and tomorrow.get('wind_direction') is not None:
            print(f"   📅 Imorgon vind: {tomorrow['wind_speed']} m/s från {tomorrow['wind_direction']}°")
        
        # Specificera tester för SMHI Observations (befintlig från före Fas 1)
        observations_tested = 'precipitation_observed' in weather_data
        print(f"\n🌧️ SMHI Observations: {'✅ Fungerar' if observations_tested else '❌ Ej tillgänglig'}")
        
        if observations_tested:
            print(f"   📁 Station: {weather_data.get('observation_station', 'Okänd')}")
            print(f"   📊 Nederbörd: {weather_data.get('precipitation_observed', 0)}mm/h")
            print(f"   🕐 Ålder: {weather_data.get('observation_age_minutes', 0):.1f} min")
            print(f"   ✅ Kvalitet: {weather_data.get('observation_quality', 'Okänd')}")
        
        # Data-prioritering test
        print(f"\n🎯 PRIORITERING:")
        print(f"   🌡️ Temperatur: {weather_data.get('temperature_source', 'N/A')}")
        print(f"   📊 Tryck: {weather_data.get('pressure_source', 'N/A')}")
        print(f"   🌧️ Nederbörd: {weather_data.get('precipitation_source', 'N/A')}")
        
        # Cykel-väder test (befintlig)
        cycling = weather_data.get('cycling_weather', {})
        print(f"\n🚴‍♂️ CYKEL-VÄDER:")
        print(f"   Varning: {'⚠️ Aktiv' if cycling.get('cycling_warning', False) else '✅ OK'}")
        print(f"   Nederbörd: {cycling.get('precipitation_mm', 0):.1f}mm/h")
        print(f"   Typ: {cycling.get('precipitation_type', 'Okänd')}")
        print(f"   Tid: {cycling.get('forecast_time', 'N/A')}")
        print(f"   Orsak: {cycling.get('reason', 'N/A')}")
        
        # Visa forecast_precipitation_2h för trigger debugging
        forecast_2h = weather_data.get('forecast_precipitation_2h', 0.0)
        print(f"\n🎯 TRIGGER DATA:")
        print(f"   precipitation: {weather_data.get('precipitation', 0.0)}mm/h")
        print(f"   forecast_precipitation_2h: {forecast_2h}mm/h")
        print(f"   TRIGGER CONDITION: precipitation > 0 OR forecast_precipitation_2h > 0.2")
        print(f"   SKULLE TRIGGA: {weather_data.get('precipitation', 0.0) > 0 or forecast_2h > 0.2}")
        
        # Test SMHI-inkonsistens fix
        print(f"\n🔄 SMHI-INKONSISTENS FIX:")
        print(f"   Weather description: {weather_data.get('weather_description', 'N/A')}")
        print(f"   Weather symbol: {weather_data.get('weather_symbol', 'N/A')}")
        if observations_tested:
            print(f"   Synkroniserad med observations: {'✅ Ja' if 'väntat' in weather_data.get('weather_description', '') else '📊 Ingen konflikt'}")
        
        # Test-data status
        if weather_data.get('test_mode'):
            print(f"\n🧪 TEST-LÄGE AKTIVT:")
            print(f"   📁 Beskrivning: {weather_data.get('test_description', 'N/A')}")
            print(f"   ⚠️ VIKTIGT: Detta är test-data, inte riktiga mätningar!")
        
        # Datakällor
        sources = weather_data.get('data_sources', [])
        print(f"\n📡 DATAKÄLLOR: {', '.join(sources) if sources else 'Ingen data'}")
        
        print(f"\n✅ 🐛 BUGFIX: FAS 1 TEST KOMPLETT - WeatherClient med VINDRIKTNING!")
        
        # FAS 1: Sammanfattning
        if wind_direction != 'SAKNAS' and wind_direction != 0.0:
            print(f"🎯 🐛 BUGFIX FRAMGÅNG: API-utökning för vindriktning KLAR")
            print(f"🌬️ Både vindstyrka ({wind_speed} m/s) och vindriktning ({wind_direction}°) hämtas från SMHI")
            print(f"🔧 parse_smhi_forecast() nu utökad med 'wd' parameter-parsning")
            print(f"📊 Data tillgänglig för nästa fas (mappning till svenska riktningar)")
            print(f"🐛 Wind direction bug FIXAD - 'alltid nordlig vind' problemet löst")
        else:
            print(f"❌ 🐛 FAS 1 PROBLEM: Vindriktning hämtas inte korrekt")
            print(f"🔧 Kontrollera att 'wd' parameter läggs till i parse_smhi_forecast()")
        
        return True
        
    except Exception as e:
        print(f"❌ Test misslyckades: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Huvud-funktion för att köra test"""
    test_weather_client()


if __name__ == "__main__":
    main()