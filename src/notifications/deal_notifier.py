"""
Deal Notifier - Šalje notifikacije za dobre ponude
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class DealNotifier:
    """Šalje notifikacije za pronađene dobre ponude"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.notification_history_file = 'data/notification_history.json'
        self._load_history()
    
    def _load_history(self):
        """Učitava istoriju poslanih notifikacija"""
        if os.path.exists(self.notification_history_file):
            with open(self.notification_history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {'sent_deals': []}
    
    def _save_history(self):
        """Čuva istoriju notifikacija"""
        os.makedirs(os.path.dirname(self.notification_history_file), exist_ok=True)
        with open(self.notification_history_file, 'w') as f:
            json.dump(self.history, f)
    
    def _was_already_sent(self, property_id: str) -> bool:
        """Proverava da li je već poslana notifikacija za ovu nekretninu"""
        return property_id in self.history['sent_deals']
    
    def send_deal_alert(self, deals: List[Dict], recipient_email: str):
        """Šalje email sa najboljim ponudama"""
        # Filtriraj samo nove ponude
        new_deals = [d for d in deals if not self._was_already_sent(d['property']['external_id'])]
        
        if not new_deals:
            logger.info("Nema novih ponuda za slanje")
            return
        
        # Kreiraj email
        subject = f"🏠 {len(new_deals)} novih potcenjenih nekretnina!"
        body = self._create_email_body(new_deals)
        
        # Pošalji email
        if self.email_from and self.email_password:
            self._send_email(recipient_email, subject, body)
            
            # Zapamti poslane
            for deal in new_deals:
                self.history['sent_deals'].append(deal['property']['external_id'])
            self._save_history()
        else:
            logger.warning("Email kredencijali nisu podešeni")
            print(f"\n📧 EMAIL PREVIEW:")
            print(f"To: {recipient_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
    
    def _create_email_body(self, deals: List[Dict]) -> str:
        """Kreira HTML body za email"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h1 style="color: #2c3e50;">🏠 Pronađene potcenjene nekretnine</h1>
            <p style="color: #7f8c8d;">Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            
            <div style="background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>TOP {min(5, len(deals))} PONUDA:</h3>
            </div>
        """
        
        for i, deal in enumerate(deals[:10], 1):
            discount_color = '#e74c3c' if deal['discount'] > 0.20 else '#e67e22'
            
            html += f"""
            <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; background: white; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50;">
                    {i}. {deal['property']['title']}
                </h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div>
                        <p><strong>📍 Lokacija:</strong> {deal['property']['city']}, {deal['property']['municipality']}</p>
                        <p><strong>📏 Površina:</strong> {deal['property']['area_m2']} m²</p>
                        <p><strong>🏠 Sobe:</strong> {deal['property']['rooms']}</p>
                    </div>
                    <div>
                        <p><strong>💰 Cena:</strong> €{deal['current_price']:,.0f}</p>
                        <p><strong>📊 Fer cena:</strong> €{deal['fair_price']:,.0f}</p>
                        <p style="color: {discount_color}; font-weight: bold;">
                            📉 Popust: {deal['discount']*100:.1f}% (€{deal['discount_amount']:,.0f})
                        </p>
                    </div>
                </div>
                
                <p><strong>⭐ Score:</strong> {deal['score']}/100</p>
                
                <a href="{deal['property']['link']}" 
                   style="display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                    Pogledaj oglas →
                </a>
            </div>
            """
        
        html += """
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px;">
                <h3>💡 Saveti za investiranje:</h3>
                <ul>
                    <li>Proveri stanje nekretnine uživo</li>
                    <li>Angažuj advokata za proveru papira</li>
                    <li>Pregovaraj za dodatni popust</li>
                    <li>Proveri planove za kvart (nova gradnja, metro, itd)</li>
                </ul>
            </div>
            
            <p style="color: #7f8c8d; margin-top: 20px; font-size: 12px;">
                Ova poruka je automatski generisana od Serbian Estate Intelligence sistema.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, recipient: str, subject: str, body: str):
        """Šalje email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email poslat na {recipient}")
            
        except Exception as e:
            logger.error(f"Greška pri slanju emaila: {str(e)}")
    
    def create_telegram_message(self, deals: List[Dict]) -> str:
        """Kreira poruku za Telegram"""
        msg = "🏠 *Pronađene potcenjene nekretnine*\n\n"
        
        for i, deal in enumerate(deals[:5], 1):
            msg += f"*{i}. {deal['property']['title']}*\n"
            msg += f"📍 {deal['property']['city']}, {deal['property']['municipality']}\n"
            msg += f"💰 €{deal['current_price']:,.0f} (popust {deal['discount']*100:.0f}%)\n"
            msg += f"📏 {deal['property']['area_m2']}m², {deal['property']['rooms']} soba\n"
            msg += f"⭐ Score: {deal['score']}/100\n"
            msg += f"🔗 {deal['property']['link']}\n\n"
        
        return msg


if __name__ == "__main__":
    # Test
    notifier = DealNotifier()
    
    # Primer deal podataka
    test_deals = [{
        'property': {
            'external_id': 'test123',
            'title': 'Odličan stan na Vračaru',
            'city': 'Beograd',
            'municipality': 'Vračar',
            'area_m2': 65,
            'rooms': 2.0,
            'link': 'https://example.com/stan'
        },
        'current_price': 120000,
        'fair_price': 150000,
        'discount': 0.20,
        'discount_amount': 30000,
        'score': 85.5
    }]
    
    # Pošalji test notifikaciju
    notifier.send_deal_alert(test_deals, 'test@example.com')