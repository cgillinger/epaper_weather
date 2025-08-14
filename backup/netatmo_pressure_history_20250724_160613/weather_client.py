#!/usr/bin/env python3
"""
Weather Client - API-anrop för SMHI och Netatmo + SunCalculator
Hämtar riktiga väderdata för E-Paper displayen
KOMPLETT NETATMO INTEGRATION: OAuth2 + Temperatur + Tryck + Luftfuktighet
"""

import requests
import json
import time
import logging
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
    """Klient för att hämta väderdata från SMHI, Netatmo och exakta soltider"""
    
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
        
        self.logger.info(f"🌍 WeatherClient initialiserad för {self.location_name}")
        self.logger.info(f"☀️ SunCalculator aktiverad för exakta soltider")
        
        # Kontrollera Netatmo-konfiguration
        if self.netatmo_config.get('client_id') and self.netatmo_config.get('refresh_token'):
            self.logger.info(f"🏠 Netatmo-integration aktiverad")
        else:
            self.logger.warning(f"⚠️ Netatmo-credentials saknas - använder endast SMHI")
    
    def get_current_weather(self) -> Dict[str, Any]:
        """Hämta komplett väderdata från alla källor INKLUSIVE Netatmo lokala sensorer"""
        try:
            # Hämta SMHI-data
            smhi_data = self.get_smhi_data()
            
            # Hämta Netatmo-data (nu fullt implementerat!)
            netatmo_data = self.get_netatmo_data()
            
            # Hämta exakta soltider
            sun_data = self.get_sun_data()
            
            # Kombinera data intelligent (Netatmo prioriterat för lokala mätningar)
            combined_data = self.combine_weather_data(smhi_data, netatmo_data, sun_data)
            
            sources = []
            if netatmo_data:
                sources.append("Netatmo")
            if smhi_data:
                sources.append("SMHI")
            
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
        """Parsa SMHI prognos-data"""
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
                elif param['name'] == 'pmin':  # Nederbörd
                    data['precipitation'] = param['values'][0]
        
        if tomorrow:
            # Morgondagens väder
            tomorrow_data = {}
            for param in tomorrow['parameters']:
                if param['name'] == 't':
                    tomorrow_data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':
                    tomorrow_data['weather_symbol'] = param['values'][0]
                    tomorrow_data['weather_description'] = self.get_weather_description(param['values'][0])
            
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
        """Fallback-data vid API-fel"""
        return {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name,
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
            # Fallback soltider
            'sun_data': {
                'sunrise': datetime.now().replace(hour=6, minute=0).isoformat(),
                'sunset': datetime.now().replace(hour=18, minute=0).isoformat(),
                'daylight_duration': '12h 0m',
                'sun_source': 'fallback'
            },
            'data_sources': ['fallback']
        }

def test_weather_client():
    """Test-funktion för Netatmo-integrerad WeatherClient"""
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
    
    print("🧪 Test av Netatmo-integrerad WeatherClient:")
    print(json.dumps(weather_data, indent=2, ensure_ascii=False, default=str))
    
    # Specifika tester
    print(f"\n📊 Datakällor:")
    print(f"  🌡️ Temperatur: {weather_data.get('temperature_source', 'N/A')}")
    print(f"  📊 Tryck: {weather_data.get('pressure_source', 'N/A')}")
    print(f"  📡 Källor: {', '.join(weather_data.get('data_sources', ['N/A']))}")

if __name__ == "__main__":
    test_weather_client()
