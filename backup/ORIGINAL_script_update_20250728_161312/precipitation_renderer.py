#!/usr/bin/env python3
"""
Precipitation Module Renderer
Första konkreta implementation av Dynamic Module System

Ansvarar för rendering av nederbörd-modul med:
- Aktuell nederbörd-status
- Prognostiserad nederbörd (2h framåt)  
- Cykel-väder varningar
- Timing-information
- Intensitets-beskrivningar
"""

from typing import Dict, List
from .base_renderer import ModuleRenderer

class PrecipitationRenderer(ModuleRenderer):
    """
    Renderer för nederbörd-modul
    
    Visar nederbörd-information med fokus på cykel-väder beslut:
    - Varningsikon för uppmärksamhet
    - Nuvarande nederbörd vs. prognostiserad
    - Timing för när nederbörd väntas
    - Intensitets-beskrivning för beslutsstöd
    """
    
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Rendera nederbörd-modul med cykel-väder fokus
        
        Layout:
        ⚠️  [Huvudstatus]
            [Timing/intensitet]
            [Beslutsstöd]
        """
        try:
            self.logger.info(f"🌧️ Renderar nederbörd-modul ({width}×{height})")
            
            # Hämta nederbörd-data med säker fallback
            precipitation = self.safe_get_value(context_data, 'precipitation', 0.0, float)
            forecast_2h = self.safe_get_value(context_data, 'forecast_precipitation_2h', 0.0, float)
            cycling_weather = self.safe_get_value(weather_data, 'cycling_weather', {}, dict)
            
            # Bestäm huvudstatus och layout
            main_text, status_text, description_text = self._determine_precipitation_status(
                precipitation, forecast_2h, cycling_weather
            )
            
            # === LAYOUT RENDERING ===
            
            # 1. Varningsikon (vänster, stort)
            icon_success = self._render_warning_icon(x, y)
            
            # 2. Huvudtext (höger om ikon)
            text_start_x = x + 60 if icon_success else x + 20
            self._render_main_status(text_start_x, y, width - (text_start_x - x), main_text)
            
            # 3. Status/timing (under huvudtext)
            self._render_status_timing(x, y, width, status_text)
            
            # 4. Beskrivning/intensitet (nederst)
            if description_text:
                self._render_description(x, y, width, height, description_text)
            
            self.logger.info(f"✅ Nederbörd-modul rendered: {main_text}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid nederbörd rendering: {e}")
            return self.render_fallback_content(x, y, width, height, 
                                               "Nederbörd-data ej tillgänglig")
    
    def _determine_precipitation_status(self, precipitation: float, forecast_2h: float, 
                                       cycling_weather: Dict) -> tuple:
        """
        Bestäm status-texter baserat på nederbörd-data
        
        Returns:
            Tuple (main_text, status_text, description_text)
        """
        try:
            # Pågående nederbörd har högst prioritet
            if precipitation > 0:
                main_text = f"Regnar nu: {precipitation:.1f}mm/h"
                status_text = "Pågående nederbörd"
                
                # Intensitets-beskrivning
                description_text = self._get_precipitation_intensity_description(precipitation)
                
            # Prognostiserad nederbörd
            elif forecast_2h > 0:
                main_text = f"Regn väntat: {forecast_2h:.1f}mm/h"
                
                # Timing från cykel-väder analys
                forecast_time = cycling_weather.get('forecast_time', 'snart')
                status_text = f"Startar kl {forecast_time}"
                
                # Typ och intensitet
                precip_type = cycling_weather.get('precipitation_type', 'Regn')
                intensity = self._get_precipitation_intensity_description(forecast_2h)
                description_text = f"{intensity} {precip_type.lower()}"
                
            # Fallback (borde inte hända då trigger inte skulle vara aktiv)
            else:
                main_text = "Nederbörd detekterad"
                status_text = "Kontrollera aktuell prognos"
                description_text = "Uppdaterar data..."
            
            return main_text, status_text, description_text
            
        except Exception as e:
            self.logger.warning(f"⚠️ Fel vid status-bestämning: {e}")
            return "Nederbörd-info", "Data ej tillgänglig", ""
    
    def _get_precipitation_intensity_description(self, mm_per_hour: float) -> str:
        """
        Konvertera mm/h till läsbar intensitetsbeskrivning
        Samma logik som weather_client.py
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
    
    def _render_warning_icon(self, x: int, y: int) -> bool:
        """
        Rendera varningsikon för uppmärksamhet
        
        Returns:
            True om ikon renderades, False vid fel
        """
        try:
            # Försök först med emoji/unicode
            return self.draw_text_with_fallback(
                (x + 15, y + 15), 
                "⚠️", 
                self.fonts.get('medium_main', self.fonts.get('small_main')), 
                fill=0
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Varningsikon fel: {e}")
            # Fallback: enkel text
            return self.draw_text_with_fallback(
                (x + 15, y + 15), 
                "!", 
                self.fonts.get('medium_main', self.fonts.get('small_main')), 
                fill=0
            )
    
    def _render_main_status(self, x: int, y: int, max_width: int, main_text: str) -> bool:
        """Rendera huvudstatus-text"""
        try:
            return self.draw_text_with_fallback(
                (x, y + 20), 
                main_text, 
                self.fonts.get('small_main', self.fonts.get('medium_desc')), 
                fill=0,
                max_width=max_width
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Huvudstatus rendering fel: {e}")
            return False
    
    def _render_status_timing(self, x: int, y: int, width: int, status_text: str) -> bool:
        """Rendera status/timing information"""
        try:
            return self.draw_text_with_fallback(
                (x + 20, y + 50), 
                status_text, 
                self.fonts.get('small_desc', self.fonts.get('tiny')), 
                fill=0,
                max_width=width - 40
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Status-timing rendering fel: {e}")
            return False
    
    def _render_description(self, x: int, y: int, width: int, height: int, 
                           description_text: str) -> bool:
        """Rendera beskrivning/intensitet nederst i modulen"""
        try:
            # Placera beskrivning i nedre delen av modulen
            desc_y = y + height - 30  # 30px från botten
            
            return self.draw_text_with_fallback(
                (x + 20, desc_y), 
                description_text, 
                self.fonts.get('tiny', self.fonts.get('small_desc')), 
                fill=0,
                max_width=width - 40
            )
            
        except Exception as e:
            self.logger.warning(f"⚠️ Beskrivning rendering fel: {e}")
            return False
    
    def get_required_data_sources(self) -> List[str]:
        """
        Nederbörd-modul behöver SMHI prognosdata och cykel-väder analys
        """
        return ['smhi', 'cycling_weather', 'forecast']
    
    def get_module_info(self) -> Dict:
        """Metadata för nederbörd-modul"""
        info = super().get_module_info()
        info.update({
            'purpose': 'Nederbörd varningar och cykel-väder beslutsstöd',
            'triggers': ['precipitation > 0', 'forecast_precipitation_2h > 0.2'],
            'layout_priority': 'Ersätter bottom_section vid nederbörd'
        })
        return info