from PyQt5.QtCore import QObject, pyqtSignal
import requests
import time
from datetime import datetime
from pymongo import MongoClient


class BackPaymentHandler(QObject):
    cryptoPurchased = pyqtSignal()  # Signal to notify when a crypto is purchased

    def __init__(self):
        super().__init__()  # Initialize QObject
        self.cached_prices = {}
        self.cache_duration = 300  # Cache duration in seconds (5 minutes)

        # MongoDB setup
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.holdings_collection = self.db['cryptocurrency_holdings']
        self.transactions_collection = self.db['transaction_history']
        # Define the users_collection
        self.users_collection = self.db['users']  # Initialize the users collection
        self.cards_collection = self.db['pay.cards']

    def get_crypto_price(self, crypto):
        current_time = time.time()
        if crypto in self.cached_prices:
            cached_price, timestamp = self.cached_prices[crypto]
            if current_time - timestamp < self.cache_duration:
                return cached_price

        try:
            url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=gbp'
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            price = data[crypto]['gbp']
            self.cached_prices[crypto] = (price, current_time)
            return price
        except requests.RequestException as e:
            print(f"Error fetching price: {e}")
            return None

    def load_holdings(self):
        holdings = self.holdings_collection.find()
        return {holding['username']: holding for holding in holdings}

    def save_holdings(self, username, data):
        self.holdings_collection.update_one({'username': username}, {'$set': data}, upsert=True)

    def add_crypto_to_user(self, username, crypto, amount, transaction_type, source):
        data = self.load_holdings()
        if username not in data:
            data[username] = {'username': username}
        if crypto in data[username]:
            data[username][crypto] += amount
        else:
            data[username][crypto] = amount
        self.save_holdings(username, data[username])
        self.record_transaction(username, crypto, amount, transaction_type, source)  # Pass transaction_type and source
        self.cryptoPurchased.emit()  # Emit the signal after purchasing crypto

    def get_user_holdings(self, username):
        data = self.holdings_collection.find_one({'username': username})
        return data or {}

    def check_and_reduce_tether(self, username, amount):
        data = self.holdings_collection.find_one({'username': username})
        if data and 'tether' in data:
            if data['tether'] >= amount:
                new_balance = data['tether'] - amount
                self.holdings_collection.update_one({'username': username}, {'$set': {'tether': new_balance}})
                return True
        return False

    def check_and_reduce_balance(self, username, currency, amount):
        """Check if the user has enough balance in the specified currency and deduct it if they do."""
        data = self.holdings_collection.find_one({'username': username})
        if data and currency in data:
            if data[currency] >= amount:
                new_balance = data[currency] - amount
                self.holdings_collection.update_one({'username': username}, {'$set': {currency: new_balance}})
                return True
        return False

    def record_transaction(self, username, crypto, amount, transaction_type, source, fee=None):
        transaction = {
            'username': username,
            'crypto': crypto,
            'amount': amount,
            'price': self.get_crypto_price(crypto),
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': transaction_type,
            'source': source
        }
        if fee is not None:
            transaction['fee'] = fee

        self.transactions_collection.insert_one(transaction)

    def update_user_holdings(self, username, holdings):
        self.holdings_collection.update_one({'username': username}, {'$set': holdings}, upsert=True)

    def is_card_already_saved(self, username, card_info):
        # Check if the card is already saved for the given user
        existing_card = self.cards_collection.find_one({
            'username': username,
            'cards.card_number': card_info['card_number']
        })
        return existing_card is not None

    def save_card(self, username, card_info):
        # Check if the card is already saved
        if self.is_card_already_saved(username, card_info):
            print("Card already saved.")
            return "Card already saved."

        try:
            # Insert new card if not already saved
            self.cards_collection.update_one(
                {'username': username},
                {'$push': {'cards': card_info}},
                upsert=True
            )
            return "Card saved successfully."
        except Exception as e:
            print(f"Failed to save card: {str(e)}")
            return f"Failed to save card: {str(e)}"

    def get_saved_cards(self, username):
        # Retrieve all saved cards for a given user
        user_data = self.cards_collection.find_one({'username': username})
        return user_data.get('cards', []) if user_data else []

    def process_payment(self, username, crypto, amount, payment_info):
        # Process the payment, add crypto to user holdings, and record the transaction
        try:
            # Check if the crypto price is available
            price = self.get_crypto_price(crypto)
            if not price:
                return "Error: Could not fetch crypto price."

            # Add crypto to user holdings
            crypto_amount = amount / price
            self.add_crypto_to_user(username, crypto, crypto_amount)

            # Record transaction in transaction history
            self.record_transaction(username, crypto, crypto_amount, "purchase", "UI")
            self.cryptoPurchased.emit()  # Emit signal for successful purchase
            return "Success: Purchase completed."
        except Exception as e:
            return f"Error: {str(e)}"

    def save_bank(self, username, bank_details):
        user_banks = self.db['pay.banks']
        existing_bank = user_banks.find_one({'username': username, 'account_number': bank_details['account_number']})

        if existing_bank:
            return "Bank already saved."

        user_banks.insert_one({'username': username, **bank_details})
        return "Bank saved successfully."

    def get_saved_banks(self, username):
        user_banks = self.db['pay.banks']
        return list(
            user_banks.find({'username': username}, {'_id': 0, 'account_number': 1, 'bank_name': 1, 'sort_code': 1}))
