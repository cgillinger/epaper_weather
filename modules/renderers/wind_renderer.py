#!/usr/bin/env python3
"""
Wind Module Renderer för E-Paper Väderstation - REN SLUTLIG DESIGN
Implementerar kollegans slutliga artefakt: Ren layout utan allmän vindikon

REN LAYOUT (kollegans slutliga vision):
┌─────────────────────┐
│  4.8 m/s            │ ← PRIMÄR: Stort värde
│  Måttlig vind       │ ← PRIMÄR: Hel rad, max två rader
│                     │ ← LUFTIG SPACING
│  ↗️ N               │ ← SEKUNDÄR: Pil + riktning vänster
└─────────────────────┘

KOLLEGANS SLUTLIGA DESIGNPRINCIPER:
✅ REN LAYOUT: Ingen allmän vindikon - tar bort visuellt brus
✅ TYDLIG HIERARKI: M/s → beskrivning → riktning 
✅ RADBRYTNING: Max två rader innan ellips
✅ VÄNSTERLINJERAT: Kardinalpil + riktning nederst
✅ RESONEMANG: Varför varje beslut tas
"""

from typing import Dict, List
from .base_renderer import ModuleRenderer

class WindRenderer(ModuleRenderer):
    """
    Renderer för wind-modul med REN SLUTLIG UX-DESIGN
    
    Implementerar kollegans slutliga artefakt:
    - INGEN allmän vindikon (tar bort visuellt brus)
    - M/s primär information (stort, vänster) 
    - Beskrivning hel rad (max två rader, ingen ellips)
    - Kardinalpil + riktning vänsterlinjerat nederst
    - Konstanter för förutsägbar layout
    - Resonemang för varje designbeslut
    """
    
    def render(self, x: int, y: int, width: int, height: int, 
               weather_data: Dict, context_data: Dict) -> bool:
        """
        Rendera wind-modul med REN SLUTLIG DESIGN
        
        Args:
            x, y: Position på canvas
            width, height: Modulens storlek (240×200px för MEDIUM 1)
            weather_data: Väderdata från weather_client
            context_data: Trigger context data
            
        Returns:
            True om rendering lyckades
        """
        try:
            self.logger.info(f"🧹 Renderar REN SLUTLIG wind-modul ({width}×{height})")
            
            # === KOLLEGANS SLUTLIGA KONSTANTER ===
            PADDING = 20
            ROW_GAP_PRIMARY = 18            # Avstånd M/s → beskrivning (minskat från 36)
            LINE_GAP = 6                    # Radavstånd mellan beskrivningsrader
            CARDINAL_ICON_SIZE = (40, 40)   # Custom storlek - inga skalningar
            CARDINAL_GAP = 8                # Mellan pil och text
            BOTTOM_ZONE_INSET = 20          # Avstånd till nederkant
            MAX_DESC_WIDTH = width - 2 * PADDING  # Använd hela bredden
            
            # Hämta vinddata med säker fallback
            wind_speed = self.safe_get_value(weather_data, 'wind_speed', 0.0, float)
            wind_direction = self.safe_get_value(weather_data, 'wind_direction', 0.0, float)
            
            # Konvertera till svenska beskrivningar
            speed_description = self.icon_manager.get_wind_description_swedish(wind_speed)
            direction_short, cardinal_code = self.icon_manager.get_wind_direction_info(wind_direction)
            
            # === MODULRAM (som andra moduler har) ===
            self.draw.rectangle(
                [(x + 2, y + 2), (x + width - 2, y + height - 2)],
                outline=0,
                width=2
            )
            
            # === HJÄLPFUNKTIONER (kollegans förslag) ===
            def text_w(text, font):
                """Textbredd"""
                bbox = self.draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0]
            
            def text_h(text, font):
                """Texthöjd"""
                bbox = self.draw.textbbox((0, 0), text, font=font)
                return bbox[3] - bbox[1]
            
            def wrap2_ellips(text, font, max_w):
                """Radbrytning: Max två rader innan ellips (kollegans algoritm)"""
                words, lines, cur = text.split(), [], ''
                for i, w in enumerate(words):
                    test = (cur + ' ' + w).strip()
                    if text_w(test, font) <= max_w:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                        if len(lines) == 1:  # Andra raden - ellipsera resten
                            rest = ' '.join([cur] + words[i+1:])
                            while text_w(rest + '…', font) > max_w and len(rest) > 1:
                                rest = rest[:-1].rstrip()
                            lines.append(rest + ('…' if len(rest) < len(' '.join([cur] + words[i+1:])) else ''))
                            return lines
                if cur:
                    lines.append(cur)
                return lines[:2]
            
            # === 1. PRIMÄRBLOCK: M/S + BESKRIVNING (REN LAYOUT) ===
            
            # M/s stort och tydligt, vänsterjusterat
            ms_text = f"{wind_speed:.1f} m/s"
            ms_font = self.fonts.get('large_main', self.fonts.get('medium_main'))
            ms_x, ms_y = x + PADDING, y + PADDING
            self.draw_text_with_fallback((ms_x, ms_y), ms_text, ms_font, fill=0)
            
            # Mät höjd för M/s
            ms_bbox = self.draw.textbbox((0, 0), ms_text, font=ms_font)
            ms_h = ms_bbox[3] - ms_bbox[1]
            
            # Beskrivning på hel rad (max två rader)
            desc_font = self.fonts.get('small_main', self.fonts.get('small_desc'))
            desc_lines = wrap2_ellips(speed_description, desc_font, MAX_DESC_WIDTH)
            
            # Rita beskrivningsrader
            for i, line in enumerate(desc_lines):
                desc_x = x + PADDING
                desc_y = ms_y + ms_h + ROW_GAP_PRIMARY + i * (text_h(line, desc_font) + LINE_GAP)
                self.draw_text_with_fallback((desc_x, desc_y), line, desc_font, fill=0)
                self.logger.info(f"📝 Beskrivningsrad {i+1}: '{line}'")
            
            # === 2. SEKUNDÄRBLOCK: KARDINALPIL + RIKTNING (VÄNSTERLINJERAT NEDERST) ===
            
            # Hämta kardinalpil och etikett
            cardinal_icon = self.icon_manager.get_wind_icon(cardinal_code, size=CARDINAL_ICON_SIZE)
            label_font = self.fonts.get('small_main', desc_font)
            
            # Positionera vänsterlinjerat i nederkant
            base_y = y + height - BOTTOM_ZONE_INSET - CARDINAL_ICON_SIZE[1]
            cx = x + PADDING  # Vänsterlinjerat som kollegun vill
            
            # Rita kardinalpil om den finns
            if cardinal_icon:
                self.paste_icon_on_canvas(cardinal_icon, cx, base_y)
                cx += CARDINAL_ICON_SIZE[0] + CARDINAL_GAP
                self.logger.info(f"✅ Kardinalpil renderad vänsterlinjerat: {cardinal_code}")
            else:
                self.logger.warning(f"⚠️ Kardinalpil saknas för kod: {cardinal_code}")
                # Använd enkel fallback-pil
                self.draw.text((cx, base_y), "→", font=label_font, fill=0)
                cx += 20
            
            # Rita riktningsetikett bredvid pil
            label_y = base_y + (CARDINAL_ICON_SIZE[1] - text_h(direction_short, label_font)) // 2
            self.draw_text_with_fallback((cx, label_y), direction_short, label_font, fill=0)
            
            # === INGEN ALLMÄN VINDIKON (kollegans beslut) ===
            # RESONEMANG: Tar bort visuellt brus, låter primärdata dominera
            # RESULTAT: Renare layout med tydlig hierarki
            
            self.logger.info(f"✅ REN SLUTLIG cykel-optimerad wind-modul: {wind_speed:.1f}m/s {speed_description}, {direction_short}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fel vid ren slutlig wind rendering: {e}")
            return self.render_fallback_content(
                x, y, width, height, 
                "Wind-data ej tillgänglig"
            )
    
    def get_required_data_sources(self) -> List[str]:
        """Wind-modul behöver SMHI prognosdata för vindstyrka och vindriktning"""
        return ['smhi']
    
    def get_module_info(self) -> Dict:
        """Metadata för ren slutlig wind-modul"""
        info = super().get_module_info()
        info.update({
            'purpose': 'Ren slutlig vindmodul enligt kollegans designartefakt',
            'data_sources': ['SMHI vindprognoser (ws + wd parametrar)'],
            'layout': 'Ersätter barometer-modulen (MEDIUM 1 position)',
            'design': 'Kollegans slutliga artefakt: Ren layout utan allmän vindikon',
            'features': [
                '✅ REN LAYOUT: Ingen allmän vindikon - tar bort visuellt brus',
                '✅ TYDLIG HIERARKI: M/s → beskrivning → riktning',
                '✅ RADBRYTNING: Max två rader innan ellips (kollegans algoritm)',
                '✅ VÄNSTERLINJERAT: Kardinalpil + riktning nederst',
                '✅ HEL RAD BESKRIVNING: Använder hela bredden utan kollision',
                '✅ RESONEMANG: Varje designbeslut motiverat och förklarat',
                '✅ CYKEL-FOKUSERAD: Snabb avläsning av vindförhållanden',
                'M/s-värde PRIMÄR (large_main font, vänsterjusterat)',
                'Beskrivande text HEL RAD (small_main font, max två rader)',
                'Kardinalpil + riktning VÄNSTERLINJERAT (32×32px med gap)',
                'Konstanter för förutsägbar layout: 20px padding, 18px radavstånd (justerat)',
                'SLUTLIG DESIGN: Implementerar kollegans kompletta artefakt',
                'Ingen allmän vindikon: Renare layout utan visuellt brus',
                'Professionell E-Paper design optimerad för cykel-användning'
            ]
        })
        return info