from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox,
    QFormLayout, QHBoxLayout, QGroupBox, QComboBox, QStackedWidget, QSizePolicy, QSpacerItem, QToolTip,
    QGraphicsOpacityEffect, QGridLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QRegExp, QPoint, QPropertyAnimation
from PyQt5.QtGui import QFont, QRegExpValidator, QIntValidator, QKeyEvent
import json
from datetime import datetime
import uuid
from pymongo import MongoClient
import logging

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['admin']
users_collection = db['users']
withdraws_collection = db['withdraws']
gbp_collection = db['gbp']  # Correct collection name for GBP balances

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


class DigitLimitValidator(QRegExpValidator):
    def __init__(self, max_digits, parent=None):
        regex = QRegExp(r"^\d{0,48}(\.\d{0,2})?$")
        super().__init__(regex, parent)
        self.max_digits = max_digits

    def validate(self, input_str, pos):
        if len(input_str.replace(".", "")) <= self.max_digits:
            return super().validate(input_str, pos)
        return QRegExpValidator.Invalid, input_str, pos


class VerificationDialog(QDialog):
    def __init__(self, stored_email):
        super().__init__()
        self.setWindowTitle("Verify Transaction")
        self.setModal(True)
        self.stored_email = stored_email
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        message = QLabel("Please Verify Transaction <br> Enter Your Email")
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)

        self.emailInput = QLineEdit()
        self.emailInput.setPlaceholderText("Enter your email")
        layout.addWidget(self.emailInput)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.verify_email)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def verify_email(self):
        if self.emailInput.text().strip().lower() == self.stored_email.lower():
            self.accept()
        else:
            QMessageBox.warning(self, "Verification Failed", "Email verification failed. Please enter the correct email.")


