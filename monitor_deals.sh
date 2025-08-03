#!/bin/bash
# Monitor Deals - Automatski pokreće analizu svakih sat vremena

echo "🏠 Serbian Estate Intelligence - Monitor"
echo "======================================"
echo "Pokrećem monitoring potcenjenih nekretnina..."
echo ""

# Podešavanja
PYTHON="python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/data/monitor.log"
EMAIL="${DEAL_NOTIFICATION_EMAIL:-}" # Iz environment varijable

# Kreiraj data folder ako ne postoji
mkdir -p "$SCRIPT_DIR/data"

# Funkcija za logovanje
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Glavna petlja
while true; do
    log "Započinjem novu analizu..."
    
    # Pokreni analizu sa scraping-om
    if [ -n "$EMAIL" ]; then
        $PYTHON "$SCRIPT_DIR/find_deals.py" --scrape --email "$EMAIL" --discount 0.10
    else
        $PYTHON "$SCRIPT_DIR/find_deals.py" --scrape --discount 0.10
    fi
    
    log "Analiza završena. Sledeća analiza za 1 sat..."
    
    # Čekaj 1 sat
    sleep 3600
done