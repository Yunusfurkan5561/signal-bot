from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import schedule
import time
import threading

TELEGRAM_TOKEN   = "8061752013:AAHoLdP85_d77ibhj8JTX6IdjNo5J_XMrTA"
ADMIN_CHAT_ID    = "1473625303"
COINGECKO_KEY    = "CG-PYL1qRSqmnKDXBehAKCwMzv7"
TWELVE_KEY       = "50bf4829752d400db746c13cbdf42f4c"

gonderilen = {}
son_update_id = 0
kullanicilar = set()

BIST100 = [
    "AKBNK","ARCLK","ASELS","BIMAS","DOHOL","EKGYO","EREGL","FROTO","GARAN","GUBRF",
    "HALKB","ISCTR","KCHOL","KOZAL","KRDMD","MGROS","PETKM","PGSUS","SAHOL","SASA",
    "SISE","TAVHL","TCELL","THYAO","TKFEN","TOASO","TTKOM","TUPRS","VAKBN","YKBNK",
    "AEFES","AGESA","AKFEN","AKGRT","AKSEN","ALARK","ALBRK","ALKIM","ANSGR","ARDYZ",
    "ASUZU","AYGAZ","BAGFS","BANVT","BRISA","BRSAN","CCOLA","CIMSA","CLEBI","CMBTN",
    "DEVA","ECILC","ECZYT","EGEEN","EMKEL","ENJSA","ENKAI","ERBOS","ESCOM","FENER",
    "GEREL","GLYHO","GOLTS","GOODY","GRSEL","GSDHO","GSRAY","HATEK","HEKTS","HLGYO",
    "HRKET","HUNER","ICBCT","IHEVA","IHLAS","IMASM","INDES","INFO","INVEO","IPEKE",
]

