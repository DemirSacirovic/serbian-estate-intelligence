#!/bin/bash
echo "🚀 Serbian Estate Intelligence - Setup Script"
echo "==========================================="
echo ""
echo "Ova skripta će instalirati sve potrebne pakete."
echo "Trebate sudo pristup!"
echo ""

# Instaliraj pip
echo "1. Instaliram pip..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv

# Kreiraj virtuelno okruženje
echo "2. Kreiram virtuelno okruženje..."
python3 -m venv venv

# Aktiviraj venv
source venv/bin/activate

# Instaliraj pakete
echo "3. Instaliram Python pakete..."
pip install beautifulsoup4==4.12.3
pip install requests==2.32.3
pip install sqlalchemy==2.0.36
pip install fastapi==0.115.7
pip install uvicorn==0.34.0
pip install redis==5.2.2
pip install pydantic==2.10.5
pip install python-dotenv==1.0.1

echo ""
echo "✅ Setup završen!"
echo ""
echo "Za pokretanje:"
echo "  source venv/bin/activate"
echo "  python3 find_deals.py --scrape"