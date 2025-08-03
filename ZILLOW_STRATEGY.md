# 🏠 ZILLOW MODEL ZA SRBIJU - Kako stvarno pronaći potcenjene nekretnine

## 🎯 ZILLOW STRATEGIJA PRILAGOĐENA ZA SRBIJU

### 1. ŠTA ZILLOW RADI DOBRO:

**Zestimate Algorithm** - procenjuje REALNU vrednost na osnovu:
- Prodaja u okolini (comparables)
- Istorije cena
- Tržišnih trendova
- Machine learning modela
- Javnih podataka (porezi, dozvole)

**Multiple Data Sources:**
- MLS (Multiple Listing Service)
- Javni registri
- Korisničke izmene
- Fotografije sa satelita
- Street view

### 2. SRPSKE SPECIFIČNOSTI (PREVARE I LAŽI):

#### 🚨 ČESTE PREVARE NA SRPSKOM TRŽIŠTU:

1. **Dupli oglasi** - isti stan na 3 sajta sa 3 različite cene
2. **Lažna hitnost** - "hitno" da bi spustili cenu, a prodaju mesecima
3. **Skriveni troškovi** - "cena bez poreza", "plus agencijska provizija"
4. **Fantom oglasi** - nepostojeći stanovi za prikupljanje kontakata
5. **Cenovni balon** - nerealno visoke cene pa "popust"
6. **Crno tržište** - prava cena 30% niža od oglašene

### 3. NOVI MULTI-SITE SCRAPER SISTEM:

```python
SERBIAN_REAL_ESTATE_SITES = {
    'halooglasi.com': {'trust': 0.9, 'volume': 'high'},
    'nekretnine.rs': {'trust': 0.85, 'volume': 'high'},
    '4zida.rs': {'trust': 0.8, 'volume': 'medium'},
    'cityexpert.rs': {'trust': 0.85, 'volume': 'medium'},
    'nadjidom.com': {'trust': 0.7, 'volume': 'low'},
    'mojkvadrat.rs': {'trust': 0.75, 'volume': 'low'},
    'oglasi.rs': {'trust': 0.6, 'volume': 'medium'},
}

FOCUS_CITIES = {
    'Beograd': {
        'avg_price_m2': 2300,
        'growth_rate': 0.08,
        'hot_areas': ['Vračar', 'NBG - Blok 63', 'Dedinje', 'Savski venac']
    },
    'Novi Sad': {
        'avg_price_m2': 1800,
        'growth_rate': 0.10,
        'hot_areas': ['Centar', 'Liman', 'Grbavica', 'Novo naselje']
    },
    'Novi Pazar': {
        'avg_price_m2': 800,
        'growth_rate': 0.15,  # Brzi rast!
        'hot_areas': ['Centar', '1. maj']
    },
    'Zlatibor': {
        'avg_price_m2': 2000,
        'growth_rate': 0.12,
        'hot_areas': ['Centar', 'Kraljeve vode']
    }
}
```

### 4. ALGORITAM ZA DETEKCIJU PRAVIH PRILIKA:

#### A) Cross-Site Validation (provera preko više sajtova):
- Isti stan na 2+ sajta = uporedi cene
- Razlika >10% = red flag
- Najniža cena - 5% = realna cena

#### B) Fraud Detection (detekcija prevara):
- "Hitno" + oglas stariji od 30 dana = LAŽE
- Previše ključnih reči ("lux", "ekskluziv", "jedinstveno") = precenjeno
- Nema broja telefona = sumnjivo
- Iste slike na više oglasa = agencijska prevara

#### C) Price History Tracking:
- Praćenje promena cena svakih 24h
- Pad cene >5% = vlasnik očajan
- Pad cene 2x u mesec dana = PRAVA PRILIKA

### 5. IMPLEMENTACIJA ZILLOW MODELA: