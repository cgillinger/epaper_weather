#!/usr/bin/env python3
"""
Test Script för Precipitation Trigger - UPPDATERAD MED OBSERVATIONS-STÖD
Simulerar nederbörd-data från SMHI Observations + Prognoser
NYTT: Testar prioriteringslogik mellan observations och prognoser
SÄKER DESIGN: Config-driven, automatisk timeout, production-safe
"""

import json
import os
import time
from datetime import datetime, timedelta

class PrecipitationTester:
    """Säker test-data injection för precipitation module MED OBSERVATIONS-STÖD"""
    
    def __init__(self):
        self.test_active = False
        self.test_file = "cache/test_precipitation.json"
        
        # Säkerställ att cache-mapp finns
        os.makedirs("cache", exist_ok=True)
        
        print("🧪 Precipitation Trigger Tester - UPPDATERAD MED OBSERVATIONS")
        print("🔒 Kräver debug.enabled=true OCH debug.allow_test_data=true i config.json") 
        print("🆕 NYTT: Stöd för SMHI Observations + Prioriteringslogik-testning")
    
    def inject_precipitation_data(self, precipitation_mm=1.5, forecast_2h_mm=2.0, 
                                precipitation_observed=None, duration_minutes=60, 
                                test_type="combined"):
        """
        UPPDATERAD: Injicera säker test nederbörd-data med observations-stöd
        
        Args:
            precipitation_mm: Aktuell nederbörd från prognoser (mm/h)
            forecast_2h_mm: Prognostiserad nederbörd (mm/h)  
            precipitation_observed: SMHI observations nederbörd (mm/h, None=auto)
            duration_minutes: Hur länge test-data ska vara aktiv
            test_type: "observations", "forecast", "combined", "conflict"
        """
        print(f"\n🧪 Injicerar säker test-data - TYP: {test_type.upper()}")
        
        # SMART AUTO-SÄTTNING av precipitation_observed baserat på test_type
        if precipitation_observed is None:
            if test_type == "observations":
                precipitation_observed = precipitation_mm  # Samma som prognos
            elif test_type == "forecast":  
                precipitation_observed = 0.0  # Regnar inte enligt observations
            elif test_type == "combined":
                precipitation_observed = precipitation_mm  # Konsistent data
            elif test_type == "conflict":
                precipitation_observed = 0.0  # Skapar konflikt med prognos
            else:
                precipitation_observed = precipitation_mm  # Default
        
        print(f"   💧 Prognos nederbörd: {precipitation_mm}mm/h") 
        print(f"   📊 Observations nederbörd: {precipitation_observed}mm/h")
        print(f"   🌦️ Prognos 2h: {forecast_2h_mm}mm/h")
        print(f"   ⏰ Timeout: {duration_minutes} minuter")
        
        # PRIORITERINGSLOGIK INFO
        if precipitation_observed > 0 and precipitation_mm != precipitation_observed:
            print(f"   ⚡ PRIORITERING: Observations ({precipitation_observed}mm/h) kommer användas istället för prognos ({precipitation_mm}mm/h)")
        elif precipitation_observed > 0:
            print(f"   ✅ KONSISTENT: Observations och prognos stämmer överens ({precipitation_observed}mm/h)")
        else:
            print(f"   📡 PROGNOS-ONLY: Observations visar 0mm/h, använder prognos ({precipitation_mm}mm/h)")
        
        expires_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        # Bestäm cykel-väder varning baserat på tröskelvärde (använd prioriterat värde)
        effective_precipitation = precipitation_observed if precipitation_observed > 0 else precipitation_mm
        cycling_warning = effective_precipitation > 0 or forecast_2h_mm > 0.2
        max_precip = max(effective_precipitation, forecast_2h_mm)
        
        # Skapa realistisk cykel-väder data
        cycling_weather = {
            "cycling_warning": cycling_warning,
            "precipitation_mm": max_precip,
            "precipitation_type": self._get_precipitation_type(max_precip),
            "precipitation_description": self._get_intensity_description(max_precip),
            "forecast_time": self._get_forecast_time(forecast_2h_mm > 0),
            "reason": f"Test: {max_precip:.1f}mm/h nederbörd" if cycling_warning else "Test: Inget regn"
        }
        
        test_data = {
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "test_type": test_type,
            "test_description": f"Test {test_type}: obs={precipitation_observed}mm/h, prog={precipitation_mm}mm/h, forecast={forecast_2h_mm}mm/h",
            
            # UPPDATERAD: Stöd för både prognoser och observations
            "precipitation": precipitation_mm,                    # Prognosdata (SMHI forecast)
            "precipitation_observed": precipitation_observed,     # NYTT: Observations data (SMHI observations)
            "forecast_precipitation_2h": forecast_2h_mm,         # Prognos kommande 2h
            
            # Cykel-väder data för komplett test
            "cycling_weather": cycling_weather
        }
        
        # Spara test-data
        with open(self.test_file, "w", encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print("✅ Säker test-data injicerad med OBSERVATIONS-stöd")
        print(f"⏰ Auto-cleanup: {expires_at.strftime('%H:%M:%S')}")
        
        # UPPDATERAD trigger-analys med prioriteringslogik
        self._analyze_trigger_activation(precipitation_mm, precipitation_observed, forecast_2h_mm)
        
        print("\n🔄 NÄSTA STEG: Restart daemon för att aktivera test-data")
        print("   python3 restart.py")
        
        self.test_active = True
    
    def _analyze_trigger_activation(self, prog_precip, obs_precip, forecast_2h):
        """Analysera exakt hur triggern kommer aktiveras med prioriteringslogik"""
        print(f"\n🎯 TRIGGER-ANALYS MED PRIORITERINGSLOGIK:")
        
        # Simulera weather_client prioriteringslogik
        effective_precipitation = obs_precip if obs_precip > 0 else prog_precip
        
        print(f"   📊 Rå värden:")
        print(f"      precipitation (prognos) = {prog_precip}")
        print(f"      precipitation_observed = {obs_precip}")
        print(f"      forecast_precipitation_2h = {forecast_2h}")
        
        print(f"   🔄 Weather_client prioritering:")
        if obs_precip > 0:
            print(f"      → OBSERVATIONS prioriteras: {obs_precip}mm/h")
        else:
            print(f"      → Fallback till PROGNOS: {prog_precip}mm/h")
        print(f"      → Effektivt precipitation = {effective_precipitation}")
        
        print(f"   🧮 Trigger condition evaluation:")
        cond1 = effective_precipitation > 0
        cond2 = forecast_2h > 0.2
        final_result = cond1 or cond2
        
        print(f"      precipitation > 0 = {effective_precipitation} > 0 = {cond1}")
        print(f"      forecast_precipitation_2h > 0.2 = {forecast_2h} > 0.2 = {cond2}")
        print(f"      FINAL: {cond1} OR {cond2} = {final_result}")
        
        if final_result:
            print(f"   🔥 TRIGGER AKTIVERAS → bottom_section = precipitation_active")
            if cond1:
                source = "OBSERVATIONS" if obs_precip > 0 else "PROGNOS"
                print(f"   💥 Aktiverad av: {source} nederbörd ({effective_precipitation}mm/h)")
            if cond2:
                print(f"   💥 Aktiverad av: Prognos 2h ({forecast_2h}mm/h)")
        else:
            print(f"   💤 Trigger aktiveras INTE → bottom_section = normal")
    
    # NYTT: Fördefinierade test-scenarion med observations-stöd
    def test_observations_only(self):
        """Test: Endast observations visar regn, prognoser visar 0"""
        print("\n📊 TEST-SCENARIO: Observations-only (Regnar nu enligt Observatorielunden)")
        self.inject_precipitation_data(
            precipitation_mm=0.0,      # Prognos: inget regn
            precipitation_observed=1.8, # Observations: regnar just nu!
            forecast_2h_mm=0.0,        # Ingen prognos-nederbörd
            duration_minutes=45,
            test_type="observations"
        )
    
    def test_forecast_only(self):
        """Test: Endast prognoser visar regn, observations visar 0"""
        print("\n📡 TEST-SCENARIO: Forecast-only (Regn förväntat, regnar inte nu)")
        self.inject_precipitation_data(
            precipitation_mm=2.2,      # Prognos: regn förväntat
            precipitation_observed=0.0, # Observations: regnar inte just nu
            forecast_2h_mm=1.8,        # Regn kommande 2h
            duration_minutes=45,
            test_type="forecast"
        )
    
    def test_conflict_scenario(self):
        """Test: Konflikt mellan observations och prognoser"""
        print("\n⚡ TEST-SCENARIO: Konflikt (Observations vs Prognoser)")
        self.inject_precipitation_data(
            precipitation_mm=3.5,      # Prognos: kraftigt regn
            precipitation_observed=0.2, # Observations: bara lätt duggregn
            forecast_2h_mm=0.8,        # Måttlig prognos
            duration_minutes=60,
            test_type="conflict"
        )
        print("   🎯 FÖRVÄNTAT: Observations (0.2mm/h) prioriteras över prognos (3.5mm/h)")
    
    def test_quality_scenarios(self):
        """Test: Olika kvalitetsscenarier för observations"""
        print("\n🔬 TEST-SCENARIO: Observations-kvalitet (simulerar dålig data)")
        # Simulera scenario där observations är opålitlig
        self.inject_precipitation_data(
            precipitation_mm=2.0,      # Pålitlig prognos
            precipitation_observed=0.0, # Observations kanske felaktig
            forecast_2h_mm=1.2,        # Kommande regn
            duration_minutes=30,
            test_type="quality_test"
        )
        print("   📋 SYFTE: Testa när observations är 0 men prognoser visar regn")
        print("   🎯 FÖRVÄNTAT: Fallback till prognosdata eftersom observations=0")
    
    def test_cycling_threshold(self):
        """Test: Cykel-väder tröskelvärde (0.2mm/h)"""
        print("\n🚴‍♂️ TEST-SCENARIO: Cykel-väder tröskelvärde")
        self.inject_precipitation_data(
            precipitation_mm=0.0,      # Regnar inte nu
            precipitation_observed=0.0, # Observations bekräftar
            forecast_2h_mm=0.25,       # Precis över tröskelvärde (0.2mm/h)
            duration_minutes=30,
            test_type="cycling_threshold"
        )
        print("   🎯 FÖRVÄNTAT: Trigger aktiveras för forecast_precipitation_2h > 0.2")
    
    # Uppdaterade hjälpmetoder (behålls oförändrade från original)
    def _get_precipitation_type(self, mm_per_hour):
        """Bestäm nederbörd-typ baserat på intensitet"""
        if mm_per_hour >= 5.0:
            return "Kraftigt regn"
        elif mm_per_hour >= 1.0:
            return "Måttligt regn"
        elif mm_per_hour > 0:
            return "Lätt regn"
        else:
            return "Ingen"
    
    def _get_intensity_description(self, mm_per_hour):
        """Få intensitetsbeskrivning (samma som weather_client)"""
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
    
    def _get_forecast_time(self, has_forecast):
        """Generera realistisk prognos-tid"""
        if has_forecast:
            future_time = datetime.now() + timedelta(minutes=30)
            return future_time.strftime('%H:%M')
        return ""
    
    def clear_test_data(self):
        """Rensa test-data och återgå till normal drift"""
        try:
            if os.path.exists(self.test_file):
                os.remove(self.test_file)
                print("🗑️ Test-data rensad")
                print("🔄 NÄSTA STEG: Restart daemon för normal drift")
                print("   python3 restart.py")
                self.test_active = False
            else:
                print("💭 Ingen test-data att rensa")
        except Exception as e:
            print(f"❌ Fel vid rensning: {e}")
    
    def status(self):
        """UPPDATERAD: Visa aktuell test-status med observations-info"""
        if os.path.exists(self.test_file):
            try:
                with open(self.test_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                
                print("🧪 TEST-LÄGE AKTIVT:")
                print(f"   🎯 Test-typ: {data.get('test_type', 'okänd')}")
                print(f"   💧 Nederbörd (prognos): {data.get('precipitation', 0)}mm/h")
                print(f"   📊 Nederbörd (observations): {data.get('precipitation_observed', 'N/A')}mm/h")
                print(f"   🌦️ Prognos 2h: {data.get('forecast_precipitation_2h', 0)}mm/h")
                print(f"   📝 Beskrivning: {data.get('test_description', 'N/A')}")
                print(f"   🕒 Skapad: {data.get('created_at', 'Okänd')}")
                print(f"   ⏰ Upphör: {data.get('expires_at', 'Okänd')}")
                
                # Kontrollera timeout
                if 'expires_at' in data:
                    try:
                        expires = datetime.fromisoformat(data['expires_at'])
                        now = datetime.now()
                        if now > expires:
                            print("   ⚠️ STATUS: UTGÅNGEN (kommer rensas vid nästa daemon-start)")
                        else:
                            remaining = expires - now
                            remaining_minutes = int(remaining.total_seconds() / 60)
                            print(f"   ✅ STATUS: AKTIV ({remaining_minutes} min kvar)")
                    except:
                        print("   ❓ STATUS: Okänd timeout")
                
                # UPPDATERAD: Prioriteringslogik-analys
                prog_precip = data.get('precipitation', 0)
                obs_precip = data.get('precipitation_observed', 0)
                if obs_precip is not None and obs_precip != prog_precip:
                    effective = obs_precip if obs_precip > 0 else prog_precip
                    print(f"\n🔄 PRIORITERINGSLOGIK:")
                    print(f"   Prognos: {prog_precip}mm/h")
                    print(f"   Observations: {obs_precip}mm/h")
                    print(f"   → Effektivt använt: {effective}mm/h")
                
                # Visa cykel-väder info
                cycling = data.get('cycling_weather', {})
                if cycling:
                    print(f"\n🚴‍♂️ Cykel-väder test:")
                    print(f"   Varning: {cycling.get('cycling_warning', False)}")
                    print(f"   Nederbörd: {cycling.get('precipitation_mm', 0):.1f}mm/h")
                    print(f"   Typ: {cycling.get('precipitation_type', 'Okänd')}")
                    print(f"   Orsak: {cycling.get('reason', 'N/A')}")
                
            except Exception as e:
                print(f"⚠️ Korrupt test-data fil: {e}")
        else:
            print("✅ Normal drift (inget test aktivt)")
            print("🔍 Test-status: weather_client läser riktig data från API:er")
    
    def show_trigger_analysis(self):
        """UPPDATERAD: Analysera trigger-conditions med prioriteringslogik"""
        print("\n🎯 TRIGGER-ANALYS MED PRIORITERINGSLOGIK:")
        
        if not os.path.exists(self.test_file):
            print("   💤 Inga test-data - triggers baseras på riktig väderdata")
            print("   📋 Condition: precipitation > 0 OR forecast_precipitation_2h > 0.2")
            print("   🔄 Prioritering: precipitation_observed > precipitation (prognoser)")
            return
        
        try:
            with open(self.test_file, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            prog_precip = data.get('precipitation', 0)
            obs_precip = data.get('precipitation_observed', 0)
            forecast = data.get('forecast_precipitation_2h', 0)
            
            print(f"   📊 Test-värden:")
            print(f"      precipitation (prognos) = {prog_precip}")
            print(f"      precipitation_observed = {obs_precip}")
            print(f"      forecast_precipitation_2h = {forecast}")
            
            print(f"   🔄 Weather_client prioritering:")
            effective_precip = obs_precip if obs_precip > 0 else prog_precip
            if obs_precip > 0:
                print(f"      → OBSERVATIONS används: {obs_precip}mm/h")
            else:
                print(f"      → Fallback till PROGNOS: {prog_precip}mm/h")
            print(f"      → final precipitation value = {effective_precip}")
            
            print(f"   🧮 Condition evaluation:")
            cond1 = effective_precip > 0
            cond2 = forecast > 0.2
            final_result = cond1 or cond2
            
            print(f"      precipitation > 0 = {effective_precip} > 0 = {cond1}")
            print(f"      forecast_precipitation_2h > 0.2 = {forecast} > 0.2 = {cond2}")
            print(f"      FINAL: {cond1} OR {cond2} = {final_result}")
            
            if final_result:
                print(f"   🔥 TRIGGER AKTIVERAS → bottom_section = precipitation_active")
                print(f"   🔄 Layout växlar från 'normal' till 'precipitation_active'")
                print(f"   📱 E-Paper visar nederbörd-modul istället för klocka+status")
                
                # Visa vilken condition som aktiverade
                if cond1:
                    source = "OBSERVATIONS" if obs_precip > 0 else "PROGNOS"
                    print(f"   💥 Aktiverad av: {source} nederbörd ({effective_precip}mm/h)")
                if cond2:
                    print(f"   💥 Aktiverad av: Prognos 2h ({forecast}mm/h)")
            else:
                print(f"   💤 Trigger aktiveras INTE → bottom_section = normal") 
                print(f"   📱 E-Paper visar normal layout (klocka+status)")
                
        except Exception as e:
            print(f"   ❌ Fel vid trigger-analys: {e}")
    
    def validate_config(self):
        """Kontrollera att config.json har korrekta inställningar för test"""
        print("\n🔍 KONFIGURATION-VALIDERING:")
        
        try:
            if not os.path.exists("config.json"):
                print("   ❌ config.json hittades inte!")
                return False
            
            with open("config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            
            debug = config.get('debug', {})
            enabled = debug.get('enabled', False)
            allow_test = debug.get('allow_test_data', False)
            timeout_hours = debug.get('test_timeout_hours', 1)
            
            print(f"   debug.enabled = {enabled}")
            print(f"   debug.allow_test_data = {allow_test}")
            print(f"   debug.test_timeout_hours = {timeout_hours}")
            
            # NYTT: Kontrollera observations-konfiguration
            stockholm_stations = config.get('stockholm_stations', {})
            if stockholm_stations:
                obs_station = stockholm_stations.get('observations_station_id', 'Saknas')
                obs_name = stockholm_stations.get('observations_station_name', 'Saknas')
                print(f"   SMHI Observations station: {obs_station} ({obs_name})")
            else:
                print("   ⚠️ Ingen stockholm_stations konfiguration")
            
            if enabled and allow_test:
                print("   ✅ Konfiguration OK för test-data")
                return True
            else:
                print("   ❌ Test-data blockerat av konfiguration!")
                print("   🔧 FIX: Sätt debug.enabled=true OCH debug.allow_test_data=true")
                return False
                
        except Exception as e:
            print(f"   ❌ Fel vid config-läsning: {e}")
            return False


def show_test_scenarios():
    """UPPDATERAD: Visa alla test-scenarion inklusive observations"""
    print("\n📋 TILLGÄNGLIGA TEST-SCENARION MED OBSERVATIONS-STÖD:")
    print("=" * 80)
    
    # GAMLA SCENARION (uppdaterade med observations-info)
    print("🔄 KLASSISKA SCENARION (uppdaterade):")
    classic_scenarios = [
        {
            "name": "💧 Lätt regn (pågående)",
            "prog": 0.8, "obs": 0.8, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations prioriterat)", 
            "expected": "Regnar nu: 0.8mm/h → Vänta med cykling"
        },
        {
            "name": "🌧️ Måttligt regn (pågående)", 
            "prog": 2.5, "obs": 2.5, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations prioriterat)",
            "expected": "Regnar nu: 2.5mm/h → Måttligt regn"
        },
        {
            "name": "⛈️ Kraftigt regn (pågående + prognos)",
            "prog": 8.0, "obs": 8.0, "forecast": 1.2,
            "trigger": "precipitation > 0 (observations prioriterat)",
            "expected": "Regnar nu: 8.0mm/h → Kraftigt regn"
        },
        {
            "name": "🌦️ Regn väntat (endast prognos)",
            "prog": 1.5, "obs": 0.0, "forecast": 1.5,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, fallback prognos)",
            "expected": "Regn väntat: 1.5mm/h → Startar kl [tid]"
        },
        {
            "name": "🚴‍♂️ Cykel-varning (minimal prognos)",
            "prog": 0.0, "obs": 0.0, "forecast": 0.3,
            "trigger": "forecast_precipitation_2h > 0.2",
            "expected": "Regn väntat: 0.3mm/h → Lätt duggregn"
        }
    ]
    
    for i, scenario in enumerate(classic_scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   Data: prog={scenario['prog']}mm/h, obs={scenario['obs']}mm/h, forecast={scenario['forecast']}mm/h")
        print(f"   Trigger: {scenario['trigger']}")
        print(f"   Förväntat: {scenario['expected']}")
        print()
    
    # NYA SCENARION (observations-specifika)
    print("🆕 NYA OBSERVATIONS-SCENARION:")
    new_scenarios = [
        {
            "name": "📊 Observations-only (Regnar enligt Observatorielunden)",
            "prog": 0.0, "obs": 1.8, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations visar regn, prognoser visar 0)",
            "expected": "Prioriterar observations: 1.8mm/h regn"
        },
        {
            "name": "📡 Forecast-only (Regn förväntat, regnar inte nu)",
            "prog": 2.2, "obs": 0.0, "forecast": 1.8,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, fallback prognos)",
            "expected": "Fallback till prognos eftersom observations=0"
        },
        {
            "name": "⚡ Konflikt (Observations vs Prognoser)",
            "prog": 3.5, "obs": 0.2, "forecast": 0.8,
            "trigger": "precipitation > 0 (observations 0.2mm/h prioriteras över prognos 3.5mm/h)",
            "expected": "Observations prioriteras: 0.2mm/h istället för 3.5mm/h"
        },
        {
            "name": "🔬 Kvalitetstest (Observations opålitlig)",
            "prog": 2.0, "obs": 0.0, "forecast": 1.2,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, använder prognos+forecast)",
            "expected": "Fallback till prognosdata när observations=0"
        }
    ]
    
    for i, scenario in enumerate(new_scenarios, 6):
        print(f"{i}. {scenario['name']}")
        print(f"   Data: prog={scenario['prog']}mm/h, obs={scenario['obs']}mm/h, forecast={scenario['forecast']}mm/h")
        print(f"   Trigger: {scenario['trigger']}")
        print(f"   Förväntat: {scenario['expected']}")
        print()


