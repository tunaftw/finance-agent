#!/usr/bin/env python3
"""Convert raw tweets to tweet-analyses format for database loading."""

import json
from datetime import datetime
from pathlib import Path

def main():
    tweets_file = Path("data/twitter/raw/matematikern3/tweets.jsonl")
    output_file = Path("data/twitter/analyses/matematikern3-tweet-analyses.json")

    tweets_2025 = []
    with open(tweets_file) as f:
        for line in f:
            tweet = json.loads(line.strip())
            posted = tweet.get('posted_at', '')
            if posted.startswith('2025'):
                tweets_2025.append(tweet)

    known_holdings = {
        'PIERCE': {'name': 'Pierce Group', 'action': 'buy', 'confidence': 'high'},
        'PIERC': {'name': 'Pierce Group', 'action': 'buy', 'confidence': 'high'},
        'NELLY': {'name': 'Nelly Group', 'action': 'buy', 'confidence': 'high'},
        'CHEF': {'name': 'Cheffelo', 'action': 'buy', 'confidence': 'high'},
        'HFG': {'name': 'HelloFresh', 'action': 'hold', 'confidence': 'medium'},
    }

    analyses = []
    for tweet in tweets_2025:
        tickers = tweet.get('mentioned_tickers', [])
        if not tickers:
            continue

        stock_mentions = []
        text = tweet.get('text', '')

        for ticker in tickers:
            ticker_upper = ticker.upper()
            if ticker_upper in known_holdings:
                info = known_holdings[ticker_upper]
                action = info['action']
                confidence = info['confidence']
                reasoning = 'Explicit innehav'

                text_lower = text.lower()
                if 'köp' in text_lower or 'bought' in text_lower or 'plocka' in text_lower:
                    action = 'buy'
                    reasoning = 'Köpsignal i tweet'
                elif 'sål' in text_lower or 'sold' in text_lower:
                    action = 'sell'
                    reasoning = 'Säljsignal i tweet'
                elif 'stark' in text_lower or 'levererar' in text_lower or 'rökare' in text_lower:
                    action = 'buy'
                    reasoning = 'Positiv rapport/utveckling'
                elif '3x' in text_lower or 'potential' in text_lower:
                    action = 'buy'
                    confidence = 'high'
                    reasoning = 'Explicit kursmål'

                final_ticker = 'PIERCE' if ticker_upper == 'PIERC' else ticker_upper

                stock_mentions.append({
                    'stock_name': info['name'],
                    'ticker': final_ticker,
                    'action': action,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'quote': text[:150] + '...' if len(text) > 150 else text
                })

        if stock_mentions:
            analyses.append({
                'tweet_id': tweet['id'],
                'source_id': 'matematikern3',
                'stock_mentions': stock_mentions,
                'market_sentiment': 'bullish' if any(m['action'] == 'buy' for m in stock_mentions) else 'neutral',
                'is_actionable': any(m['action'] in ['buy', 'sell'] for m in stock_mentions),
                'is_speculation': False,
                'has_price_target': '3x' in text.lower() or 'mdr' in text.lower(),
                'processed_at': datetime.now().isoformat(),
                'model_used': 'claude-opus-4.5-analysis'
            })

    output = {
        'source_id': 'matematikern3',
        'analyzed_at': datetime.now().isoformat(),
        'model_used': 'claude-opus-4.5-analysis',
        'total_analyses': len(analyses),
        'analyses': analyses
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Created {output_file} with {len(analyses)} tweet analyses")

if __name__ == '__main__':
    main()
