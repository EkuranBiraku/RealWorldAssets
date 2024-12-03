from PyQt5.QtWidgets import (QCheckBox, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGridLayout, QFrame, QLineEdit, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QColor, QBrush, QPainter
from PyQt5.QtCore import QRect, Qt, pyqtSignal
import base64
import datetime
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from pymongo import MongoClient
from backpayment import BackPaymentHandler
from bson import ObjectId


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 25)
        self.setStyleSheet("QCheckBox::indicator { width: 0px; }")  # Hide default checkbox indicator
        self.setChecked(False)  # Ensure it starts unchecked

    def paintEvent(self, event):
        rect = self.rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.isChecked():
            brush = QBrush(QColor("#8cff8c"))
        else:
            brush = QBrush(QColor("grey"))

        # Draw rounded rectangle
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 12.5, 12.5)

        # Draw circle
        circle_rect = QRect(2, 2, 21, 21) if not self.isChecked() else QRect(25, 2, 21, 21)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(circle_rect)

        painter.end()

    def mouseReleaseEvent(self, event):
        # Toggle the checked state
        self.setChecked(not self.isChecked())
        self.update()  # Trigger a repaint to update the visual state
        super().mouseReleaseEvent(event)


class EmailVerificationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Email Verification')
        self.setFixedSize(400, 200)
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout()

        self.label = QLabel("Please enter your email for verification:")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        layout.addWidget(self.email_input)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        # Adding hover effect to the buttons
        self.buttonBox.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton {
                background-color: lightblue;
                color: black;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ADD8E6;
            }
        """)
        self.buttonBox.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton {
                background-color: lightblue;
                color: black;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ADD8E6;
            }
        """)

        self.setLayout(layout)

    def getEmail(self):
        return self.email_input.text()


