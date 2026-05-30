import re
from pathlib import Path

def extract_urls(file_path):
    content = Path(file_path).read_text(encoding='utf-8')
    urls = re.findall(r'https?://[^\s"\'\(\)]+', content)
    return sorted(list(set(urls)))

files = [
    'script/nenen88.py',
    'script/SM/setup.py',
    'script/KC/setup.py'
]

all_urls = []
for f in files:
    try:
        all_urls.extend(extract_urls(f))
    except Exception as e:
        print(f"Error reading {f}: {e}")

unique_urls = sorted(list(set(all_urls)))
for url in unique_urls:
    print(url)
