#!/usr/bin/env python3
"""
Mass Scraper - Prikuplja podatke sa više stranica
Ne treba SQLAlchemy, samo requests i BeautifulSoup
"""
import sys
sys.path.append('src')

from scrapers.halooglasi_scraper import HaloOglasiScraper
import json
import time
from datetime import datetime

def mass_scrape():
    print("🚀 MASS SCRAPER - Prikupljam podatke za analizu")
    print("=" * 60)
    
    scraper = HaloOglasiScraper()
    all_properties = []
    
    # Različite kategorije i lokacije
    searches = [
        # Beograd - prodaja stanova
        {'type': 'prodaja-stanova', 'location': 'beograd', 'pages': 10},
        # Jeftiniji gradovi
        {'type': 'prodaja-stanova', 'location': 'novi-sad', 'pages': 5},
        {'type': 'prodaja-stanova', 'location': 'nis', 'pages': 5},
        # Izdavanje (za poređenje ROI)
        {'type': 'izdavanje-stanova', 'location': 'beograd', 'pages': 3},
    ]
    
    for search in searches:
        print(f"\n📍 Skeniram: {search['type']} - {search['location']}")
        print("-" * 40)
        
        for page in range(1, search['pages'] + 1):
            print(f"  Stranica {page}/{search['pages']}...", end='', flush=True)
            
            try:
                properties = scraper.search_properties(
                    property_type=search['type'],
                    location=search['location'],
                    page=page
                )
                
                if properties:
                    # Dodaj tip i lokaciju
                    for prop in properties:
                        prop['search_type'] = search['type']
                        prop['search_location'] = search['location']
                    
                    all_properties.extend(properties)
                    print(f" ✓ ({len(properties)} oglasa)")
                else:
                    print(" ✗ (nema rezultata)")
                    break
                    
                # Pauza između zahteva
                time.sleep(2)
                
            except Exception as e:
                print(f" ✗ (greška: {str(e)})")
    
    print(f"\n✅ UKUPNO PRIKUPLJENO: {len(all_properties)} oglasa")
    
    # Sačuvaj podatke
    filename = f"data/mass_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_count': len(all_properties),
            'properties': all_properties
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Podaci sačuvani u: {filename}")
    
    # Brza statistika
    print("\n📊 BRZA STATISTIKA:")
    print("-" * 40)
    
    by_location = {}
    price_ranges = {
        'do_50k': 0,
        '50k_100k': 0,
        '100k_200k': 0,
        '200k_500k': 0,
        'preko_500k': 0
    }
    
    for prop in all_properties:
        # Po lokaciji
        loc = prop.get('search_location', 'nepoznato')
        if loc not in by_location:
            by_location[loc] = 0
        by_location[loc] += 1
        
        # Po ceni
        price_str = prop.get('price', '')
        if '€' in price_str:
            try:
                price = float(price_str.replace('€', '').replace('.', '').strip())
                if price < 50000:
                    price_ranges['do_50k'] += 1
                elif price < 100000:
                    price_ranges['50k_100k'] += 1
                elif price < 200000:
                    price_ranges['100k_200k'] += 1
                elif price < 500000:
                    price_ranges['200k_500k'] += 1
                else:
                    price_ranges['preko_500k'] += 1
            except:
                pass
    
    print("\nPo lokaciji:")
    for loc, count in by_location.items():
        print(f"  {loc}: {count} oglasa")
    
    print("\nPo ceni:")
    print(f"  Do €50k: {price_ranges['do_50k']}")
    print(f"  €50k-100k: {price_ranges['50k_100k']}")
    print(f"  €100k-200k: {price_ranges['100k_200k']}")
    print(f"  €200k-500k: {price_ranges['200k_500k']}")
    print(f"  Preko €500k: {price_ranges['preko_500k']}")
    
    return filename

if __name__ == "__main__":
    print("⚠️  PAŽNJA: Ovo će potrajati ~5-10 minuta")
    print("Prikupljam podatke sa halooglasi.com...")
    print("")
    
    result_file = mass_scrape()
    
    print("\n✅ ZAVRŠENO!")
    print(f"\nSledeći korak:")
    print(f"python3 advanced_analyzer.py --file {result_file}")