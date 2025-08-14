#!/usr/bin/env python3
"""
Weather Client - API-anrop för SMHI och Netatmo + SunCalculator
Hämtar riktiga väderdata för E-Paper displayen
KOMPLETT NETATMO INTEGRATION: OAuth2 + Temperatur + Tryck + Luftfuktighet
NYTT: CYKEL-VÄDER INTEGRATION: Nederbörd-analys för cykling
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
    """Klient för att hämta väderdata från SMHI, Netatmo och exakta soltider + CYKEL-VÄDER"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialisera med konfiguration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # SMHI konfiguration
        self.latitude = config['location']['latitude']
        self.longitude = config['location']['longitude']
        self.location_name = config['location']['name']
        
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
        
        # NYTT: Tryckhistorik för 3-timmars tendenser (meteorologisk standard)
        self.pressure_history_file = "cache/pressure_history.json"
        self.ensure_cache_directory()
        
        # NYTT: CYKEL-VÄDER konstanter
        self.CYCLING_PRECIPITATION_THRESHOLD = 0.2  # mm/h - Tröskelvärde för cykel-väder varning
        
        self.logger.info(f"🌍 WeatherClient initialiserad för {self.location_name}")
        self.logger.info(f"☀️ SunCalculator aktiverad för exakta soltider")
        self.logger.info(f"🚴‍♂️ Cykel-väder aktiverat (tröskelvärde: {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
        
        # Kontrollera Netatmo-konfiguration
        if self.netatmo_config.get('client_id') and self.netatmo_config.get('refresh_token'):
            self.logger.info(f"🏠 Netatmo-integration aktiverad")
        else:
            self.logger.warning(f"⚠️ Netatmo-credentials saknas - använder endast SMHI")
    
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
        🚴‍♂️ NYTT: Analysera väder för cykling kommande timmen
        
        Args:
            smhi_forecast_data: Full SMHI forecast data med timeSeries
            
        Returns:
            Dict med cykel-väder analys
        """
        try:
            if not smhi_forecast_data or 'timeSeries' not in smhi_forecast_data:
                self.logger.warning("⚠️ Ingen SMHI forecast-data för cykel-analys")
                return {'cycling_warning': False, 'reason': 'No forecast data'}
            
            now = datetime.now(timezone.utc)
            
            # Analysera kommande timmen (0-60 minuter framåt)
            next_hour_forecasts = []
            for forecast in smhi_forecast_data['timeSeries']:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                
                # Bara kommande timmen
                if now <= forecast_time <= now + timedelta(hours=1):
                    next_hour_forecasts.append(forecast)
            
            if not next_hour_forecasts:
                self.logger.warning("⚠️ Ingen prognos för kommande timmen")
                return {'cycling_warning': False, 'reason': 'No hourly forecast'}
            
            # Analysera nederbörd och nederbörd-typ för varje prognos
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
            warning_forecast = None
            
            for forecast in next_hour_forecasts:
                forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
                
                # Extrahera nederbörd-parametrar
                precipitation = 0.0
                precip_type = 0
                
                for param in forecast['parameters']:
                    if param['name'] == 'pmin':  # Nederbörd mm/h
                        precipitation = param['values'][0]
                    elif param['name'] == 'pcat':  # Nederbörd-typ
                        precip_type = param['values'][0]
                
                # Kolla om detta överstiger tröskelvärdet
                if precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                    if precipitation > max_precipitation:
                        max_precipitation = precipitation
                        precipitation_type_code = precip_type
                        warning_forecast = forecast_time
            
            # Om vi hittade betydande nederbörd
            if max_precipitation >= self.CYCLING_PRECIPITATION_THRESHOLD:
                cycling_analysis['cycling_warning'] = True
                cycling_analysis['precipitation_mm'] = max_precipitation
                cycling_analysis['precipitation_type'] = self.get_precipitation_type_description(precipitation_type_code)
                cycling_analysis['precipitation_description'] = self.get_precipitation_intensity_description(max_precipitation)
                cycling_analysis['forecast_time'] = warning_forecast.strftime('%H:%M') if warning_forecast else 'Okänd tid'
                cycling_analysis['reason'] = f"Nederbörd förväntat: {max_precipitation:.1f}mm/h"
                
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING: {cycling_analysis['precipitation_description']} {cycling_analysis['precipitation_type']} kl {cycling_analysis['forecast_time']}")
            else:
                self.logger.info(f"🚴‍♂️ Cykel-väder OK: Max {max_precipitation:.1f}mm/h (under {self.CYCLING_PRECIPITATION_THRESHOLD}mm/h)")
            
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
        """Hämta komplett väderdata från alla källor INKLUSIVE Netatmo lokala sensorer + CYKEL-VÄDER"""
        try:
            # Hämta SMHI-data
            smhi_data = self.get_smhi_data()
            
            # Hämta Netatmo-data (nu fullt implementerat!)
            netatmo_data = self.get_netatmo_data()
            
            # Hämta exakta soltider
            sun_data = self.get_sun_data()
            
            # NYTT: Hämta full SMHI forecast för cykel-analys
            smhi_forecast_data = self.get_smhi_forecast_data()
            
            # NYTT: Analysera cykel-väder
            cycling_weather = self.analyze_cycling_weather(smhi_forecast_data)
            
            # Kombinera data intelligent (Netatmo prioriterat för lokala mätningar)
            combined_data = self.combine_weather_data(smhi_data, netatmo_data, sun_data)
            
            # NYTT: Lägg till cykel-väder information
            combined_data['cycling_weather'] = cycling_weather
            
            sources = []
            if netatmo_data:
                sources.append("Netatmo")
            if smhi_data:
                sources.append("SMHI")
            
            # NYTT: Logga cykel-väder status
            if cycling_weather.get('cycling_warning'):
                self.logger.info(f"🚴‍♂️ CYKEL-VARNING aktiv: {cycling_weather.get('reason')}")
            
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
        """Hämta väderdata från SMHI API"""
        # Kontrollera cache (30 min)
        if time.time() - self.smhi_cache['timestamp'] < 1800:
            if self.smhi_cache['data']:
                self.logger.info("📋 Använder cachad SMHI-data")
                return self.smhi_cache['data']
        
        try:
            self.logger.info("🌐 Hämtar SMHI väderdata...")
            
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
            
            # Extrahera data
            smhi_data = self.parse_smhi_forecast(current_forecast, tomorrow_forecast)
            
            # Uppdatera cache
            self.smhi_cache = {'data': smhi_data, 'timestamp': time.time()}
            
            self.logger.info("✅ SMHI-data hämtad")
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
        """Parsa SMHI prognos-data - UTÖKAD MED NEDERBÖRD för cykel-väder"""
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
            10: "Kraftiga regnskurar", 11: "Åska", 12: "Lätt snöblandad regn",
            13: "Måttlig snöblandad regn", 14: "Kraftig snöblandad regn",
            15: "Lätta snöbyar", 16: "Måttliga snöbyar", 17: "Kraftiga snöbyar",
            18: "Lätt regn", 19: "Måttligt regn", 20: "Kraftigt regn",
            21: "Åska", 22: "Lätt snöblandad regn", 23: "Måttlig snöblandad regn",
            24: "Kraftig snöblandad regn", 25: "Lätt snöfall", 26: "Måttligt snöfall",
            27: "Kraftigt snöfall"
        }
        return descriptions.get(symbol, "Okänt väder")
    
    def combine_weather_data(self, smhi_data: Dict, netatmo_data: Dict, sun_data: Dict) -> Dict[str, Any]:
        """
        INTELLIGENT KOMBINERING: Netatmo lokala mätningar + SMHI prognoser
        
        Args:
            smhi_data: SMHI väderdata (prognoser, vind, nederbörd)
            netatmo_data: Netatmo sensordata (temperatur, tryck)
            sun_data: Exakta soltider från SunCalculator
            
        Returns:
            Optimalt kombinerad väderdata
        """
        combined = {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name
        }
        
        # PRIORITERING: Netatmo för lokala mätningar, SMHI för prognoser
        
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
            combined['weather_description'] = smhi_data.get('weather_description')
            combined['wind_speed'] = smhi_data.get('wind_speed')
            combined['precipitation'] = smhi_data.get('precipitation')
            combined['precipitation_type'] = smhi_data.get('precipitation_type')  # NYTT
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
        
        # DATAKÄLLA-SAMMANFATTNING
        sources = []
        if netatmo_data:
            if 'temperature' in netatmo_data:
                sources.append("Netatmo-temp")
            if 'pressure' in netatmo_data:
                sources.append("Netatmo-tryck")
        if smhi_data:
            sources.append("SMHI-prognos")
        
        combined['data_sources'] = sources
        
        return combined
    
    def get_fallback_data(self) -> Dict[str, Any]:
        """Fallback-data vid API-fel - UTÖKAD MED CYKEL-VÄDER fallback"""
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
            'tomorrow': {
                'temperature': 18.0,
                'weather_description': 'Okänt'
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
    """Test-funktion för Netatmo-integrerad WeatherClient MED CYKEL-VÄDER"""
    # Test-config
    config = {
        'location': {
            'name': 'Stockholm',
            'latitude': 59.3293,
            'longitude': 18.0686
        },
        'api_keys': {
            'netatmo': {
                'client_id': '6777e8548b640a21df054d45',
                'client_secret': 'soPPFwnp0LMJ0tWqP0zV7JStBUcEMLpRP3SMQsKx6',
                'refresh_token': '5c3dd9b22733bf0c008b8f1c|29bed9d652a614b35738718f5ae859ce'
            }
        }
    }
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Testa klient
    client = WeatherClient(config)
    weather_data = client.get_current_weather()
    
    print("🧪 Test av Netatmo-integrerad WeatherClient MED CYKEL-VÄDER:")
    print(json.dumps(weather_data, indent=2, ensure_ascii=False, default=str))
    
    # Specifika tester
    print(f"\n📊 Datakällor:")
    print(f"  🌡️ Temperatur: {weather_data.get('temperature_source', 'N/A')}")
    print(f"  📊 Tryck: {weather_data.get('pressure_source', 'N/A')}")
    print(f"  📡 Källor: {', '.join(weather_data.get('data_sources', ['N/A']))}")
    
    # NYTT: Cykel-väder test
    cycling = weather_data.get('cycling_weather', {})
    print(f"\n🚴‍♂️ Cykel-väder:")
    print(f"  Varning: {cycling.get('cycling_warning', False)}")
    print(f"  Nederbörd: {cycling.get('precipitation_mm', 0):.1f}mm/h")
    print(f"  Typ: {cycling.get('precipitation_type', 'Okänd')}")
    print(f"  Orsak: {cycling.get('reason', 'N/A')}")

if __name__ == "__main__":
    test_weather_client()