veriler = {
    "kripto": [
        ("bitcoin", "BTC"), ("ethereum", "ETH"), ("binancecoin", "BNB"),
        ("solana", "SOL"), ("ripple", "XRP"), ("dogecoin", "DOGE"),
        ("cardano", "ADA"), ("tron", "TRX"), ("avalanche-2", "AVAX"),
        ("chainlink", "LINK"), ("shiba-inu", "SHIB"), ("the-open-network", "TON"),
        ("polkadot", "DOT"), ("bitcoin-cash", "BCH"), ("near", "NEAR"),
        ("matic-network", "MATIC"), ("litecoin", "LTC"), ("internet-computer", "ICP"),
        ("uniswap", "UNI"), ("ethereum-classic", "ETC"),
    ]
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot active!")
    def log_message(self, *args):
        pass

def web_sunucu():
    HTTPServer(("0.0.0.0", 10000), Handler).serve_forever()

def telegram_gonder(mesaj, chat_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    hedefler = [chat_id] if chat_id else list(kullanicilar) + [ADMIN_CHAT_ID]
    for cid in hedefler:
        try:
            requests.post(url, json={"chat_id": cid, "text": mesaj}, timeout=10)
        except Exception as e:
            print(f"Telegram hata ({cid}): {e}")

def veri_cek_kripto(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}&x_cg_demo_api_key={COINGECKO_KEY}"
    r = requests.get(url, timeout=15)
    return [float(x[4]) for x in r.json()]

def veri_cek_bist(sembol):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{sembol}.IS?interval=1d&range=2y"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    data = r.json()
    fiyatlar = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return [f for f in fiyatlar if f is not None]

def ema_dizi(fiyatlar, period):
    k = 2 / (period + 1)
    sonuc = [fiyatlar[0]]
    for f in fiyatlar[1:]:
        sonuc.append(f * k + sonuc[-1] * (1 - k))
    return sonuc

def sart_kontrol(fiyatlar, yon="al"):
    if len(fiyatlar) < 210:
        return False, False
    ema200 = ema_dizi(fiyatlar, 200)
    fast   = ema_dizi(fiyatlar, 12)
    slow   = ema_dizi(fiyatlar, 26)
    macd   = [f - s for f, s in zip(fast, slow)]
    signal = ema_dizi(macd, 9)
    fiyat  = fiyatlar[-2]
    m      = macd[-2]
    m_sig  = signal[-2]
    if yon == "al":
        simdi  = fiyat > ema200[-2] and m > 0 and m_sig > 0 and m > m_sig
        onceki = fiyatlar[-3] > ema200[-3] and macd[-3] > 0 and signal[-3] > 0 and macd[-3] > signal[-3]
    else:
        simdi  = fiyat < ema200[-2] and m < 0 and m_sig < 0 and m < m_sig
        onceki = fiyatlar[-3] < ema200[-3] and macd[-3] < 0 and signal[-3] < 0 and macd[-3] < signal[-3]
    return simdi, (simdi and not onceki)

def kripto_tara():
    telegram_gonder(f"Kripto tarama basliyor... ({len(veriler['kripto'])} coin)")
    for coin_id, sembol in veriler["kripto"]:
        try:
            gun = veri_cek_kripto(coin_id, 365)
            gun_al, gun_al_yeni = sart_kontrol(gun, "al")
            gun_sat, gun_sat_yeni = sart_kontrol(gun, "sat")
            time.sleep(3)
            dort = veri_cek_kripto(coin_id, 90)
            dort_al, dort_al_yeni = sart_kontrol(dort, "al")
            dort_sat, dort_sat_yeni = sart_kontrol(dort, "sat")
            time.sleep(3)

            if gun_al_yeni and not gonderilen.get(f"{sembol}_gun_al"):
                telegram_gonder(f"AL SINYALI (Gunluk)\n{sembol}")
                gonderilen[f"{sembol}_gun_al"] = True
            elif not gun_al:
                gonderilen[f"{sembol}_gun_al"] = False

            if dort_al_yeni and not gonderilen.get(f"{sembol}_dort_al"):
                telegram_gonder(f"AL SINYALI (4 Saatlik)\n{sembol}")
                gonderilen[f"{sembol}_dort_al"] = True
            elif not dort_al:
                gonderilen[f"{sembol}_dort_al"] = False

            if gun_sat_yeni and not gonderilen.get(f"{sembol}_gun_sat"):
                telegram_gonder(f"SAT SINYALI (Gunluk)\n{sembol}")
                gonderilen[f"{sembol}_gun_sat"] = True
            elif not gun_sat:
                gonderilen[f"{sembol}_gun_sat"] = False

            if dort_sat_yeni and not gonderilen.get(f"{sembol}_dort_sat"):
                telegram_gonder(f"SAT SINYALI (4 Saatlik)\n{sembol}")
                gonderilen[f"{sembol}_dort_sat"] = True
            elif not dort_sat:
                gonderilen[f"{sembol}_dort_sat"] = False

            if gun_al and dort_al and gun_al_yeni and dort_al_yeni:
                telegram_gonder(f"GUCLU AL SINYALI!\n{sembol}")

            print(f"{sembol} Gun AL:{'OK' if gun_al else '-'} SAT:{'OK' if gun_sat else '-'} | 4S AL:{'OK' if dort_al else '-'} SAT:{'OK' if dort_sat else '-'}")

        except Exception as e:
            print(f"{sembol} hata: {e}")
            time.sleep(5)

    telegram_gonder("Kripto tarama tamamlandi!")

def bist_tara():
    telegram_gonder(f"BIST tarama basliyor... ({len(BIST100)} hisse)")
    for sembol in BIST100:
        try:
            fiyatlar = veri_cek_bist(sembol)
            al, al_yeni = sart_kontrol(fiyatlar, "al")
            sat, sat_yeni = sart_kontrol(fiyatlar, "sat")
            if al_yeni and not gonderilen.get(f"{sembol}_al"):
                telegram_gonder(f"AL SINYALI (BIST)\n{sembol}")
                gonderilen[f"{sembol}_al"] = True
            elif not al:
                gonderilen[f"{sembol}_al"] = False
            if sat_yeni and not gonderilen.get(f"{sembol}_sat"):
                telegram_gonder(f"SAT SINYALI (BIST)\n{sembol}")
                gonderilen[f"{sembol}_sat"] = True
            elif not sat:
                gonderilen[f"{sembol}_sat"] = False
            print(f"{sembol} AL:{'OK' if al else '-'} SAT:{'OK' if sat else '-'}")
            time.sleep(8)
        except Exception as e:
            print(f"{sembol} hata: {e}")
            time.sleep(10)
    telegram_gonder("BIST tarama tamamlandi!")

def komut_dinle():
    global son_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    while True:
        try:
            r = requests.get(url, params={"offset": son_update_id + 1, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])
            for update in updates:
                son_update_id = update["update_id"]
                mesaj = update.get("message", {}).get("text", "")
                chat_id = str(update.get("message", {}).get("chat", {}).get("id", ""))
                if not chat_id:
                    continue

                # Her mesaj atan kullaniciyi kaydet
                kullanicilar.add(chat_id)

                print(f"Komut: {mesaj} | Chat: {chat_id}")

                # Sadece admin yapabilir
                if mesaj.startswith("/ekle "):
                    if chat_id != ADMIN_CHAT_ID:
                        telegram_gonder("Bu komut sadece admin icin.", chat_id)
                        continue
                    parca = mesaj.split()
                    if len(parca) == 3:
                        veriler["kripto"].append((parca[1].lower(), parca[2].upper()))
                        telegram_gonder(f"{parca[2].upper()} eklendi!")
                    else:
                        telegram_gonder("Format: /ekle coin-id SEMBOL", chat_id)

                elif mesaj.startswith("/sil "):
                    if chat_id != ADMIN_CHAT_ID:
                        telegram_gonder("Bu komut sadece admin icin.", chat_id)
                        continue
                    sembol = mesaj.split()[1].upper()
                    veriler["kripto"] = [(c, s) for c, s in veriler["kripto"] if s != sembol]
                    telegram_gonder(f"{sembol} silindi!")

                # Herkes yapabilir
                elif mesaj == "/start":
                    telegram_gonder("Merhaba! Sinyal botuna hosgeldin. /yardim yaz.", chat_id)

                elif mesaj == "/tara":
                    threading.Thread(target=kripto_tara).start()

                elif mesaj == "/bist":
                    threading.Thread(target=bist_tara).start()

                elif mesaj == "/liste":
                    telegram_gonder("Kriptolar:\n" + "\n".join([s for _, s in veriler["kripto"]]), chat_id)

                elif mesaj == "/bistliste":
                    telegram_gonder("BIST100:\n" + "\n".join(BIST100), chat_id)

                elif mesaj == "/yardim":
                    telegram_gonder(
                        "/tara - Kripto tara\n"
                        "/bist - BIST tara\n"
                        "/liste - Kripto listesi\n"
                        "/bistliste - BIST listesi\n"
                        "/yardim - Yardim",
                        chat_id
                    )

        except Exception as e:
            print(f"Komut hatasi: {e}")
            time.sleep(5)

Thread(target=web_sunucu, daemon=True).start()
threading.Thread(target=komut_dinle, daemon=True).start()
telegram_gonder(f"Sinyal Botu aktif! /yardim yaz.")
kripto_tara()
schedule.every(4).hours.do(kripto_tara)
schedule.every(4).hours.do(bist_tara)
while True:
    schedule.run_pending()
    time.sleep(60)
