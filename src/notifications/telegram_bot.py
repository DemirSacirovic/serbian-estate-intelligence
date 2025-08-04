"""
Telegram Bot za Serbian Estate Intelligence
Šalje instant notifikacije o dobrim ponudama
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram bot za notifikacije"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_deal_alert(self, deal: Dict):
        """Šalje alert za pojedinačnu ponudu"""
        message = self._format_deal_message(deal)
        
        # Pošalji tekst
        self._send_message(message, parse_mode='Markdown')
        
        # Pošalji lokaciju ako je dostupna
        if deal.get('coordinates'):
            self._send_location(
                deal['coordinates']['lat'],
                deal['coordinates']['lon']
            )
    
    def send_daily_summary(self, deals: List[Dict], stats: Dict):
        """Šalje dnevni izveštaj"""
        message = self._format_daily_summary(deals, stats)
        self._send_message(message, parse_mode='Markdown')
    
    def send_price_drop_alert(self, property_data: Dict, old_price: float, new_price: float):
        """Šalje alert o padu cene"""
        drop_percent = ((old_price - new_price) / old_price) * 100
        
        message = f"""
🔻 *PAD CENE!*

*{property_data['title']}*
📍 {property_data['city']}, {property_data.get('municipality', 'Nepoznato')}

💰 Stara cena: €{old_price:,.0f}
💸 Nova cena: €{new_price:,.0f}
📉 Pad: {drop_percent:.0f}% (€{old_price - new_price:,.0f})

🏠 {property_data.get('area', '?')}m², {property_data.get('rooms', '?')} soba

🔗 [Pogledaj oglas]({property_data['link']})

⚡ *Ovo je prilika - cena je pala!*
"""
        
        self._send_message(message, parse_mode='Markdown')
    
    def send_desperate_seller_alert(self, seller_data: Dict):
        """Šalje alert o očajnom prodavcu"""
        message = f"""
🚨 *OČAJAN PRODAVAC!*

*{seller_data['property']['title']}*
📍 {seller_data['property'].get('location', 'Nepoznato')}

🔥 Desperation Score: {seller_data['desperation_score']}/100
📅 Na tržištu: {seller_data['days_on_market']} dana
📉 Spuštao cenu: {seller_data['total_drops']} puta

💰 Trenutna cena: €{seller_data['current_price']:,.0f}
💡 Preporučena ponuda: €{seller_data['recommendation']['suggested_offer']:,.0f}

📋 *Argumenti za pregovaranje:*
"""
        
        for point in seller_data['recommendation']['talking_points']:
            message += f"• {point}\n"
        
        message += f"\n🎯 Strategija: *{seller_data['recommendation']['strategy']}*"
        
        if seller_data['property'].get('link'):
            message += f"\n\n🔗 [Pogledaj oglas]({seller_data['property']['link']})"
        
        self._send_message(message, parse_mode='Markdown')
    
    def _format_deal_message(self, deal: Dict) -> str:
        """Formatira poruku za ponudu"""
        prop = deal['property']
        estimate = deal.get('estimate', {})
        
        # Emoji na osnovu ratinga
        rating_emojis = {
            'AAA': '🌟🌟🌟',
            'AA': '🌟🌟',
            'A': '🌟',
            'B': '⭐',
            'C': '💫'
        }
        
        rating = estimate.get('investment_rating', 'B')
        emoji = rating_emojis.get(rating, '⭐')
        
        message = f"""
🏠 *NOVA PRILIKA!* {emoji}

*{prop['title']}*
📍 {prop['city']}, {prop.get('municipality', 'Nepoznato')}

💰 Cena: €{prop['price']:,.0f}
📊 Procena: €{estimate.get('estimated_value', 0):,.0f}
📉 Popust: {estimate.get('discount', 0)*100:.0f}% (€{deal.get('savings', 0):,.0f})

📏 Površina: {prop.get('area', '?')}m²
🏠 Sobe: {prop.get('rooms', '?')}
🏢 Sprat: {prop.get('floor', '?')}/{prop.get('total_floors', '?')}

⭐ Rating: *{rating}*
📈 Confidence: {estimate.get('confidence_score', 0)}%
"""
        
        # Dodaj razloge ako je dobra ponuda
        if estimate.get('discount', 0) > 0.1:
            message += "\n💡 *Zašto je dobra ponuda:*\n"
            
            if 'found_on' in deal and len(deal['found_on']) > 1:
                message += f"• Pronađena na {len(deal['found_on'])} sajtova\n"
            
            trend = estimate.get('market_trend', {})
            if trend.get('direction') == 'rapidly rising':
                message += f"• Brzi rast tržišta ({trend.get('yearly_change', 0)*100:.0f}% godišnje)\n"
        
        # ROI procena
        monthly_rent = prop['price'] * 0.004
        yearly_roi = (monthly_rent * 12) / prop['price'] * 100
        message += f"\n💸 Procena izdavanja: €{monthly_rent:.0f}/mesec ({yearly_roi:.1f}% ROI)"
        
        # Link
        if prop.get('link'):
            message += f"\n\n🔗 [Pogledaj oglas]({prop['link']})"
        
        # Call to action
        if estimate.get('discount', 0) > 0.15:
            message += "\n\n⚡ *HITNO POGLEDAJ - ODLIČNA PRILIKA!*"
        
        return message
    
    def _format_daily_summary(self, deals: List[Dict], stats: Dict) -> str:
        """Formatira dnevni izveštaj"""
        message = f"""
