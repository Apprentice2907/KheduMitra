import json
data = json.load(open('data/sample_dataset.json', encoding='utf-8'))
gu_entries = [d for d in data if d.get('metadata', {}).get('language') == 'gu']
print(f'Total entries: {len(data)}')
print(f'Gujarati entries: {len(gu_entries)}')
# Check content_gu field (where Gujarati script lives)
gu_content_entries = [d for d in data if d.get('content_gu', '').strip()]
print(f'Entries with content_gu: {len(gu_content_entries)}')
sample = gu_content_entries[0]['content_gu'][:100] if gu_content_entries else 'NONE'
print(f'Sample Gujarati content: {sample}')
has_gujarati = any(0x0A80 <= ord(c) <= 0x0AFF for c in sample)
print(f'Contains real Gujarati Unicode (not escaped): {has_gujarati}')
