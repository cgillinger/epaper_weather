#!/usr/bin/env python3
"""
Test Script för Precipitation Trigger - FIXAD MED ROBUST CLEANUP
Simulerar nederbörd-data från SMHI Observations + Prognoser
FIXAT: Force-rensning, auto-cleanup, tydlig timing-feedback, intuitivt interface
SÄKER DESIGN: Config-driven, automatisk timeout, production-safe
"""

import json
import os
import time
from datetime import datetime, timedelta

class PrecipitationTester:
    """Säker test-data injection för precipitation module - FIXAD MED ROBUST CLEANUP"""
    
    def __init__(self):
        self.test_active = False
        self.test_file = "cache/test_precipitation.json"
        
        # Säkerställ att cache-mapp finns
        os.makedirs("cache", exist_ok=True)
        
        print("🧪 Precipitation Trigger Tester - FIXAD MED ROBUST CLEANUP")
        print("🔒 Kräver debug.enabled=true OCH debug.allow_test_data=true i config.json") 
        print("🆕 FIXAT: Auto-cleanup, force-rensning, tydlig timing-feedback")
        
        # NYTT: Auto-cleanup av utgången test-data vid start
        self._auto_cleanup_expired_tests()
    
    def _auto_cleanup_expired_tests(self):
        """NYTT: Automatisk rensning av utgången test-data vid script-start"""
        if not os.path.exists(self.test_file):
            return
        
        try:
            with open(self.test_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            if 'expires_at' in test_data:
                expires = datetime.fromisoformat(test_data['expires_at'])
                now = datetime.now()
                
                if now > expires:
                    age_hours = (now - expires).total_seconds() / 3600
                    print(f"🧹 AUTO-CLEANUP: Utgången test-data hittades ({age_hours:.1f}h gammal)")
                    
                    try:
                        os.remove(self.test_file)
                        print(f"✅ Utgången test-data automatiskt rensad")
                        print(f"💡 TIP: Kör 'python3 restart.py' om E-Paper fortfarande visar test-layout")
                    except Exception as e:
                        print(f"⚠️ Kunde inte auto-rensa: {e}")
                        print(f"🔧 Försök manuell rensning med alternativ 15")
                else:
                    remaining = expires - now
                    remaining_minutes = int(remaining.total_seconds() / 60)
                    test_desc = test_data.get('test_description', 'Okänd test')
                    print(f"🧪 BEFINTLIGT TEST AKTIVT: {test_desc}")
                    print(f"⏰ Återstående tid: {remaining_minutes} minuter")
                    print(f"💡 TIP: Välj alternativ 11 för detaljer, eller 15 för att rensa nu")
        
        except Exception as e:
            print(f"⚠️ Fel vid auto-cleanup check: {e}")
    
    def inject_precipitation_data(self, precipitation_mm=1.5, forecast_2h_mm=2.0, 
                                precipitation_observed=None, duration_minutes=60, 
                                test_type="combined"):
        """
        UPPDATERAD: Injicera säker test nederbörd-data med TYDLIG TIMING-FEEDBACK
        """
        print(f"\n🧪 STARTAR TEST-DATA INJECTION")
        print(f"=" * 50)
        print(f"🎯 Test-typ: {test_type.upper()}")
        
        # SMART AUTO-SÄTTNING av precipitation_observed baserat på test_type
        if precipitation_observed is None:
            if test_type == "observations":
                precipitation_observed = precipitation_mm
            elif test_type == "forecast":  
                precipitation_observed = 0.0
            elif test_type == "combined":
                precipitation_observed = precipitation_mm
            elif test_type == "conflict":
                precipitation_observed = 0.0
            else:
                precipitation_observed = precipitation_mm
        
        print(f"📊 DATA-VÄRDEN:")
        print(f"   💧 Prognos nederbörd: {precipitation_mm}mm/h") 
        print(f"   📊 Observations nederbörd: {precipitation_observed}mm/h")
        print(f"   🌦️ Prognos 2h: {forecast_2h_mm}mm/h")
        print(f"   ⏰ Test-varaktighet: {duration_minutes} minuter")
        
        # PRIORITERINGSLOGIK INFO
        print(f"\n🔄 PRIORITERINGSLOGIK:")
        if precipitation_observed > 0 and precipitation_mm != precipitation_observed:
            print(f"   ⚡ OBSERVATIONS ({precipitation_observed}mm/h) kommer prioriteras över prognos ({precipitation_mm}mm/h)")
        elif precipitation_observed > 0:
            print(f"   ✅ KONSISTENT: Observations och prognos stämmer överens ({precipitation_observed}mm/h)")
        else:
            print(f"   📡 PROGNOS-ONLY: Observations=0mm/h, använder prognos ({precipitation_mm}mm/h)")
        
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
        
        # Spara test-data med validering
        try:
            with open(self.test_file, "w", encoding='utf-8') as f:
                json.dump(test_data, f, indent=2, ensure_ascii=False)
            
            # Validera att filen faktiskt sparades
            if os.path.exists(self.test_file):
                file_size = os.path.getsize(self.test_file)
                print(f"\n✅ TEST-DATA SPARAT FRAMGÅNGSRIKT")
                print(f"   📁 Fil: {self.test_file} ({file_size} bytes)")
                print(f"   ⏰ Auto-cleanup: {expires_at.strftime('%H:%M:%S')}")
            else:
                print(f"\n❌ FEL: Test-data sparades inte korrekt!")
                return
            
        except Exception as e:
            print(f"\n❌ FEL vid sparande av test-data: {e}")
            return
        
        # UPPDATERAD trigger-analys med prioriteringslogik
        self._analyze_trigger_activation(precipitation_mm, precipitation_observed, forecast_2h_mm)
        
        # NYTT: TYDLIG TIMING-INSTRUKTION
        print(f"\n" + "="*60)
        print(f"🚀 NÄSTA STEG - EXAKT TIMING:")
        print(f"=" * 60)
        print(f"1️⃣ Restart daemon: python3 restart.py")
        print(f"   ⏰ Tid: 20-30 sekunder (daemon startar om)")
        print(f"")
        print(f"2️⃣ Vänta på E-Paper uppdatering:")
        print(f"   ⏰ Tid: 60-90 sekunder efter restart")
        print(f"   📱 Resultat: Nederbörd-layout ersätter klocka+status")
        print(f"")
        print(f"3️⃣ Bekräfta med screenshot:")
        print(f"   📸 Kommando: python3 screenshot.py --output test_aktiv")
        print(f"   ⏰ Tid: Omedelbart")
        print(f"")
        print(f"💡 TOTAL TID FRÅN NU: ~2 minuter tills E-Paper ändras")
        print(f"=" * 60)
        
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
            print(f"   🔥 TRIGGER KOMMER AKTIVERAS → nederbörd-layout")
            if cond1:
                source = "OBSERVATIONS" if obs_precip > 0 else "PROGNOS"
                print(f"   💥 Aktiverad av: {source} nederbörd ({effective_precipitation}mm/h)")
            if cond2:
                print(f"   💥 Aktiverad av: Prognos 2h ({forecast_2h}mm/h)")
        else:
            print(f"   💤 Trigger kommer INTE aktiveras → normal layout")
    
    # NYTT: Fördefinierade test-scenarion med TYDLIG FEEDBACK
    def test_observations_only(self):
        """Test: Endast observations visar regn, prognoser visar 0"""
        print("\n📊 TEST-SCENARIO: Observations-only")
        print("🎯 SYFTE: Regnar nu enligt Observatorielunden, men prognoser visar 0")
        print("💡 FÖRVÄNTAT: Observations prioriteras, trigger aktiveras")
        self.inject_precipitation_data(
            precipitation_mm=0.0,      # Prognos: inget regn
            precipitation_observed=1.8, # Observations: regnar just nu!
            forecast_2h_mm=0.0,        # Ingen prognos-nederbörd
            duration_minutes=45,
            test_type="observations"
        )
    
    def test_forecast_only(self):
        """Test: Endast prognoser visar regn, observations visar 0"""
        print("\n📡 TEST-SCENARIO: Forecast-only")
        print("🎯 SYFTE: Regn förväntat enligt prognoser, men regnar inte nu")
        print("💡 FÖRVÄNTAT: Fallback till prognoser eftersom observations=0")
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
        print("🎯 SYFTE: Observations och prognoser säger olika saker")
        print("💡 FÖRVÄNTAT: Observations (0.2mm/h) prioriteras över prognos (3.5mm/h)")
        self.inject_precipitation_data(
            precipitation_mm=3.5,      # Prognos: kraftigt regn
            precipitation_observed=0.2, # Observations: bara lätt duggregn
            forecast_2h_mm=0.8,        # Måttlig prognos
            duration_minutes=60,
            test_type="conflict"
        )
    
    def test_quality_scenarios(self):
        """Test: Olika kvalitetsscenarier för observations"""
        print("\n🔬 TEST-SCENARIO: Observations-kvalitet")
        print("🎯 SYFTE: Simulera när observations är opålitlig (0mm/h)")
        print("💡 FÖRVÄNTAT: Fallback till prognosdata eftersom observations=0")
        self.inject_precipitation_data(
            precipitation_mm=2.0,      # Pålitlig prognos
            precipitation_observed=0.0, # Observations kanske felaktig
            forecast_2h_mm=1.2,        # Kommande regn
            duration_minutes=30,
            test_type="quality_test"
        )
    
    def test_cycling_threshold(self):
        """Test: Cykel-väder tröskelvärde (0.2mm/h)"""
        print("\n🚴‍♂️ TEST-SCENARIO: Cykel-väder tröskelvärde")
        print("🎯 SYFTE: Testa precis över cykel-varnings-gränsen (0.2mm/h)")
        print("💡 FÖRVÄNTAT: Trigger aktiveras för forecast_precipitation_2h > 0.2")
        self.inject_precipitation_data(
            precipitation_mm=0.0,      # Regnar inte nu
            precipitation_observed=0.0, # Observations bekräftar
            forecast_2h_mm=0.25,       # Precis över tröskelvärde (0.2mm/h)
            duration_minutes=30,
            test_type="cycling_threshold"
        )
    
    # Uppdaterade hjälpmetoder (behålls oförändrade)
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
        """FIXAD: Robust rensning av test-data med force-option och validering"""
        print(f"\n🗑️ STARTAR TEST-DATA RENSNING")
        print(f"=" * 40)
        
        if not os.path.exists(self.test_file):
            print("💭 Ingen test-data att rensa (filen finns inte)")
            print("✅ Normal drift är redan aktiv")
            return
        
        # Visa vad som ska rensas
        try:
            with open(self.test_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            test_desc = test_data.get('test_description', 'Okänd test')
            print(f"📋 Hittat test: {test_desc}")
            
            # Kontrollera om test redan är utgånget
            if 'expires_at' in test_data:
                expires = datetime.fromisoformat(test_data['expires_at'])
                now = datetime.now()
                if now > expires:
                    age_hours = (now - expires).total_seconds() / 3600
                    print(f"⏰ Test redan utgånget ({age_hours:.1f}h sedan)")
                else:
                    remaining = expires - now
                    remaining_minutes = int(remaining.total_seconds() / 60)
                    print(f"⏰ Test fortfarande aktivt ({remaining_minutes} min kvar)")
            
        except Exception as e:
            print(f"⚠️ Kunde inte läsa test-data fil: {e}")
            print("🔧 Försöker ändå rensa filen...")
        
        # Försök normal rensning
        print(f"🗑️ Rensar test-data fil...")
        try:
            os.remove(self.test_file)
            
            # Validera att rensning lyckades
            if os.path.exists(self.test_file):
                print(f"❌ NORMAL RENSNING MISSLYCKADES - filen finns fortfarande")
                
                # FORCE-RENSNING
                print(f"🔧 FÖRSÖKER FORCE-RENSNING...")
                try:
                    os.chmod(self.test_file, 0o777)  # Sätt full behörighet
                    os.remove(self.test_file)
                    
                    if os.path.exists(self.test_file):
                        print(f"❌ ÄVEN FORCE-RENSNING MISSLYCKADES")
                        print(f"🆘 MANUAL ACTION KRÄVS:")
                        print(f"   rm -f {self.test_file}")
                        print(f"   python3 restart.py")
                        return
                    else:
                        print(f"✅ FORCE-RENSNING LYCKADES")
                    
                except Exception as force_error:
                    print(f"❌ Force-rensning misslyckades: {force_error}")
                    print(f"🆘 MANUAL ACTION KRÄVS:")
                    print(f"   sudo rm -f {self.test_file}")
                    print(f"   python3 restart.py")
                    return
            else:
                print(f"✅ Test-data fil framgångsrikt rensad")
                
                # Dubbelkolla att den verkligen är borta
                time.sleep(0.1)  # Kort paus för filsystem
                if os.path.exists(self.test_file):
                    print(f"⚠️ VARNING: Test-fil återdök efter rensning!")
                else:
                    print(f"✅ Validering OK: Test-fil definitivt borttagen")
        
        except Exception as e:
            print(f"❌ Normal rensning misslyckades: {e}")
            print(f"🔧 MANUAL CLEANUP:")
            print(f"   rm -f {self.test_file}")
            print(f"   python3 restart.py")
            return
        
        # TYDLIG ÅTERSTÄLLNINGS-INSTRUKTION
        print(f"\n" + "="*50)
        print(f"🔄 ÅTERSTÄLLNING TILL NORMAL DRIFT:")
        print(f"=" * 50)
        print(f"1️⃣ Restart daemon: python3 restart.py")
        print(f"   ⏰ Tid: 20-30 sekunder")
        print(f"")
        print(f"2️⃣ Vänta på E-Paper återställning:")
        print(f"   ⏰ Tid: 60-90 sekunder efter restart")
        print(f"   📱 Resultat: Tillbaka till klocka+status layout")
        print(f"")
        print(f"3️⃣ Bekräfta återställning:")
        print(f"   📸 Kommando: python3 screenshot.py --output normal_igen")
        print(f"   ⏰ Tid: Omedelbart")
        print(f"")
        print(f"💡 TOTAL TID FRÅN NU: ~2 minuter tills E-Paper återställs")
        print(f"=" * 50)
        
        self.test_active = False
    
    def status(self):
        """FÖRBÄTTRAD: Visa test-status med tydlig timing-info"""
        print(f"\n📊 TEST-STATUS RAPPORT")
        print(f"=" * 40)
        
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
                
                # FÖRBÄTTRAD timeout-info
                if 'expires_at' in data:
                    try:
                        expires = datetime.fromisoformat(data['expires_at'])
                        created = datetime.fromisoformat(data.get('created_at', data['expires_at']))
                        now = datetime.now()
                        
                        age_minutes = int((now - created).total_seconds() / 60)
                        
                        if now > expires:
                            expired_hours = (now - expires).total_seconds() / 3600
                            print(f"   ⚠️ STATUS: UTGÅNGET ({expired_hours:.1f}h sedan)")
                            print(f"   🔄 ACTION: Välj alternativ 15 för rensning")
                        else:
                            remaining = expires - now
                            remaining_minutes = int(remaining.total_seconds() / 60)
                            print(f"   ✅ STATUS: AKTIVT ({remaining_minutes} min kvar, aktivt i {age_minutes} min)")
                            
                            # Timing-tips baserat på ålder
                            if age_minutes < 5:
                                print(f"   ⏰ TIMING: Test nyligen aktiverat - vänta ~{5-age_minutes} min för E-Paper ändring")
                            else:
                                print(f"   📱 TIMING: E-Paper borde redan visa test-layout")
                    
                    except Exception as time_error:
                        print(f"   ❓ STATUS: Kan inte tolka timeout ({time_error})")
                
                # FÖRBÄTTRAD prioriteringslogik-info
                prog_precip = data.get('precipitation', 0)
                obs_precip = data.get('precipitation_observed', 0)
                if obs_precip is not None and obs_precip != prog_precip:
                    effective = obs_precip if obs_precip > 0 else prog_precip
                    print(f"\n🔄 PRIORITERINGSLOGIK:")
                    print(f"   Prognos: {prog_precip}mm/h")
                    print(f"   Observations: {obs_precip}mm/h")
                    print(f"   → Effektivt använt: {effective}mm/h")
                    
                    if obs_precip > 0:
                        print(f"   💡 OBSERVATIONS prioriteras")
                    else:
                        print(f"   💡 Fallback till PROGNOS")
                
                # Cykel-väder info
                cycling = data.get('cycling_weather', {})
                if cycling:
                    print(f"\n🚴‍♂️ Cykel-väder test:")
                    print(f"   Varning: {'⚠️ AKTIV' if cycling.get('cycling_warning', False) else '✅ INAKTIV'}")
                    print(f"   Nederbörd: {cycling.get('precipitation_mm', 0):.1f}mm/h")
                    print(f"   Typ: {cycling.get('precipitation_type', 'Okänd')}")
                    print(f"   Orsak: {cycling.get('reason', 'N/A')}")
                
            except Exception as e:
                print(f"⚠️ Korrupt test-data fil: {e}")
                print(f"🔧 Rekommendation: Välj alternativ 15 för force-rensning")
        else:
            print("✅ NORMAL DRIFT AKTIV")
            print("   📋 Ingen test-data hittades")
            print("   🔍 Weather_client läser riktig data från API:er")
            print("   📱 E-Paper visar verklig väderdata")
    
    def show_trigger_analysis(self):
        """FÖRBÄTTRAD: Trigger-analys med tydlig förklaring"""
        print(f"\n🎯 TRIGGER-ANALYS MED PRIORITERINGSLOGIK")
        print(f"=" * 50)
        
        if not os.path.exists(self.test_file):
            print("💤 INGEN TEST-DATA AKTIV")
            print("   📋 Triggers baseras på riktig väderdata från API:er")
            print("   🔄 Condition: precipitation > 0 OR forecast_precipitation_2h > 0.2")
            print("   📊 Prioritering: precipitation_observed > precipitation (prognoser)")
            print("   💡 Kör ett test-scenario för att se trigger-analys i aktion")
            return
        
        try:
            with open(self.test_file, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            prog_precip = data.get('precipitation', 0)
            obs_precip = data.get('precipitation_observed', 0)
            forecast = data.get('forecast_precipitation_2h', 0)
            
            print(f"📊 TEST-DATA VÄRDEN:")
            print(f"   precipitation (prognos) = {prog_precip}")
            print(f"   precipitation_observed = {obs_precip}")
            print(f"   forecast_precipitation_2h = {forecast}")
            
            print(f"\n🔄 WEATHER_CLIENT PRIORITERING:")
            effective_precip = obs_precip if obs_precip > 0 else prog_precip
            if obs_precip > 0:
                print(f"   → OBSERVATIONS används: {obs_precip}mm/h")
                print(f"   💡 Observatorielunden-data prioriteras över prognoser")
            else:
                print(f"   → Fallback till PROGNOS: {prog_precip}mm/h")
                print(f"   💡 Observations är 0, använder prognosdata istället")
            print(f"   → FINAL precipitation value = {effective_precip}")
            
            print(f"\n🧮 TRIGGER CONDITION EVALUATION:")
            cond1 = effective_precip > 0
            cond2 = forecast > 0.2
            final_result = cond1 or cond2
            
            print(f"   Condition 1: precipitation > 0")
            print(f"                {effective_precip} > 0 = {cond1}")
            print(f"   Condition 2: forecast_precipitation_2h > 0.2")
            print(f"                {forecast} > 0.2 = {cond2}")
            print(f"   FINAL RESULT: {cond1} OR {cond2} = {final_result}")
            
            print(f"\n🎯 FÖRVÄNTAT RESULTAT:")
            if final_result:
                print(f"   🔥 TRIGGER AKTIVERAS → bottom_section = precipitation_active")
                print(f"   🔄 Layout växlar från 'normal' till 'precipitation_active'")
                print(f"   📱 E-Paper visar nederbörd-modul istället för klocka+status")
                
                # Visa vilken condition som aktiverade
                activators = []
                if cond1:
                    source = "OBSERVATIONS" if obs_precip > 0 else "PROGNOS"
                    activators.append(f"{source} nederbörd ({effective_precip}mm/h)")
                if cond2:
                    activators.append(f"Prognos 2h ({forecast}mm/h)")
                
                print(f"   💥 Aktiverat av: {' OCH '.join(activators)}")
            else:
                print(f"   💤 TRIGGER AKTIVERAS INTE → bottom_section = normal") 
                print(f"   📱 E-Paper visar normal layout (klocka+status)")
                print(f"   💡 Alla värden är under tröskelnivåerna")
                
        except Exception as e:
            print(f"❌ Fel vid trigger-analys: {e}")
    
    def validate_config(self):
        """FÖRBÄTTRAD: Config-validering med actionable feedback"""
        print(f"\n🔍 KONFIGURATION-VALIDERING")
        print(f"=" * 40)
        
        try:
            if not os.path.exists("config.json"):
                print("❌ config.json hittades inte!")
                print("🔧 ACTION: Kontrollera att du kör från rätt katalog")
                return False
            
            with open("config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            
            debug = config.get('debug', {})
            enabled = debug.get('enabled', False)
            allow_test = debug.get('allow_test_data', False)
            timeout_hours = debug.get('test_timeout_hours', 1)
            
            print(f"🔧 DEBUG-INSTÄLLNINGAR:")
            print(f"   debug.enabled = {enabled}")
            print(f"   debug.allow_test_data = {allow_test}")
            print(f"   debug.test_timeout_hours = {timeout_hours}")
            
            # OBSERVATIONS-konfiguration
            stockholm_stations = config.get('stockholm_stations', {})
            print(f"\n📊 OBSERVATIONS-KONFIGURATION:")
            if stockholm_stations:
                obs_station = stockholm_stations.get('observations_station_id', 'Saknas')
                obs_name = stockholm_stations.get('observations_station_name', 'Saknas')
                print(f"   SMHI Station: {obs_station} ({obs_name})")
                
                alt_station = stockholm_stations.get('alternative_station_id', 'Saknas')
                alt_name = stockholm_stations.get('alternative_station_name', 'Saknas')
                print(f"   Fallback Station: {alt_station} ({alt_name})")
            else:
                print("   ⚠️ Ingen stockholm_stations konfiguration")
            
            # VALIDATION RESULTAT
            print(f"\n🎯 VALIDERING:")
            if enabled and allow_test:
                print("   ✅ Konfiguration OK för test-data")
                print("   🚀 Test-system är aktiverat och redo att användas")
                return True
            else:
                print("   ❌ Test-data blockerat av konfiguration!")
                print("   🔧 FIX KRÄVS:")
                if not enabled:
                    print("      - Sätt debug.enabled = true i config.json")
                if not allow_test:
                    print("      - Sätt debug.allow_test_data = true i config.json")
                print("   💡 Efter fix: restart daemon med python3 restart.py")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Felaktig JSON-syntax i config.json: {e}")
            print(f"🔧 ACTION: Kontrollera kommatecken och paranteser")
            return False
        except Exception as e:
            print(f"❌ Fel vid config-läsning: {e}")
            return False


def show_test_scenarios():
    """FÖRBÄTTRAD: Visa alla test-scenarion med tydliga förväntningar"""
    print("\n📋 TILLGÄNGLIGA TEST-SCENARION MED OBSERVATIONS-STÖD")
    print("=" * 80)
    
    # KLASSISKA SCENARION (uppdaterade med observations-info)
    print("🔄 KLASSISKA SCENARION (uppdaterade med observations):")
    classic_scenarios = [
        {
            "name": "💧 Lätt regn (pågående)",
            "prog": 0.8, "obs": 0.8, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations prioriterat)", 
            "expected": "Nederbörd-layout: 'Regnar nu 0.8mm/h' → Vänta med cykling",
            "timing": "~2 min från aktivering till E-Paper ändring"
        },
        {
            "name": "🌧️ Måttligt regn (pågående)", 
            "prog": 2.5, "obs": 2.5, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations prioriterat)",
            "expected": "Nederbörd-layout: 'Regnar nu 2.5mm/h' → Måttligt regn",
            "timing": "~2 min från aktivering till E-Paper ändring"
        },
        {
            "name": "⛈️ Kraftigt regn (pågående + prognos)",
            "prog": 8.0, "obs": 8.0, "forecast": 1.2,
            "trigger": "precipitation > 0 (observations prioriterat)",
            "expected": "Nederbörd-layout: 'Regnar nu 8.0mm/h' → Kraftigt regn",
            "timing": "~2 min från aktivering till E-Paper ändring"
        },
        {
            "name": "🌦️ Regn väntat (endast prognos)",
            "prog": 1.5, "obs": 0.0, "forecast": 1.5,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, fallback prognos)",
            "expected": "Nederbörd-layout: 'Regn väntat 1.5mm/h' → Startar [tid]",
            "timing": "~2 min från aktivering till E-Paper ändring"
        },
        {
            "name": "🚴‍♂️ Cykel-varning (minimal prognos)",
            "prog": 0.0, "obs": 0.0, "forecast": 0.3,
            "trigger": "forecast_precipitation_2h > 0.2",
            "expected": "Nederbörd-layout: 'Regn väntat 0.3mm/h' → Lätt duggregn",
            "timing": "~2 min från aktivering till E-Paper ändring"
        }
    ]
    
    for i, scenario in enumerate(classic_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   📊 Data: prog={scenario['prog']}mm/h, obs={scenario['obs']}mm/h, forecast={scenario['forecast']}mm/h")
        print(f"   🎯 Trigger: {scenario['trigger']}")
        print(f"   📱 Förväntat: {scenario['expected']}")
        print(f"   ⏰ Timing: {scenario['timing']}")
    
    # NYA SCENARION (observations-specifika)
    print(f"\n🆕 NYA OBSERVATIONS-SCENARION:")
    new_scenarios = [
        {
            "name": "📊 Observations-only (Regnar enligt Observatorielunden)",
            "prog": 0.0, "obs": 1.8, "forecast": 0.0,
            "trigger": "precipitation > 0 (observations visar regn, prognoser visar 0)",
            "expected": "Observations prioriteras: 'Regnar nu 1.8mm/h' från Observatorielunden",
            "timing": "~2 min, visar prioritering av observations över prognoser"
        },
        {
            "name": "📡 Forecast-only (Regn förväntat, regnar inte nu)",
            "prog": 2.2, "obs": 0.0, "forecast": 1.8,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, fallback prognos)",
            "expected": "Fallback till prognos: 'Regn förväntat 2.2mm/h' eftersom observations=0",
            "timing": "~2 min, visar fallback-logik när observations är 0"
        },
        {
            "name": "⚡ Konflikt (Observations vs Prognoser)",
            "prog": 3.5, "obs": 0.2, "forecast": 0.8,
            "trigger": "precipitation > 0 (observations 0.2mm/h prioriteras över prognos 3.5mm/h)",
            "expected": "Observations vinner: 'Regnar nu 0.2mm/h' istället för prognos 3.5mm/h",
            "timing": "~2 min, tydligt visar prioritering av låg observations över hög prognos"
        },
        {
            "name": "🔬 Kvalitetstest (Observations opålitlig)",
            "prog": 2.0, "obs": 0.0, "forecast": 1.2,
            "trigger": "forecast_precipitation_2h > 0.2 (observations=0, använder prognos+forecast)",
            "expected": "Fallback till prognos: 'Regn väntat 2.0mm/h' när observations=0",
            "timing": "~2 min, visar robust fallback när observations saknas"
        }
    ]
    
    for i, scenario in enumerate(new_scenarios, 6):
        print(f"\n{i}. {scenario['name']}")
        print(f"   📊 Data: prog={scenario['prog']}mm/h, obs={scenario['obs']}mm/h, forecast={scenario['forecast']}mm/h")
        print(f"   🎯 Trigger: {scenario['trigger']}")
        print(f"   📱 Förväntat: {scenario['expected']}")
        print(f"   ⏰ Timing: {scenario['timing']}")
    
    print(f"\n💡 GENERELL TIMING FÖR ALLA SCENARION:")
    print(f"   1️⃣ Test aktiveras: Omedelbart (JSON-fil sparas)")
    print(f"   2️⃣ Restart daemon: 20-30 sekunder")
    print(f"   3️⃣ E-Paper ändring: 60-90 sekunder efter restart")
    print(f"   📊 Total tid: ~2 minuter från test-aktivering till synlig ändring")


def main():
    """FÖRBÄTTRAD: Huvudmeny med tydlig navigation och timing-info"""
    tester = PrecipitationTester()
    
    while True:
        print("\n" + "="*80)
        print("🧪 PRECIPITATION TRIGGER TESTER - FIXAD MED ROBUST CLEANUP")
        print("="*80)
        print("💡 Varje test tar ~2 minuter från aktivering till E-Paper ändring")
        
        print("\n📊 KLASSISKA SCENARION (uppdaterade med observations):")
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
        print("11. 📊 Visa test-status (med timing-info)")
        print("12. 🎯 Analysera trigger-conditions (detaljerad förklaring)")
        print("13. 🔍 Validera konfiguration (med fix-tips)")
        print("14. 📋 Visa alla test-scenarion (med förväntningar)")
        print("15. 🗑️ Rensa test-data (ROBUST - force-rensning om nödvändigt)")
        print("16. 🚪 Avsluta")
        
        print("\n💡 TIPS:")
        print("   • Välj 11 för att se aktuell status och timing")
        print("   • Välj 15 för att garanterat rensa test-data")
        print("   • Varje test ger tydliga nästa-steg instruktioner")
        print("   • Test-data rensas automatiskt efter 1 timme")
        
        try:
            choice = input(f"\n🎯 Välj alternativ (1-16): ").strip()
            
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
                print("💡 Kom ihåg att rensa test-data om det är aktivt!")
                break
            else:
                print("❌ Ogiltigt val - välj nummer mellan 1-16")
                
        except KeyboardInterrupt:
            print("\n👋 Avbrutet av användare")
            print("💡 Test-data kan fortfarande vara aktivt - välj 15 för rensning")
            break
        except Exception as e:
            print(f"❌ Fel: {e}")
            print("🔧 Försök igen eller välj ett annat alternativ")

if __name__ == "__main__":
    print("🔒 SÄKERHETSINFO: Test-data kräver debug.allow_test_data=true i config.json")
    print("⏰ Test-data rensas automatiskt efter 1 timme (eller manuellt med alternativ 15)")
    print("🏭 Production-safe: Ignoreras om debug.enabled=false")
    print("🆕 FIXAT: Auto-cleanup, force-rensning, tydlig timing-feedback")
    print("💡 Varje test tar ~2 minuter från aktivering till E-Paper ändring")
    main()
