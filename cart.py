from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QLabel, \
    QMessageBox, QGraphicsOpacityEffect, QComboBox, QLineEdit, QWidget, QStackedWidget, QHeaderView, QSizePolicy, \
    QFormLayout, QFrame, QDialogButtonBox
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRegExp
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator, QIntValidator, QKeyEvent
import qtawesome as qta
import requests
from pymongo import MongoClient
from backpayment import BackPaymentHandler
import random
import smtplib
from email.mime.text import MIMEText
import re
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import time




class CartWindow(QDialog):
    basketCleared = pyqtSignal()
    appUpdated = pyqtSignal()  # Global signal for app updates

    postcodeChanged = pyqtSignal(str)
    addressChanged = pyqtSignal(str)

    def __init__(self, basket,username=None,back_payment_handler=None, parent=None):
        super().__init__(parent)
        self.basket = basket
        self.username = username  # Store the username of the logged-in user
        self.back_payment_handler = back_payment_handler  # Store the back_payment_handler
        self.failed_attempts = 0  # Track the number of failed attempts
        self.lockout_time = 0  # Time when the user can try again
        self.network_prices = {}
        self.delivery_fee = 5.99
        # Set up MongoDB connection
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client['admin']
        self.cards_collection = self.db['pay.cards']
        self.banks_collection = self.db['pay.banks']
        self.cart_collection = self.db['cart']  # This is where we'll store the cart data
        self.item_in_cart = {}  # To track which items are in the cart

        self.setWindowTitle("Basket")
        self.setFixedSize(650, 800)


        self.stackedWidget = QStackedWidget()

        # Initialize the UI
        self.initUI()
        self.fetchNetworkPrices()


        # Set the default values for the dropdowns
        self.updateNetwork(self.network_dropdown.currentText())
        self.updateDelivery(self.delivery_dropdown.currentText())

        # Connect signals for postcode and address
        self.postcodeChanged.connect(self.onPostcodeChanged)
        self.addressChanged.connect(self.onAddressChanged)

    def initUI(self):
        self.layout = QVBoxLayout()

        # Create cart page and add to stacked widget
        cart_page = QWidget()
        cart_layout = QVBoxLayout()

        # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(['Image', 'Art Name', 'Artist', 'Valuation', 'Remove'])
        self.tableWidget.verticalHeader().setVisible(False)

        # Create buttons for the cart page
        cart_button_layout = QHBoxLayout()

        # Initialize the checkout button before populateTable is called
        self.checkout_button = QPushButton("Checkout")
        self.checkout_button.clicked.connect(self.checkout)

        self.clear_button = QPushButton("Clear Basket")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6666;
            }
            QPushButton:hover {
                background-color: #ff9999;
            }
        """)
        self.clear_button.clicked.connect(self.clearBasket)
        cart_button_layout.addWidget(self.checkout_button)
        cart_button_layout.addWidget(self.clear_button)

        cart_layout.addWidget(self.tableWidget)
        cart_layout.addLayout(cart_button_layout)

        cart_page.setLayout(cart_layout)

        # Add cart page to the stacked widget
        self.stackedWidget.addWidget(cart_page)

        # Now populate the table after the button is initialized
        self.populateTable()

        # Create the checkout form and add it to stacked widget
        self.checkoutForm = self.createCheckoutForm()
        self.stackedWidget.addWidget(self.checkoutForm)
        self.stackedWidget.addWidget(self.createCardPaymentForm(self.checkoutForm))
        self.stackedWidget.addWidget(self.createBankTransferForm())

        self.layout.addWidget(self.stackedWidget)
        self.setLayout(self.layout)

    def reloadCart(self):
        # Load the latest cart data from the database
        self.loadCartFromDatabase()

        # Repopulate the cart table
        self.populateTable()

        # Ensure the checkout button reflects the state of the basket
        self.checkout_button.setEnabled(len(self.basket) > 0)
    def createCheckoutForm(self):
        checkout_form_page = QWidget()
        form_layout = QVBoxLayout()

        label_style = "font-size: 20px;"

        # Network selection with icons
        network_label = QLabel("Please Select Network")
        network_label.setStyleSheet(label_style)
        self.network_dropdown = QComboBox()

        # Add items with icons
        bitcoin_icon = QIcon("btc.png")  # Replace with actual path
        ethereum_icon = QIcon("eth.png")  # Replace with actual path
        self.network_dropdown.addItem(bitcoin_icon, "Bitcoin")
        self.network_dropdown.addItem(ethereum_icon, "Ethereum")
        self.network_dropdown.setStyleSheet("padding: 8px;")

        self.network_dropdown.currentTextChanged.connect(self.updateNetwork)

        # Postcode input with a callback for address lookup
        postcode_label = QLabel("Enter Postcode")
        postcode_label.setStyleSheet(label_style)
        self.postcode_input = QLineEdit()
        self.postcode_input.setStyleSheet("padding: 8px;")
        self.postcode_input.textChanged.connect(self.lookupAddresses)  # Call lookup when postcode changes
        self.postcode_input.textChanged.connect(self.updatePostcode)

        # Address selection
        address_label = QLabel("Choose Address")
        address_label.setStyleSheet(label_style)
        self.address_dropdown = QComboBox()
        self.address_dropdown.addItem("Enter postcode first")  # Placeholder before addresses are fetched
        self.address_dropdown.setStyleSheet("padding: 8px;")
        self.postcode_input.setFixedWidth(100)  # Adjust the width as necessary
        self.address_dropdown.currentTextChanged.connect(self.updateAddress)

        # Delivery provider selection with icons
        delivery_label = QLabel("Choose Delivery Provider")
        delivery_label.setStyleSheet(label_style)
        self.delivery_dropdown = QComboBox()

        dpd_icon = QIcon("DPD.png")  # Replace with actual path to DPD icon
        royal_mail_icon = QIcon("RM.png")  # Replace with actual path to Royal Mail icon

        self.delivery_dropdown.addItem(dpd_icon, "DPD")
        self.delivery_dropdown.addItem(royal_mail_icon, "RoyalMail")
        self.delivery_dropdown.setStyleSheet("padding: 8px;")

        self.delivery_dropdown.currentTextChanged.connect(self.updateDelivery)

        # Payment method selection with icons
        payment_label = QLabel("Choose Payment Method")
        payment_label.setStyleSheet(label_style)
        self.payment_dropdown = QComboBox()
        self.payment_dropdown.addItem(qta.icon('fa.credit-card', color='white'), "Card Payment")
        self.payment_dropdown.addItem(qta.icon('fa.university', color='white'), "Bank Transfer")
        self.payment_dropdown.setStyleSheet("padding: 8px;")

        # Adding elements to form layout
        form_layout.addWidget(network_label)
        form_layout.addWidget(self.network_dropdown)
        form_layout.addWidget(postcode_label)
        form_layout.addWidget(self.postcode_input)
        form_layout.addWidget(address_label)
        form_layout.addWidget(self.address_dropdown)
        form_layout.addWidget(delivery_label)
        form_layout.addWidget(self.delivery_dropdown)
        form_layout.addWidget(payment_label)
        form_layout.addWidget(self.payment_dropdown)

        # Back and Next buttons
        button_layout = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setStyleSheet("padding: 10px;")
        self.back_button.clicked.connect(self.goBackToCart)

        self.next_button = QPushButton("Next")
        self.next_button.setStyleSheet("padding: 10px;")
        self.next_button.setEnabled(False)  # Initially disable the Next button
        self.next_button.clicked.connect(self.showPaymentWindow)  # Connect to method to determine next step

        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.next_button)

        form_layout.addLayout(button_layout)
        checkout_form_page.setLayout(form_layout)

        return checkout_form_page

    def updatePostcode(self, text):
        self.postcodeChanged.emit(text)

    def updateAddress(self, text):
        self.addressChanged.emit(text)

    def updateNetwork(self, text):
        # Directly update the UI based on the selected network
        self.onNetworkChanged(text)

    def updateDelivery(self, text):
        # Directly update the UI based on the selected delivery
        self.onDeliveryChanged(text)


    def onDeliveryChanged(self, delivery):
        # Update the label for the delivery fee based on the changed delivery value
        delivery_fee = 5.99  # Assuming a fixed delivery fee for now

        # Set label for delivery option with light blue text for "Delivery Option" and center alignment
        self.delivery_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Delivery Option\n</div> <div style='text-align:center;'>{delivery}</div>")
        self.delivery_fee_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Delivery Fee\n</div> <div style='text-align:center;'>£{delivery_fee:.2f}</div>")

        # Keep the style for the label
        self.delivery_label.setStyleSheet("font-size: 18px;")
        self.delivery_fee_label.setStyleSheet("font-size: 18px;")

    def showPaymentWindow(self):
        # Check which payment method is selected
        selected_payment_method = self.payment_dropdown.currentText()

        # Repopulate the payment window with the updated basket contents
        if selected_payment_method == "Card Payment":
            # Remove the old payment form and add a new one with updated contents
            self.stackedWidget.removeWidget(self.stackedWidget.widget(2))
            card_payment_form = self.createCardPaymentForm(self.checkoutForm)
            self.stackedWidget.insertWidget(2, card_payment_form)
            self.fadeTransition(self.stackedWidget.currentWidget(), card_payment_form)
            self.stackedWidget.setCurrentWidget(card_payment_form)

        elif selected_payment_method == "Bank Transfer":
            # Remove the old bank transfer form and add a new one with updated contents
            self.stackedWidget.removeWidget(self.stackedWidget.widget(3))
            bank_transfer_form = self.createBankTransferForm()
            self.stackedWidget.insertWidget(3, bank_transfer_form)
            self.fadeTransition(self.stackedWidget.currentWidget(), bank_transfer_form)
            self.stackedWidget.setCurrentWidget(bank_transfer_form)

        # Ensure that the styling is re-applied when switching widgets
        self.applyStyles()

    def applyStyles(self):
        # Re-apply the styles for each label to ensure consistency
        self.delivery_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Delivery Option</div><div style='text-align:center;'>{self.delivery_dropdown.currentText()}</div>"
        )
        self.delivery_fee_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Delivery Fee</div><div style='text-align:center;'>£{self.delivery_fee:.2f}</div>"
        )

        # Dynamically calculate the network fee based on the selected network
        selected_network = self.network_dropdown.currentText()
        if selected_network == "Bitcoin":
            network_fee = self.network_fee_btc
            fee_display = f"{network_fee:.8f} BTC ≈ ${self.network_fee_usd:.2f} USD"
        elif selected_network == "Ethereum":
            network_fee = self.network_fee_eth
            fee_display = f"{network_fee:.6f} ETH ≈ ${self.network_fee_usd:.2f} USD"
        else:
            fee_display = "No network selected."

        self.network_fee_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Network Fee</div><div style='text-align:center;'>{fee_display}</div>"
        )
        self.network_fee_label.setStyleSheet("font-size: 18px;")

        self.postcode_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Postcode</div><div style='text-align:center;'>{self.postcode_input.text()}</div>"
        )
        self.address_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Delivery Address</div><div style='text-align:center;'>{self.address_dropdown.currentText()}</div>"
        )

    def createCardPaymentForm(self, checkoutForm):
        payment_form_page = QWidget()
        form_layout = QVBoxLayout()

        # Add a table to display the order details
        tableWidget = QTableWidget()
        tableWidget.setColumnCount(4)
        tableWidget.setHorizontalHeaderLabels(['Image', 'Art Name', 'Artist', 'Valuation'])
        tableWidget.verticalHeader().setVisible(False)
        tableWidget.verticalHeader().setDefaultSectionSize(80)  # Adjust height based on image size

        # Set a fixed width for the table to make it larger
        tableWidget.setFixedWidth(600)  # Adjust this value based on your design needs

        # Set the column resize mode to stretch or resize based on content
        tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Stretch columns to fit

        # Populate the table with basket items
        tableWidget.setRowCount(len(self.basket))
        for index, item in enumerate(self.basket):
            image_path = item.get('image_file_path', None)
            pixmap = QPixmap(image_path).scaled(70, 70, Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation) if image_path else QPixmap(
                'path_to_default_image.png').scaled(60, 60)
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            tableWidget.setCellWidget(index, 0, image_label)

            art_name_item = QTableWidgetItem(item['asset'])
            artist_name_item = QTableWidgetItem(item['artist_name'])
            valuation_item = QTableWidgetItem(item['asset_valuation'])
            art_name_item.setTextAlignment(Qt.AlignCenter)
            artist_name_item.setTextAlignment(Qt.AlignCenter)
            valuation_item.setTextAlignment(Qt.AlignCenter)

            tableWidget.setItem(index, 1, art_name_item)
            tableWidget.setItem(index, 2, artist_name_item)
            tableWidget.setItem(index, 3, valuation_item)

        form_layout.addWidget(tableWidget)
        # Horizontal line separator below the table
        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.HLine)
        separator_top.setStyleSheet("color: white;")
        form_layout.addWidget(separator_top)

        # Payment method selection - Credit Card Details
        card_form_layout = QFormLayout()
        card_form_layout.setContentsMargins(70, 0, 0, 0)  # 50px left margin, adjust as needed

        # Card Number
        cardNumberLabel = QLabel("Card Number")
        cardNumberLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.cardNumberInput = QLineEdit()
        self.cardNumberInput.setFixedWidth(250)
        self.cardNumberInput.setPlaceholderText("1234 5678 9012 3456")
        self.cardNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{16}$")))
        self.cardNumberInput.textChanged.connect(self.validateCardPayment)

        # Cardholder's Name
        cardholderNameLabel = QLabel("Cardholder's Name")
        cardholderNameLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.cardholderNameInput = QLineEdit()
        self.cardholderNameInput.setFixedWidth(250)
        self.cardholderNameInput.setPlaceholderText("John Doe")
        self.cardholderNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,30}$")))
        self.cardholderNameInput.setMaxLength(30)
        self.cardholderNameInput.textChanged.connect(self.validateCardPayment)

        # Expiration Date
        expirationDateLabel = QLabel("Expiration Date")
        expirationDateLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.expirationDateInput = QLineEdit()
        self.expirationDateInput.setFixedWidth(120)
        self.expirationDateInput.setPlaceholderText("MM/YY")
        self.expirationDateInput.setValidator(QRegExpValidator(QRegExp(r"^(0[1-9]|1[0-2])\/\d{2}$")))
        self.expirationDateInput.textEdited.connect(self.formatExpirationDate)
        self.expirationDateInput.textChanged.connect(self.validateCardPayment)

        # CVC
        cvcLabel = QLabel("CVC")
        cvcLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.cvcInput = QLineEdit()
        self.cvcInput.setFixedWidth(90)
        self.cvcInput.setPlaceholderText("CVC")
        self.cvcInput.setValidator(QRegExpValidator(QRegExp(r"^\d{3}$")))
        self.cvcInput.textChanged.connect(self.validateCardPayment)

        # Add card payment fields to form layout
        card_form_layout.addRow(cardNumberLabel, self.cardNumberInput)
        card_form_layout.addRow(cardholderNameLabel, self.cardholderNameInput)
        # Expiration Date and CVC in a horizontal layout
        exp_cvc_layout = QHBoxLayout()
        exp_cvc_layout.addWidget(self.expirationDateInput)
        exp_cvc_layout.addWidget(self.cvcInput)

        # Add the expiration date label and the combined layout for expiration and CVC
        card_form_layout.addRow(expirationDateLabel, exp_cvc_layout)
        form_layout.addLayout(card_form_layout)

        # Create horizontal layout for "Save Card" button and dropdown
        card_save_layout = QHBoxLayout()

        # Save Card Button
        self.saveCardButton = QPushButton("Save Card")
        self.saveCardButton.setFixedWidth(100)  # Reduce width of button
        self.saveCardButton.clicked.connect(self.saveCard)  # Connect to the saveCard method
        card_save_layout.addWidget(self.saveCardButton)

        # Saved Cards Dropdown
        self.myCardsDropdown = QComboBox()
        self.myCardsDropdown.addItem("Select Saved Card")
        self.myCardsDropdown.setFixedWidth(170)  # Adjust width of dropdown
        card_save_layout.addWidget(self.myCardsDropdown)

        # Add the horizontal layout to the form
        form_layout.addLayout(card_save_layout)

        # Load the saved cards into the dropdown
        self.loadSavedCards()

        # Horizontal line separator below the table
        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.HLine)
        separator_top.setStyleSheet("color: white;")
        form_layout.addWidget(separator_top)

        # Layout to hold payment fees and postcode/address side by side
        h_layout = QHBoxLayout()

        # Payment fees layout
        fees_layout = QVBoxLayout()

        # Delivery Option and Fee
        delivery_option = self.delivery_dropdown.currentText()
        delivery_fee = 5.99
        self.delivery_label = QLabel(f"Delivery Option: {delivery_option}")
        self.delivery_fee_label = QLabel(f"Delivery Fee: £{delivery_fee:.2f}")
        fees_layout.addWidget(self.delivery_label)
        fees_layout.addWidget(self.delivery_fee_label)

        # Network Fee
        selected_network = self.network_dropdown.currentText()
        network_fee = 0.0001 if selected_network == "Bitcoin" else 0.003 if selected_network == "Ethereum" else 0
        self.network_fee_label = QLabel(f"Network Fee: {network_fee} {selected_network}")
        fees_layout.addWidget(self.network_fee_label)

        # Add the fees layout to the horizontal layout
        h_layout.addLayout(fees_layout)

        # Add a vertical line separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: white;")
        h_layout.addWidget(separator)

        # Postcode and Address layout
        postcode_address_layout = QVBoxLayout()

        self.postcode_label = QLabel(f"Postcode: {self.postcode_input.text()}")
        self.postcode_label.setStyleSheet("font-size: 18px;")
        postcode_address_layout.addWidget(self.postcode_label)

        self.address_label = QLabel(f"Delivery Address: {self.address_dropdown.currentText()}")
        self.address_label.setStyleSheet("font-size: 18px;")
        postcode_address_layout.addWidget(self.address_label)

        # Add postcode and address layout to the horizontal layout
        h_layout.addLayout(postcode_address_layout)

        # Add the horizontal layout to the main form layout
        form_layout.addLayout(h_layout)

        # Horizontal line separator above the total sum
        separator_above_total = QFrame()
        separator_above_total.setFrameShape(QFrame.HLine)
        separator_above_total.setStyleSheet("color: white;")
        form_layout.addWidget(separator_above_total)

        # Total price in light green, centered
        total_price_label = QLabel(f"{self.calculateTotalPrice()}")
        total_price_label.setStyleSheet("color: lightgreen; font-size: 16px; font-weight: bold; text-align: center;")
        total_price_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(total_price_label)
        self.total_price_label = total_price_label

        # Back and Confirm buttons
        button_layout = QHBoxLayout()

        # Back button
        back_button = QPushButton("Back")
        back_button.setStyleSheet("padding: 10px;")
        back_button.clicked.connect(self.goBackToCheckout)  # Method to go back to the checkout window
        button_layout.addWidget(back_button)

        self.confirm_button = QPushButton("Confirm Trade")
        self.confirm_button.setEnabled(False)  # Initially disabled

        self.confirm_button.clicked.connect(self.confirm_transfer)  # Now calls the correct method
        self.confirm_button.setStyleSheet("padding: 10px;")
        button_layout.addWidget(self.confirm_button)

        # Add the button layout to the form layout
        form_layout.addLayout(button_layout)

        payment_form_page.setLayout(form_layout)
        return payment_form_page

    def goBackToCheckout(self):
        # Transition back to the checkout page with animation
        self.fadeTransition(self.stackedWidget.currentWidget(), self.stackedWidget.widget(1))
        self.stackedWidget.setCurrentWidget(self.stackedWidget.widget(1))

    def onPostcodeChanged(self, postcode):
        # Set the label part to light blue and leave the postcode as default
        self.postcode_label.setText(f'<span style="color: lightblue;">Postcode</span><br>{postcode}')
        self.postcode_label.setAlignment(Qt.AlignCenter)  # Center the label text
        self.postcode_label.setStyleSheet("font-size: 18px;")  # Set the font size

    def onAddressChanged(self, address):
        # Set the label part to light blue and leave the address as default
        self.address_label.setText(f'<span style="color: lightblue;">Delivery Address</span><br>{address}')
        self.address_label.setAlignment(Qt.AlignCenter)  # Center the label text
        self.address_label.setStyleSheet("font-size: 18px;")  # Set the font size

    def formatExpirationDate(self, text):
        # Automatically add a slash after the month (MM) when the user inputs two digits
        if len(text) == 2 and not text.endswith('/'):
            self.expirationDateInput.setText(text + '/')
            self.expirationDateInput.setCursorPosition(3)  # Move the cursor to the right after the slash

    def createBankTransferForm(self):
        bank_transfer_form_page = QWidget()
        form_layout = QVBoxLayout()

        # Add a table to display the order details (Same as before)
        tableWidget = QTableWidget()
        tableWidget.setColumnCount(4)
        tableWidget.setHorizontalHeaderLabels(['Image', 'Art Name', 'Artist', 'Valuation'])
        tableWidget.verticalHeader().setVisible(False)
        tableWidget.verticalHeader().setDefaultSectionSize(80)  # Adjust height based on image size
        tableWidget.setFixedWidth(600)  # Adjust this value based on your design needs
        tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Stretch columns to fit
        tableWidget.setRowCount(len(self.basket))

        for index, item in enumerate(self.basket):
            image_path = item.get('image_file_path', None)
            pixmap = QPixmap(image_path).scaled(70, 70, Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation) if image_path else QPixmap(
                'path_to_default_image.png').scaled(60, 60)
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            tableWidget.setCellWidget(index, 0, image_label)

            art_name_item = QTableWidgetItem(item['asset'])
            artist_name_item = QTableWidgetItem(item['artist_name'])
            valuation_item = QTableWidgetItem(item['asset_valuation'])
            art_name_item.setTextAlignment(Qt.AlignCenter)
            artist_name_item.setTextAlignment(Qt.AlignCenter)
            valuation_item.setTextAlignment(Qt.AlignCenter)

            tableWidget.setItem(index, 1, art_name_item)
            tableWidget.setItem(index, 2, artist_name_item)
            tableWidget.setItem(index, 3, valuation_item)

        form_layout.addWidget(tableWidget)

        # Horizontal line separator below the table
        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.HLine)
        separator_top.setStyleSheet("color: white;")
        form_layout.addWidget(separator_top)

        # Bank transfer details section with input fields and validations
        bank_form_layout = QFormLayout()
        bank_form_layout.setContentsMargins(70, 0, 0, 0)

        # Account Number Input
        accountNumberLabel = QLabel("Account Number")
        accountNumberLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.accountNumberInput = QLineEdit()
        self.accountNumberInput.setFixedWidth(250)
        self.accountNumberInput.setPlaceholderText("12345678")
        self.accountNumberInput.setValidator(QIntValidator(0, 99999999))  # Up to 8 digits
        self.accountNumberInput.textChanged.connect(self.validateBankTransfer)

        # Bank Name Input
        bankNameLabel = QLabel("Bank Name")
        bankNameLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.bankNameInput = QLineEdit()
        self.bankNameInput.setFixedWidth(250)
        self.bankNameInput.setPlaceholderText("XYZ Bank")
        self.bankNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,20}$")))  # Up to 20 letters
        self.bankNameInput.textChanged.connect(self.validateBankTransfer)

        # Sort Code Input with event filter for formatting
        sortCodeLabel = QLabel("Sort Code")
        sortCodeLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")
        self.sortCodeInput = QLineEdit()
        self.sortCodeInput.setFixedWidth(120)
        self.sortCodeInput.setPlaceholderText("12-34-56")
        self.sortCodeInput.setMaxLength(8)  # Ensure it accommodates the formatted sort code (XX-XX-XX)
        self.sortCodeInput.textChanged.connect(self.validateBankTransfer)

        self.sortCodeInput.installEventFilter(self)

        bank_form_layout.addRow(accountNumberLabel, self.accountNumberInput)
        bank_form_layout.addRow(bankNameLabel, self.bankNameInput)
        bank_form_layout.addRow(sortCodeLabel, self.sortCodeInput)

        # "Save Bank" Button and "My Banks" Dropdown
        self.saveBankButton = QPushButton("Save Bank")
        self.myBanksDropdown = QComboBox()
        self.myBanksDropdown.addItem("Select Saved Bank")  # Placeholder
        self.myBanksDropdown.setFixedWidth(150)
        self.saveBankButton.setFixedWidth(100)

        bank_save_layout = QHBoxLayout()
        bank_save_layout.addWidget(self.saveBankButton)
        bank_save_layout.addWidget(self.myBanksDropdown)

        form_layout.addLayout(bank_form_layout)
        form_layout.addLayout(bank_save_layout)

        # Load saved banks into the dropdown
        self.loadSavedBanks()

        # Connect the save bank button to the method to save bank details
        self.saveBankButton.clicked.connect(self.saveBank)

        separator_bottom = QFrame()
        separator_bottom.setFrameShape(QFrame.HLine)
        separator_bottom.setStyleSheet("color: white;")
        form_layout.addWidget(separator_bottom)


        # Layout to hold payment fees and postcode/address side by side
        h_layout = QHBoxLayout()

        # Payment fees layout
        fees_layout = QVBoxLayout()

        # Delivery Option and Fee
        delivery_option = self.delivery_dropdown.currentText()
        delivery_fee = 5.99
        self.delivery_label = QLabel(f"Delivery Option: {delivery_option}")
        self.delivery_fee_label = QLabel(f"Delivery Fee: £{delivery_fee:.2f}")
        fees_layout.addWidget(self.delivery_label)
        fees_layout.addWidget(self.delivery_fee_label)

        # Network Fee
        selected_network = self.network_dropdown.currentText()
        network_fee = 0.0001 if selected_network == "Bitcoin" else 0.003 if selected_network == "Ethereum" else 0
        self.network_fee_label = QLabel(f"Network Fee: {network_fee} {selected_network}")
        fees_layout.addWidget(self.network_fee_label)

        # Add the fees layout to the horizontal layout
        h_layout.addLayout(fees_layout)

        # Add a vertical line separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: white;")
        h_layout.addWidget(separator)

        # Postcode and Address layout
        postcode_address_layout = QVBoxLayout()

        self.postcode_label = QLabel(f"Postcode: {self.postcode_input.text()}")
        self.postcode_label.setStyleSheet("font-size: 18px;")
        postcode_address_layout.addWidget(self.postcode_label)

        self.address_label = QLabel(f"Delivery Address: {self.address_dropdown.currentText()}")
        self.address_label.setStyleSheet("font-size: 18px;")
        postcode_address_layout.addWidget(self.address_label)

        # Add postcode and address layout to the horizontal layout
        h_layout.addLayout(postcode_address_layout)


        # Add the horizontal layout to the main form layout
        form_layout.addLayout(h_layout)

        # Horizontal line separator below the table
        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.HLine)
        separator_top.setStyleSheet("color: white;")
        form_layout.addWidget(separator_top)

        # Total price in light green, centered
        total_price_label = QLabel(f"{self.calculateTotalPrice()}")
        total_price_label.setStyleSheet("color: lightgreen; font-size: 16px; font-weight: bold; text-align: center;")
        total_price_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(total_price_label)
        self.total_price_label = total_price_label

        # Back and Confirm buttons
        button_layout = QHBoxLayout()

        # Back button
        back_button = QPushButton("Back")
        back_button.setStyleSheet("padding: 10px;")
        back_button.clicked.connect(self.goBackToCheckout)  # Method to go back to the checkout window
        button_layout.addWidget(back_button)

        self.confirm_button = QPushButton("Confirm Trade")
        self.confirm_button.setEnabled(False)  # Initially disabled

        self.confirm_button.clicked.connect(self.confirm_transfer)  # Now calls the correct method
        self.confirm_button.setStyleSheet("padding: 10px;")
        button_layout.addWidget(self.confirm_button)

        # Add the button layout to the form layout
        form_layout.addLayout(button_layout)

        self.confirm_button.clicked.connect(self.completePayment)


        # Add the button layout to the form layout
        form_layout.addLayout(button_layout)

        bank_transfer_form_page.setLayout(form_layout)
        return bank_transfer_form_page

    def eventFilter(self, obj, event):
        if obj == self.sortCodeInput and event.type() == QKeyEvent.KeyPress:
            if event.key() in {Qt.Key_0, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8,
                               Qt.Key_9}:
                current_text = self.sortCodeInput.text().replace('-', '')
                cursor_position = self.sortCodeInput.cursorPosition()
                new_text = current_text[:cursor_position] + event.text() + current_text[cursor_position:]
                if len(new_text) <= 6:
                    formatted_text = '-'.join([new_text[i:i + 2] for i in range(0, len(new_text), 2)])
                    self.sortCodeInput.setText(formatted_text)
                    self.sortCodeInput.setCursorPosition(cursor_position + 1)
                return True
            elif event.key() == Qt.Key_Backspace:
                current_text = self.sortCodeInput.text().replace('-', '')
                cursor_position = self.sortCodeInput.cursorPosition()
                if cursor_position > 0:
                    new_text = current_text[:cursor_position - 1] + current_text[cursor_position:]
                    formatted_text = '-'.join([new_text[i:i + 2] for i in range(0, len(new_text), 2)])
                    self.sortCodeInput.setText(formatted_text)
                    self.sortCodeInput.setCursorPosition(cursor_position - 1)
                return True
        return super().eventFilter(obj, event)
    def calculateTotalPrice(self):
        total_usdt = 0.0
        total_btc = 0.0
        total_eth = 0.0

        selected_network = self.network_dropdown.currentText()

        # Get real-time network fees
        network_fee_btc = 0.0
        network_fee_eth = 0.0

        if 'BTC' in self.network_prices:
            network_fee_btc = 3 / self.network_prices['BTC']  # Convert $3 to BTC
        if 'ETH' in self.network_prices:
            network_fee_eth = 3 / self.network_prices['ETH']  # Convert $3 to ETH

        # Iterate through basket items
        for item in self.basket:
            price_str = item['asset_valuation'].split()[0]
            currency = item['asset_valuation'].split()[1]

            try:
                price_value = float(price_str)

                if currency == "USDT":
                    total_usdt += price_value
                elif currency == "BTC":
                    total_btc += price_value
                elif currency == "ETH":
                    total_eth += price_value

            except ValueError:
                print(f"Error converting {price_str} to float.")

        # Only add the network fee if a specific network is chosen
        if selected_network == "Bitcoin":
            total_btc += network_fee_btc
        elif selected_network == "Ethereum":
            total_eth += network_fee_eth

        # Prepare the output for each scenario
        total_output = ""

        # Show the total BTC including network fee if applicable
        if total_btc > 0:
            total_output += f"Total Bitcoin: {total_btc:.8f} BTC\n"

        # Show the total ETH including network fee if applicable
        if total_eth > 0:
            total_output += f"Total Ethereum: {total_eth:.8f} ETH\n"

        # Always show the USDT total if it's greater than 0
        if total_usdt > 0:
            total_output += f"Total USDT: {total_usdt:.2f}\n"

        # Return the total output
        return total_output.strip()

    def fetchNetworkPrices(self):
        # Only fetch once when the cart is loaded or network is changed
        api_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"

        try:
            response = requests.get(api_url)
            data = response.json()

            # Store the prices in a dictionary
            self.network_prices['BTC'] = data['bitcoin']['usd']
            self.network_prices['ETH'] = data['ethereum']['usd']

        except Exception as e:
            print(f"Error fetching network prices: {e}")

    def onNetworkChanged(self, network):
        if network == "Bitcoin":
            # Calculate the equivalent of $3 in Bitcoin
            network_price_usd = self.network_prices.get('BTC', 0)
            if network_price_usd > 0:
                network_fee = 3 / network_price_usd  # Calculate the BTC equivalent of 3 USD
            else:
                network_fee = 0
            total_network_fee_usd = network_fee * network_price_usd
            fee_display = f"{network_fee:.8f} BTC ≈ ${total_network_fee_usd:.2f} USD"
            self.network_fee_btc = network_fee  # Store the BTC network fee dynamically
            self.network_fee_usd = total_network_fee_usd  # Store the fee in USD for use later

        elif network == "Ethereum":
            # Calculate the equivalent of $3 in Ethereum
            network_price_usd = self.network_prices.get('ETH', 0)
            if network_price_usd > 0:
                network_fee = 3 / network_price_usd  # Calculate the ETH equivalent of 3 USD
            else:
                network_fee = 0
            total_network_fee_usd = network_fee * network_price_usd
            fee_display = f"{network_fee:.6f} ETH ≈ ${total_network_fee_usd:.2f} USD"
            self.network_fee_eth = network_fee  # Store the ETH network fee dynamically
            self.network_fee_usd = total_network_fee_usd  # Store the fee in USD for use later

        else:
            fee_display = "No network selected."

        # Update the label to show the network fee
        self.network_fee_label.setText(
            f"<div style='color:lightblue; text-align:center;'>Network Fee</div> <div style='text-align:center;'>{fee_display}</div>")
        self.network_fee_label.setStyleSheet("font-size: 18px;")

        # Call updateTotalPrice to reflect the new fee in the total
        self.updateTotalPrice()

    def updateTotalPrice(self):
        total_price_text = self.calculateTotalPrice()
        self.total_price_label.setText(total_price_text)
    def completePayment(self):
        QMessageBox.information(self, "Payment Complete", "Your payment has been processed successfully.")

    def lookupAddresses(self):
        postcode = self.postcode_input.text().strip().replace(" ", "")
        if len(postcode) < 5:
            self.postcode_input.setStyleSheet("border: 2px solid red; padding: 8px;")  # Red border for invalid input
            self.next_button.setEnabled(False)  # Disable the Next button
            return

        # Placeholder while fetching
        self.address_dropdown.clear()
        self.address_dropdown.addItem("Looking up addresses...")

        # Postcodes.io API request
        api_url = f"https://api.postcodes.io/postcodes/{postcode}"

        try:
            response = requests.get(api_url)
            data = response.json()

            if response.status_code == 200 and data['status'] == 200:
                result = data['result']
                # We'll populate the dropdown with different location info available
                self.address_dropdown.clear()

                # Add relevant address parts (this example uses admin_ward)
                if result.get("admin_ward"):
                    self.address_dropdown.addItem(result["admin_ward"])

                # If valid, change border color to default and enable the Next button
                self.postcode_input.setStyleSheet("border: 2px solid green; padding: 8px;")
                self.next_button.setEnabled(True)  # Enable the Next button

            else:
                self.address_dropdown.clear()
                self.address_dropdown.addItem("Invalid postcode or no addresses found")
                self.postcode_input.setStyleSheet(
                    "border: 2px solid red; padding: 8px;")  # Red border for invalid input
                self.next_button.setEnabled(False)  # Disable the Next button

        except Exception as e:
            self.address_dropdown.clear()
            self.address_dropdown.addItem("Error fetching addresses")
            QMessageBox.critical(self, "API Error", f"An error occurred: {e}")
            self.postcode_input.setStyleSheet("border: 2px solid red; padding: 8px;")  # Red border for error
            self.next_button.setEnabled(False)  # Disable the Next button
    def checkout(self):
        # Transition to checkout form page with animation
        self.fadeTransition(self.stackedWidget.currentWidget(), self.stackedWidget.widget(1))
        self.stackedWidget.setCurrentWidget(self.stackedWidget.widget(1))

    def goBackToCart(self):
        # Transition back to the cart page with animation
        self.fadeTransition(self.stackedWidget.currentWidget(), self.stackedWidget.widget(0))
        self.stackedWidget.setCurrentWidget(self.stackedWidget.widget(0))

    def fadeTransition(self, current_widget, next_widget):
        # Set up fade-out for current widget
        self.opacityEffect = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(self.opacityEffect)
        self.fadeOutAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeOutAnimation.setDuration(2000)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)

        # Set up fade-in for next widget
        self.opacityEffectNext = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(self.opacityEffectNext)
        self.fadeInAnimation = QPropertyAnimation(self.opacityEffectNext, b"opacity")
        self.fadeInAnimation.setDuration(2000)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)

        self.fadeOutAnimation.start()
        self.fadeInAnimation.start()

    def populateTable(self):
        self.tableWidget.setRowCount(0)  # Clear existing rows

        self.tableWidget.setRowCount(len(self.basket))

        # Disable checkout button if basket is empty
        self.checkout_button.setEnabled(len(self.basket) > 0)

        # Adjust row height to fit the image
        self.tableWidget.verticalHeader().setDefaultSectionSize(80)

        for index, token in enumerate(self.basket):
            # Fetch the image path from the correct key
            image_path = token.get('image_file_path', None)

            if image_path:  # If image path is available
                pixmap = QPixmap(image_path).scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:  # Fallback image
                pixmap = QPixmap('path_to_default_image.png').scaled(60, 60, Qt.KeepAspectRatio,
                                                                     Qt.SmoothTransformation)

            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            self.tableWidget.setCellWidget(index, 0, image_label)

            # Add item details
            art_name_item = QTableWidgetItem(token['asset'])
            artist_name_item = QTableWidgetItem(token['artist_name'])
            valuation_item = QTableWidgetItem(token['asset_valuation'])

            art_name_item.setTextAlignment(Qt.AlignCenter)
            artist_name_item.setTextAlignment(Qt.AlignCenter)
            valuation_item.setTextAlignment(Qt.AlignCenter)

            self.tableWidget.setItem(index, 1, art_name_item)
            self.tableWidget.setItem(index, 2, artist_name_item)
            self.tableWidget.setItem(index, 3, valuation_item)

            # Set the state of the button based on the item's presence in the basket
            if token['asset'] not in self.item_in_cart:
                self.item_in_cart[token['asset']] = True  # Track item state in the cart

            # Remove button (or Add if item is already in cart)
            if self.item_in_cart[token['asset']]:
                remove_button = QPushButton("Remove")
                remove_button.setStyleSheet("background-color: #ff6666; color:black;")
                remove_button.clicked.connect(lambda checked, token=token: self.removeFromBasket(token))
            else:
                remove_button = QPushButton("Add")
                remove_button.setStyleSheet("background-color: #66ff66; color:black;")
                remove_button.clicked.connect(lambda checked, token=token: self.addToBasket(token))

            remove_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.tableWidget.setCellWidget(index, 4, remove_button)

        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

    def removeFromBasket(self, token):
        self.basket.remove(token)
        self.item_in_cart[token['asset']] = False  # Mark item as no longer in the cart
        self.saveCartToDatabase()  # Save updated cart to MongoDB

        # Update the button for the removed item
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 1).text() == token['asset']:
                add_button = QPushButton("Add")
                add_button.setStyleSheet("background-color: #66ff66; color:black;")
                add_button.clicked.connect(lambda checked, token=token: self.addToBasket(token))
                self.tableWidget.setCellWidget(row, 4, add_button)

        # Emit signal to update the header basket count
        self.basketCleared.emit()

    def clearBasket(self):
        self.basket.clear()
        self.saveCartToDatabase()  # Save the cleared basket to MongoDB

        self.populateTable()
        self.basketCleared.emit()  # Emit signal that the basket is cleared
        self.checkout_button.setEnabled(False)

    def saveCard(self):
        card_number = self.cardNumberInput.text().strip()
        cardholder_name = self.cardholderNameInput.text().strip()
        expiration_date = self.expirationDateInput.text().strip()
        cvc = self.cvcInput.text().strip()

        # Validate fields before saving
        if len(card_number) != 16:
            QMessageBox.warning(self, 'Invalid Card Number', 'Card number must be 16 digits.')
            return
        if len(cardholder_name) < 5:
            QMessageBox.warning(self, 'Invalid Cardholder Name', 'Cardholder name must be at least 5 characters long.')
            return
        if not re.match(r"^(0[1-9]|1[0-2])\/\d{2}$", expiration_date):
            QMessageBox.warning(self, 'Invalid Expiration Date', 'Expiration date must be in MM/YY format.')
            return
        if len(cvc) != 3:
            QMessageBox.warning(self, 'Invalid CVC', 'CVC must be 3 digits.')
            return

        # Proceed with saving card after validation passes
        saved_card = {
            'card_number': card_number,
            'cardholder_name': cardholder_name,
            'expiration_date': expiration_date
        }

        try:
            response = self.back_payment_handler.save_card(self.username, saved_card)
            if response == "Card already saved.":
                QMessageBox.warning(self, 'Duplicate Card', 'This card is already saved.')
            elif response == "Card saved successfully.":
                QMessageBox.information(self, 'Card Saved', 'Your card information has been saved.')
                self.loadSavedCards()  # Reload saved cards into the dropdown
            else:
                QMessageBox.warning(self, 'Error', response)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to save card information: {str(e)}')

    def loadSavedCards(self):
        try:
            # Fetch saved cards for the current user
            saved_cards = self.back_payment_handler.get_saved_cards(self.username)
            self.myCardsDropdown.clear()  # Clear existing entries
            self.myCardsDropdown.addItem("Select Saved Card")  # Add placeholder

            if saved_cards:
                self.saved_cards = saved_cards  # Store saved cards for autofill
                for card in saved_cards:
                    # Display masked card number (e.g., **** **** **** 1234)
                    masked_card = f"**** **** **** {card['card_number'][-4:]}"
                    self.myCardsDropdown.addItem(masked_card)

                # Connect dropdown change to autofill method
                self.myCardsDropdown.currentIndexChanged.connect(self.autofillCardDetails)

            else:
                self.myCardsDropdown.addItem("No saved cards available.")

        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to load saved cards: {str(e)}')

    def saveBank(self):
        account_number = self.accountNumberInput.text().strip()
        bank_name = self.bankNameInput.text().strip()
        sort_code = self.sortCodeInput.text().strip().replace("-", "")

        # Validate fields before saving
        if len(account_number) != 8:
            QMessageBox.warning(self, 'Invalid Account Number', 'Account number must be 8 digits.')
            return
        if len(bank_name) < 5:
            QMessageBox.warning(self, 'Invalid Bank Name', 'Bank name must be at least 5 characters long.')
            return
        if len(sort_code) != 6:
            QMessageBox.warning(self, 'Invalid Sort Code', 'Sort code must be 6 digits.')
            return

        # Proceed with saving bank after validation passes
        saved_bank = {
            'account_number': account_number,
            'bank_name': bank_name,
            'sort_code': sort_code
        }

        try:
            response = self.back_payment_handler.save_bank(self.username, saved_bank)
            if response == "Bank already saved.":
                QMessageBox.warning(self, 'Duplicate Bank', 'This bank is already saved.')
            elif response == "Bank saved successfully.":
                QMessageBox.information(self, 'Bank Saved', 'Your bank information has been saved.')
                self.loadSavedBanks()  # Reload saved banks into the dropdown
            else:
                QMessageBox.warning(self, 'Error', response)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to save bank information: {str(e)}')

    def loadSavedBanks(self):
        try:
            # Fetch saved banks for the current user
            saved_banks = self.back_payment_handler.get_saved_banks(self.username)
            self.myBanksDropdown.clear()
            self.myBanksDropdown.addItem("Select Saved Bank")  # Add placeholder

            if saved_banks:
                self.saved_banks = saved_banks  # Store saved banks for autofill
                for bank in saved_banks:
                    # Display masked account number (e.g., ****5678)
                    masked_account = f"****{bank['account_number'][-4:]}"
                    self.myBanksDropdown.addItem(f"{bank['bank_name']} ({masked_account})")

                # Connect dropdown change to autofill method
                self.myBanksDropdown.currentIndexChanged.connect(self.autofillBankDetails)

            else:
                self.myBanksDropdown.addItem("No saved banks available.")

        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to load saved banks: {str(e)}')
    def autofillCardDetails(self):
        # Get the selected index
        selected_index = self.myCardsDropdown.currentIndex() - 1  # Subtract 1 because of placeholder
        if selected_index >= 0:
            # Get the selected card details from stored cards
            selected_card = self.saved_cards[selected_index]
            self.cardNumberInput.setText(selected_card['card_number'])
            self.cardholderNameInput.setText(selected_card['cardholder_name'])
            self.expirationDateInput.setText(selected_card['expiration_date'])

    def autofillBankDetails(self):
        # Get the selected index
        selected_index = self.myBanksDropdown.currentIndex() - 1  # Subtract 1 because of placeholder
        if selected_index >= 0:
            # Get the selected bank details from stored banks
            selected_bank = self.saved_banks[selected_index]
            self.accountNumberInput.setText(selected_bank['account_number'])
            self.bankNameInput.setText(selected_bank['bank_name'])
            self.sortCodeInput.setText(selected_bank['sort_code'])

    def loadCartFromDatabase(self):
        # Check if username is available
        if self.username:
            # Find the cart specifically for the logged-in user
            user_cart = self.cart_collection.find_one({"username": self.username})
            if user_cart and "basket" in user_cart:
                self.basket = user_cart["basket"]  # Load the user's cart into the basket
            else:
                self.basket = []  # If no cart is found, start with an empty cart
        else:
            self.basket = []  # No username, default to empty cart

    # Method to save the cart to MongoDB when changes are made
    def saveCartToDatabase(self):
        # Ensure that the cart is saved for the specific user
        if self.username:
            self.cart_collection.update_one(
                {"username": self.username},
                {"$set": {"basket": self.basket}},
                upsert=True
            )

        # Reload the cart from the database after saving
        self.loadCartFromDatabase()

    def addToBasket(self, token):
        self.basket.append(token)
        self.item_in_cart[token['asset']] = True  # Mark item as added to the cart
        self.saveCartToDatabase()

        # Update the button for the added item
        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 1).text() == token['asset']:
                remove_button = QPushButton("Remove")
                remove_button.setStyleSheet("background-color: #ff6666; color:black;")
                remove_button.clicked.connect(lambda checked, token=token: self.removeFromBasket(token))
                self.tableWidget.setCellWidget(row, 4, remove_button)

        # Emit signal to update the header basket count
        self.basketCleared.emit()

    def confirm_transfer(self):
        # Check if the user is in the lockout period
        current_time = time.time()
        if current_time < self.lockout_time:
            QMessageBox.warning(self, 'Locked Out', 'Please wait 60 seconds before trying again.')
            return

        # Assuming that you have a way to get the user's email
        user_email = self.get_user_email()

        # Generate a random 6-digit verification code
        verification_code = random.randint(100000, 999999)

        # Send the verification code to the user's email
        self.send_verification_code(user_email, verification_code)

        # Prompt the user to enter the verification code
        verification_dialog = EmailVerificationDialog(self, verification_code)
        if verification_dialog.exec_() == QDialog.Accepted:
            entered_code = verification_dialog.getCode()

            # Check if the entered code matches the sent code
            if str(entered_code) == str(verification_code):
                QMessageBox.information(self, 'Verification Successful','Verification Successful')
                self.complete_transfer_process()  # Proceed with the actual transfer process
                self.failed_attempts = 0  # Reset failed attempts after success
            else:
                self.failed_attempts += 1
                if self.failed_attempts < 3:
                    QMessageBox.warning(self, 'Verification Failed', f'Incorrect code. You have {3 - self.failed_attempts} more attempt(s).')
                else:
                    self.lockout_time = time.time() + 60  # Lockout for 60 seconds
                    QMessageBox.warning(self, 'Locked Out', 'Too many failed attempts. Please try again in 60 seconds.')
    def send_verification_code(self, email, verification_code):
        # This method sends the email with the verification code
        msg = MIMEText(f"Your transfer verification code is: {verification_code}")
        msg['Subject'] = 'Your Transfer Verification Code'
        msg['From'] = 'spiro.biraku@gmail.com'  # Replace with your email
        msg['To'] = email

        # Set up the SMTP server
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('spiro.biraku@gmail.com', 'dzwzskcdswbrddaa')  # Replace with your credentials
                server.sendmail('spiro.biraku@gmail.com', email, msg.as_string())
        except Exception as e:
            print(f"Error sending email: {e}")



    def get_user_email(self):
        # Ensure that the username is valid
        if not self.username:
            raise ValueError("Username is not provided")

        # Query the users collection for the logged-in user's email
        users_collection = self.db['users']  # Assuming the collection is named 'users'
        user_data = users_collection.find_one({"username": self.username})

        if user_data and "email" in user_data:
            return user_data['email']
        else:
            raise ValueError(f"Email not found for user: {self.username}")

    def validateCardPayment(self):
        # Check if card number, cardholder name, expiration date, and CVC are filled
        card_number_valid = bool(self.cardNumberInput.text().strip())
        cardholder_name_valid = bool(self.cardholderNameInput.text().strip())
        expiration_date_valid = bool(self.expirationDateInput.text().strip())
        cvc_valid = bool(self.cvcInput.text().strip())

        # Enable the confirm button only if all fields are valid
        if card_number_valid and cardholder_name_valid and expiration_date_valid and cvc_valid:
            self.confirm_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)

    def validateBankTransfer(self):
        # Check if account number, bank name, and sort code are filled
        account_number_valid = bool(self.accountNumberInput.text().strip())
        bank_name_valid = bool(self.bankNameInput.text().strip())
        sort_code_valid = bool(self.sortCodeInput.text().strip())

        # Enable the confirm button only if all fields are valid
        if account_number_valid and bank_name_valid and sort_code_valid:
            self.confirm_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)

    def generate_rsa_signature_key(self, transaction_details):
        # Generate RSA private key for signing
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Prepare transaction details for signing, excluding the public key
        transaction_data = f"{transaction_details['art_name']}|{transaction_details['old_owner']}|{transaction_details['new_owner']}"

        # Generate a signature for the transaction data
        signature = private_key.sign(
            transaction_data.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

        # Return the signature as a hex string
        return signature.hex()

    # Save transaction details in 'trade_history' and update ownership in the 'artwork' collection
    def complete_transaction(self, transaction_details):
        # Step 1: Fetch the old owner from the 'ledger' collection using the 'asset' field
        ledger_entry = self.db['ledger'].find_one({'asset': transaction_details['art_name']})

        if ledger_entry and 'owner' in ledger_entry:
            transaction_details['old_owner'] = ledger_entry['owner']  # Old owner (seller)
        else:
            QMessageBox.warning(self, "Error", "Old owner not found in the ledger.")
            return  # Exit if no old owner is found

        # Step 2: Generate the RSA signature key for this transaction
        signature_key = self.generate_rsa_signature_key(transaction_details)

        # Step 3: Save the transaction in the 'trade_history' collection
        trade_record = {
            'art_name': transaction_details['art_name'],
            'old_owner': transaction_details['old_owner'],
            'new_owner': transaction_details['new_owner'],
            'signature_key': signature_key,  # Save the signature key only
            'valuation': transaction_details['valuation'],
            'payment_method': transaction_details['payment_method'],  # Card or Bank
            'network_method': transaction_details['network_method'],  # Bitcoin or Ethereum
            'network_fee': transaction_details['network_fee'],
            'delivery_method': transaction_details['delivery_method'],
            'delivery_address': transaction_details['delivery_address'],
            'total_amount_paid': transaction_details['total_amount_paid'],
            'timestamp': time.time()  # Record when the transaction happened
        }

        # Insert the trade history into the new collection
        self.db['trade_history'].insert_one(trade_record)

        # Step 4: Update the ownership of the art piece in the 'artwork' collection
        self.db['artwork'].update_one(
            {'art_name': transaction_details['art_name']},  # Using 'art_name' instead of 'art_public_key'
            {'$set': {'owner': transaction_details['new_owner']}}  # Transfer ownership in artwork collection
        )

        # Step 5: Update the ledger collection to reflect the new owner of the art
        # This will update only the 'owner' field for the matching 'asset', preventing duplication
        self.db['ledger'].update_one(
            {'asset': transaction_details['art_name']},  # Match by the asset (art_name)
            {'$set': {'owner': transaction_details['new_owner']}},  # Update the owner
            upsert=False  # Prevent inserting a new document if not found, only update existing ones
        )

        self.appUpdated.emit()

        QMessageBox.information(self, "Transaction Complete",
                                f"Transaction successfully completed.")

    def removePurchasedItemsFromCart(self, art_name):
        # Remove the purchased item from the local basket
        self.basket = [item for item in self.basket if item['asset'] != art_name]

        # Save the updated basket to the database
        self.saveCartToDatabase()

        # Reload the cart from the database to ensure the local state is synchronized
        self.loadCartFromDatabase()

        # Update the UI to reflect the changes
        self.populateTable()
        self.checkout_button.setEnabled(len(self.basket) > 0)  # Disable checkout button if the basket is empty

    def complete_transfer_process(self):
        # Collect transaction details
        transaction_details = {
            'art_name': self.basket[0]['asset'],
            'old_owner': self.basket[0]['artist_name'],
            'new_owner': self.username,  # Current logged-in user as buyer
            'valuation': self.basket[0]['asset_valuation'],
            'payment_method': self.payment_dropdown.currentText(),
            'network_method': self.network_dropdown.currentText(),  # Crypto type (Bitcoin, Ethereum, etc.)
            'network_fee': self.network_fee_label.text(),
            'delivery_method': self.delivery_dropdown.currentText(),
            'delivery_address': self.address_dropdown.currentText(),
            'total_amount_paid': self.total_price_label.text()
        }

        # Step 1: Ensure the buyer has sufficient cryptocurrency balance before proceeding
        if not self.check_crypto_balance(transaction_details['new_owner'], transaction_details['valuation']):
            QMessageBox.warning(self, 'Insufficient Balance',
                                'You do not have enough cryptocurrency to complete the purchase.')
            return  # Stop the process if the buyer doesn't have enough funds

        # Step 2: Complete the transaction logic
        self.complete_transaction(transaction_details)

        # Step 3: Update seller's and buyer's cryptocurrency wallets
        self.update_crypto_wallets(transaction_details['old_owner'], transaction_details['new_owner'],
                                   transaction_details['valuation'])

        # Step 4: Remove all purchased items from the cart
        self.clearBasket()

        # Step 5: Save the updated cart to the database
        self.saveCartToDatabase()

        # Step 6: Refresh the UI
        self.populateTable()

        # Emit signals to update other parts of the app
        self.basketCleared.emit()
        self.appUpdated.emit()

        # Notify the user of the successful transaction
        QMessageBox.information(self, 'Transaction Completed', 'The trade has been completed successfully.')

        # Close the CartWindow or perform other final actions
        self.close()

    # Function to update the buyer's and seller's cryptocurrency holdings
    def update_crypto_wallets(self, seller_username, buyer_username, valuation):
        # Step 1: Fetch both seller's and buyer's cryptocurrency holdings
        seller_crypto = self.db['cryptocurrency_holdings'].find_one({'username': seller_username})
        buyer_crypto = self.db['cryptocurrency_holdings'].find_one({'username': buyer_username})

        # Step 2: Detect the crypto type from valuation (Assumes format like "100 USDT")
        try:
            valuation_value = float(valuation.split()[0])  # Extract the numeric value
            crypto_type = valuation.split()[1]  # Extract the crypto type (e.g., USDT, BTC, ETH)
        except (ValueError, IndexError):
            print("Error: Invalid valuation format.")
            return

        # Step 3: Ensure both buyer and seller have crypto wallets
        if not buyer_crypto:
            QMessageBox.warning(self, 'Error', f'Buyer "{buyer_username}" does not have a cryptocurrency wallet.')
            return
        if not seller_crypto:
            QMessageBox.warning(self, 'Error', f'Seller "{seller_username}" does not have a cryptocurrency wallet.')
            return

        # Step 4: Update the crypto balance for the buyer (deduct)
        if crypto_type == 'BTC':
            if buyer_crypto.get('bitcoin', 0) >= valuation_value:
                buyer_crypto['bitcoin'] -= valuation_value
            else:
                QMessageBox.warning(self, 'Insufficient Balance', 'You do not have enough Bitcoin.')
                return
        elif crypto_type == 'ETH':
            if buyer_crypto.get('ethereum', 0) >= valuation_value:
                buyer_crypto['ethereum'] -= valuation_value
            else:
                QMessageBox.warning(self, 'Insufficient Balance', 'You do not have enough Ethereum.')
                return
        elif crypto_type == 'USDT':
            if buyer_crypto.get('tether', 0) >= valuation_value:
                buyer_crypto['tether'] -= valuation_value
            else:
                QMessageBox.warning(self, 'Insufficient Balance', 'You do not have enough Tether.')
                return
        else:
            QMessageBox.warning(self, 'Invalid Crypto', 'Unsupported cryptocurrency type in valuation.')
            return

        # Save updated buyer balance to the database
        self.db['cryptocurrency_holdings'].update_one(
            {'username': buyer_username},
            {'$set': buyer_crypto},
            upsert=True
        )
        print(f"Deducted {valuation_value} {crypto_type} from {buyer_username}'s wallet.")

        # Step 5: Update the crypto balance for the seller (add)
        if crypto_type == 'BTC':
            seller_crypto['bitcoin'] = seller_crypto.get('bitcoin', 0) + valuation_value
        elif crypto_type == 'ETH':
            seller_crypto['ethereum'] = seller_crypto.get('ethereum', 0) + valuation_value
        elif crypto_type == 'USDT':
            seller_crypto['tether'] = seller_crypto.get('tether', 0) + valuation_value

        # Save updated seller balance to the database
        self.db['cryptocurrency_holdings'].update_one(
            {'username': seller_username},
            {'$set': seller_crypto},
            upsert=True
        )
        print(f"Added {valuation_value} {crypto_type} to {seller_username}'s wallet.")

    def check_crypto_balance(self, buyer_username, valuation):
        # Step 1: Fetch the buyer's cryptocurrency holdings
        buyer_crypto = self.db['cryptocurrency_holdings'].find_one({'username': buyer_username})

        # Step 2: Parse the valuation string (Assumes format like "100 USDT")
        try:
            valuation_value = float(valuation.split()[0])  # Extract the numeric value
            crypto_type = valuation.split()[1]  # Extract the crypto type (e.g., USDT, BTC, ETH)
        except (ValueError, IndexError):
            print("Error: Invalid valuation format.")
            return False  # Return False for an invalid format

        # Step 3: Ensure the buyer has enough balance
        if crypto_type == 'BTC' and buyer_crypto.get('bitcoin', 0) >= valuation_value:
            return True  # Buyer has enough Bitcoin
        elif crypto_type == 'ETH' and buyer_crypto.get('ethereum', 0) >= valuation_value:
            return True  # Buyer has enough Ethereum
        elif crypto_type == 'USDT' and buyer_crypto.get('tether', 0) >= valuation_value:
            return True  # Buyer has enough Tether
        else:
            return False  # Buyer does not have enough funds


class EmailVerificationDialog(QDialog):
    def __init__(self, parent=None, verification_code=None):
        super().__init__(parent)
        self.verification_code = verification_code  # Store the verification code
        self.setWindowTitle('Email Verification')
        self.setFixedSize(400, 200)
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout()

        self.label = QLabel("Enter 6 digit code")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter email verification code")
        layout.addWidget(self.code_input)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def getCode(self):
        return self.code_input.text()