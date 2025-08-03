"""
Halooglasi.com Web Scraper
Scraper za prikupljanje podataka o nekretninama sa halooglasi.com
"""
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Postavi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HaloOglasiScraper:
    """Scraper klasa za halooglasi.com"""
    
    def __init__(self):
        self.base_url = "https://www.halooglasi.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def search_properties(self, 
                         property_type: str = "prodaja-stanova",
                         location: str = "beograd",
                         page: int = 1) -> List[Dict]:
        """
        Pretražuje nekretnine na halooglasi.com
        
        Args:
            property_type: Tip nekretnine (prodaja-stanova, izdavanje-stanova, itd)
            location: Lokacija (beograd, novi-sad, itd)
            page: Broj stranice za paginaciju
            
        Returns:
            Lista rečnika sa podacima o nekretninama
        """
        url = f"{self.base_url}/nekretnine/{property_type}/{location}?page={page}"
        logger.info(f"Scraping URL: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            properties = []
            
            # Pronađi sve oglase
            listings = soup.find_all('div', class_='product-item')
            
            for listing in listings:
                property_data = self._extract_property_data(listing)
                if property_data:
                    properties.append(property_data)
                    
            logger.info(f"Pronađeno {len(properties)} nekretnina na stranici {page}")
            return properties
            
        except Exception as e:
            logger.error(f"Greška pri scraping-u: {str(e)}")
            return []
    
    def _extract_property_data(self, listing) -> Optional[Dict]:
        """Ekstraktuje podatke o nekretnini iz HTML elementa"""
        try:
            # Naslov i link
            title_elem = listing.find('h3', class_='product-title')
            if not title_elem or not title_elem.find('a'):
                return None
                
            title = title_elem.get_text(strip=True)
            link = title_elem.find('a')['href']
            if not link.startswith('http'):
                link = self.base_url + link
            
            # Cena
            price_elem = listing.find('div', class_='central-feature')
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            
            # Lokacija
            location_elem = listing.find('ul', class_='subtitle-places')
            location = location_elem.get_text(strip=True) if location_elem else "N/A"
            
            # Površina i dodatne informacije
            features = []
            feature_list = listing.find('ul', class_='product-features')
            if feature_list:
                features = [li.get_text(strip=True) for li in feature_list.find_all('li')]
            
            # ID oglasa
            ad_id = listing.get('data-id', 'N/A')
            
            return {
                'id': ad_id,
                'title': title,
                'price': price,
                'location': location,
                'features': features,
                'link': link,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Greška pri ekstraktovanju podataka: {str(e)}")
            return None
    
    def get_property_details(self, property_url: str) -> Dict:
        """Preuzima detaljne informacije o specifičnoj nekretnini"""
        logger.info(f"Preuzimam detalje za: {property_url}")
        
        try:
            response = self.session.get(property_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': property_url,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Osnovne informacije
            basic_info = soup.find('div', class_='base-info')
            if basic_info:
                details['description'] = basic_info.get_text(strip=True)
            
            # Karakteristike
            characteristics = {}
            char_section = soup.find('div', class_='product-characteristics')
            if char_section:
                for row in char_section.find_all('li'):
                    label = row.find('span', class_='field-name')
                    value = row.find('span', class_='field-value')
                    if label and value:
                        characteristics[label.get_text(strip=True)] = value.get_text(strip=True)
            
            details['characteristics'] = characteristics
            
            # Slike
            images = []
            gallery = soup.find('div', class_='gallery-thumbnails')
            if gallery:
                for img in gallery.find_all('img'):
                    img_url = img.get('src') or img.get('data-src')
                    if img_url:
                        images.append(img_url)
            
            details['images'] = images
            
            return details
            
        except Exception as e:
            logger.error(f"Greška pri preuzimanju detalja: {str(e)}")
            return {}
    
    def save_to_json(self, data: List[Dict], filename: str):
        """Čuva podatke u JSON fajl"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Podaci sačuvani u {filename}")


# Primer korišćenja
if __name__ == "__main__":
    scraper = HaloOglasiScraper()
    
    # Pretraži stanove za prodaju u Beogradu
    print("Počinjem scraping...")
    properties = scraper.search_properties(
        property_type="prodaja-stanova",
        location="beograd",
        page=1
    )
    
    # Sačuvaj rezultate
    if properties:
        scraper.save_to_json(properties, "data/raw/halooglasi_stanovi.json")
        print(f"Pronađeno {len(properties)} nekretnina")
        
        # Prikupi detalje za prvu nekretninu
        if properties[0]['link']:
            details = scraper.get_property_details(properties[0]['link'])
            print(f"Detalji prve nekretnine: {json.dumps(details, indent=2, ensure_ascii=False)}")
    else:
        print("Nije pronađena nijedna nekretnina")