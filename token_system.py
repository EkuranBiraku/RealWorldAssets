import json
import base64
import logging
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from pymongo import MongoClient
from bson import ObjectId
import os

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_logging():
    logger = logging.getLogger('token_system')
    logger.setLevel(logging.DEBUG)
    f_handler = logging.FileHandler('token_system.log')
    f_handler.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)
    c_handler.setFormatter(c_format)
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)
    return logger

logger = setup_logging()

# MongoDB setup
client = MongoClient('localhost', 27017)
db = client['admin']
ledger_collection = db.ledger  # Access the 'ledger' collection
transaction_history_collection = db.transaction_history  # Collection for transaction history
keys_collection = db.keys  # Collection for storing keys
assets_created_collection = db.assets_created  # Collection for storing created assets

keys = {}  # Key management

def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key

def generate_and_store_keys(owner):
    private_key, public_key = generate_keys()
    keys[owner] = {'private_key': private_key, 'public_key': public_key}
    return private_key, public_key

# Function to create digital art tokens
def create_token(owner, art_title, artist_name, creation_date, art_valuation, art_description, image_file_path, for_sale, location=None, cert_file_path=None):
    if not all([owner, art_title, artist_name, creation_date, art_valuation, art_description, image_file_path]):
        raise ValueError("All digital art token information must be provided.")

    # Check if the art token already exists for the owner
    if ledger_collection.find_one({"owner": owner, "asset": art_title}):
        raise ValueError(f"Art token with title '{art_title}' already exists for the owner '{owner}'.")

    # Retrieve or generate keys for the owner
    key_document = keys_collection.find_one({'owner': owner})
    if not key_document:
        owner_private_key, owner_public_key = generate_and_store_keys(owner)
        keys_collection.insert_one({
            'owner': owner,
            'private_key': owner_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8'),
            'public_key': owner_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
        })
    else:
        owner_private_key = serialization.load_pem_private_key(
            key_document['private_key'].encode('utf-8'),
            password=None
        )
        owner_public_key = serialization.load_pem_public_key(
            key_document['public_key'].encode('utf-8')
        )

    token_id = ledger_collection.count_documents({}) + 1  # Get the next available token ID

    # Read certification file content if provided
    cert_data = None
    if cert_file_path:
        with open(cert_file_path, "rb") as cert_file:
            cert_data = cert_file.read()

    # Create the digital art token structure
    token = {
        'id': token_id,
        'owner': owner,
        'asset': art_title,
        'asset_category': 'Art',  # Set the category as 'Art'
        'artist_name': artist_name,
        'creation_date': creation_date,
        'asset_valuation': art_valuation,
        'asset_description': art_description,
        'image_file_path': image_file_path,
        'for_sale': for_sale,  # Save the for_sale status
        'location': location,  # Add location to the token data
        'owner_public_key': owner_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8'),
        'certification_data': cert_data,  # Add the certification file content
        'certification_file_name': os.path.basename(cert_file_path) if cert_file_path else None,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'fee': 5  # Include the creation fee here
    }

    # Serialize the token and sign it
    message = json.dumps(token, default=str).encode()
    signature = owner_private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    token['signature'] = base64.b64encode(signature).decode('utf-8')

    # Insert the new token into the ledger collection
    ledger_collection.insert_one(token)
    logger.info("Digital art token created successfully: {}".format(token))

    # Save transaction history
    transaction = {
        'token_id': token_id,
        'asset': art_title,
        'owner': owner,
        'asset_category': 'Art',
        'artist_name': artist_name,
        'creation_date': creation_date,
        'owner_public_key': token['owner_public_key'],
        'signature': token['signature'],
        'timestamp': token['timestamp'],
        'fee': 3  # Include the creation fee here
    }
    save_transaction_history(transaction)

    return token


# Function to retrieve tokens that are for sale
def retrieve_tokens_for_sale():
    try:
        tokens = ledger_collection.find({'for_sale': True})
        return list(tokens)
    except Exception as e:
        logger.error(f"Error retrieving tokens for sale: {e}")
        return []

# Retrieve private key for the owner
def retrieve_private_key(owner):
    private_key_info = keys.get(owner)
    if private_key_info:
        return private_key_info['private_key']
    else:
        logger.error(f"No private key found for owner: {owner}")
        raise KeyError(f"No private key found for owner: {owner}")

# Verify the signature of the token
def verify_signature(token, message, signature):
    try:
        public_key = load_pem_public_key(token['owner_public_key'].encode('utf-8'))
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        logger.info("Signature verified successfully for token ID: {}".format(token['id']))
        return True
    except Exception as e:
        logger.error("Verification failed for token ID: {}, Error: {}".format(token['id'], e))
        return False

# Save transaction history to the database
def save_transaction_history(transaction):
    try:
        db['asset_history'].insert_one(transaction)
        logger.info("Transaction history saved successfully: {}".format(transaction))
    except Exception as e:
        logger.error(f"Error saving transaction history: {e}")
        raise

# Convert ObjectId instances to strings except for _id
def convert_object_id_to_str(data):
    if isinstance(data, list):
        for item in data:
            convert_object_id_to_str(item)
    elif isinstance(data, dict):
        for key, value in data.items():
            if key != "_id":  # Ensure that the _id field is not converted
                if isinstance(value, ObjectId):
                    data[key] = str(value)
                elif isinstance(value, (dict, list)):
                    convert_object_id_to_str(value)

# Function to transfer a digital art token to a new owner
def transfer_token(token_id, new_owner, fee):
    try:
        token = ledger_collection.find_one({'id': token_id})
        if not token:
            raise ValueError("Token with ID {} not found.".format(token_id))

        old_owner = token['owner']
        old_owner_public_key = token['owner_public_key']
        old_signature = token['signature']
        asset = token['asset']

        # Generate new keys for the new owner
        new_owner_private_key, new_owner_public_key = generate_and_store_keys(new_owner)

        # Update the token's owner, public key, and signature
        token['owner'] = new_owner
        token['owner_public_key'] = new_owner_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        message = json.dumps(token, default=str).encode()
        new_signature = new_owner_private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        token['signature'] = base64.b64encode(new_signature).decode('utf-8')

        # Convert any ObjectId instances to strings except for _id
        convert_object_id_to_str(token)

        # Save the updated token back to the database
        ledger_collection.replace_one({'id': token_id}, token, upsert=True)

        # Save transaction history
        transaction = {
            'token_id': token_id,
            'asset': asset,
            'old_owner': old_owner,
            'new_owner': new_owner,
            'old_owner_public_key': old_owner_public_key,
            'new_owner_public_key': token['owner_public_key'],
            'old_signature': old_signature,
            'new_signature': token['signature'],
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'fee': fee  # Add fee to the transaction
        }
        convert_object_id_to_str(transaction)  # Convert ObjectId instances in the transaction data
        save_transaction_history(transaction)

        logger.info("Token transferred successfully: {}".format(token))
        return token

    except Exception as e:
        logger.error(f"Error transferring token: {e}")
        raise

# Function to log the transfer of a token
def log_transfer(token_id, old_owner, new_owner):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('transfers.log', 'a') as log_file:
        log_file.write(f"{timestamp} - Token ID: {token_id}, Old Owner: {old_owner}, New Owner: {new_owner}\n")

# Display tokens available for sale
def display_tokens():
    tokens = retrieve_tokens_for_sale()
    for token in tokens:
        logger.info("Displaying token: {}".format(token))