def main():
    """UPPDATERAD: Huvudmeny med observations-test-scenarion"""
    tester = PrecipitationTester()
    
    while True:
        print("\n" + "="*80)
        print("🧪 PRECIPITATION TRIGGER TESTER - MED OBSERVATIONS-STÖD")
        print("="*80)
        
        print("📊 KLASSISKA SCENARION (uppdaterade):")
        print("1. 💧 Simulera lätt regn (0.8mm/h prog+obs)")
        print("2. 🌧️ Simulera måttligt regn (2.5mm/h prog+obs)")  
        print("3. ⛈️ Simulera kraftigt regn (8.0mm/h prog+obs)")
        print("4. 🌦️ Simulera prognos utan pågående regn (0 obs + 1.5mm/h prognos)")
        print("5. 🚴‍♂️ Simulera cykel-varning (0 obs + 0.3mm/h forecast)")
        
        print("\n🆕 NYA OBSERVATIONS-SCENARION:")
        print("6. 📊 Test observations-only (1.8mm/h obs, 0 prognos)")
        print("7. 📡 Test forecast-only (0 obs, 2.2mm/h prognos)")
        print("8. ⚡ Test konflikt-scenario (0.2mm/h obs vs 3.5mm/h prognos)")
        print("9. 🔬 Test kvalitetsscenario (0 obs, pålitlig prognos)")
        print("10. 🚴‍♂️ Test cykel-tröskelvärde (0.25mm/h forecast)")
        
        print("\n🔧 KONTROLL & ANALYS:")
        print("11. 📊 Visa test-status")
        print("12. 🎯 Analysera trigger-conditions")
        print("13. 🔍 Validera konfiguration")
        print("14. 📋 Visa alla test-scenarion")
        print("15. 🗑️ Rensa test-data (normal drift)")
        print("16. 🚪 Avsluta")
        
        try:
            choice = input("\nVälj alternativ (1-16): ").strip()
            
            # Klassiska scenarion (uppdaterade)
            if choice == "1":
                tester.inject_precipitation_data(0.8, 0.0, 0.8, 30, "combined")
            elif choice == "2":
                tester.inject_precipitation_data(2.5, 0.0, 2.5, 45, "combined")
            elif choice == "3":
                tester.inject_precipitation_data(8.0, 1.2, 8.0, 60, "combined")
            elif choice == "4":
                tester.inject_precipitation_data(1.5, 1.5, 0.0, 45, "forecast")
            elif choice == "5":
                tester.inject_precipitation_data(0.0, 0.3, 0.0, 30, "forecast")
            
            # Nya observations-scenarion
            elif choice == "6":
                tester.test_observations_only()
            elif choice == "7":
                tester.test_forecast_only()
            elif choice == "8":
                tester.test_conflict_scenario()
            elif choice == "9":
                tester.test_quality_scenarios()
            elif choice == "10":
                tester.test_cycling_threshold()
            
            # Kontroll och analys
            elif choice == "11":
                tester.status()
            elif choice == "12":
                tester.show_trigger_analysis()
            elif choice == "13":
                tester.validate_config()
            elif choice == "14":
                show_test_scenarios()
            elif choice == "15":
                tester.clear_test_data()
            elif choice == "16":
                print("👋 Avslutar precipitation tester")
                break
            else:
                print("❌ Ogiltigt val")
                
        except KeyboardInterrupt:
            print("\n👋 Avbrutet av användare")
            break
        except Exception as e:
            print(f"❌ Fel: {e}")

if __name__ == "__main__":
    print("🔒 SÄKERHETSINFO: Test-data kräver debug.allow_test_data=true i config.json")
    print("⏰ Test-data rensas automatiskt efter 1 timme")
    print("🏭 Production-safe: Ignoreras om debug.enabled=false")
    print("🆕 NYTT: Stöd för SMHI Observations + Prioriteringslogik-testning")
    main()
