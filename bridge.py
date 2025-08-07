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
    w3 = connect_to(chain)
    contracts = get_contract_info(chain, contract_info)
    contract_address = contracts["address"]
    abi = contracts["abi"]
    contract = w3.eth.contract(address=contract_address, abi=abi)

    latest_block = w3.eth.block_number
    from_block = latest_block - 5 if latest_block >= 5 else 0

    events = []
    if chain == "source":
        # Look for "Deposit" events
        try:
            deposit_events = contract.events.Deposit().get_logs(fromBlock=from_block, toBlock="latest")
            for evt in deposit_events:
                print(f"Deposit event detected on source: {evt}")
                # Connect to destination and call wrap()
                dst_web3 = connect_to("destination")
                dst_contract_info = get_contract_info("destination", contract_info)
                dst_contract = dst_web3.eth.contract(address=dst_contract_info["address"], abi=dst_contract_info["abi"])
                warden = contracts["warden"]
                nonce = dst_web3.eth.get_transaction_count(warden)
                txn = dst_contract.functions.wrap(
                    evt.args['token'],
                    evt.args['recipient'],
                    evt.args['amount']
                ).build_transaction({
                    'chainId': 97,
                    'gas': 500000,
                    'gasPrice': dst_web3.to_wei('10', 'gwei'),
                    'nonce': nonce
                })
                signed_txn = dst_web3.eth.account.sign_transaction(txn, private_key=dst_contract_info["private_key"])
                dst_web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        except Exception as e:
            print(f"Error scanning Deposit: {e}")

    elif chain == "destination":
        # Look for "Unwrap" events
        try:
            unwrap_events = contract.events.Unwrap().get_logs(fromBlock=from_block, toBlock="latest")
            for evt in unwrap_events:
                print(f"Unwrap event detected on destination: {evt}")
                # Connect to source and call withdraw()
                src_web3 = connect_to("source")
                src_contract_info = get_contract_info("source", contract_info)
                src_contract = src_web3.eth.contract(address=src_contract_info["address"], abi=src_contract_info["abi"])
                warden = contracts["warden"]
                nonce = src_web3.eth.get_transaction_count(warden)
                txn = src_contract.functions.withdraw(
                    evt.args['token'],
                    evt.args['recipient'],
                    evt.args['amount']
                ).build_transaction({
                    'chainId': 43113,
                    'gas': 500000,
                    'gasPrice': src_web3.to_wei('25', 'gwei'),
                    'nonce': nonce
                })
                signed_txn = src_web3.eth.account.sign_transaction(txn, private_key=src_contract_info["private_key"])
                src_web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        except Exception as e:
            print(f"Error scanning Unwrap: {e}")