class BuyAssetWindow(QDialog):
    purchaseSuccessful = pyqtSignal()

    def __init__(self, token, current_user_email, username, back_payment_handler, parent=None):
        super().__init__(parent)
        self.token = token
        self.current_user_email = current_user_email
        self.username = username
        self.back_payment_handler = back_payment_handler
        self.setWindowTitle("Buy Art")
        self.setFixedSize(700, 700)  # Adjusted for additional details

        # MongoDB setup
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']
        self.holdings_collection = self.db['cryptocurrency_holdings']
        self.transactions_collection = self.db['transaction_history']
        self.asset_history_collection = self.db['asset_history']

        self.setupUI()

    def setupUI(self):
        main_layout = QVBoxLayout()

        # Art Details Section
        art_details_frame = QFrame()
        art_details_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #ADD8E6;
                border-radius: 8px;
                padding: 10px;
                background-color: #1d2129;
            }
            QLabel {
                font-size: 14px;
                color: #ffffff;
            }
        """)
        art_layout = QGridLayout(art_details_frame)

        image_label = QLabel()
        pixmap = QPixmap(self.token['image_file_path']).scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: none;")  # Remove border from the image label

        art_layout.addWidget(image_label, 0, 0, 7, 1, alignment=Qt.AlignCenter)
        art_layout.addWidget(QLabel(f"Art Title: {self.token['art_title']}"), 0, 1)
        art_layout.addWidget(QLabel(f"Valuation: {self.token['art_valuation']}"), 1, 1)
        art_layout.addWidget(QLabel(f"Artist: {self.token['artist_name']}"), 2, 1)
        art_layout.addWidget(QLabel(f"Creation Date: {self.token['creation_date']}"), 3, 1)

        art_description_label = QLabel(f"Description: {self.token['art_description']}")
        art_description_label.setWordWrap(True)
        art_layout.addWidget(art_description_label, 4, 1, 2, 1)  # Spanning two rows

        main_layout.addWidget(art_details_frame)

        # Email Verification Section
        self.verification_button = QPushButton("Please Verify Your E-mail")
        self.verification_button.setFixedWidth(200)  # Reduced width
        self.verification_button.setStyleSheet("""
            QPushButton {
                background-color: lightblue;
                color: black;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                margin-top:20px;
            }
            QPushButton:hover {
                background-color: #6495ED;
            }
        """)
        self.verification_button.clicked.connect(self.verifyEmail)
        self.verification_layout = QVBoxLayout()
        self.verification_layout.addWidget(self.verification_button, alignment=Qt.AlignCenter)  # Centered
        main_layout.addLayout(self.verification_layout)

        # Spacer before Network Fee Label
        main_layout.addStretch(1)

        # Network Fee Label without Animation inside the same frame
        network_fee_label = QLabel("Network Fee<br><span style='color:yellow;'>20 USDT</span>")
        network_fee_label.setAlignment(Qt.AlignCenter)
        network_fee_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                padding: 5px;
                margin: 0px;
                border: 1px solid #ADD8E6;
                border-radius: 8px;
                background-color: #1d2129;
            }
        """)
        main_layout.addWidget(network_fee_label, alignment=Qt.AlignCenter)

        # Spacer to push elements to the bottom
        main_layout.addStretch(1)

        # Confirm Purchase Button at the bottom center with List Asset On Market on the right
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)

        # Confirm Button in the center
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: lightblue;
                color: black;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 18px;
                margin-left:160px;
                    }
            QPushButton:hover {
                background-color: #6495ED;
            }
        """)
        self.confirm_button.clicked.connect(self.confirmPurchase)
        self.confirm_button.setEnabled(False)  # Initially disable the confirm purchase button
        bottom_layout.addWidget(self.confirm_button, alignment=Qt.AlignCenter)

        bottom_layout.addStretch(1)

        # List Art On Market toggle on the right
        toggle_layout = QVBoxLayout()
        toggle_label = QLabel("List Art On Market")
        toggle_label.setStyleSheet("color: white; font-size:16px;")
        self.list_on_market_checkbox = ToggleSwitch()

        toggle_layout.addWidget(toggle_label, alignment=Qt.AlignCenter)
        toggle_layout.addWidget(self.list_on_market_checkbox, alignment=Qt.AlignCenter)

        bottom_layout.addLayout(toggle_layout)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def verifyEmail(self):
        email_verification_dialog = EmailVerificationDialog(self)
        if email_verification_dialog.exec_() == QDialog.Accepted:
            entered_email = email_verification_dialog.getEmail()
            if entered_email == self.current_user_email:
                # Logic to handle successful email verification
                self.verification_button.hide()
                success_label = QLabel("Successful Verification")
                success_label.setStyleSheet("color: lightgreen; font-size: 16px;margin-top:20px;")
                success_label.setAlignment(Qt.AlignCenter)  # Center the text
                self.verification_layout.addWidget(success_label, alignment=Qt.AlignCenter)
                self.confirm_button.setEnabled(True)  # Enable the confirm purchase button
            else:
                QMessageBox.warning(self, 'Email Verification Failed', 'Please Try Again')

    def confirmPurchase(self):
        # Load the user's cryptocurrency holdings from MongoDB
        holdings = self.holdings_collection.find_one({'username': self.username}) or {}

        # Map art valuation currencies to their corresponding keys in the holdings file
        currency_mapping = {
            'USDT': 'tether',
            'BTC': 'bitcoin',
            'ETH': 'ethereum'
        }

        # Extract the art valuation and currency
        art_valuation_str, art_currency = self.token['art_valuation'].split()
        art_valuation = float(art_valuation_str)
        art_currency_key = currency_mapping.get(art_currency)

        # Check if the user has enough balance
        user_balance = holdings.get(art_currency_key, 0.0)
        network_fee = 20.0  # Network fee in USDT

        if user_balance >= art_valuation:
            # Check if user has enough USDT to cover the network fee
            usdt_balance = holdings.get('tether', 0.0)
            if usdt_balance < network_fee:
                QMessageBox.warning(self, 'Insufficient Balance',
                                    'You do not have enough USDT to cover the network fee.')
                return

            # Deduct the art valuation from the user's holdings
            self.holdings_collection.update_one({'username': self.username},
                                                {'$inc': {art_currency_key: -art_valuation, 'tether': -network_fee}},
                                                upsert=True)

            # Add the art valuation to the seller's holdings
            self.holdings_collection.update_one({'username': self.token['owner']},
                                                {'$inc': {art_currency_key: art_valuation}}, upsert=True)

            # Record the transactions
            self.back_payment_handler.record_transaction(self.username, art_currency_key, -art_valuation, 'art_buy',
                                                         'art_buy', fee=network_fee)  # Buyer spent
            self.back_payment_handler.record_transaction(self.token['owner'], art_currency_key, art_valuation,
                                                         'art_sell', 'art_sell')  # Seller received

            # Transfer the token ownership and record the transaction
            self.transferTokenOwnership()
            QMessageBox.information(self, 'Purchase Successful',
                                    f"Purchased {self.token['art_title']} valued at {self.token['art_valuation']}")
            self.purchaseSuccessful.emit()  # Emit the signal
            self.accept()  # Close the window

        else:
            QMessageBox.warning(self, 'Insufficient Balance',
                                'You do not have enough balance to complete this purchase.')

    def generate_keys(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()
        return private_key, public_key

    def sign_message(self, private_key, message):
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    @staticmethod
    def convert_object_id_to_str(data):
        if isinstance(data, list):
            for item in data:
                BuyAssetWindow.convert_object_id_to_str(item)
        elif isinstance(data, dict):
            for key, value in data.items():
                if key == '_id':
                    data[key] = str(value)
                elif isinstance(value, ObjectId):
                    data[key] = str(value)
                elif isinstance(value, (dict, list)):
                    BuyAssetWindow.convert_object_id_to_str(value)

    def transferTokenOwnership(self):
        token = self.ledger_collection.find_one({'id': self.token['id']})
        if not token:
            QMessageBox.warning(self, 'Error', 'Unable to load token.')
            return

        old_owner = token['owner']
        old_owner_public_key = token['owner_public_key']
        old_signature = token['signature']
        new_owner = self.username

        # Generate new keys for the new owner
        new_owner_private_key, new_owner_public_key = self.generate_keys()

        # Update the token's owner, public key, and signature
        token['owner'] = new_owner
        token['owner_public_key'] = new_owner_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        # Convert ObjectId fields to strings
        self.convert_object_id_to_str(token)

        message = json.dumps(token).encode()
        new_signature = self.sign_message(new_owner_private_key, message)
        token['signature'] = base64.b64encode(new_signature).decode('utf-8')

        # Update for_sale status based on checkbox
        token['for_sale'] = self.list_on_market_checkbox.isChecked()

        # Remove the _id field before updating the document
        token_id = token.pop('_id', None)

        # Save the updated token back to the database
        self.ledger_collection.update_one({'id': self.token['id']}, {'$set': token})

        # Record the transaction
        transaction = {
            'token_id': token['id'],
            'art_title': token['art_title'],
            'old_owner': old_owner,
            'new_owner': new_owner,
            'old_owner_public_key': old_owner_public_key,
            'new_owner_public_key': token['owner_public_key'],
            'old_signature': old_signature,
            'new_signature': token['signature'],
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.saveTransactionHistory(transaction)

    def saveTransactionHistory(self, transaction):
        self.asset_history_collection.insert_one(transaction)
