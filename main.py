import argparse
from datetime import datetime
import sqlite3
from typing import List
from urllib.parse import urlsplit
from twilio.rest import Client
import time

from sources import Offer, HANDLERS

# Twilio setup
SOURCE_PHONENUMBER = "<phone_number_from_twilio>"
TARGET_PHONENUMBER = "<your_phonenumber>"
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN =""

def init_database(db: sqlite3.Connection):
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS offers (id INTEGER NOT NULL PRIMARY KEY, title TEXT, url TEXT, scraped_at TEXT)")
    cur.close()


def filter_missing_offers(db: sqlite3.Connection, offers: List[Offer]) -> List[Offer]:
    missing_offers = []

    cur = db.cursor()

    for offer in offers:
        cur.execute("SELECT * FROM offers WHERE url = ?", (offer.url,))
        result = cur.fetchall()
        if not result:
            missing_offers.append(offer)

    cur.close()

    return missing_offers


def save_offers(db: sqlite3.Connection, offers: List[Offer]):
    cur = db.cursor()

    scraped_at = datetime.now().isoformat()
    rows = [(offer.title, offer.url, scraped_at) for offer in offers]
    cur.executemany("INSERT INTO offers (title, url, scraped_at) VALUES (?, ?, ?)", rows)

    cur.close()
    db.commit()


def twilio_send(offer: Offer):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    body = "Nowa oferta \"{}\" {}".format(offer.title, offer.url)

    message1 = client.messages \
                    .create(
                        body=body,
                        from_=SOURCE_PHONENUMBER,
                        to=TARGET_PHONENUMBER
                    )
    message2 = client.messages \
                    .create(
                        body=body,
                        from_=SOURCE_PHONENUMBER,
                        to=TARGET_PHONENUMBER
                    )
    print(message1.sid, message2.sid)
    # headers = {"Access-Token": os.getenv("PUSHBULLET_TOKEN")}

    # response = requests.post("https://api.pushbullet.com/v2/pushes", json=payload, headers=headers)
    # assert response.ok


def gather_offers(url: str) -> List[Offer]:
    split = urlsplit(url)
    handler = HANDLERS[split.netloc]
    return handler(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()

    db = sqlite3.connect("offers.sqlite")
    init_database(db)

    # links with queries - I have selected for wrzeszcz, 3-4 rooms
    queries = [
        "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bfilter_enum_rooms%5D%5B0%5D=three&search%5Bfilter_enum_rooms%5D%5B1%5D=four&search%5Bdistrict_id%5D=99",
        "https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/gdansk/wrzeszcz?distanceRadius=0&page=1&limit=36&market=ALL&locations=%5Bdistricts_6-30%5D&roomsNumber=%5BTHREE%2CFOUR%2CFIVE%2CSIX%5D&viewType=listing&lang=pl&searchingCriteria=wynajem&searchingCriteria=mieszkanie&searchingCriteria=cala-polska",
        "https://ogloszenia.trojmiasto.pl/nieruchomosci-mam-do-wynajecia/mieszkanie/gdansk/wrzeszcz/ri,3_.html",
        "https://gratka.pl/nieruchomosci/mieszkania/wynajem?liczba-pokoi:min=3&lokalizacja[0]=117179&lokalizacja[1]=33771825&lokalizacja[2]=33771827",
        "https://www.morizon.pl/do-wynajecia/mieszkania/gdansk/wrzeszcz/?ps%5Bnumber_of_rooms_from%5D=3",
    ]

    try:
        offers = set()
        for query in queries:
            offers.update(gather_offers(query))
    except:
        print("Errored")

    missing = filter_missing_offers(db, list(offers))

    for offer in missing:
        twilio_send(offer)

    save_offers(db, missing)

    print(f"[{datetime.now()}] New offers: {len(missing)}")

if __name__ == "__main__":
    while(True):
        main()
        time.sleep(600)

