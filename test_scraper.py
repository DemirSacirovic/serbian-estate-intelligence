#!/usr/bin/env python3
"""Test skripta za halooglasi scraper"""

import sys
sys.path.append('src')

from scrapers.halooglasi_scraper import HaloOglasiScraper
import json

def test_basic_search():
    """Testira osnovnu pretragu"""
    print("=== Test osnovne pretrage ===")
    scraper = HaloOglasiScraper()
    
    # Pretraži prvu stranicu
    properties = scraper.search_properties(
        property_type="prodaja-stanova",
        location="beograd", 
        page=1
    )
    
    if properties:
        print(f"✓ Pronađeno {len(properties)} nekretnina")
        print("\nPrimer prve nekretnine:")
        print(json.dumps(properties[0], indent=2, ensure_ascii=False))
    else:
        print("✗ Nije pronađena nijedna nekretnina")
    
    return properties

def test_property_details(property_url):
    """Testira preuzimanje detalja"""
    print(f"\n=== Test detalja nekretnine ===")
    print(f"URL: {property_url}")
    
    scraper = HaloOglasiScraper()
    details = scraper.get_property_details(property_url)
    
    if details:
        print("✓ Detalji uspešno preuzeti")
        print(f"Broj karakteristika: {len(details.get('characteristics', {}))}")
        print(f"Broj slika: {len(details.get('images', []))}")
    else:
        print("✗ Neuspešno preuzimanje detalja")
    
    return details

if __name__ == "__main__":
    # Test 1: Osnovna pretraga
    properties = test_basic_search()
    
    # Test 2: Detalji (ako ima rezultata)
    if properties and properties[0].get('link'):
        details = test_property_details(properties[0]['link'])
        
        # Sačuvaj test rezultate
        print("\n=== Čuvanje test rezultata ===")
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'search_results': properties[:3],  # Samo prve 3
                'property_details': details
            }, f, ensure_ascii=False, indent=2)
        print("✓ Rezultati sačuvani u test_results.json")