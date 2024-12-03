from PyQt5.QtWidgets import QGridLayout, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QComboBox, QLineEdit, QMessageBox, QSpacerItem, QSizePolicy, QStackedWidget, QFormLayout, QGroupBox, QGraphicsOpacityEffect
from PyQt5.QtGui import QFont, QIcon, QDoubleValidator, QIntValidator, QRegExpValidator, QKeyEvent
from PyQt5.QtCore import Qt, QRegExp, QPropertyAnimation
import qtawesome as qta
from pymongo import MongoClient

class PaymentTab(QWidget):
    def __init__(self, username, back_payment_handler):
        super().__init__()
        self.username = username

        self.back_payment_handler = back_payment_handler

        self.initUI()
        self.back_payment_handler.cryptoPurchased.connect(self.clearFields)  # Connect signal to slot
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client['admin']
        self.users_collection = self.db['users']
        # Ensure the 'pay.cards' collection exists
        self.cards_collection = self.db['pay.cards']

        # Create an index on 'username' for faster queries (optional but recommended)
        self.cards_collection.create_index('username')

    def initUI(self):
        self.setWindowTitle('Buy Cryptocurrency')
        mainLayout = QVBoxLayout()  # Main layout for the entire window

        self.stackedWidget = QStackedWidget()
        self.initCryptocurrencyDetailsUI()
        self.initPaymentDetailsUI()

        mainLayout.addWidget(self.stackedWidget)
        self.setLayout(mainLayout)

        # Set initial payment form to Bank Transfer
        self.paymentForms.setCurrentWidget(self.bankTransferForm)

        # Setup validators
        self.setupValidators()

    def initCryptocurrencyDetailsUI(self):
        self.cryptoDetailsWidget = QWidget()
        layout = QVBoxLayout(self.cryptoDetailsWidget)
        layout.setContentsMargins(20, 40, 20, 20)  # Add top margin to move the container down

        containerFrame = QGroupBox("Cryptocurrency Details")
        containerFrame.setStyleSheet("""
            QFrame {
                border-radius: 15px;
                padding: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
                min-width: 400px;
            }
            QGroupBox {
                border: 4px solid lightblue;
                padding: 25px;
                border-radius: 25px;
                font-size: 25px;
                margin-top:20px;
            }
        """)

        containerLayout = QVBoxLayout()
        containerFrame.setLayout(containerLayout)

        labelFont = QFont("Arial", 16)
        labelStyle = """
            QLabel {
                background-color: lightblue;
                color: black;
                border-radius: 5px;
                padding: 5px;
                margin-bottom: 10px;
                font-size:18px;
            }
        """

        # Crypto selection
        cryptoLayout = QVBoxLayout()
        cryptoLabel = QLabel("Select Cryptocurrency")
        cryptoLabel.setFont(labelFont)
        cryptoLabel.setAlignment(Qt.AlignCenter)
        cryptoLabel.setStyleSheet(labelStyle)
        self.cryptoComboBox = QComboBox()
        self.cryptoComboBox.addItem(QIcon('btc.png'), 'Bitcoin (BTC)')
        self.cryptoComboBox.addItem(QIcon('eth.png'), 'Ethereum (ETH)')
        self.cryptoComboBox.addItem(QIcon('tether.png'), 'Tether (USDT)')
        self.cryptoComboBox.setFixedWidth(250)
        self.cryptoComboBox.currentIndexChanged.connect(self.updateTotalAmountGBP)
        cryptoLayout.addWidget(cryptoLabel, alignment=Qt.AlignCenter)
        cryptoLayout.addWidget(self.cryptoComboBox, alignment=Qt.AlignCenter)

        # Amount input
        amountLayout = QVBoxLayout()
        amountLabel = QLabel("Enter Amount")
        amountLabel.setFont(labelFont)
        amountLabel.setAlignment(Qt.AlignCenter)
        amountLabel.setStyleSheet(labelStyle)
        self.amountInput = QLineEdit()
        self.amountInput.setPlaceholderText("0.00")
        self.amountInput.setFixedWidth(250)
        self.amountInput.setValidator(QDoubleValidator(0.0, 999999.99, 2))
        self.amountInput.textChanged.connect(self.updateTotalAmountGBP)
        self.amountInput.textChanged.connect(self.checkAmountValid)

        amountLayout.addWidget(amountLabel, alignment=Qt.AlignCenter)
        amountLayout.addWidget(self.amountInput, alignment=Qt.AlignCenter)

        # Payment method selection
        paymentLayout = QVBoxLayout()
        paymentMethodLabel = QLabel("Select Payment Method")
        paymentMethodLabel.setFont(labelFont)
        paymentMethodLabel.setAlignment(Qt.AlignCenter)
        paymentMethodLabel.setStyleSheet(labelStyle)
        self.paymentMethodComboBox = QComboBox()
        self.paymentMethodComboBox.addItem(qta.icon('fa.credit-card', color='white'), 'Credit Card      0% Fees')
        self.paymentMethodComboBox.addItem(qta.icon('fa.university', color='white'), 'Bank Transfer    0% Fees')
        self.paymentMethodComboBox.setFixedWidth(250)
        self.paymentMethodComboBox.currentIndexChanged.connect(self.onPaymentMethodChanged)
        paymentLayout.addWidget(paymentMethodLabel, alignment=Qt.AlignCenter)
        paymentLayout.addWidget(self.paymentMethodComboBox, alignment=Qt.AlignCenter)

        # Total amount
        totalAmountLabel = QLabel("Total Amount in GBP")
        totalAmountLabel.setFont(labelFont)
        totalAmountLabel.setAlignment(Qt.AlignCenter)
        totalAmountLabel.setStyleSheet(labelStyle)
        self.totalAmountOutput = QLabel("0.00")
        self.totalAmountOutput.setAlignment(Qt.AlignCenter)
        self.totalAmountOutput.setFixedWidth(400)
        self.totalAmountOutput.setStyleSheet("border: 1px solid lightgreen; padding: 5px; color: lightgreen;")

        totalAmountLayout = QVBoxLayout()
        totalAmountLayout.addWidget(totalAmountLabel, alignment=Qt.AlignCenter)
        totalAmountLayout.addWidget(self.totalAmountOutput, alignment=Qt.AlignCenter)

        # Add layouts to the container layout
        containerLayout.addLayout(cryptoLayout)
        containerLayout.addLayout(amountLayout)
        containerLayout.addLayout(paymentLayout)
        containerLayout.addLayout(totalAmountLayout)

        layout.addWidget(containerFrame, alignment=Qt.AlignCenter)

        self.continueButton = QPushButton("Continue")
        self.continueButton.setFixedSize(200, 50)
        self.continueButton.setStyleSheet("font-size: 20px;")
        self.continueButton.setEnabled(False)  # Initially disable the button
        self.continueButton.clicked.connect(self.showPaymentDetails)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))  # Add this line
        layout.addWidget(self.continueButton, alignment=Qt.AlignCenter)

        self.stackedWidget.addWidget(self.cryptoDetailsWidget)

    def checkAmountValid(self):
        amount_text = self.amountInput.text().strip()
        if amount_text and float(amount_text) > 0:
            self.continueButton.setEnabled(True)
        else:
            self.continueButton.setEnabled(False)

    def initPaymentDetailsUI(self):
        self.paymentDetailsWidget = QWidget()
        layout = QVBoxLayout(self.paymentDetailsWidget)
        layout.setContentsMargins(20, 100, 20, 20)  # Add top margin to move the container down

        containerFrame = QGroupBox("Payment Details")
        containerFrame.setStyleSheet("""
            QFrame {
                border-radius: 15px;
                padding: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
                min-width: 100px;
            }
            QGroupBox {
                border: 4px solid lightblue;
                padding: 25px;
                border-radius: 25px;
                font-size: 25px;
            }
        """)

        containerLayout = QVBoxLayout()
        containerFrame.setLayout(containerLayout)

        self.paymentForms = QStackedWidget()
        self.creditCardForm = self.createCreditCardForm()
        self.bankTransferForm = self.createBankTransferForm()
        self.paymentForms.addWidget(self.creditCardForm)
        self.paymentForms.addWidget(self.bankTransferForm)
        self.paymentForms.setCurrentWidget(self.bankTransferForm)

        containerLayout.addWidget(self.paymentForms)

        layout.addWidget(containerFrame, alignment=Qt.AlignCenter)

        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)  # Remove space between buttons
        buttonLayout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the layout

        self.backButton = QPushButton("")
        self.backButton.setFixedSize(50, 50)
        self.backButton.setStyleSheet("font-size: 14px;")
        back_icon = qta.icon('fa.arrow-left', color='white')
        self.backButton.setIcon(back_icon)
        self.backButton.clicked.connect(self.showCryptoDetails)
        buttonLayout.addWidget(self.backButton)

        self.submitButton = QPushButton("Buy")
        self.submitButton.setFixedSize(150, 50)
        self.submitButton.setStyleSheet("font-size: 16px;")
        self.submitButton.clicked.connect(self.validateInputs)
        buttonLayout.addWidget(self.submitButton)

        # Create a new container for the buttons and center it
        buttonContainer = QWidget()
        buttonContainer.setLayout(buttonLayout)
        layout.addWidget(buttonContainer, alignment=Qt.AlignCenter)

        self.stackedWidget.addWidget(self.paymentDetailsWidget)

    def createCreditCardForm(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        cardNumberLabel = QLabel("Card Number")
        cardNumberLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.cardNumberInput = QLineEdit()
        self.cardNumberInput.setFixedWidth(250)
        self.cardNumberInput.setPlaceholderText("1234 5678 9012 3456")
        self.cardNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{16}$")))
        self.cardNumberInput.setStyleSheet("margin-top:15px;")

        cardholderNameLabel = QLabel("Cardholder's Name")
        cardholderNameLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.cardholderNameInput = QLineEdit()
        self.cardholderNameInput.setFixedWidth(250)
        self.cardholderNameInput.setPlaceholderText("John Doe")
        self.cardholderNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,30}$")))
        self.cardholderNameInput.setMaxLength(30)
        self.cardholderNameInput.setStyleSheet("margin-top:15px;")

        expirationDateLabel = QLabel("Expiration Date")
        expirationDateLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.expirationDateInput = QLineEdit()
        self.expirationDateInput.setFixedWidth(120)
        self.expirationDateInput.setPlaceholderText("MM/YY")
        self.expirationDateInput.setValidator(QRegExpValidator(QRegExp(r"^(0[1-9]|1[0-2])\/\d{2}$")))
        self.expirationDateInput.textEdited.connect(self.formatExpirationDate)
        self.expirationDateInput.setStyleSheet("margin-top:15px;")

        cvcLabel = QLabel("CVC")
        cvcLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.cvcInput = QLineEdit()
        self.cvcInput.setFixedWidth(120)
        self.cvcInput.setPlaceholderText("123")
        self.cvcInput.setValidator(QRegExpValidator(QRegExp(r"^\d{3}$")))
        self.cvcInput.setStyleSheet("margin-top:15px;")

        # Add the existing fields to the form layout
        layout.addRow(cardNumberLabel, self.cardNumberInput)
        layout.addRow(cardholderNameLabel, self.cardholderNameInput)
        layout.addRow(expirationDateLabel, self.expirationDateInput)
        layout.addRow(cvcLabel, self.cvcInput)

        # Add a spacer item to push the Save Card elements further down
        spacerItem = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacerItem)  # Add spacer before the Save Card and Dropdown

        # Create Save Card Button
        self.saveCardButton = QPushButton("Save Card")
        self.saveCardButton.setFixedSize(120, 45)
        self.saveCardButton.setStyleSheet("font-size: 15px;")
        self.saveCardButton.clicked.connect(self.saveCard)

        # Create Choose Saved Card Dropdown
        self.savedCardsDropdown = QComboBox()  # Rename here to match the variable name in loadSavedCards
        self.savedCardsDropdown.setFixedSize(250, 40)
        self.savedCardsDropdown.setStyleSheet("font-size: 15px;")

        # Step 3: Connect the signal to the populateCardDetails method
        self.savedCardsDropdown.currentIndexChanged.connect(self.populateCardDetails)

        # Load saved cards into the dropdown (this function needs to be implemented)
        self.loadSavedCards()

        # Create a horizontal layout to hold Save Card Button and Saved Cards Dropdown
        saveCardLayout = QHBoxLayout()
        saveCardLayout.addWidget(self.saveCardButton)
        saveCardLayout.addSpacing(20)  # Add 20 pixels of space
        saveCardLayout.addWidget(self.savedCardsDropdown)

        # Add the horizontal layout with the two new elements to the form layout
        layout.addRow(saveCardLayout)

        return widget

    def saveCard(self):
        card_number = self.cardNumberInput.text().strip()
        cardholder_name = self.cardholderNameInput.text().strip()
        expiration_date = self.expirationDateInput.text().strip()
        cvc = self.cvcInput.text().strip()

        # Simple validation to ensure card information is filled
        if card_number and cardholder_name and expiration_date and cvc:
            saved_card = {
                'card_number': card_number,
                'cardholder_name': cardholder_name,
                'expiration_date': expiration_date
            }

            try:
                # Delegate saving card to BackPaymentHandler and check for response
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
        else:
            QMessageBox.warning(self, 'Invalid Input', 'Please fill in all card details before saving.')

    def loadSavedCards(self):
        try:
            # Fetch saved cards using BackPaymentHandler
            saved_cards = self.back_payment_handler.get_saved_cards(self.username)

            # Clear the dropdown before adding new items
            self.savedCardsDropdown.clear()

            # Set the placeholder text as the combo box current text
            self.savedCardsDropdown.setEditable(True)
            self.savedCardsDropdown.lineEdit().setPlaceholderText("Choose Saved Card")
            self.savedCardsDropdown.setEditable(False)

            # Add saved cards to the dropdown
            if saved_cards:
                for card in saved_cards:
                    card_display = f"{card['cardholder_name']} - **** {card['card_number'][-4:]}"
                    self.savedCardsDropdown.addItem(card_display, card)  # Store card data as userData

                # Select the first saved card by default
                self.savedCardsDropdown.setCurrentIndex(-1)
            else:
                # Show a default message if no saved cards are available
                self.savedCardsDropdown.addItem("No cards available")
                self.savedCardsDropdown.setEnabled(False)  # Disable dropdown if no cards are available

        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to load saved cards: {str(e)}')

    def populateCardDetails(self):
        # Get the selected index from the dropdown
        selected_index = self.savedCardsDropdown.currentIndex()

        # Check if a valid card is selected (index >= 0)
        if selected_index >= 0:
            # Get the card details from the data stored in the dropdown item
            selected_card = self.savedCardsDropdown.itemData(selected_index)
            if selected_card:
                # Populate the payment fields with the selected card details
                self.cardNumberInput.setText(selected_card.get('card_number', ''))
                self.cardholderNameInput.setText(selected_card.get('cardholder_name', ''))
                self.expirationDateInput.setText(selected_card.get('expiration_date', ''))
                self.cvcInput.setText('')  # CVC should remain blank for security
        else:
            # Clear the payment fields if no valid card is selected
            self.cardNumberInput.clear()
            self.cardholderNameInput.clear()
            self.expirationDateInput.clear()
            self.cvcInput.clear()

    def validateInputs(self):
        amount_text = self.amountInput.text().strip()
        if not amount_text or float(amount_text) == 0:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid amount.')
            return

        crypto = self.cryptoComboBox.currentText().lower().split()[0]
        amount = float(amount_text)
        payment_method = self.paymentMethodComboBox.currentText()
        payment_info = {}

        if self.paymentForms.currentWidget() == self.creditCardForm:
            card_number = self.cardNumberInput.text().strip()
            cardholder_name = self.cardholderNameInput.text().strip()
            expiration_date = self.expirationDateInput.text().strip()
            cvc = self.cvcInput.text().strip()

            if not (card_number and cardholder_name and expiration_date and cvc):
                QMessageBox.warning(self, 'Invalid Input', 'Please fill in all credit card details.')
                return
            payment_info = {
                'type': 'card',
                'card_number': card_number,
                'cardholder_name': cardholder_name,
                'expiration_date': expiration_date,
                'cvc': cvc
            }
        elif self.paymentForms.currentWidget() == self.bankTransferForm:
            # Bank transfer details logic
            # Gather the required fields and add to payment_info
            pass

        response = self.back_payment_handler.process_payment(self.username, crypto, amount, payment_info)
        if response.startswith("Success"):
            QMessageBox.information(self, 'Success', response)
            self.clearFields()
        else:
            QMessageBox.warning(self, 'Error', response)

    def createBankTransferForm(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        accountNumberLabel = QLabel("Account Number")
        accountNumberLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.accountNumberInput = QLineEdit()
        self.accountNumberInput.setFixedWidth(250)
        self.accountNumberInput.setPlaceholderText("12345678")
        self.accountNumberInput.setStyleSheet("margin-top:15px;")
        self.accountNumberInput.setValidator(QIntValidator(0, 99999999))

        sortCodeLabel = QLabel("Sort Code")
        sortCodeLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.sortCodeInput = QLineEdit()
        self.sortCodeInput.setFixedWidth(250)
        self.sortCodeInput.setPlaceholderText("Enter sort code")
        self.sortCodeInput.setStyleSheet("margin-top:15px;")
        self.sortCodeInput.installEventFilter(self)

        bankNameLabel = QLabel("Bank Name")
        bankNameLabel.setStyleSheet("font-size: 16px; padding-bottom:10px;")  # Reduce padding-bottom
        self.bankNameInput = QLineEdit()
        self.bankNameInput.setFixedWidth(250)
        self.bankNameInput.setPlaceholderText("Bank Name")
        self.bankNameInput.setStyleSheet("margin-top:15px;")
        self.bankNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,20}$")))

        layout.addRow(bankNameLabel, self.bankNameInput)
        layout.addRow(accountNumberLabel, self.accountNumberInput)
        layout.addRow(sortCodeLabel, self.sortCodeInput)

        return widget

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

    def formatExpirationDate(self, text):
        if len(text) == 2 and not text.endswith('/'):
            self.expirationDateInput.setText(text + '/')
            self.expirationDateInput.setCursorPosition(3)  # Move cursor to right after the slash

    def onPaymentMethodChanged(self, index):
        selected_method = self.paymentMethodComboBox.currentText()
        if selected_method.startswith("Credit Card"):
            self.paymentForms.setCurrentWidget(self.creditCardForm)
        elif selected_method.startswith("Bank Transfer"):
            self.paymentForms.setCurrentWidget(self.bankTransferForm)
        else:
            self.paymentForms.setCurrentWidget(self.placeholderForm)

    def updateTotalAmountGBP(self):
        crypto = self.cryptoComboBox.currentText().lower()
        amount_text = self.amountInput.text()

        try:
            amount = float(amount_text)
        except ValueError:
            self.totalAmountOutput.setText("£0.00")
            return

        if crypto == 'bitcoin (btc)':
            price = self.back_payment_handler.get_crypto_price('bitcoin')
        elif crypto == 'ethereum (eth)':
            price = self.back_payment_handler.get_crypto_price('ethereum')
        elif crypto == 'tether (usdt)':
            price = self.back_payment_handler.get_crypto_price('tether')
        else:
            price = None

        if price is not None:
            total_amount = amount * price
            formatted_amount = "£{:,.2f}".format(total_amount)
            self.totalAmountOutput.setText(formatted_amount)
        else:
            self.totalAmountOutput.setText("£0.00")

    def setupValidators(self):
        # Set validators for all inputs
        self.amountInput.setValidator(QRegExpValidator(
            QRegExp(r"^\d{0,5}(\.\d{1,2})?$")))  # Up to 5 digits before decimal, and up to 2 digits after decimal
        self.cardNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{16}$")))  # Up to 16 digits
        self.expirationDateInput.setValidator(QRegExpValidator(QRegExp(r"^(0[1-9]|1[0-2])\/\d{2}$")))  # MM/YY format
        self.cvcInput.setValidator(QRegExpValidator(QRegExp(r"^\d{3}$")))  # Exactly 3 digits
        self.accountNumberInput.setValidator(QIntValidator(0, 99999999))  # Up to 8 digits
        self.bankNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,20}$")))  # Up to 20 letters

        # Connect textChanged signals to check card input validation
        self.cardNumberInput.textChanged.connect(self.checkCardInputsValid)
        self.cardholderNameInput.textChanged.connect(self.checkCardInputsValid)
        self.expirationDateInput.textChanged.connect(self.checkCardInputsValid)
        self.cvcInput.textChanged.connect(self.checkCardInputsValid)

        # Disable Save Card button initially
        self.saveCardButton.setEnabled(False)

    def clearFields(self):
        self.cryptoComboBox.setCurrentIndex(0)
        self.amountInput.clear()
        self.paymentMethodComboBox.setCurrentIndex(0)
        self.cardNumberInput.clear()
        self.cardholderNameInput.clear()
        self.expirationDateInput.clear()
        self.cvcInput.clear()
        self.accountNumberInput.clear()
        self.sortCodeInput.clear()
        self.bankNameInput.clear()
        self.totalAmountOutput.setText("0.00")

    def checkCardInputsValid(self):
        # Check if all card inputs are valid
        if (
                self.cardNumberInput.hasAcceptableInput() and
                self.cardholderNameInput.hasAcceptableInput() and
                self.expirationDateInput.hasAcceptableInput() and
                self.cvcInput.hasAcceptableInput()
        ):
            self.saveCardButton.setEnabled(True)
        else:
            self.saveCardButton.setEnabled(False)

    def validateInputs(self):
        amount_text = self.amountInput.text().strip()
        if not amount_text or float(amount_text) == 0:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid amount.')
            return

        if self.paymentForms.currentWidget() == self.creditCardForm:
            if not self.cardNumberInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid card number.')
                return
            if not self.cardholderNameInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid cardholder name.')
                return
            if not self.expirationDateInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid expiration date in MM/YY format.')
                return
            if not self.cvcInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid CVC.')
                return

        if self.paymentForms.currentWidget() == self.bankTransferForm:
            if not self.accountNumberInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid account number.')
                return
            sort_code_text = self.sortCodeInput.text().strip()
            if len(sort_code_text) != 8 or '--' in sort_code_text:
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid sort code in 12-34-56 format.')
                return
            if not self.bankNameInput.hasAcceptableInput():
                QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid bank name.')
                return

        # Reuse validation for save card
        if (
                self.cardNumberInput.hasAcceptableInput() and
                self.cardholderNameInput.hasAcceptableInput() and
                self.expirationDateInput.hasAcceptableInput() and
                self.cvcInput.hasAcceptableInput()
        ):
            self.saveCardButton.setEnabled(True)
        else:
            self.saveCardButton.setEnabled(False)

        # Get crypto and calculate total cost
        crypto = self.cryptoComboBox.currentText().lower().split()[0]  # Get crypto name (bitcoin, ethereum, tether)
        amount = float(amount_text)
        price = self.back_payment_handler.get_crypto_price(crypto)
        total_cost = amount * price if price is not None else 0

        # Show confirmation dialog
        self.showConfirmationDialog(crypto, amount, total_cost)

    def proceed_with_purchase(self, crypto, amount):
        self.back_payment_handler.add_crypto_to_user(self.username, crypto, amount, 'crypto_purchase',
                                                     'Crypto Purchase')
        QMessageBox.information(self, 'Success', 'Purchase completed successfully.')
        self.clearFields()

    def showConfirmationDialog(self, crypto, amount, total_cost):
        confirm_msg = QMessageBox()
        confirm_msg.setIcon(QMessageBox.Question)
        confirm_msg.setWindowTitle('Confirm Purchase')
        confirm_msg.setText(f'Are you sure you want to proceed with the purchase?\n\n'
                            f'Crypto: {crypto}\nAmount: {amount}\nTotal Cost: £{total_cost:,.2f}')
        confirm_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_msg.setDefaultButton(QMessageBox.No)

        result = confirm_msg.exec_()

        if result == QMessageBox.Yes:
            self.proceed_with_purchase(crypto, amount)

    def showPaymentDetails(self):
        selected_method = self.paymentMethodComboBox.currentText()
        if selected_method.startswith("Credit Card"):
            self.paymentForms.setCurrentWidget(self.creditCardForm)
        elif selected_method.startswith("Bank Transfer"):
            self.paymentForms.setCurrentWidget(self.bankTransferForm)

        self.switchWidget(self.paymentDetailsWidget)

    def showCryptoDetails(self):
        # Clear the payment fields when navigating back
        self.clearFields()
        self.switchWidget(self.cryptoDetailsWidget)

    def switchWidget(self, widget):
        self.opacityEffect = QGraphicsOpacityEffect()
        self.stackedWidget.setGraphicsEffect(self.opacityEffect)

        self.fadeOutAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeOutAnimation.setDuration(500)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)
        self.fadeOutAnimation.finished.connect(lambda: self.showNextWidget(widget))
        self.fadeOutAnimation.start()

    def showNextWidget(self, widget):
        self.stackedWidget.setCurrentWidget(widget)
        self.fadeInAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeInAnimation.setDuration(500)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)
        self.fadeInAnimation.start()
