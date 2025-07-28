from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]



def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return 0
    
        #YOUR CODE HERE
    # Load contract data
    info = get_contract_info(chain, contract_info)
    contract_address = info['contract']
    abi = info['abi']
    warden_key = info['warden_key']
    
    w3 = connect_to(chain)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    end_block = w3.eth.get_block_number()
    start_block = end_block - 5

    # Choose the event type and destination chain
    if chain == 'source':
        event_type = contract.events.Deposit
        opposite_chain = 'destination'
        opposite_function = 'wrap'
    else:
        event_type = contract.events.Unwrap
        opposite_chain = 'source'
        opposite_function = 'withdraw'

    # Filter and collect events
    try:
        event_filter = event_type.create_filter(fromBlock=start_block, toBlock=end_block)
        events = event_filter.get_all_entries()
    except Exception as e:
        print(f"Error filtering events: {e}")
        return

    for evt in events:
        args = evt.args
        token = args['token']
        to = args['to']
        amount = args['amount']

        # Prepare message
        message = f"{token.lower()}|{to.lower()}|{amount}"
        message_hash = w3.keccak(text=message)
        signed_message = Account.signHash(message_hash, private_key=warden_key)

        # Call opposite chain function
        dest_info = get_contract_info(opposite_chain, contract_info)
        dest_contract = connect_to(opposite_chain).eth.contract(
            address=dest_info['contract'],
            abi=dest_info['abi']
        )
        tx = dest_contract.functions[opposite_function](
            token, to, amount, signed_message.signature
        ).build_transaction({
            'from': Account.from_key(warden_key).address,
            'nonce': connect_to(opposite_chain).eth.get_transaction_count(Account.from_key(warden_key).address),
            'gas': 500000,
            'gasPrice': connect_to(opposite_chain).eth.gas_price
        })
        signed_tx = connect_to(opposite_chain).eth.account.sign_transaction(tx, private_key=warden_key)
        tx_hash = connect_to(opposite_chain).eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Sent {opposite_function} tx: {tx_hash.hex()}")
