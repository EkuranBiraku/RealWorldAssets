from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QFormLayout, QGroupBox, QFrame, QHBoxLayout,
    QMessageBox
)
from PyQt5.QtCore import Qt, QRegExp, QTimer, QSequentialAnimationGroup, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QRegExpValidator, QColor
import requests
import time
from pymongo import MongoClient
import uuid
from datetime import datetime


class DigitLimitValidator(QRegExpValidator):
    def __init__(self, max_digits, parent=None):
        regex = QRegExp(r"^\d{1,10}(\.\d{1,10})?$")
        super().__init__(regex, parent)
        self.max_digits = max_digits

    def validate(self, input_str, pos):
        if len(input_str.replace(".", "")) <= self.max_digits:
            return super().validate(input_str, pos)
        return QRegExpValidator.Invalid, input_str, pos


class ConvertCryptoTab(QWidget):
    def __init__(self, username, back_payment_handler):
        super().__init__()
        self.username = username
        self.back_payment_handler = back_payment_handler
        self.cached_prices = {}
        self.cache_duration = 300  # Cache duration in seconds (5 minutes)
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.gbp_collection = self.db['gbp']
        self.conversions_collection = self.db['cryptoconversions']
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()

        # Title
        title = QLabel("")
        title.setStyleSheet("""
            QLabel {
                font-size: 30px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(title)

        # Container Frame with modern styling
        containerFrame = QFrame()
        containerFrame.setStyleSheet("""
            QFrame {
                border: 4px solid lightblue;
                border-radius: 25px;
                padding: 20px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                min-width: 330px;

            }
        """)

        containerLayout = QVBoxLayout()
        containerFrame.setLayout(containerLayout)

        # GroupBox for form layout
        groupBox = QGroupBox()
        groupBox.setStyleSheet("""
            QGroupBox {
                color: lightblue;
                border: none;

            }
        """)
        formLayout = QFormLayout()
        formLayout.setVerticalSpacing(20)
        groupBox.setLayout(formLayout)

        labelFont = QFont("Arial", 12)  # Smaller font size for labels

        # Please Select Crypto
        selectCryptoLabel = QLabel("Please Select Crypto")
        selectCryptoLabel.setFont(labelFont)
        selectCryptoLabel.setAlignment(Qt.AlignCenter)
        selectCryptoLabel.setStyleSheet(""" QLabel {background-color: lightblue; color:black; font-size:18px; padding:7px;border-radius: 5px
                    }
                """)
        self.cryptoDropdown = QComboBox()
        self.populateCryptoDropdown()  # Populate the dropdown with user's crypto holdings
        self.cryptoDropdown.currentIndexChanged.connect(
            self.updateConversion)  # Update conversion on crypto selection change
        self.cryptoDropdown.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-left:15px;
                margin-right:15px;
            }
        """)
        formLayout.addRow(selectCryptoLabel)
        formLayout.addRow(self.cryptoDropdown)

        # Select Amount
        selectAmountLabel = QLabel("Select Amount")
        selectAmountLabel.setFont(labelFont)
        selectAmountLabel.setAlignment(Qt.AlignCenter)
        selectAmountLabel.setStyleSheet(""" QLabel {background-color: lightblue; color:black; font-size:18px;padding:7px;border-radius: 5px
                    }
                """)
        self.amountInput = QLineEdit()
        self.amountInput.setPlaceholderText("Enter amount")
        self.amountInput.setValidator(DigitLimitValidator(10))
        self.amountInput.textChanged.connect(self.validateAmount)  # Connect the validation method
        self.amountInput.textChanged.connect(self.updateConversion)  # Update conversion on amount change
        self.amountInput.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                margin-left:15px;
                margin-right:15px;
            }
        """)
        formLayout.addRow(selectAmountLabel)
        formLayout.addRow(self.amountInput)

        # Amount in GBP
        amountInGBPLabel = QLabel("Amount in GBP")
        amountInGBPLabel.setFont(labelFont)
        amountInGBPLabel.setAlignment(Qt.AlignCenter)
        amountInGBPLabel.setStyleSheet(""" QLabel {background-color: lightblue; color:black; font-size:18px; padding:7px;border-radius: 5px
                    }
                """)
        self.amountInGBPDisplay = QLabel()
        self.amountInGBPDisplay.setAlignment(Qt.AlignCenter)
        self.amountInGBPDisplay.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 5px;
                color: black;
                background-color: white;
                margin-left:15px;
                margin-right:15px;
            }
        """)
        formLayout.addRow(amountInGBPLabel)
        formLayout.addRow(self.amountInGBPDisplay)

        containerLayout.addWidget(groupBox)

        # Add the container frame layout to mainLayout
        containerFrameLayout = QHBoxLayout()
        containerFrameLayout.addStretch(1)
        containerFrameLayout.addWidget(containerFrame)
        containerFrameLayout.addStretch(1)
        mainLayout.addLayout(containerFrameLayout)

        # Add conversion fee label with animation to mainLayout after containerFrame
        conversionFeeLabel = QLabel("Conversion Fee: 3 USDT")
        conversionFeeLabel.setAlignment(Qt.AlignCenter)
        conversionFeeLabel.setStyleSheet("""
            QLabel {
                padding: 5px;
                color: yellow;
                border: none;
                background: none;
                border-radius: 5px
            }
        """)
        conversionFeeLabel.setMaximumSize(conversionFeeLabel.sizeHint().width() + 30,
                                          conversionFeeLabel.sizeHint().height() + 10)
        mainLayout.addWidget(conversionFeeLabel, alignment=Qt.AlignCenter)

        # Convert button centered below the form
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        self.convertButton = QPushButton("Convert Crypto")
        self.convertButton.setFixedWidth(200)
        self.convertButton.clicked.connect(self.confirmConversion)  # Connect to confirm conversion method
        self.convertButton.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: lightblue;
                color:black;
            }
        """)
        buttonLayout.addWidget(self.convertButton, alignment=Qt.AlignCenter)
        buttonLayout.addStretch(1)

        mainLayout.addLayout(buttonLayout)

        self.setLayout(mainLayout)

        # Timer to refresh prices periodically
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.updateConversion)
        self.refresh_timer.start(60000)  # Refresh every 60 seconds

    def populateCryptoDropdown(self):
        self.cryptoDropdown.clear()  # Clear existing items before repopulating
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        for crypto in ["Bitcoin", "Ethereum", "Tether"]:
            amount = holdings.get(crypto.lower(), 0)
            self.cryptoDropdown.addItem(f"{crypto} : {amount}")

    def validateAmount(self):
        amount_text = self.amountInput.text()
        selected_crypto = self.cryptoDropdown.currentText().split(':')[0].strip()
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        max_amount = holdings.get(selected_crypto.lower(), 0)

        try:
            amount = float(amount_text)
            if amount > max_amount:
                self.amountInput.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid red;
                        padding: 10px;
                    }
                """)
            else:
                self.amountInput.setStyleSheet("""
                    QLineEdit {
                        padding: 10px;
                    }
                """)
        except ValueError:
            self.amountInput.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                }
            """)

    def updateConversion(self):
        amount_text = self.amountInput.text()
        selected_crypto = self.cryptoDropdown.currentText().split(':')[0].strip().lower()

        if not amount_text:
            self.amountInGBPDisplay.setText("")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            self.amountInGBPDisplay.setText("")
            return

        crypto_price = self.get_cached_or_online_crypto_price(selected_crypto)
        if crypto_price is not None:
            gbp_amount = amount * crypto_price
            self.amountInGBPDisplay.setText(f"{gbp_amount:,.2f} GBP")
        else:
            self.amountInGBPDisplay.setText("")

    def get_cached_or_online_crypto_price(self, crypto):
        current_time = time.time()
        if crypto in self.cached_prices:
            cached_price, timestamp = self.cached_prices[crypto]
            if current_time - timestamp < self.cache_duration:
                return cached_price

        price = self.get_online_crypto_price(crypto)
        if price is not None:
            self.cached_prices[crypto] = (price, current_time)
        return price

    def get_online_crypto_price(self, crypto, retries=3, backoff_factor=1):
        crypto_id = {"bitcoin": "bitcoin", "ethereum": "ethereum", "usdt": "tether"}.get(crypto)
        if not crypto_id:
            return None

        for attempt in range(retries):
            try:
                url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=gbp'
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                return data[crypto_id]['gbp']
            except requests.RequestException as e:
                print(f"Error fetching price: {e}")
                if response.status_code == 429:
                    print(f"Rate limit exceeded. Retrying in {backoff_factor} seconds...")
                    time.sleep(backoff_factor)
                    backoff_factor *= 2
                else:
                    break

        return None

    def confirmConversion(self):
        amount_text = self.amountInput.text()
        if not amount_text:
            QMessageBox.warning(self, 'Input Error', 'Enter Amount field cannot be empty.')
            return

        selected_crypto = self.cryptoDropdown.currentText().split(':')[0].strip()
        gbp_amount = self.amountInGBPDisplay.text()

        # Check if the user has enough crypto to convert
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        crypto_amount = holdings.get(selected_crypto.lower(), 0)
        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(self, 'Input Error', 'Invalid amount.')
            return

        if amount > crypto_amount:
            QMessageBox.warning(self, 'Insufficient Funds', f'You do not have enough {selected_crypto} to convert.')
            return

        # Check if the user has enough tether (USDT) for the conversion fee
        usdt_balance = holdings.get('tether', 0)
        conversion_fee = 3  # Conversion fee in USDT
        if usdt_balance < conversion_fee:
            QMessageBox.warning(self, 'Insufficient Funds',
                                'You do not have enough USDT to cover the conversion fee of 3 USDT.')
            return

        # Check if the user has enough tether (USDT) to cover both the fee and the amount
        if selected_crypto.lower() == 'tether' and (amount + conversion_fee) > usdt_balance:
            QMessageBox.warning(self, 'Insufficient Funds',
                                'You do not have enough USDT to cover both the conversion amount and the fee.')
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Crypto Conversion")
        msg_box.setText(
            f"Are you sure you want to convert {amount_text} {selected_crypto} to GBP?\n\nEquivalent Amount in GBP: {gbp_amount}")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg_box.exec_()

        if result == QMessageBox.Ok:
            self.convert()

    def save_gbp_amount(self, gbp_amount):
        user_gbp = self.gbp_collection.find_one({"username": self.username})
        if user_gbp:
            self.gbp_collection.update_one({"username": self.username}, {"$inc": {"amount": gbp_amount}})
        else:
            self.gbp_collection.insert_one({"username": self.username, "amount": gbp_amount})

    def convert(self):
        amount_text = self.amountInput.text()
        from_crypto = self.cryptoDropdown.currentText().split(':')[0].strip().lower()

        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(self, 'Input Error', 'Invalid amount.')
            return

        # Check if the user has enough crypto to convert
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        crypto_amount = holdings.get(from_crypto, 0)
        if amount > crypto_amount:
            QMessageBox.warning(self, 'Insufficient Funds',
                                f'You do not have enough {from_crypto.capitalize()} to convert.')
            return

        # Deduct the conversion fee in USDT (tether)
        conversion_fee = 3  # Conversion fee in USDT
        if holdings.get('tether', 0) < conversion_fee:
            QMessageBox.warning(self, 'Insufficient Funds', 'You do not have enough USDT to cover the conversion fee.')
            return

        # Check if the user has enough tether (USDT) to cover both the fee and the amount
        if from_crypto == 'tether' and (amount + conversion_fee) > holdings.get('tether', 0):
            QMessageBox.warning(self, 'Insufficient Funds',
                                'You do not have enough USDT to cover both the conversion amount and the fee.')
            return

        crypto_price = self.get_cached_or_online_crypto_price(from_crypto)
        if crypto_price is not None:
            gbp_amount = amount * crypto_price
            self.amountInGBPDisplay.setText(f"{gbp_amount:,.2f} GBP")
            self.save_gbp_amount(gbp_amount)
            self.deduct_crypto(from_crypto, amount, conversion_fee)
            self.record_conversion(from_crypto, amount, gbp_amount, conversion_fee)  # Record the conversion
            QMessageBox.information(self, 'Success', 'Conversion successful.')
        else:
            QMessageBox.warning(self, 'Conversion Error', 'Failed to fetch the cryptocurrency price.')

    def deduct_crypto(self, crypto, amount, fee):
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        if crypto in holdings:
            holdings[crypto] -= amount
            if holdings[crypto] < 0:
                holdings[crypto] = 0

        # Deduct the conversion fee in USDT (tether)
        if 'tether' in holdings:
            holdings['tether'] -= fee
            if holdings['tether'] < 0:
                holdings['tether'] = 0

        self.back_payment_handler.update_user_holdings(self.username, holdings)

        # Update the dropdown with the new holdings
        self.populateCryptoDropdown()

    def record_conversion(self, crypto, amount, gbp_amount, fee):
        conversion_record = {
            'id': str(uuid.uuid4()),  # Generate a unique ID for each conversion
            'username': self.username,
            'crypto': crypto,
            'amount': amount,
            'gbp_amount': gbp_amount,
            'fee': fee,
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.conversions_collection.insert_one(conversion_record)
