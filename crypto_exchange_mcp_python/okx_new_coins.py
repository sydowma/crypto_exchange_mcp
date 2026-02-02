import requests
import json
from datetime import datetime, timedelta


def fetch_okx_instruments(inst_type):
    """Fetch instruments data from OKX public API"""
    url = f"https://www.okx.com/api/v5/public/instruments?instType={inst_type}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {inst_type} data: {e}")
        return None


def get_new_coins():
    """Get new coins from OKX sorted by listing time"""
    instrument_types = ['SPOT', 'SWAP', 'MARGIN']
    all_instruments = []
    
    for inst_type in instrument_types:
        print(f"Fetching {inst_type} instruments...")
        data = fetch_okx_instruments(inst_type)
        
        if data and data.get('code') == '0':
            instruments = data.get('data', [])
            for instrument in instruments:
                # Include all instruments, use '0' as default listTime if not present
                list_time = instrument.get('listTime', '0')
                inst_id = instrument.get('instId', '')
                base_ccy = instrument.get('baseCcy')
                
                # For SWAP instruments, extract baseCcy from instId if not available
                if not base_ccy and inst_type == 'SWAP' and inst_id:
                    # Extract base currency from patterns like "SYRUP-USDT-SWAP"
                    parts = inst_id.split('-')
                    if len(parts) >= 2:
                        base_ccy = parts[0]
                
                all_instruments.append({
                    'instId': inst_id,
                    'baseCcy': base_ccy or 'N/A',
                    'quoteCcy': instrument.get('quoteCcy'),
                    'listTime': list_time,
                    'instType': inst_type
                })
    
    # Sort by listTime descending (newest first)
    all_instruments.sort(key=lambda x: int(x['listTime']), reverse=True)
    
    return all_instruments


def format_timestamp(timestamp):
    """Convert timestamp to readable format"""
    if timestamp == '0':
        return 'N/A'
    return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')


def main():
    print("Fetching new coins from OKX...")
    instruments = get_new_coins()
    
    if not instruments:
        print("No instruments found")
        return
    
    # Calculate cutoff time (30 days ago)
    cutoff_time = datetime.now() - timedelta(days=30)
    cutoff_timestamp = int(cutoff_time.timestamp() * 1000)
    
    # Extract unique base currencies listed within last 30 days
    seen_base_currencies = set()
    unique_base_currencies = []
    
    for instrument in instruments:
        base_ccy = instrument['baseCcy']
        list_time = instrument['listTime']
        
        # Skip if no valid listTime or older than 30 days
        if list_time == '0' or int(list_time) < cutoff_timestamp:
            continue
            
        if base_ccy and base_ccy != 'N/A' and base_ccy not in seen_base_currencies:
            seen_base_currencies.add(base_ccy)
            unique_base_currencies.append({
                'baseCcy': base_ccy,
                'listTime': instrument['listTime'],
                'instType': instrument['instType']
            })
    
    print(f"\nFound {len(unique_base_currencies)} unique base currencies, showing top 30:\n")
    
    top_30 = unique_base_currencies[:30]
    base_currencies_list = [item['baseCcy'] for item in top_30]
    
    print(",".join(base_currencies_list))


if __name__ == "__main__":
    main()