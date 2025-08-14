#!/usr/bin/env python3
"""
Weather Client - API-anrop för SMHI och Netatmo
Hämtar riktiga väderdata för E-Paper displayen
KORRIGERAD VERSION - Datetime timezone-fix implementerad
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

class WeatherClient:
    """Klient för att hämta väderdata från SMHI och Netatmo"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialisera med konfiguration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # SMHI konfiguration
        self.latitude = config['location']['latitude']
        self.longitude = config['location']['longitude']
        self.location_name = config['location']['name']
        
        # Netatmo konfiguration (om tillgänglig)
        self.netatmo_config = config.get('api_keys', {}).get('netatmo', {})
        self.netatmo_token = None
        
        # Cache för API-anrop
        self.smhi_cache = {'data': None, 'timestamp': 0}
        self.netatmo_cache = {'data': None, 'timestamp': 0}
        
        self.logger.info(f"🌍 WeatherClient initialiserad för {self.location_name}")
    
    def get_current_weather(self) -> Dict[str, Any]:
        """Hämta komplett väderdata från alla källor"""
        try:
            # Hämta SMHI-data
            smhi_data = self.get_smhi_data()
            
            # Försök hämta Netatmo-data
            netatmo_data = self.get_netatmo_data()
            
            # Kombinera data intelligent
            combined_data = self.combine_weather_data(smhi_data, netatmo_data)
            
            self.logger.info("✅ Väderdata hämtad från alla källor")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid hämtning av väderdata: {e}")
            return self.get_fallback_data()
    
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
                if param['name'] == 't':  # Temperatur
                    data['temperature'] = round(param['values'][0], 1)
                elif param['name'] == 'Wsymb2':  # Vädersymbol
                    data['weather_symbol'] = param['values'][0]
                    data['weather_description'] = self.get_weather_description(param['values'][0])
                elif param['name'] == 'ws':  # Vindstyrka
                    data['wind_speed'] = param['values'][0]
                elif param['name'] == 'msl':  # Lufttryck
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
    
    def get_netatmo_data(self) -> Dict[str, Any]:
        """Hämta data från Netatmo (implementeras senare)"""
        # TODO: Implementera Netatmo OAuth2 och API-anrop
        self.logger.info("⏭️ Netatmo-integration kommer i nästa steg")
        return {}
    
    def combine_weather_data(self, smhi_data: Dict, netatmo_data: Dict) -> Dict[str, Any]:
        """Kombinera väderdata från alla källor intelligent"""
        combined = {
            'timestamp': datetime.now().isoformat(),
            'location': self.location_name
        }
        
        # Prioritera Netatmo för lokala mätningar, SMHI för prognoser
        if netatmo_data:
            combined['temperature_source'] = 'netatmo'
            combined['temperature'] = netatmo_data.get('temperature')
            combined['humidity'] = netatmo_data.get('humidity')
            combined['pressure'] = netatmo_data.get('pressure')
        elif smhi_data:
            combined['temperature_source'] = 'smhi'
            combined['temperature'] = smhi_data.get('temperature')
            combined['pressure'] = smhi_data.get('pressure')
        
        # SMHI för väder och prognoser
        if smhi_data:
            combined['weather_symbol'] = smhi_data.get('weather_symbol')
            combined['weather_description'] = smhi_data.get('weather_description')
            combined['wind_speed'] = smhi_data.get('wind_speed')
            combined['precipitation'] = smhi_data.get('precipitation')
            combined['tomorrow'] = smhi_data.get('tomorrow', {})
        
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
            'tomorrow': {
                'temperature': 18.0,
                'weather_description': 'Okänt'
            }
        }

def test_weather_client():
    """Test-funktion"""
    # Test-config
    config = {
        'location': {
            'name': 'Stockholm',
            'latitude': 59.3293,
            'longitude': 18.0686
        },
        'api_keys': {}
    }
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Testa klient
    client = WeatherClient(config)
    weather_data = client.get_current_weather()
    
    print("🧪 Test av WeatherClient:")
    print(json.dumps(weather_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_weather_client()