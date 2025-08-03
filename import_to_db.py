#!/usr/bin/env python3
"""
Import processed data to database
"""
import sys
import json
import os
from datetime import datetime

sys.path.append('src')

from database.db_manager import DatabaseManager
from processors.data_processor import DataProcessor

def import_test_data():
    """Importuje test podatke u bazu"""
    print("=== Import podataka u bazu ===")
    
    # Inicijalizuj database
    db = DatabaseManager()
    
    # Učitaj test podatke
    if os.path.exists('test_results.json'):
        with open('test_results.json', 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Procesiraj podatke
        processor = DataProcessor()
        processed = processor.process_batch(test_data['search_results'])
        
        # Dodaj tip nekretnine
        for prop in processed:
            prop['property_type'] = 'stan'
            prop['listing_type'] = 'prodaja'
        
        # Importuj u bazu
        count = db.insert_batch(processed)
        print(f"✓ Importovano {count} nekretnina")
        
        # Prikaži statistike
        stats = db.get_statistics()
        print(f"\n=== Statistike baze ===")
        print(f"Ukupno nekretnina: {stats['total_properties']}")
        print(f"Prosečna cena: €{stats['avg_price_eur']:,.0f}")
        print(f"Prosečna površina: {stats['avg_area']:.0f} m²")
        print(f"Prosečna cena po m²: €{stats['avg_price_per_m2']:,.0f}/m²")
        
    else:
        print("✗ Nema test podataka. Pokreni prvo test_scraper.py")

if __name__ == "__main__":
    import_test_data()