📊 *DNEVNI IZVEŠTAJ*
{datetime.now().strftime('%d.%m.%Y')}

🔍 Skenirano: {stats.get('total_scanned', 0)} oglasa
✅ Pronađeno: {len(deals)} dobrih ponuda
💰 Prosečan popust: {stats.get('avg_discount', 0)*100:.0f}%

🏆 *TOP 3 PONUDE:*
"""
        
        for i, deal in enumerate(deals[:3], 1):
            prop = deal['property']
            est = deal.get('estimate', {})
            
            message += f"""
{i}. *{prop['title'][:40]}...*
   📍 {prop['city']}, {prop.get('municipality', '?')}
   💰 €{prop['price']:,.0f} ({est.get('discount', 0)*100:.0f}% popust)
   ⭐ {est.get('investment_rating', 'B')}
"""
        
        # Tržišni uvidi
        message += f"""

📈 *TRŽIŠNI UVIDI:*
• Najbolja lokacija: {stats.get('best_location', 'N/A')}
• Najbrži rast: {stats.get('fastest_growing', 'N/A')}
• Preporuka: {stats.get('recommendation', 'Nastavi praćenje')}
"""
        
        return message
    
    def _send_message(self, text: str, parse_mode: str = None):
        """Šalje poruku preko Telegram API"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram kredencijali nisu podešeni")
            print("\n📱 TELEGRAM PREVIEW:")
            print(text)
            return
        
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text
        }
        
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                logger.info("Telegram poruka poslata uspešno")
            else:
                logger.error(f"Telegram greška: {response.text}")
        except Exception as e:
            logger.error(f"Greška pri slanju Telegram poruke: {str(e)}")
    
    def _send_location(self, latitude: float, longitude: float):
        """Šalje lokaciju na mapi"""
        if not self.bot_token or not self.chat_id:
            return
        
        url = f"{self.base_url}/sendLocation"
        data = {
            'chat_id': self.chat_id,
            'latitude': latitude,
            'longitude': longitude
        }
        
        try:
            requests.post(url, json=data)
        except Exception as e:
            logger.error(f"Greška pri slanju lokacije: {str(e)}")
    
    def setup_webhook(self, webhook_url: str):
        """Postavlja webhook za primanje komandi"""
        url = f"{self.base_url}/setWebhook"
        data = {'url': webhook_url}
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            logger.info("Webhook postavljen uspešno")
            return True
        else:
            logger.error(f"Greška pri postavljanju webhook: {response.text}")
            return False
    
    @staticmethod
    def get_setup_instructions() -> str:
        """Vraća instrukcije za setup"""
        return """
📱 TELEGRAM BOT SETUP:

1. Otvori Telegram i pronađi @BotFather
2. Pošalji /newbot
3. Daj ime botu (npr. Serbian Estate Bot)
4. Daj username (npr. serbian_estate_bot)
5. Kopiraj TOKEN koji dobiješ

6. Pokreni bota i pošalji mu bilo koju poruku
7. Otvori: https://api.telegram.org/bot<TOKEN>/getUpdates
8. Pronađi "chat":{"id": BROJ} - to je tvoj CHAT_ID

9. Dodaj u .env:
   TELEGRAM_BOT_TOKEN=tvoj_token_ovde
   TELEGRAM_CHAT_ID=tvoj_chat_id_ovde

10. Testiraj:
    python3 src/notifications/telegram_bot.py
"""


# Test
if __name__ == "__main__":
    print(TelegramNotifier.get_setup_instructions())
    
    # Test notifier
    notifier = TelegramNotifier()
    
    # Test deal
    test_deal = {
        'property': {
            'title': 'Odličan stan na Vračaru, hitna prodaja',
            'price': 120000,
            'city': 'Beograd',
            'municipality': 'Vračar',
            'area': 65,
            'rooms': 2,
            'floor': 3,
            'total_floors': 5,
            'link': 'https://example.com/stan-vracar'
        },
        'estimate': {
            'estimated_value': 150000,
            'discount': 0.20,
            'investment_rating': 'AAA',
            'confidence_score': 85
        },
        'savings': 30000,
        'found_on': ['halooglasi', '4zida', 'nekretnine.rs']
    }
    
    print("\n🔔 Šaljem test notifikaciju...")
    notifier.send_deal_alert(test_deal)
    
    # Test desperate seller
    test_seller = {
        'property': {
            'title': 'Stan NBG blok 45',
            'location': 'Novi Beograd, Blok 45'
        },
        'desperation_score': 85,
        'days_on_market': 120,
        'total_drops': 4,
        'current_price': 95000,
        'recommendation': {
            'suggested_offer': 80000,
            'strategy': 'AGRESIVNO - Prodavac je vrlo očajan',
            'talking_points': [
                'Nekretnina je na tržištu već 120 dana',
                'Cena je već spuštana 4 puta',
                'Ukupno spuštanje cene: €25,000'
            ]
        }
    }
    
    print("\n🚨 Šaljem alert o očajnom prodavcu...")
    notifier.send_desperate_seller_alert(test_seller)