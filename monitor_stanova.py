import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime

class HaloOglasiMonitor:
    def __init__(self, url, check_interval=120):
        """
        url: URL sa filterima koje želiš da pratiš
        check_interval: interval provere u sekundama (default 2 minuta)
        """
        self.url = url
        self.check_interval = check_interval
        self.seen_ads_file = "seen_ads.json"
        self.seen_ads = self.load_seen_ads()
        
        # TVOJI TELEGRAM KREDENCIJALI
        self.bot_token = "8374213656:AAEnvDyhMbFtHVtgsHKtGyiFgRKseNMNF78"
        self.chat_id = "-5084974453"  # ID Telegram grupe "Stanovi - Oglasi"
        
    def load_seen_ads(self):
        """Učitaj već viđene oglase iz fajla"""
        if os.path.exists(self.seen_ads_file):
            with open(self.seen_ads_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_seen_ads(self):
        """Sačuvaj viđene oglase u fajl"""
        with open(self.seen_ads_file, 'w', encoding='utf-8') as f:
            json.dump(self.seen_ads, f, ensure_ascii=False, indent=2)
    
    def fetch_ads(self):
        """Preuzmi oglase sa sajta"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ Greška pri preuzimanju stranice: {e}")
            return None
    
    def parse_ads(self, html):
        """Parsiraj HTML i izvuci oglase"""
        soup = BeautifulSoup(html, 'html.parser')
        ads = []
        
        # Pronađi sve linkove ka oglasima
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            
            # Filtriraj samo linkove ka oglasima stanova (PRODAJA)
            if '/nekretnine/prodaja-stanova/' in href and '?' in href:
                try:
                    # Izvuci ID iz URL-a
                    ad_id = href.split('/')[-1].split('?')[0]
                    
                    # Preskoci ako je vec u listi
                    if any(ad['id'] == ad_id for ad in ads):
                        continue
                    
                    # Pokusaj da izvuces naslov
                    title = "Novi oglas za stan"
                    title_elem = link.find_parent()
                    if title_elem:
                        text = title_elem.get_text(strip=True)
                        if text and len(text) > 5:
                            title = text[:200]
                    
                    full_link = f"https://www.halooglasi.com{href}" if not href.startswith('http') else href
                    
                    ads.append({
                        'id': ad_id,
                        'title': title,
                        'link': full_link,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    continue
        
        # Ukloni duplikate po ID-u
        unique_ads = []
        seen_ids = set()
        for ad in ads:
            if ad['id'] not in seen_ids:
                unique_ads.append(ad)
                seen_ids.add(ad['id'])
        
        return unique_ads
    
    def send_telegram_notification(self, ad):
        """Pošalji Telegram obaveštenje za jedan oglas"""
        message = f"🏠 <b>NOVI OGLAS - PRODAJA STANA!</b>\n\n"
        message += f"📋 {ad['title']}\n\n"
        message += f"🔗 <a href='{ad['link']}'>OTVORI OGLAS - ZOVI ODMAH!</a>\n\n"
        message += f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Telegram: Poruka poslata!")
            else:
                print(f"⚠️ Telegram: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Greška pri slanju Telegram poruke: {e}")
    
    def test_telegram(self):
        """Testiraj Telegram konekciju"""
        print("\n🧪 Testiram Telegram konekciju...")
        message = "✅ <b>TEST PORUKA</b>\n\nBot radi! Čekaću nove oglase za stanove."
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram radi! Proveri svoj Telegram.")
                return True
            else:
                print(f"❌ Telegram greška: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"❌ Ne mogu da se povežem sa Telegramom: {e}")
            return False
    
    def check_for_new_ads(self):
        """Proveri da li ima novih oglasa"""
        print(f"\n🔍 Proveravаm oglase... [{datetime.now().strftime('%H:%M:%S')}]")
        
        html = self.fetch_ads()
        if not html:
            return
        
        current_ads = self.parse_ads(html)
        print(f"📊 Pronađeno {len(current_ads)} oglasa na stranici")
        
        # Proveri koje oglase nismo videli
        new_ads = [ad for ad in current_ads if ad['id'] not in self.seen_ads]
        
        if new_ads:
            print(f"\n🎉 NOVO! Pronađeno {len(new_ads)} novih oglasa:")
            
            for ad in new_ads:
                print(f"\n📢 Novi oglas: {ad['id']}")
                print(f"   🔗 {ad['link']}")
                
                # Pošalji Telegram obaveštenje
                self.send_telegram_notification(ad)
                
                # Dodaj u viđene
                self.seen_ads.append(ad['id'])
                
                # Pauza između poruka da ne spamujemo
                time.sleep(1)
            
            # Sačuvaj ažurirane viđene oglase
            self.save_seen_ads()
            print(f"\n✅ Svi novi oglasi su sačuvani i poslati!")
            
        else:
            print("✓ Nema novih oglasa")
    
    def run(self):
        """Pokreni monitoring"""
        print("\n" + "="*70)
        print("🚀 HALO OGLASI MONITOR - PRAĆENJE NOVIH STANOVA")
        print("="*70)
        print(f"\n🔗 URL: {self.url[:80]}...")
        print(f"⏱️  Interval provere: {self.check_interval} sekundi ({self.check_interval//60} min)")
        print(f"📂 Već viđeno oglasa: {len(self.seen_ads)}")
        
        # Test Telegram
        if not self.test_telegram():
            print("\n⚠️ UPOZORENJE: Telegram test nije prošao!")
            print("Proveri da si pokrenuo bota: https://t.me/dzklic_bot")
            response = input("\nNastavi svejedno? (y/n): ")
            if response.lower() != 'y':
                return
        
        print("\n" + "="*70)
        print("✅ BOT JE AKTIVAN - Čekam nove oglase...")
        print("="*70)
        print("\n💡 Pritisni Ctrl+C da zaustaviš\n")
        
        while True:
            try:
                self.check_for_new_ads()
                print(f"💤 Spavam {self.check_interval} sekundi...\n")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n" + "="*70)
                print("🛑 MONITOR ZAUSTAVLJEN")
                print("="*70)
                print(f"📊 Ukupno praćeno oglasa: {len(self.seen_ads)}")
                break
                
            except Exception as e:
                print(f"\n❌ Neočekivana greška: {e}")
                print(f"Pokušavam ponovo za {self.check_interval} sekundi...")
                time.sleep(self.check_interval)


# POKRETANJE BOTA
if __name__ == "__main__":
    # Tvoj URL sa filterima (Prodaja stanova - Beograd, 50k-110k EUR, 25-60m2, lift, uknjiženo)
    URL = "https://www.halooglasi.com/nekretnine/prodaja-stanova?grad_id_l-lokacija_id_l-mikrolokacija_id_l=40381%2C40769&cena_d_from=50000&cena_d_to=110000&cena_d_unit=4&kvadratura_d_from=25&kvadratura_d_to=60&kvadratura_d_unit=1&sprat_order_i_from=11&dodatno_id_ls=12000004%2C12000025&ostalo_id_ls=12100001"
    
    # Provera na svaka 2 minuta (120 sekundi)
    # Možeš smanjiti na 60 (1 min) ako želiš još brže
    CHECK_INTERVAL = 120
    
    # Pokreni monitor
    monitor = HaloOglasiMonitor(URL, CHECK_INTERVAL)
    monitor.run()