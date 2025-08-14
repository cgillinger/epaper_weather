#!/usr/bin/env python3
"""
Debug script för att analysera SMHI forecast data extraction
Kontrollerar varför forecast_precipitation_2h = 0 när weather_symbol = 18
"""

import sys
import os
import json
sys.path.append('modules')

from weather_client import WeatherClient

def debug_forecast_extraction():
    """Detaljerad analys av SMHI forecast data"""
    
    print("🔍 DEBUGGING FORECAST DATA EXTRACTION")
    print("=" * 50)
    
    # Ladda config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Skapa client
    client = WeatherClient(config)
    
    print("\n📡 HÄMTAR FULL SMHI FORECAST DATA...")
    smhi_forecast_data = client.get_smhi_forecast_data()
    
    if not smhi_forecast_data or 'timeSeries' not in smhi_forecast_data:
        print("❌ Ingen SMHI forecast data!")
        return
    
    print(f"✅ SMHI forecast data hämtad: {len(smhi_forecast_data['timeSeries'])} tidpunkter")
    
    # Analysera de första 5 prognoserna
    print("\n📊 ANALYS AV FÖRSTA 5 PROGNOSERNA:")
    print("-" * 40)
    
    for i, forecast in enumerate(smhi_forecast_data['timeSeries'][:5]):
        valid_time = forecast.get('validTime', 'N/A')
        print(f"\n{i+1}. {valid_time}")
        
        # Extrahera parametrar
        params = {}
        for param in forecast.get('parameters', []):
            name = param.get('name')
            values = param.get('values', [])
            if values:
                params[name] = values[0]
        
        # Visa relevanta parametrar
        weather_symbol = params.get('Wsymb2', 'N/A')
        precipitation = params.get('pmin', 'N/A')  # mm/h
        precip_type = params.get('pcat', 'N/A')
        temperature = params.get('t', 'N/A')
        
        print(f"   Weather symbol: {weather_symbol}")
        print(f"   Precipitation: {precipitation} mm/h")
        print(f"   Precip type: {precip_type}")
        print(f"   Temperature: {temperature}°C")
        
        # Visa vad weather_symbol betyder
        if isinstance(weather_symbol, (int, float)):
            symbol_desc = get_weather_description(int(weather_symbol))
            print(f"   Symbol meaning: {symbol_desc}")
    
    # Analysera cykel-väder specifikt
    print("\n🚴‍♂️ CYKEL-VÄDER ANALYS:")
    print("-" * 30)
    
    cycling_analysis = client.analyze_cycling_weather(smhi_forecast_data)
    print(f"Cycling warning: {cycling_analysis.get('cycling_warning', 'N/A')}")
    print(f"Precipitation mm: {cycling_analysis.get('precipitation_mm', 'N/A')}")
    print(f"Reason: {cycling_analysis.get('reason', 'N/A')}")
    
    # Leta efter nästa timmes data specifikt
    print("\n⏰ KOMMANDE TIMMEN SPECIFIKT:")
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    next_hour = now + timedelta(hours=1)
    
    next_hour_forecasts = []
    for forecast in smhi_forecast_data['timeSeries']:
        forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
        if now <= forecast_time <= next_hour:
            next_hour_forecasts.append((forecast_time, forecast))
    
    print(f"Found {len(next_hour_forecasts)} forecasts for next hour")
    
    for forecast_time, forecast in next_hour_forecasts:
        params = {}
        for param in forecast.get('parameters', []):
            name = param.get('name')
            values = param.get('values', [])
            if values:
                params[name] = values[0]
        
        precipitation = params.get('pmin', 0)
        weather_symbol = params.get('Wsymb2', 0)
        
        print(f"  {forecast_time.strftime('%H:%M')}: Symbol {weather_symbol}, Precipitation {precipitation}mm/h")

def get_weather_description(symbol: int) -> str:
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

if __name__ == "__main__":
    debug_forecast_extraction()
