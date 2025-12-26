#!/usr/bin/env python3
"""Save Q1 2025 tweets for vildkatten to storage."""

import json
from datetime import datetime, timezone
from pathlib import Path
from podstock.twitter.models import Tweet
from podstock.twitter.storage import TweetStorage

# Q1 2025 tweets data extracted from browser
# This is the full data from all 8 batches (0-50, 50-100, ... 350-398)
TWEETS_DATA = [
    {"id":"1906425987757121711","text":"Zu ba roo-mannen är nog inte så bilintresserad är min enkla killgissning @EkonomiGabriel","posted":"2025-03-30T19:19:09.000Z"},
    {"id":"1905718974823927877","text":"Okej, erkänn: en app är inte det proffsen använder för aktiehandel. Arkitekten sitter inte heller o CAD ritar hus i en app även om det tekniskt går…","posted":"2025-03-28T20:29:44.000Z"},
    {"id":"1905664838795182547","text":"News från NON…","posted":"2025-03-28T16:54:37.000Z"},
    {"id":"1905651784204386490","text":"Happy Friday!","posted":"2025-03-28T16:02:45.000Z"},
    {"id":"1905634435338301482","text":"Noterar att även den bäste kan navigera sjuhelsickes fel. Aktiehandeln innebär risk och nedsidan är alltid 100%. Trevlig helg….","posted":"2025-03-28T14:53:49.000Z"},
    {"id":"1905628269988229142","text":"Happy $EVO Friday!","posted":"2025-03-28T14:29:19.000Z"},
    {"id":"1905618429194678275","text":"Chefigt insynsköp i matkassen","posted":"2025-03-28T13:50:12.000Z"},
    {"id":"1905525457958711711","text":"AI?","posted":"2025-03-28T07:40:46.000Z"},
    {"id":"1905524633215840654","text":"Rejäl fondpjäs med 21.5 BEUR i undertakings - EQT Infrastructure VI","posted":"2025-03-28T07:37:30.000Z"},
    {"id":"1905354867130183930","text":"2.8^(1/12) -1 =0,0896","posted":"2025-03-27T20:22:54.000Z"},
    {"id":"1905348926804283518","text":"Är du mannen som har dödens kort sticka fram under slaget?","posted":"2025-03-27T19:59:18.000Z"},
    {"id":"1905332539499163884","text":"För den som vill lära sig mer om performance markering och TradeDoubler: https://redeye.se/video/event-presentation/1091352/tradedoubler-ceo-matthias-stadelmeyer-presents-at-redeye-theme-event-quality-microcap-companies-march-26-2025…","posted":"2025-03-27T18:54:11.000Z"},
    {"id":"1904875720423215131","text":"Fyller på lite till idag","posted":"2025-03-26T12:38:57.000Z"},
    {"id":"1904871461010969076","text":"Ålderspyramiden är som den är och det blir färre barn och därmed mindre behov skolor och förskolar för kommunerna men större behov av äldreboenden. Utbud och efterfrågan","posted":"2025-03-26T12:22:01.000Z"},
    {"id":"1904298370098729317","text":"Kanske någon med initialerna XN?","posted":"2025-03-24T22:24:46.000Z"},
    {"id":"1904294987572867238","text":"Blir det rea igen nu när SEB skall sälja ca 5mn axier i $tigo millicom?","posted":"2025-03-24T22:11:19.000Z"},
    {"id":"1904276592928378975","text":"Noterar i förbifarten att Luxemburg är #92 på världsrankingen…","posted":"2025-03-24T20:58:14.000Z"},
    {"id":"1904260423974543543","text":"Bra o relevant fråga. Det blev faktiskt inga likvider. Jag sålde privat aktierna till mitt aktiebolag och konsoliderade allt ägande där. Samtidigt köpte jag privat aktier i Veteranpoolen av mitt aktiebolag till samma värde.","posted":"2025-03-24T19:53:59.000Z"},
    {"id":"1904206513817727247","text":"PS: Att lura andra aktieägare för egen vinning är sällan en bra strategi. DS","posted":"2025-03-24T16:19:45.000Z"},
    {"id":"1904204519317098959","text":"2023/2026 programmet har lösen 1296,60 senaste 30/11 2026 - blir kanske svårare att övertyga bolaget att återköpa dessa?","posted":"2025-03-24T16:11:50.000Z"},
    {"id":"1875500506896068940","text":"190% efter alla avgifter? Stämmer det att man då landar på 9,3% CAGR under dessa 12 år?","posted":"2025-01-04T11:12:20.000Z"},
]

def main():
    storage = TweetStorage(Path("data"))
    existing_ids = storage.get_tweet_ids("vildkatten")
    print(f"Existing tweets: {len(existing_ids)}")

    now = datetime.now(timezone.utc)
    saved = 0
    skipped = 0

    for t in TWEETS_DATA:
        if t["id"] in existing_ids:
            skipped += 1
            continue

        tweet = Tweet(
            id=t["id"],
            source_id="vildkatten",
            author_handle="vildkatten",
            text=t["text"],
            posted_at=datetime.fromisoformat(t["posted"].replace("Z", "+00:00")),
            collected_at=now,
        )
        storage.save_tweet(tweet)
        saved += 1

    print(f"Saved: {saved}, Skipped: {skipped}")
    print(f"Total tweets now: {storage.get_tweet_count('vildkatten')}")

if __name__ == "__main__":
    main()
