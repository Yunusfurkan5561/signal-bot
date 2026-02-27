import requests
import schedule
import time
import threading

TELEGRAM_TOKEN   = "8061752013:AAHoLdP85_d77ibhj8JTX6IdjNo5J_XMrTA"
TELEGRAM_CHAT_ID = "1473625303"
COINGECKO_KEY    = "CG-PYL1qRSqmnKDXBehAKCwMzv7"
TWELVE_KEY       = "50bf4829752d400db746c13cbdf42f4c"
gonderilen = {}
son_update_id = 0
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
def veri_cek_bist(sembol):
    url = f"https://api.twelvedata.com/time_series?symbol={sembol}&exchange=BIST&interval=1day&outputsize=300&apikey={TWELVE_KEY}"
    r = requests.get(url, timeout=15)
    data = r.json()
    if "values" not in data:
        raise Exception(f"veri yok")
    return [float(x["close"]) for x in reversed(data["values"])]

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
def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj}, timeout=10)
    except Exception as e:
        print(f"Telegram hata: {e}")

def veri_cek_kripto(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}&x_cg_demo_api_key={COINGECKO_KEY}"
    r = requests.get(url, timeout=15)
    return [float(x[4]) for x in r.json()]

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
                telegram_gonder(f"AL SINYALI (Gunluk)\n{sembol}\nTum sartlar olusту!")
                gonderilen[f"{sembol}_gun_al"] = True
            elif not gun_al:
                gonderilen[f"{sembol}_gun_al"] = False

            if dort_al_yeni and not gonderilen.get(f"{sembol}_dort_al"):
                telegram_gonder(f"AL SINYALI (4 Saatlik)\n{sembol}\nTum sartlar olusту!")
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
                telegram_gonder(f"GUCLU AL SINYALI!\n{sembol}\nHem gunluk hem 4 saatlik!")

            print(f"{sembol} Gun AL:{'OK' if gun_al else '-'} SAT:{'OK' if gun_sat else '-'} | 4S AL:{'OK' if dort_al else '-'} SAT:{'OK' if dort_sat else '-'}")

        except Exception as e:
            print(f"{sembol} hata: {e}")
            time.sleep(5)

    telegram_gonder("Kripto tarama tamamlandi!")

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
                print(f"Komut: {mesaj}")

                if mesaj == "/tara":
                    threading.Thread(target=kripto_tara).start()
                elif mesaj == "/bist":
                    threading.Thread(target=bist_tara).start()
                elif mesaj.startswith("/ekle "):
                    parca = mesaj.split()
                    if len(parca) == 3:
                        coin_id = parca[1].lower()
                        sembol = parca[2].upper()
                        veriler["kripto"].append((coin_id, sembol))
                        telegram_gonder(f"{sembol} listeye eklendi!")
                    else:
                        telegram_gonder("Format: /ekle coin-id SEMBOL\nornek: /ekle avalanche-2 AVAX")

                elif mesaj.startswith("/sil "):
                    sembol = mesaj.split()[1].upper()
                    veriler["kripto"] = [(c, s) for c, s in veriler["kripto"] if s != sembol]
                    telegram_gonder(f"{sembol} listeden silindi!")

                elif mesaj == "/liste":
                    liste = "\n".join([s for _, s in veriler["kripto"]])
                    telegram_gonder(f"Kriptolar:\n{liste}")

                elif mesaj == "/yardim":
                    telegram_gonder("/tara - Kripto tara\n/bist - BIST tara\n/ekle bitcoin BTC - Ekle\n/sil BTC - Sil\n/liste - Liste")

        except Exception as e:
            print(f"Komut hatasi: {e}")
            time.sleep(5)

threading.Thread(target=komut_dinle, daemon=True).start()
telegram_gonder("Sinyal Botu aktif!\n/yardim yaz komutlari gor.")
kripto_tara()
schedule.every(4).hours.do(kripto_tara)

while True:
    schedule.run_pending()
    time.sleep(60)
