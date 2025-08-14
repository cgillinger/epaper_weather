#!/bin/bash
echo "🔍 DEBUGGING NEDERBÖRD-TRIGGER PROBLEM"
echo "======================================"

echo ""
echo "📋 1. DAEMON STATUS:"
sudo systemctl status epaper-weather --no-pager -l

echo ""
echo "📋 2. SENASTE DAEMON-LOGGAR (trigger evaluation):"
sudo journalctl -u epaper-weather -n 20 | grep -E "(trigger|precipitation|REGN|weather_description)"

echo ""
echo "📋 3. CACHE-FILER STATUS:"
echo "SMHI cache:"
ls -la cache/smhi_cache* 2>/dev/null || echo "Ingen SMHI cache"

echo "Observations cache:"
ls -la cache/observations_cache* 2>/dev/null || echo "Ingen observations cache"

echo "Pressure history:"
ls -la cache/pressure_history.json 2>/dev/null || echo "Ingen pressure history"

echo ""
echo "📋 4. TEST-DATA STATUS:"
if [ -f "cache/test_precipitation.json" ]; then
    echo "⚠️ TEST-DATA AKTIVT:"
    cat cache/test_precipitation.json
else
    echo "✅ Ingen test-data aktiv"
fi

echo ""
echo "📋 5. CONFIG TRIGGER-INSTÄLLNINGAR:"
echo "Precipitation trigger:"
grep -A 10 "precipitation_trigger" config.json

echo ""
echo "🔧 NÄSTA STEG: Kör weather_client.py test för detaljerad data-analys"
echo "python3 modules/weather_client.py"
