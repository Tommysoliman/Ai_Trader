import feedparser
import requests

# Test Reuters RSS
print("=" * 60)
print("Testing Reuters RSS Feed")
print("=" * 60)
try:
    url = 'https://feeds.reuters.com/reuters/technologyNews'
    print(f'URL: {url}')
    feed = feedparser.parse(url)
    print(f'Entries found: {len(feed.entries)}')
    if feed.entries:
        for i, entry in enumerate(feed.entries[:3]):
            print(f'\n  Entry {i+1}: {entry.get("title", "No title")[:80]}...')
    else:
        print('No entries found')
        print('Feed status:', feed.get('status'))
        print('Feed bozo:', feed.get('bozo'))
        print('Feed bozo exception:', feed.get('bozo_exception'))
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')

print("\n" + "=" * 60)
print("Testing New York Times API")
print("=" * 60)
try:
    api_key = '6D2eiLvS2MO6mrEYyjOBRJ5FLpvOsPoboaeeF4DryeqDBEXK'
    url = 'https://api.nytimes.com/svc/search/v2/articlesearch.json'
    params = {
        'q': 'technology',
        'sort': 'newest',
        'api-key': api_key,
        'page': 0
    }
    print(f'URL: {url}')
    print(f'Query: {params["q"]}')
    response = requests.get(url, params=params, timeout=10)
    print(f'Status Code: {response.status_code}')
    
    if response.status_code != 200:
        print(f'Response text: {response.text[:200]}...')
    else:
        data = response.json()
        status = data.get('status')
        print(f'API Status: {status}')
        
        docs = data.get('response', {}).get('docs', [])
        print(f'Articles found: {len(docs)}')
        
        if docs:
            for i, doc in enumerate(docs[:3]):
                headline = doc.get('headline', {}).get('main', 'No title')
                print(f'\n  Article {i+1}: {headline[:80]}...')
        else:
            print('Response:', data)
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
