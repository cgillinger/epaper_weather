#!/usr/bin/env python3
"""
Fix för weather_client.py - Datetime timezone-problem
Kör detta för att automatiskt fixa datetime-felet
"""

def fix_weather_client():
    """Fixa datetime-problemet i weather_client.py"""
    
    try:
        with open('weather_client.py', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ weather_client.py hittades inte!")
        return False
    
    print("🔧 Fixar datetime timezone-problem...")
    
    # Hitta och ersätt den problematiska koden
    old_code = '''            # Hitta närmaste tidpunkt
            now = datetime.now()
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
                    break'''
    
    new_code = '''            # Hitta närmaste tidpunkt
            from datetime import timezone
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
                    break'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Skriv tillbaka
        with open('weather_client.py', 'w') as f:
            f.write(content)
        
        print("✅ Datetime-fel fixat!")
        return True
    else:
        print("⚠️ Kunde inte hitta exakt kod att ersätta")
        return False

if __name__ == "__main__":
    fix_weather_client()

