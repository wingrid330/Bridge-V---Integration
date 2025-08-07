from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
from dotenv import load_dotenv
import os

load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Load contract info
with open("contract_info.json") as f:
    contracts = json.load(f)

tokens = [
    "0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c",
    "0x0773b81e0524447784CcE1F3808fed6AaA156eC8"
]

# === Register on Source (Avalanche) ===
w3_source = Web3(Web3.HTTPProvider("https://api.avax-test.network/ext/bc/C/rpc"))
w3_source.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
source_info = contracts["source"]
source_contract = w3_source.eth.contract(address=source_info["address"], abi=source_info["abi"])
source_nonce = w3_source.eth.get_transaction_count(source_info["warden"])

for i, token in enumerate(tokens):
    tx = source_contract.functions.registerToken(token).build_transaction({
        "from": source_info["warden"],
        "nonce": source_nonce + i,
        "gas": 200000,
        "gasPrice": w3_source.to_wei("30", "gwei")
    })
    signed_tx = w3_source.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3_source.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Registered token {token} on Source. Tx hash: {tx_hash.hex()}")

# === Create wrapped tokens on Destination (BNB) ===
w3_dest = Web3(Web3.HTTPProvider("https://data-seed-prebsc-1-s1.binance.org:8545/"))
dest_info = contracts["destination"]
dest_contract = w3_dest.eth.contract(address=dest_info["address"], abi=dest_info["abi"])
dest_nonce = w3_dest.eth.get_transaction_count(dest_info["warden"])

for i, token in enumerate(tokens):
    name = f"Wrapped Token {i+1}"
    symbol = f"WT{i+1}"
    tx = dest_contract.functions.createToken(token, name, symbol).build_transaction({
        "from": dest_info["warden"],
        "nonce": dest_nonce + i,
        "gas": 300000,
        "gasPrice": w3_dest.to_wei("30", "gwei")
    })
    signed_tx = w3_dest.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3_dest.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Created wrapped token for {token} on Destination. Tx hash: {tx_hash.hex()}")
