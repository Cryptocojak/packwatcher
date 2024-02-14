import tweepy
import time
import logging
from web3 import Web3
from env import if_key
import asyncio
import aiohttp
from collections import Counter
#from the_presidents_club_dict import presidents_club
from pres_club_dict import current_pres_club_dict
new_pres_club_dict = {}

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
completed_tasks = 0

async def fetch_metadata_async(session, token_id):
    retry_count = 3
    while retry_count > 0:
        try:
            # Replace this URL with the actual URL you use to fetch metadata
            url = f"https://ipfs.io/ipfs/bafybeidgwnebxxrcjj3glcxtncvkeuokynlvb3oimrp4nwmv7sds34lela/{token_id}.json"
            async with session.get(url) as response:
                metadata = await response.json()
                return metadata
        except Exception as e:
                # print('\n')
                # logging.warning(f"Failed to fetch metadata for token ID {token_id}. Retrying... (Remaining retries: {retry_count})")
                retry_count -= 1
                if retry_count > 0:
                    await asyncio.sleep(1)
    logging.error(f"Completely failed to fetch metadata for token ID {token_id}. No more retries.")
    return None
    
async def update_progress_bar(total_mints):
    global completed_tasks
    while True:
        completion = completed_tasks / total_mints
        print_progress_bar(completion)
        if completed_tasks >= total_mints:
            print()  # Move to the next line after 100% completion
            break
        await asyncio.sleep(1)  # Update every second

def print_progress_bar(completion):
    bar_length = 40
    block = int(round(bar_length * completion))
    progress = "|" + "=" * block + "-" * (bar_length - block) + "|"
    print(f"\r{progress} {completion * 100:.2f}%", end="")

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

def format_address(address):
    if len(address) < 11:
        return address
    return address[:6] + '...' + address[-4:]

async def query_single_mint(session, contract, token_id):
    global completed_tasks
    try:
        metadata = await fetch_metadata_async(session, token_id)
        brand = check_brand(metadata)
        if brand == "President's Club":
            current_owner = contract.functions.ownerOf(token_id).call()
            new_pres_club_dict.update({token_id: current_owner})
    except Exception as e:
        print(f"Error fetching details for token ID {token_id}: {e}")
    finally:
        completed_tasks += 1 

async def query_all_mints_async(contract, total_mints):
    global new_pres_club_dict
    progress_task = asyncio.create_task(update_progress_bar(total_mints))
    async with aiohttp.ClientSession() as session:
        tasks = []
        for token_id in (range(total_mints)):
            task = query_single_mint(session, contract, token_id)
            tasks.append(task)
        await asyncio.gather(*tasks)
    await progress_task 

def make_presidents_club_dict(current_num_of_mints):
    asyncio.run(query_all_mints_async(nft_contract, current_num_of_mints))
    sorted_new_pres_club_dict = {k: new_pres_club_dict[k] for k in sorted(new_pres_club_dict)}
    if sorted_new_pres_club_dict != current_pres_club_dict:
        with open('pres_club_dict.py', 'w') as f:
            f.write('current_pres_club_dict = ' + str(sorted_new_pres_club_dict))
    dict_length = len(new_pres_club_dict)
    print(f"\nThere are {dict_length} President's Club packs\n")
    unique_addresses = len(set(new_pres_club_dict.values()))
    print(f"There are {unique_addresses} members of the President's Club\n")
    owners = list(new_pres_club_dict.values())
    owners_count = Counter(owners)
    multiple_owners = {address: count for address, count in owners_count.items() if count > 1}
    print("Addresses that hold more than one pack:\n")
    sorted_multiple_owners = {k: v for k, v in sorted(multiple_owners.items(), key=lambda item: item[1], reverse=True)}
    for address, count in sorted_multiple_owners.items():
        formatted_address = format_address(address)
        print(f"{formatted_address} holds {count} packs")
    print('\n')

def main():
    make_presidents_club_dict(get_current_number_of_mints(nft_contract))

if __name__ == '__main__':
    main()