class WithdrawCryptoTab(QWidget):
    def __init__(self, username, back_payment_handler):
        super().__init__()
        self.username = username
        self.back_payment_handler = back_payment_handler
        self.initUI()

    def initUI(self):
        self.stackedWidget = QStackedWidget(self)
        self.initWithdrawDetailsUI()
        self.initDetailsUI()

        mainLayout = QVBoxLayout()
        title = QLabel("")
        title.setStyleSheet("font-size: 30px;")
        title.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(title)

        mainLayout.addWidget(self.stackedWidget)

        self.continueButton = QPushButton("Continue ⟶")
        self.continueButton.setEnabled(False)
        self.continueButton.setFixedSize(200, 50)
        self.continueButton.setStyleSheet("font-size: 18px;")
        self.continueButton.clicked.connect(self.showDetails)
        mainLayout.addWidget(self.continueButton, alignment=Qt.AlignCenter)

        mainLayout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(mainLayout)

    def initWithdrawDetailsUI(self):
        self.withdrawDetailsWidget = QWidget()
        layout = QGridLayout()

        containerFrame = QGroupBox("Withdraw Details")
        containerFrame.setStyleSheet("""
            QFrame {
                border-radius: 5px;
                padding: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
                min-width: 400px;
            }
            QGroupBox {
                border: 4px solid lightblue;
                padding: 25px;
                border-radius: 25px;
                max-height: 400px;
                font-size:25px;
            }
        """)

        containerLayout = QVBoxLayout()
        containerFrame.setLayout(containerLayout)

        groupBox = QGroupBox()
        groupBox.setStyleSheet("""
            QGroupBox {
                color: lightblue;
                border: none;
            }
        """)
        formLayout = QFormLayout()
        formLayout.setVerticalSpacing(15)
        groupBox.setLayout(formLayout)

        labelFont = QFont("Arial")

        amountLabel = QLabel("Choose amount of GBP")
        amountLabel.setFont(labelFont)
        amountLabel.setAlignment(Qt.AlignCenter)
        amountLabel.setStyleSheet("background-color: lightblue; color: black; font-size: 20px;")
        self.amountInput = QLineEdit()
        self.amountInput.setPlaceholderText("Enter amount to withdraw")
        self.amountInput.setValidator(QRegExpValidator(QRegExp(r'^\d{1,50}(\.\d{1,50})?$')))
        self.amountInput.setStyleSheet("padding: 10px; margin-left:12px;margin-right:12px;")
        self.amountInput.textChanged.connect(self.validateAmount)

        self.gbpBalanceLabel = QLabel()
        self.gbpBalanceLabel.setAlignment(Qt.AlignCenter)
        self.gbpBalanceLabel.setStyleSheet(
            "color: lightgreen; font-size: 16px; border: 1px solid lightgreen; border-radius: 5px; min-width:20px; margin-left:12px;margin-right:12px;")
        formLayout.addRow(amountLabel)
        formLayout.addRow(self.gbpBalanceLabel)
        formLayout.addRow(self.amountInput)

        withdrawMethodLabel = QLabel("Choose Withdraw Method")
        withdrawMethodLabel.setFont(labelFont)
        withdrawMethodLabel.setAlignment(Qt.AlignCenter)
        withdrawMethodLabel.setStyleSheet("background-color: lightblue; color: black; font-size: 20px;")
        self.withdrawMethodDropdown = QComboBox()
        self.withdrawMethodDropdown.addItems(["Bank Transfer 0% Fees", "Card Transfer 0% Fees"])
        self.withdrawMethodDropdown.setStyleSheet(
            "padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-left:12px; font-size:14px;margin-right:12px;")
        self.withdrawMethodDropdown.currentIndexChanged.connect(self.onWithdrawMethodChanged)
        formLayout.addRow(withdrawMethodLabel)
        formLayout.addRow(self.withdrawMethodDropdown)

        containerLayout.addWidget(groupBox, alignment=Qt.AlignCenter)

        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 2, 0)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 0)
        layout.addWidget(containerFrame, 1, 1, alignment=Qt.AlignCenter)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 2)

        self.withdrawDetailsWidget.setLayout(layout)
        self.stackedWidget.addWidget(self.withdrawDetailsWidget)

        self.updateGbpBalance()

    def initDetailsUI(self):
        self.detailsWidget = QWidget()
        layout = QGridLayout()

        rightContainer = QGroupBox("Details")
        rightContainer.setStyleSheet("""
            QGroupBox {
                border: 4px solid lightblue;
                border-radius: 25px;
                padding: 22px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                min-width: 530px;
                max-height: 390px;
            }
        """)

        rightLayout = QVBoxLayout()
        rightContainer.setLayout(rightLayout)

        rightLayout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.paymentForms = QStackedWidget()
        rightLayout.addWidget(self.paymentForms)

        self.cardTransferForm = self.createCardTransferForm()
        self.paymentForms.addWidget(self.cardTransferForm)

        self.bankTransferForm = self.createBankTransferForm()
        self.paymentForms.addWidget(self.bankTransferForm)

        self.paymentForms.setCurrentWidget(self.bankTransferForm)

        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), 2, 0)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 0)
        layout.addWidget(rightContainer, 1, 1, alignment=Qt.AlignCenter)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 2)

        buttonLayout = QHBoxLayout()

        self.backButton = QPushButton("⟵ Back")
        self.backButton.setFixedSize(200, 50)
        self.backButton.setStyleSheet("font-size: 18px;")
        self.backButton.clicked.connect(self.goBack)
        buttonLayout.addWidget(self.backButton)

        self.withdrawButton = QPushButton("Withdraw")
        self.withdrawButton.setFixedSize(200, 50)
        self.withdrawButton.setStyleSheet("font-size: 18px;")
        self.withdrawButton.clicked.connect(self.withdraw)
        buttonLayout.addWidget(self.withdrawButton)

        layout.addLayout(buttonLayout, 3, 1, alignment=Qt.AlignCenter)

        self.detailsWidget.setLayout(layout)
        self.stackedWidget.addWidget(self.detailsWidget)

    def createCardTransferForm(self):
        formLayout = QFormLayout()

        labelFont = QFont("Arial", 12)

        cardNumberLabel = QLabel("Card Number")
        cardNumberLabel.setFont(labelFont)
        self.cardNumberInput = QLineEdit()
        self.cardNumberInput.setPlaceholderText("1234 5678 9012 3456")
        self.cardNumberInput.setMaxLength(16)
        self.cardNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{0,16}$")))
        self.cardNumberInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        formLayout.addRow(cardNumberLabel, self.cardNumberInput)

        cardHolderNameLabel = QLabel("Cardholder")
        cardHolderNameLabel.setFont(labelFont)
        self.cardHolderNameInput = QLineEdit()
        self.cardHolderNameInput.setPlaceholderText("John Doe")
        self.cardHolderNameInput.setMaxLength(50)
        self.cardHolderNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]*$")))
        self.cardHolderNameInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        formLayout.addRow(cardHolderNameLabel, self.cardHolderNameInput)

        expirationDateLabel = QLabel("Expiration Date")
        expirationDateLabel.setFont(labelFont)
        self.expirationDateInput = QLineEdit()
        self.expirationDateInput.setPlaceholderText("MM/YY")
        self.expirationDateInput.setMaxLength(5)
        self.expirationDateInput.setValidator(QRegExpValidator(QRegExp(r"^(0[1-9]|1[0-2])\/([2-9][0-9])$")))
        self.expirationDateInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        self.expirationDateInput.textEdited.connect(self.formatExpirationDate)
        cvcLabel = QLabel("CVC")
        cvcLabel.setFont(labelFont)
        self.cvcInput = QLineEdit()
        self.cvcInput.setPlaceholderText("123")
        self.cvcInput.setMaxLength(3)
        self.cvcInput.setValidator(QRegExpValidator(QRegExp(r"^\d{3}$")))
        self.cvcInput.setStyleSheet("padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        expirationCvcLayout = QHBoxLayout()
        expirationCvcLayout.addWidget(self.expirationDateInput)
        expirationCvcLayout.addWidget(cvcLabel)
        expirationCvcLayout.addWidget(self.cvcInput)
        formLayout.addRow(expirationDateLabel, expirationCvcLayout)

        widget = QWidget()
        widget.setLayout(formLayout)
        return widget

    def createBankTransferForm(self):
        formLayout = QFormLayout()

        labelFont = QFont("Arial", 12)

        bankNameLabel = QLabel("Bank Name")
        bankNameLabel.setFont(labelFont)
        self.bankNameInput = QLineEdit()
        self.bankNameInput.setPlaceholderText("Bank Name")
        self.bankNameInput.setMaxLength(50)
        self.bankNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]*$")))
        self.bankNameInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        formLayout.addRow(bankNameLabel, self.bankNameInput)

        accountNumberLabel = QLabel("Account Number")
        accountNumberLabel.setFont(labelFont)
        self.accountNumberInput = QLineEdit()
        self.accountNumberInput.setPlaceholderText("12345678")
        self.accountNumberInput.setMaxLength(8)
        self.accountNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{0,8}$")))
        self.accountNumberInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        formLayout.addRow(accountNumberLabel, self.accountNumberInput)

        sortCodeLabel = QLabel("Sort Code")
        sortCodeLabel.setFont(labelFont)
        self.sortCodeInput = QLineEdit()
        self.sortCodeInput.setPlaceholderText("11-22-33")
        self.sortCodeInput.setValidator(
            QRegExpValidator(QRegExp(r"^\d{2}-\d{2}-\d{2}$")))
        self.sortCodeInput.setStyleSheet(
            "padding: 10px; border: none; border-bottom: 1px solid #ccc; border-radius: 0;")
        self.sortCodeInput.installEventFilter(self)
        formLayout.addRow(sortCodeLabel, self.sortCodeInput)

        widget = QWidget()
        widget.setLayout(formLayout)
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
            self.expirationDateInput.setCursorPosition(3)

    def onWithdrawMethodChanged(self, index):
        selected_method = self.withdrawMethodDropdown.currentText()
        if "Card Transfer" in selected_method:
            self.paymentForms.setCurrentWidget(self.cardTransferForm)
        else:
            self.paymentForms.setCurrentWidget(self.bankTransferForm)

    def setupValidators(self):
        self.cardNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{16}$")))
        self.expirationDateInput.setValidator(QRegExpValidator(QRegExp(r"^(0[1-9]|1[0-2])\/[2-9][0-9]$")))
        self.cvcInput.setValidator(QRegExpValidator(QRegExp(r"^\d{3}$")))
        self.cardHolderNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,50}$")))

        self.accountNumberInput.setValidator(QRegExpValidator(QRegExp(r"^\d{8}$")))
        self.sortCodeInput.setValidator(QRegExpValidator(QRegExp(r"^\d{2}-\d{2}-\d{2}$")))
        self.bankNameInput.setValidator(QRegExpValidator(QRegExp(r"^[A-Za-z\s]{1,50}$")))

    def updateGbpBalance(self):
        gbp_balance = self.get_gbp_balance(self.username)
        self.gbpBalanceLabel.setText(f"Your GBP Balance: {gbp_balance:.2f}£")

    def get_gbp_balance(self, username):
        user_balance = gbp_collection.find_one({"username": username})
        return user_balance['amount'] if user_balance else 0.0  # Changed 'balance' to 'amount'

    def validateAmount(self):
        amount_text = self.amountInput.text()
        try:
            amount = float(amount_text)
        except ValueError:
            amount = 0.0

        gbp_balance = self.get_gbp_balance(self.username)
        if amount > gbp_balance:
            self.amountInput.setStyleSheet("padding: 10px; margin-left:12px; border: 2px solid red;")
            QToolTip.showText(self.amountInput.mapToGlobal(QPoint(0, 0)), "Amount exceeds available GBP balance")
            self.continueButton.setEnabled(False)
        elif amount <= 0:
            self.amountInput.setStyleSheet("padding: 10px; margin-left:12px; border: 2px solid red;")
            QToolTip.showText(self.amountInput.mapToGlobal(QPoint(0, 0)), "Enter a valid amount greater than 0")
            self.continueButton.setEnabled(False)
        else:
            self.amountInput.setStyleSheet("padding: 10px; margin-left:12px;")
            QToolTip.hideText()
            self.continueButton.setEnabled(True)

    def onWithdrawMethodChanged(self, index):
        selected_method = self.withdrawMethodDropdown.currentText()
        if "Card Transfer" in selected_method:
            self.paymentForms.setCurrentWidget(self.cardTransferForm)
        else:
            self.paymentForms.setCurrentWidget(self.bankTransferForm)

    def showDetails(self):
        self.continueButton.hide()
        self.withdrawButton.show()
        self.backButton.show()

        self.opacityEffect = QGraphicsOpacityEffect()
        self.stackedWidget.setGraphicsEffect(self.opacityEffect)

        self.fadeOutAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeOutAnimation.setDuration(500)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)
        self.fadeOutAnimation.finished.connect(self.showNextWidget)
        self.fadeOutAnimation.start()

    def showNextWidget(self):
        self.stackedWidget.setCurrentWidget(self.detailsWidget)
        self.fadeInAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeInAnimation.setDuration(500)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)
        self.fadeInAnimation.start()

    def goBack(self):
        self.withdrawButton.hide()
        self.backButton.hide()
        self.continueButton.show()

        self.opacityEffect = QGraphicsOpacityEffect()
        self.stackedWidget.setGraphicsEffect(self.opacityEffect)

        self.fadeOutAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeOutAnimation.setDuration(500)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)
        self.fadeOutAnimation.finished.connect(self.showWithdrawDetailsWidget)
        self.fadeOutAnimation.start()

    def showWithdrawDetailsWidget(self):
        self.stackedWidget.setCurrentWidget(self.withdrawDetailsWidget)
        self.fadeInAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeInAnimation.setDuration(500)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)
        self.fadeInAnimation.start()

    def withdraw(self):
        selected_method = self.withdrawMethodDropdown.currentText()

        if "Card Transfer" in selected_method:
            card_number = self.cardNumberInput.text()
            card_holder_name = self.cardHolderNameInput.text()
            expiration_date = self.expirationDateInput.text()
            cvc = self.cvcInput.text()

            if not card_number or not card_holder_name or not expiration_date or not cvc:
                QMessageBox.warning(self, 'Incomplete Form', 'Please fill in all card details.')
                return
            if len(card_number) != 16 or not card_number.isdigit():
                QMessageBox.warning(self, 'Invalid Card Number', 'Card number must be 16 digits.')
                return
            if len(expiration_date) != 5 or not QRegExp(r"^(0[1-9]|1[0-2])\/([2-9][0-9])$").exactMatch(expiration_date):
                QMessageBox.warning(self, 'Invalid Expiration Date',
                                    'Expiration date must be in MM/YY format and valid.')
                return
            if len(cvc) != 3 or not cvc.isdigit():
                QMessageBox.warning(self, 'Invalid CVC', 'CVC must be 3 digits.')
                return

        elif "Bank Transfer" in selected_method:
            account_number = self.accountNumberInput.text()
            sort_code = self.sortCodeInput.text()
            bank_name = self.bankNameInput.text()

            if not account_number or not sort_code or not bank_name:
                QMessageBox.warning(self, 'Incomplete Form', 'Please fill in all bank details.')
                return
            if len(account_number) != 8 or not account_number.isdigit():
                QMessageBox.warning(self, 'Invalid Account Number', 'Account number must be 8 digits.')
                return
            if len(sort_code) != 8 or not QRegExp(r"^\d{2}-\d{2}-\d{2}$").exactMatch(sort_code):
                QMessageBox.warning(self, 'Invalid Sort Code', 'Sort code must be 6 digits in the format XX-XX-XX.')
                return
            if len(bank_name) > 50 or not QRegExp(r"^[A-Za-z\s]*$").exactMatch(bank_name):
                QMessageBox.warning(self, 'Invalid Bank Name', 'Bank name must be up to 50 letters.')
                return

        user_email = self.get_user_email(self.username)
        dialog = VerificationDialog(user_email)
        if dialog.exec_() == QDialog.Accepted:
            amount = float(self.amountInput.text())
            self.updateUserBalance(self.username, -amount)
            self.record_withdraw(selected_method)
            self.updateGbpBalance()
            self.clearFields()
            QMessageBox.information(self, 'Success', 'Withdrawal successful.')
        else:
            QMessageBox.information(self, 'Cancelled', 'Withdrawal cancelled.')

    def clearFields(self):
        self.amountInput.clear()
        self.withdrawMethodDropdown.setCurrentIndex(0)

        self.cardNumberInput.clear()
        self.cardHolderNameInput.clear()
        self.expirationDateInput.clear()
        self.cvcInput.clear()

        self.accountNumberInput.clear()
        self.sortCodeInput.clear()
        self.bankNameInput.clear()

    def get_user_email(self, username):
        user = users_collection.find_one({"username": username})
        return user['email'] if user else ""

    def updateUserBalance(self, username, amount):
        gbp_collection.update_one(
            {"username": username},
            {"$inc": {"amount": amount}}  # Changed 'balance' to 'amount'
        )

    def record_withdraw(self, method):
        withdraw_id = str(uuid.uuid4())
        amount = self.amountInput.text()
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        method = method.replace(" 0% Fees", "")

        withdraw_data = {
            "id": withdraw_id,
            "username": self.username,
            "date_time": date_time,
            "amount": amount,
            "method": method
        }

        withdraws_collection.insert_one(withdraw_data)
