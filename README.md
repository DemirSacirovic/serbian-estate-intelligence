# Serbian Estate Intelligence Platform

Platforma za prikupljanje, analizu i pretragu podataka o nekretninama u Srbiji.

## 🏠 Pregled

Serbian Estate Intelligence je platforma koja automatski prikuplja podatke o nekretninama sa vodećih oglasnih sajtova u Srbiji, procesira ih i omogućava naprednu pretragu preko REST API-ja.

### Ključne funkcionalnosti

- 🔍 **Web Scraping**: Automatsko prikupljanje podataka sa halooglasi.com
- 🧹 **Data Processing**: Čišćenje i normalizacija podataka
- 💾 **Database**: PostgreSQL/SQLite za skladištenje
- 🚀 **REST API**: FastAPI za pretragu i analizu
- 📊 **Statistike**: Real-time statistike tržišta

## 📋 Zahtev

- Python 3.11+
- PostgreSQL 13+ (opciono, može SQLite)
- Redis (opciono, za caching)

## 🛠️ Instalacija

### 1. Kloniraj repozitorijum

```bash
git clone https://github.com/yourusername/serbian-estate-intelligence.git
cd serbian-estate-intelligence
```

### 2. Kreiraj virtuelno okruženje

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ili
venv\Scripts\activate  # Windows
```

### 3. Instaliraj zavisnosti

```bash
pip install -r requirements.txt
```

### 4. Podesi environment varijable

```bash
cp .env.example .env
# Edituj .env fajl sa tvojim podešavanjima
```

## 🚀 Pokretanje

### Scraper

```bash
# Test scraping
python test_scraper.py

# Pun scraping (sve kategorije)
python src/scrapers/scrape_manager.py
```

### Database

```bash
# Importuj test podatke
python import_to_db.py
```

### API Server

```bash
# Pokreni API
python run_api.py

# API će biti dostupan na:
# http://localhost:8000
# Dokumentacija: http://localhost:8000/docs
```

## 📚 API Dokumentacija

### Pretraga nekretnina

```http
POST /api/properties/search
Content-Type: application/json

{
  "city": "Beograd",
  "min_price": 50000,
  "max_price": 200000,
  "min_area": 40,
  "max_area": 100,
  "rooms": 2.0,
  "property_type": "stan",
  "listing_type": "prodaja",
  "limit": 50
}
```

### Statistike

```http
GET /api/stats
```

Vraća:
```json
{
  "total_properties": 1234,
  "active_properties": 1200,
  "avg_price_eur": 125000,
  "avg_price_per_m2": 2100,
  "avg_area": 65,
  "cities": {
    "Beograd": {
      "count": 800,
      "avg_price": 145000
    }
  }
}
```

### Detalji nekretnine

```http
GET /api/properties/{id}
```

### Lista gradova

```http
GET /api/cities
```

## 🏗️ Arhitektura

```
serbian-estate-intelligence/
├── src/
│   ├── scrapers/         # Web scraping moduli
│   ├── processors/       # Data cleaning i processing
│   ├── database/         # Database modeli i manager
│   ├── api/             # FastAPI aplikacija
│   └── notifications/   # Email/SMS notifikacije (TODO)
├── data/
│   ├── raw/            # Sirovi podaci sa scraping-a
│   ├── processed/      # Očišćeni podaci
│   └── models/         # ML modeli (TODO)
├── tests/              # Unit i integration testovi
└── docker/             # Docker konfiguracija
```

## 🔧 Konfiguracija

### Environment varijable (.env)

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/serbian_estates
# ili za SQLite:
# DATABASE_URL=sqlite:///data/serbian_estates.db

# API
API_HOST=0.0.0.0
API_PORT=8000

# Scraping
SCRAPE_DELAY=2.0
MAX_PAGES_PER_CATEGORY=10

# Redis (opciono)
REDIS_URL=redis://localhost:6379
```

## 🐳 Docker

```bash
# Build image
docker build -t serbian-estates .

# Run container
docker run -p 8000:8000 serbian-estates

# Ili sa docker-compose
docker-compose up
```

## 📊 Primeri korišćenja

### Python

```python
import requests

# Pretraži stanove
response = requests.post('http://localhost:8000/api/properties/search', 
    json={
        "city": "Beograd",
        "min_price": 80000,
        "max_price": 150000,
        "rooms": 2.0
    }
)

stanovi = response.json()
print(f"Pronađeno {len(stanovi)} stanova")
```

### JavaScript

```javascript
// Pretraži stanove
const searchParams = {
    city: "Novi Sad",
    min_area: 50,
    max_area: 80,
    listing_type: "prodaja"
};

fetch('http://localhost:8000/api/properties/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(searchParams)
})
.then(res => res.json())
.then(data => console.log(`Pronađeno ${data.length} nekretnina`));
```

## 🧪 Testiranje

```bash
# Pokreni sve testove
pytest

# Samo unit testove
pytest tests/unit/

# Sa coverage
pytest --cov=src tests/
```

## 🚀 Deployment

### Heroku

```bash
heroku create serbian-estates-api
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

### VPS (Ubuntu/Debian)

```bash
# Instaliraj zavisnosti
sudo apt update
sudo apt install python3.11 postgresql nginx

# Setup systemd service
sudo cp deploy/serbian-estates.service /etc/systemd/system/
sudo systemctl enable serbian-estates
sudo systemctl start serbian-estates

# Setup Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/serbian-estates
sudo ln -s /etc/nginx/sites-available/serbian-estates /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

## 📈 Monitoring

- Health check: `GET /health`
- Metrics: Integrisano sa Prometheus (TODO)
- Logs: Structured logging sa correlation IDs

## 🤝 Kontribucija

1. Fork projekat
2. Kreiraj feature branch (`git checkout -b feature/nova-funkcionalnost`)
3. Commit izmene (`git commit -m 'Dodaj novu funkcionalnost'`)
4. Push na branch (`git push origin feature/nova-funkcionalnost`)
5. Otvori Pull Request

## 📝 License

MIT License - vidi [LICENSE](LICENSE) fajl za detalje.

## 👨‍💻 Autor

Demir Sacirovic - PhD Geoscience, Python Developer

## 🙏 Zahvalnice

- FastAPI za odličan web framework
- SQLAlchemy za ORM

- BeautifulSoup za web scraping
