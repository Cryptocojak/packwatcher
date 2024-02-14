import tweepy
import time
import logging
import importlib
import pres_club_dict
from web3 import Web3
from env import consumer_key, consumer_secret, access_token, access_token_secret, if_key
import requests
from pres_club_dict import current_pres_club_dict

og_dict = current_pres_club_dict
running = True
query_interval = 7500
CONTRACT_ADDRESS = '0xEEd41d06AE195CA8f5CaCACE4cd691EE75F0683f' #cigawrettes contract
w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{if_key}'))

latest_block = w3.eth.get_block('latest')
nft_contract = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=[
        {
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "tokenURI",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "ownerOf",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
)

next_mint = (nft_contract.functions.totalSupply().call())
current_mint = next_mint - 1

def fetch_metadata(token_id):
    retry_count = 3
    while retry_count > 0:
        try:
            url = f"https://ipfs.io/ipfs/bafybeidgwnebxxrcjj3glcxtncvkeuokynlvb3oimrp4nwmv7sds34lela/{token_id}.json"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logging.warning(f"Received {response.status_code} status code for token ID {token_id}. Retrying... (Remaining retries: {retry_count})")
        except Exception as e:
            logging.warning(f"Failed to fetch metadata for token ID {token_id}. Retrying... (Remaining retries: {retry_count})")
        retry_count -= 1
        if retry_count > 0:
            time.sleep(1)
    logging.error(f"Completely failed to fetch metadata for token ID {token_id}. No more retries.")
    return None

def get_current_number_of_mints(contract):
    global current_mint
    global next_mint
    try:
        next_mint = contract.functions.totalSupply().call()
        current_mint = next_mint - 1
        return current_mint
    except Exception as e:
        logging.exception(f"Error getting total supply: {e}")
        return None   
    
def check_brand(metadata):
    attributes = metadata.get('attributes', [])
    for attribute in attributes:
        if attribute.get('trait_type') == 'Brand':
            return attribute.get('value')
    return None

def query_single_mint(contract, token_id):
    try:
        metadata = fetch_metadata(token_id)
        brand = check_brand(metadata)
        if brand == "President's Club":
            current_owner = contract.functions.ownerOf(token_id).call()
            og_dict.update({token_id: current_owner})
    except Exception as e:
        print(f"Error fetching details for token ID {token_id}: {e}")

client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

def send_tweet(tweet):
    response = client.create_tweet(text=f"{tweet}")
    logging.info(f"\n\n\n tweet sent \n\n https://twitter.com/user/status/{response.data['id']}\n")
    pass

def reload_dict():
    global og_dict
    importlib.reload(pres_club_dict)
    og_dict = pres_club_dict.current_pres_club_dict

def write_dict():
    sorted_new_pres_club_dict = {k: og_dict[k] for k in sorted(og_dict)}
    with open('pres_club_dict.py', 'w') as f:
        f.write('current_pres_club_dict = ' + str(sorted_new_pres_club_dict))

def check_single_pack_owner(token_id):
    current_owner = nft_contract.functions.ownerOf(token_id).call()
    saved_owner = og_dict.get(token_id)
    if current_owner == saved_owner:
        print(f"No change in ownership for pack {token_id}: {saved_owner}.\n")
    else:
        og_dict.update({token_id: current_owner})
        write_dict()
        saved_owner = format_address(saved_owner)
        current_owner = format_address(current_owner)
        print(f"Ownership changed for pack {token_id}: {saved_owner} -> {current_owner}\n")
        tweet = f"Ownership changed for President's Club pack {token_id}: {saved_owner} -> {current_owner}! \n\n https://blur.io/asset/0xeed41d06ae195ca8f5cacace4cd691ee75f0683f/{token_id}."
        send_tweet(tweet)
        

def check_range_of_packs(first, last):
    for pack in range(first, last):
        query_single_mint(nft_contract, pack)
        print(f'checked pack {pack}')

def check_all_packs_owners():
    reload_dict()
    for pack in og_dict.keys():
        check_single_pack_owner(pack)

def format_address(address):
    if len(address) < 11:  # If address is already too short, just return it
        return address
    return address[:6] + '...' + address[-4:]

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    global current_mint
    print('\n')
    last_tweeted = current_mint
    new_mint = get_current_number_of_mints(nft_contract)
    check_all_packs_owners()
    last_pres = next(reversed(current_pres_club_dict))
    check_range_of_packs(last_pres, new_mint+1)
    write_dict()
    club_counter = 0
    
    while running:
        new_mint = get_current_number_of_mints(nft_contract)
        logging.info(f"🚬 🚬 🚬 🚬 🚬 🚬 {new_mint} ")
        last_pres = next(reversed(current_pres_club_dict))
        
        if new_mint is not None and new_mint != last_tweeted:
            logging.info(f"new mint, {new_mint}, last tweeted, {last_tweeted}")
            time.sleep(60)  # Wait for one minute to check for additional mints
            final_mint = get_current_number_of_mints(nft_contract)
            mints_count = final_mint - last_tweeted
            tweet = f"{mints_count} new cigawrette pack(s) detected! \n\n https://blur.io/asset/0xeed41d06ae195ca8f5cacace4cd691ee75f0683f/{final_mint}."
            print(tweet)
            last_tweeted = final_mint
            check_all_packs_owners()
        time.sleep(query_interval / 1000)
        if club_counter < 50:
            club_counter +=1
            print(club_counter)
        else:
            club_counter = 0
            check_all_packs_owners()
            check_range_of_packs(last_pres+1, last_tweeted+1)
            write_dict() 
        

if __name__ == '__main__':
    main()