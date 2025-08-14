#!/usr/bin/env python3
"""
Debug script för att analysera tids-filtrering i analyze_cycling_weather
Förklarar varför "19:00" fortfarande visas kl 19:26
"""

import sys
import os
import json
from datetime import datetime, timezone, timedelta
sys.path.append('modules')

from weather_client import WeatherClient

def debug_time_filtering():
    """Detaljerad analys av tids-filtrering i cykel-väder"""
    
    print("🕐 DEBUGGING TIDS-FILTRERING I CYKEL-VÄDER")
    print("=" * 50)
    
    # Visa aktuell tid
    now_local = datetime.now()
    now_utc = datetime.now(timezone.utc)
    
    print(f"\n⏰ AKTUELL TID:")
    print(f"   Lokal tid: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   UTC tid: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   Timezone: {now_local.astimezone().tzinfo}")
    
    # Ladda config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Skapa client
    client = WeatherClient(config)
    
    print(f"\n📡 HÄMTAR SMHI FORECAST DATA...")
    smhi_forecast_data = client.get_smhi_forecast_data()
    
    if not smhi_forecast_data or 'timeSeries' not in smhi_forecast_data:
        print("❌ Ingen SMHI forecast data!")
        return
    
    print(f"✅ SMHI forecast data hämtad: {len(smhi_forecast_data['timeSeries'])} tidpunkter")
    
    # Analysera tids-filtrering (samma logik som analyze_cycling_weather)
    print(f"\n🔍 ANALYSERAR TIDS-FILTRERING (samma logik som analyze_cycling_weather):")
    print("-" * 60)
    
    # Kommande 2 timmar (samma som i funktionen)
    future_window_end = now_utc + timedelta(hours=2)
    print(f"Analyserar prognoser mellan:")
    print(f"   Start: {now_utc.strftime('%H:%M')} UTC")
    print(f"   Slut:  {future_window_end.strftime('%H:%M')} UTC")
    
    next_hours_forecasts = []
    all_forecasts_debug = []
    
    for i, forecast in enumerate(smhi_forecast_data['timeSeries'][:10]):  # Bara första 10 för debug
        try:
            forecast_time = datetime.fromisoformat(forecast['validTime'].replace('Z', '+00:00'))
            
            # Extrahera precipitation
            precipitation = 0.0
            for param in forecast.get('parameters', []):
                if param.get('name') == 'pmin' and param.get('values'):
                    precipitation = float(param['values'][0])
                    break
            
            # Debug info
            time_str = forecast_time.strftime('%H:%M')
            is_future = now_utc <= forecast_time
            is_in_window = now_utc <= forecast_time <= future_window_end
            over_threshold = precipitation >= 0.2
            
            debug_info = {
                'index': i,
                'time': time_str,
                'time_full': forecast_time,
                'precipitation': precipitation,
                'is_future': is_future,
                'is_in_window': is_in_window, 
                'over_threshold': over_threshold,
                'would_include': is_in_window and over_threshold
            }
            all_forecasts_debug.append(debug_info)
            
            # Samma condition som i analyze_cycling_weather
            if now_utc <= forecast_time <= future_window_end:
                next_hours_forecasts.append((forecast_time, forecast, precipitation))
                
        except Exception as e:
            print(f"⚠️ Fel vid parsning av forecast {i}: {e}")
            continue
    
    # Visa alla prognoser med debug-info
    print(f"\n📋 ALLA PROGNOSER (första 10):")
    print("Tid   | Nederbörd | Framtid? | I fönster? | >Tröskel? | Inkluderas?")
    print("-" * 65)
    
    for debug in all_forecasts_debug:
        future_mark = "✅" if debug['is_future'] else "❌"
        window_mark = "✅" if debug['is_in_window'] else "❌"  
        threshold_mark = "✅" if debug['over_threshold'] else "❌"
        include_mark = "⚠️ YES" if debug['would_include'] else "❌"
        
        print(f"{debug['time']} | {debug['precipitation']:8.1f} | {future_mark:8} | {window_mark:10} | {threshold_mark:9} | {include_mark}")
    
    # Analysera resulterad lista (samma som funktionen använder)
    print(f"\n🎯 PROGNOSER SOM INKLUDERAS I ANALYS:")
    if next_hours_forecasts:
        print(f"Hittade {len(next_hours_forecasts)} prognoser i 2h-fönstret:")
        
        max_precipitation = 0.0
        warning_forecast_time = None
        
        for forecast_time, forecast, precipitation in next_hours_forecasts:
            print(f"   {forecast_time.strftime('%H:%M')}: {precipitation}mm/h")
            
            if precipitation >= 0.2 and precipitation > max_precipitation:
                max_precipitation = precipitation
                warning_forecast_time = forecast_time
        
        if warning_forecast_time:
            selected_time = warning_forecast_time.strftime('%H:%M')
            print(f"\n⚠️ VALD TID FÖR VARNING: {selected_time}")
            print(f"   Nederbörd: {max_precipitation}mm/h")
            
            # Förklara varför denna tid valdes
            time_diff = (warning_forecast_time - now_utc).total_seconds() / 60
            if time_diff < 0:
                print(f"   🚨 PROBLEMET: Tiden ligger {abs(time_diff):.1f} minuter I DÅTID!")
            else:
                print(f"   ✅ Tiden ligger {time_diff:.1f} minuter i framtiden")
        else:
            print("✅ Ingen nederbörd över tröskelvärde hittad")
    else:
        print("❌ Inga prognoser hittades i 2h-fönstret")
    
    print(f"\n💡 FÖRKLARING AV PROBLEMET:")
    print("Om 19:00 fortfarande visas kl 19:26, beror det troligen på:")
    print("1. SMHI API returnerar 19:00 som en 'giltig' prognos-tidpunkt")
    print("2. Tids-jämförelsen 'now <= forecast_time' tolkar 19:00 som framtida")
    print("3. Timezone-förvirring mellan lokal tid och UTC")

if __name__ == "__main__":
    debug_time_filtering()
