#!/bin/bash
# Setup automatskog pokretanja Estate Hunter Pro

echo "⚙️  ESTATE HUNTER PRO - Automatizacija"
echo "===================================="
echo ""

# Putanje
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="/usr/bin/python3"
VENV_PATH="$SCRIPT_DIR/venv/bin/python"

# Proveri da li postoji venv
if [ -f "$VENV_PATH" ]; then
    PYTHON_PATH="$VENV_PATH"
    echo "✓ Koristi se virtuelno okruženje"
else
    echo "⚠️  Virtuelno okruženje nije pronađeno, koristi se sistem Python"
fi

# Kreiraj cron wrapper script
cat > "$SCRIPT_DIR/cron_hunter.sh" << 'EOF'
#!/bin/bash
# Cron wrapper za Estate Hunter Pro

# Postavi environment
export PATH=/usr/local/bin:/usr/bin:/bin
cd "$(dirname "$0")"

# Log fajl
LOG_FILE="data/cron_$(date +%Y%m%d).log"

echo "===== ESTATE HUNTER PRO - $(date) =====" >> "$LOG_FILE"

# Pokreni hunter
if [ -f "venv/bin/python" ]; then
    venv/bin/python estate_hunter_pro.py >> "$LOG_FILE" 2>&1
else
    python3 estate_hunter_pro.py >> "$LOG_FILE" 2>&1
fi

echo "===== ZAVRŠENO - $(date) =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Rotacija logova (čuvaj samo poslednjih 7 dana)
find data/ -name "cron_*.log" -mtime +7 -delete
find data/ -name "hunt_results_*.json" -mtime +30 -delete
EOF

chmod +x "$SCRIPT_DIR/cron_hunter.sh"

echo "✓ Kreiran cron wrapper script"
echo ""
echo "Izaberite učestalost pokretanja:"
echo "1) Svakih 6 sati (preporučeno)"
echo "2) Svakih 12 sati"
echo "3) Jednom dnevno (u 9:00)"
echo "4) Dva puta dnevno (9:00 i 21:00)"
echo "5) Svaki sat (agresivno)"
echo ""
read -p "Vaš izbor (1-5): " choice

# Generiši cron liniju
case $choice in
    1)
        CRON_LINE="0 */6 * * * $SCRIPT_DIR/cron_hunter.sh"
        SCHEDULE="svakih 6 sati"
        ;;
    2)
        CRON_LINE="0 */12 * * * $SCRIPT_DIR/cron_hunter.sh"
        SCHEDULE="svakih 12 sati"
        ;;
    3)
        CRON_LINE="0 9 * * * $SCRIPT_DIR/cron_hunter.sh"
        SCHEDULE="svaki dan u 9:00"
        ;;
    4)
        CRON_LINE="0 9,21 * * * $SCRIPT_DIR/cron_hunter.sh"
        SCHEDULE="u 9:00 i 21:00"
        ;;
    5)
        CRON_LINE="0 * * * * $SCRIPT_DIR/cron_hunter.sh"
        SCHEDULE="svaki sat"
        ;;
    *)
        echo "Nevažeći izbor!"
        exit 1
        ;;
esac

echo ""
echo "📅 Izabrano: $SCHEDULE"
echo ""

# Dodaj u crontab
echo "Dodajem u crontab..."
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo "✓ Dodato u crontab!"
echo ""
echo "📋 Trenutni crontab:"
crontab -l | grep "cron_hunter"

echo ""
echo "✅ Automatizacija podešena!"
echo ""
echo "ℹ️  Korisne komande:"
echo "   crontab -l         # Vidi sve cron jobove"
echo "   crontab -e         # Edituj cron jobove"
echo "   tail -f data/cron_*.log  # Prati logove"
echo ""
echo "🔔 Ne zaboravi da podesiš Telegram notifikacije u config.json!"