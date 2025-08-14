#!/bin/bash
echo "🔧 FIXAR TRIGGER CONDITION - off-by-one error"
echo "============================================="

echo ""
echo "📊 PROBLEMET:"
echo "Trigger condition: 'forecast_precipitation_2h > 0.2'"
echo "Faktiskt värde: 0.2mm/h"
echo "0.2 > 0.2 = FALSE ❌"
echo ""

echo "💡 LÖSNINGEN:"
echo "Ändra trigger condition till: 'forecast_precipitation_2h >= 0.2'"
echo "0.2 >= 0.2 = TRUE ✅"
echo ""

echo "🔒 BACKUP konfiguration först:"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/config_update_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp config.json "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/config.json"
echo ""

echo "🔧 UTFÖR ÄNDRING:"
echo "Söker efter: 'forecast_precipitation_2h > 0.2'"
echo "Ersätter med: 'forecast_precipitation_2h >= 0.2'"

# Använd sed för att göra ändringen
sed -i 's/forecast_precipitation_2h > 0\.2/forecast_precipitation_2h >= 0.2/g' config.json

if grep -q "forecast_precipitation_2h >= 0.2" config.json; then
    echo "✅ Ändring genomförd framgångsrikt!"
    echo ""
    echo "📋 VERIFIERING:"
    echo "Nya trigger condition:"
    grep -A 1 -B 1 "forecast_precipitation_2h >= 0.2" config.json
else
    echo "❌ Ändring misslyckades!"
    echo "Återställer från backup..."
    cp "$BACKUP_DIR/config.json" .
    echo "🔙 Återställt från backup"
fi

echo ""
echo "🎯 NÄSTA STEG:"
echo "1. Restart daemon: python3 restart.py"
echo "2. Vänta 60-90 sekunder"
echo "3. Nederbörd-modulen ska nu aktiveras!"
