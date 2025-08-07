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

# Token addresses to register
tokens_avax = [
    "0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c",
    "0x0773b81e0524447784CcE1F3808fed6AaA156eC8"
]

tokens_bsc = [
    "0xc677c31AD31F73A5290f5ef067F8CEF8d301e45c",
    "0x0773b81e0524447784CcE1F3808fed6AaA156eC8"
]

# Setup source (Avalanche)
w3_source = Web3(Web3.HTTPProvider("https://api.avax-test.network/ext/bc/C/rpc"))
w3_source.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
src = contracts["source"]
src_contract = w3_source.eth.contract(address=src["address"], abi=src["abi"])
src_nonce = w3_source.eth.get_transaction_count(src["warden"])

# Register tokens on Source
for token in tokens_avax:
    tx = src_contract.functions.registerToken(token).build_transaction({
        "from": src["warden"],
        "nonce": src_nonce,
        "gas": 200000,
        "gasPrice": int(w3_source.eth.gas_price * 1.2),
        "chainId": 43113
    })
    signed = w3_source.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3_source.eth.send_raw_transaction(signed.raw_transaction)
    print(f"[AVAX] Registered token {token} → tx: {tx_hash.hex()}")
    src_nonce += 1

# Setup destination (BSC)
w3_dest = Web3(Web3.HTTPProvider("https://data-seed-prebsc-1-s1.binance.org:8545/"))
w3_dest.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
dst = contracts["destination"]
dst_contract = w3_dest.eth.contract(address=dst["address"], abi=dst["abi"])
dst_nonce = w3_dest.eth.get_transaction_count(dst["warden"])

# Create wrapped tokens on Destination
for i, token in enumerate(tokens_bsc):
    name = f"Wrapped Token {i+1}"
    symbol = f"WT{i+1}"
    tx = dst_contract.functions.createToken(token, name, symbol).build_transaction({
        "from": dst["warden"],
        "nonce": dst_nonce,
        "gas": 300000,
        "gasPrice": int(w3_dest.eth.gas_price * 1.2),
        "chainId": 97
    })
    signed = w3_dest.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3_dest.eth.send_raw_transaction(signed.raw_transaction)
    print(f"[BSC] Created token {token} → tx: {tx_hash.hex()}")
    dst_nonce += 1
