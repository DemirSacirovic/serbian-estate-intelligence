"""
Scrape Manager - Upravlja procesom scrapinga
"""
import os
import json
import time
from datetime import datetime
from typing import List, Dict
import logging
from halooglasi_scraper import HaloOglasiScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScrapeManager:
    """Upravlja scraping procesima"""
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        self.scraper = HaloOglasiScraper()
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Kreira potrebne direktorijume ako ne postoje"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "daily"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "archive"), exist_ok=True)
    
    def scrape_multiple_pages(self, 
                             property_type: str, 
                             location: str, 
                             max_pages: int = 10,
                             delay: float = 2.0) -> List[Dict]:
        """
        Scrape-uje više stranica sa paginacijom
        
        Args:
            property_type: Tip nekretnine
            location: Lokacija
            max_pages: Maksimalan broj stranica
            delay: Pauza između zahteva (u sekundama)
        """
        all_properties = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping stranica {page}/{max_pages}")
            
            properties = self.scraper.search_properties(
                property_type=property_type,
                location=location,
                page=page
            )
            
            if not properties:
                logger.warning(f"Nema rezultata na stranici {page}, prekidam")
                break
                
            all_properties.extend(properties)
            
            # Pauza između zahteva da ne opteretimo server
            if page < max_pages:
                time.sleep(delay)
        
        return all_properties
    
    def scrape_all_categories(self, location: str = "beograd") -> Dict[str, List[Dict]]:
        """Scrape-uje sve kategorije nekretnina"""
        categories = {
            "prodaja-stanova": "Stanovi - Prodaja",
            "izdavanje-stanova": "Stanovi - Izdavanje",
            "prodaja-kuca": "Kuće - Prodaja",
            "izdavanje-kuca": "Kuće - Izdavanje",
            "prodaja-poslovnog-prostora": "Poslovni prostor - Prodaja",
            "izdavanje-poslovnog-prostora": "Poslovni prostor - Izdavanje"
        }
        
        results = {}
        
        for category_key, category_name in categories.items():
            logger.info(f"Počinjem scraping za: {category_name}")
            
            properties = self.scrape_multiple_pages(
                property_type=category_key,
                location=location,
                max_pages=5  # Početno samo 5 stranica po kategoriji
            )
            
            results[category_key] = properties
            logger.info(f"Završen {category_name}: {len(properties)} nekretnina")
            
            # Pauza između kategorija
            time.sleep(5)
        
        return results
    
    def save_daily_data(self, data: Dict[str, List[Dict]]):
        """Čuva dnevne podatke"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Čuvaj po kategorijama
        for category, properties in data.items():
            if properties:
                filename = f"{category}_{date_str}.json"
                filepath = os.path.join(self.data_dir, "daily", filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({
                        'category': category,
                        'date': date_str,
                        'count': len(properties),
                        'properties': properties
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Sačuvano {len(properties)} nekretnina u {filename}")
    
    def get_statistics(self, data: Dict[str, List[Dict]]) -> Dict:
        """Generiše statistike o prikupljenim podacima"""
        stats = {
            'total_properties': 0,
            'categories': {},
            'price_ranges': {
                'under_50k': 0,
                '50k_100k': 0,
                '100k_200k': 0,
                '200k_500k': 0,
                'over_500k': 0
            }
        }
        
        for category, properties in data.items():
            stats['categories'][category] = len(properties)
            stats['total_properties'] += len(properties)
            
            # Analiziraj cene
            for prop in properties:
                price_str = prop.get('price', '')
                try:
                    # Pokušaj da izvučeš broj iz cene
                    if '€' in price_str:
                        price_num = float(price_str.replace('€', '').replace('.', '').strip())
                        
                        if price_num < 50000:
                            stats['price_ranges']['under_50k'] += 1
                        elif price_num < 100000:
                            stats['price_ranges']['50k_100k'] += 1
                        elif price_num < 200000:
                            stats['price_ranges']['100k_200k'] += 1
                        elif price_num < 500000:
                            stats['price_ranges']['200k_500k'] += 1
                        else:
                            stats['price_ranges']['over_500k'] += 1
                except:
                    pass
        
        return stats
    
    def run_daily_scrape(self, location: str = "beograd"):
        """Pokreće kompletni dnevni scraping proces"""
        logger.info(f"Započinje dnevni scraping za {location}")
        start_time = time.time()
        
        # Prikupi podatke
        data = self.scrape_all_categories(location)
        
        # Sačuvaj podatke
        self.save_daily_data(data)
        
        # Generiši i prikaži statistike
        stats = self.get_statistics(data)
        
        duration = time.time() - start_time
        logger.info(f"Scraping završen za {duration:.2f} sekundi")
        logger.info(f"Ukupno prikupljeno: {stats['total_properties']} nekretnina")
        
        # Sačuvaj statistike
        stats_file = os.path.join(self.data_dir, f"stats_{datetime.now().strftime('%Y-%m-%d')}.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return stats


if __name__ == "__main__":
    manager = ScrapeManager()
    
    # Pokreni test scraping samo za stanove
    print("Počinje test scraping...")
    test_data = manager.scrape_multiple_pages(
        property_type="prodaja-stanova",
        location="beograd",
        max_pages=2  # Samo 2 stranice za test
    )
    
    print(f"Prikupljeno {len(test_data)} stanova")
    
    # Opciono: pokreni pun dnevni scraping
    # stats = manager.run_daily_scrape()