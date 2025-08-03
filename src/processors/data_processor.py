"""
Data Processor - Čisti i procesira sirove podatke o nekretninama
"""
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Procesira i čisti podatke o nekretninama"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        
    def process_property(self, property_data: Dict) -> Optional[Dict]:
        """
        Procesira pojedinačnu nekretninu
        
        Args:
            property_data: Sirovi podaci o nekretnini
            
        Returns:
            Očišćeni i obogaćeni podaci ili None ako je nevaljan
        """
        try:
            processed = {
                'id': property_data.get('id'),
                'title': self._clean_text(property_data.get('title', '')),
                'scraped_at': property_data.get('scraped_at'),
                'link': property_data.get('link'),
                'processed_at': datetime.now().isoformat()
            }
            
            # Procesiraj cenu
            price_info = self._extract_price(property_data.get('price', ''))
            processed.update(price_info)
            
            # Procesiraj lokaciju
            location_info = self._extract_location(property_data.get('location', ''))
            processed.update(location_info)
            
            # Procesiraj karakteristike
            features_info = self._extract_features(property_data.get('features', []))
            processed.update(features_info)
            
            # Dodatne kalkulacije
            if processed.get('price_eur') and processed.get('area_m2'):
                processed['price_per_m2'] = round(processed['price_eur'] / processed['area_m2'], 2)
            
            self.processed_count += 1
            return processed
            
        except Exception as e:
            logger.error(f"Greška pri procesiranju {property_data.get('id')}: {str(e)}")
            self.error_count += 1
            return None
    
    def _clean_text(self, text: str) -> str:
        """Čisti tekst od viška whitespace i specijalnih karaktera"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_price(self, price_str: str) -> Dict:
        """Ekstraktuje cenu i valutu"""
        result = {
            'price_raw': price_str,
            'price_eur': None,
            'price_rsd': None,
            'currency': None
        }
        
        if not price_str:
            return result
        
        # Ukloni whitespace
        price_str = price_str.strip()
        
        # Pokušaj da pronađeš broj
        # Prvo EUR
        eur_match = re.search(r'([\d.,]+)\s*€', price_str)
        if eur_match:
            price_num = eur_match.group(1).replace('.', '').replace(',', '.')
            try:
                result['price_eur'] = float(price_num)
                result['currency'] = 'EUR'
                # Približna konverzija (1 EUR = 117 RSD)
                result['price_rsd'] = result['price_eur'] * 117
            except:
                pass
        
        # Zatim RSD/din
        rsd_match = re.search(r'([\d.,]+)\s*(RSD|din)', price_str, re.IGNORECASE)
        if rsd_match and not result['price_eur']:
            price_num = rsd_match.group(1).replace('.', '').replace(',', '.')
            try:
                result['price_rsd'] = float(price_num)
                result['currency'] = 'RSD'
                # Približna konverzija
                result['price_eur'] = result['price_rsd'] / 117
            except:
                pass
        
        return result
    
    def _extract_location(self, location_str: str) -> Dict:
        """Ekstraktuje komponente lokacije"""
        result = {
            'location_raw': location_str,
            'city': None,
            'municipality': None,
            'neighborhood': None,
            'street': None
        }
        
        if not location_str:
            return result
        
        # Očisti lokaciju
        location_str = self._clean_text(location_str)
        
        # Pokušaj da razdvojiš komponente
        # Format je obično: GradOpštinaKvartUlica
        parts = re.findall(r'[A-ZŠĐŽČĆ][a-zšđžčć]+(?:\s+[a-zšđžčć]+)*', location_str)
        
        if parts:
            # Prvi deo je obično grad
            if 'Beograd' in location_str:
                result['city'] = 'Beograd'
            elif 'Novi Sad' in location_str:
                result['city'] = 'Novi Sad'
            
            # Traži opštinu
            if 'Opština' in location_str:
                municipality_match = re.search(r'Opština\s+([^A-ZŠĐŽČĆ]+)', location_str)
                if municipality_match:
                    result['municipality'] = municipality_match.group(1).strip()
            
            # Poslednji deo je često ulica
            if len(parts) >= 2:
                result['street'] = parts[-1]
            
            # Kvart je obično između opštine i ulice
            if len(parts) >= 3:
                result['neighborhood'] = parts[-2]
        
        return result
    
    def _extract_features(self, features_list: List[str]) -> Dict:
        """Ekstraktuje karakteristike nekretnine"""
        result = {
            'area_m2': None,
            'rooms': None,
            'floor': None,
            'total_floors': None,
            'features_raw': features_list
        }
        
        for feature in features_list:
            # Površina
            area_match = re.search(r'(\d+(?:\.\d+)?)\s*m2', feature)
            if area_match:
                try:
                    result['area_m2'] = float(area_match.group(1))
                except:
                    pass
            
            # Broj soba
            rooms_match = re.search(r'(\d+(?:\.\d+)?)\s*Broj soba', feature)
            if rooms_match:
                try:
                    result['rooms'] = float(rooms_match.group(1))
                except:
                    pass
            
            # Spratnost
            floor_match = re.search(r'([IVX\d]+|PR|VPR|SUT)/([IVX\d]+)', feature)
            if floor_match:
                result['floor'] = self._convert_floor(floor_match.group(1))
                result['total_floors'] = self._convert_floor(floor_match.group(2))
        
        return result
    
    def _convert_floor(self, floor_str: str) -> Optional[int]:
        """Konvertuje oznaku sprata u broj"""
        floor_str = floor_str.upper()
        
        # Specijalni slučajevi
        if floor_str == 'PR':
            return 0
        elif floor_str == 'VPR':
            return 0  # Visoko prizemlje tretiramo kao prizemlje
        elif floor_str == 'SUT':
            return -1
        
        # Rimski brojevi
        roman_map = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
        }
        
        if floor_str in roman_map:
            return roman_map[floor_str]
        
        # Pokušaj kao obični broj
        try:
            return int(floor_str)
        except:
            return None
    
    def process_batch(self, properties: List[Dict]) -> List[Dict]:
        """Procesira batch nekretnina"""
        processed = []
        
        for prop in properties:
            processed_prop = self.process_property(prop)
            if processed_prop:
                processed.append(processed_prop)
        
        logger.info(f"Procesirano {self.processed_count} nekretnina, {self.error_count} grešaka")
        return processed
    
    def save_processed_data(self, data: List[Dict], output_file: str):
        """Čuva procesirane podatke"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_at': datetime.now().isoformat(),
                'total_count': len(data),
                'properties': data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Procesirani podaci sačuvani u {output_file}")


# Test
if __name__ == "__main__":
    # Učitaj test podatke
    with open('test_results.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    processor = DataProcessor()
    
    # Procesiraj prvi stan
    if test_data['search_results']:
        processed = processor.process_property(test_data['search_results'][0])
        print("Procesirani podaci:")
        print(json.dumps(processed, indent=2, ensure_ascii=False))
    
    # Procesiraj sve
    all_processed = processor.process_batch(test_data['search_results'])
    processor.save_processed_data(all_processed, 'data/processed/test_processed.json')