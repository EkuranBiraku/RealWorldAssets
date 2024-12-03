# Import necessary modules and classes
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import (QFrame, QLineEdit, QMessageBox, QGroupBox, QProgressBar,
    QWidget, QVBoxLayout, QLabel, QPushButton, QTabWidget, QComboBox, QGridLayout,
    QApplication, QDesktopWidget, QListWidget, QStackedWidget, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen, QColor
import sys
import re
import uuid
from pymongo import MongoClient
from backpayment import BackPaymentHandler
from AssetsWindow import AssetsWindow
from Tabs.convert import ConvertCryptoTab
from Tabs.withdraw import WithdrawCryptoTab

class UserProfileWindow(QWidget):
    def __init__(self, mainApp, username="", email="", back_payment_handler=None):
        super().__init__()
        self.mainApp = mainApp
        self.username = username
        self.email = email
        self.back_payment_handler = back_payment_handler or BackPaymentHandler()

        self.back_payment_handler.cryptoPurchased.connect(self.updateWallet)
        self.back_payment_handler.cryptoPurchased.connect(self.populateCryptoTransactions)


        # MongoDB setup
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['admin']
        self.users_collection = self.db['users']
        self.transactions_collection = self.db['transactions']
        self.withdraws_collection = self.db['withdraws']
        self.conversions_collection = self.db['cryptoconversions']
        self.device_history_collection = self.db['device_history']
        self.assets_history_collection = self.db['asset_history']
        self.gbp_collection = self.db['gbp']
        self.ledger_collection = self.db['ledger']  # Add this line

        self.initUI()

    def initUI(self):
        self.setWindowTitle("User Profile")
        self.setFixedSize(1250, 750)
        self.center()

        mainLayout = QVBoxLayout(self)  # Main layout to hold content and footer

        contentLayout = QHBoxLayout()  # Layout to hold sidebar and contentStack

        # Sidebar Layout
        sidebarLayout = QVBoxLayout()
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setMinimumHeight(620)  # Ensure minimum height for the sidebar

        self.sidebar.addItem("Personal Info")
        self.sidebar.addItem("Security")
        self.sidebar.addItem("Art Transactions")
        self.sidebar.addItem("My Orders")


        self.sidebar.setSpacing(15)

        # Apply QSS stylesheet for sidebar
        self.sidebar.setStyleSheet("""
            QListWidget::item:hover {
                background-color: lightblue;
                color:black;
                border-radius:25px;
            }
            QListWidget::item:selected {
                background-color: lightblue;
                color: black;
                border-radius:25px;
            }
            QListWidget::item:selected:active {
                background-color: lightblue;
                color: black;
                border-radius:25px;
            }
        """)

        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            item.setSizeHint(QSize(100, 120))

        sidebarLayout.addWidget(self.sidebar)
        sidebarLayout.addStretch(1)  # Add stretchable space to push content up

        # Main Content (Stacked Widget)
        self.contentStack = QStackedWidget()
        contentLayout.addLayout(sidebarLayout)
        contentLayout.addWidget(self.contentStack)

        mainLayout.addLayout(contentLayout)  # Add content layout to the main layout

        self.setupPersonalInfo()
        self.setupSecurity()
        self.setupTransactionHistory()

        self.sidebar.currentRowChanged.connect(self.displaySection)

        # Add a horizontal line to visually separate the footer
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: white; background-color: white;")
        line.setFixedHeight(5)  # Set the height of the line

        mainLayout.addWidget(line)  # Add the horizontal line above the footer

        footerLayout = QHBoxLayout()
        footerLayout.setContentsMargins(640, 10, 0, 0)  # Add left margin to move the button to the right

        logoutButton = QPushButton("Log Out")
        logoutButton.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: red;
                color: white;
            }
        """)
        logoutButton.setFixedSize(150, 60)
        logoutButton.clicked.connect(self.logOut)

        footerLayout.addWidget(logoutButton, alignment=Qt.AlignLeft)  # Keep the button aligned left within the margins
        footerLayout.addStretch(1)

        mainLayout.addLayout(footerLayout)  # Add footer layout to the main layout

        self.setLayout(mainLayout)

    def setupPersonalInfo(self):
        personalInfo = QWidget()
        mainLayout = QVBoxLayout(personalInfo)
        mainLayout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Align content at the top center
        mainLayout.setSpacing(20)  # Adjust spacing as needed

        # Top section with image, user name, and email
        topSection = QHBoxLayout()

        # Profile image on the left
        imageLabel = QLabel()
        pixmap = QPixmap("profile.png").scaledToWidth(100)
        radius = 50

        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(pixmap))
        painter.setPen(QPen(Qt.transparent))
        painter.drawRoundedRect(pixmap.rect(), radius, radius)
        painter.end()
        imageLabel.setPixmap(rounded)
        imageLabel.setContentsMargins(180, 0, 0, 0)  # Left, top, right, bottom margins

        # Username and email on the right of the image
        userInfoLayout = QVBoxLayout()
        usernameLabel = QLabel(self.username)
        emailLabel = QLabel(self.email)

        usernameLabel.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        emailLabel.setStyleSheet("font-size: 14px; color: lightgray;")

        userInfoLayout.addWidget(usernameLabel)
        userInfoLayout.addWidget(emailLabel)
        userInfoLayout.setSpacing(5)

        userInfoLayout.setContentsMargins(0, 0, 200, 0)  # Left, top, right, bottom margins

        topSection.addWidget(imageLabel, alignment=Qt.AlignLeft)
        topSection.addLayout(userInfoLayout)

        mainLayout.addLayout(topSection)
        # Add a horizontal line to separate the username/email from the Total GBP card
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: white; background-color: white;")
        line.setFixedHeight(2)  # Set the height of the line
        mainLayout.addWidget(line)  # Add the line to the main layout

        # Initialize totalGbpDisplay before using it
        self.totalGbpDisplay = QLabel("0.00")
        self.totalGbpDisplay.setAlignment(Qt.AlignCenter)
        self.totalGbpDisplay.setStyleSheet("""
            QLabel {
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                min-width: 100px;
                color: lightgreen;
            }
        """)

        # Main layout for Total GBP, My Wallet, and My Assets
        totalGbpCard = self.createCard("Total GBP", "Withdraw GBP", self.totalGbpDisplay, self.openWithdrawWindow)

        # Wallet and Assets Layout (side by side)
        bottomCardsLayout = QHBoxLayout()
        bottomCardsLayout.setSpacing(20)

        # My Wallet Section (Card 1)
        walletCard = self.createWalletCard()
        bottomCardsLayout.addWidget(walletCard)

        # My Assets Section (Card 2)
        assetsCard = self.createCard("My Assets", "View My Assets", None, self.viewAssets)
        bottomCardsLayout.addWidget(assetsCard)

        # Add Total GBP card in the middle of the main layout
        mainLayout.addWidget(totalGbpCard, alignment=Qt.AlignCenter)

        # Add My Wallet and My Assets cards side by side below Total GBP
        mainLayout.addLayout(bottomCardsLayout)

        # Add to content stack
        self.contentStack.addWidget(personalInfo)

        # Set the Total GBP value
        self.totalGbpDisplay.setText(f"{self.get_user_gbp():,.2f}£")

    # Helper method to create standard cards
    def createCard(self, title, buttonText, displayWidget=None, buttonCallback=None):
        card = QFrame()
        card.setStyleSheet("border:2px solid lightblue; border-radius: 15px; padding: 10px;")
        card.setFixedSize(300, 200)  # Same size for all cards
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet("color: lightgreen; font-size: 16px;background-color: lightblue;color:black;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        if displayWidget:
            layout.addWidget(displayWidget, alignment=Qt.AlignCenter)

        button = QPushButton(buttonText)
        button.clicked.connect(buttonCallback)
        button.setFixedWidth(150)
        layout.addWidget(button, alignment=Qt.AlignCenter)

        return card

    # Special method for creating the Wallet card (since it has additional widgets)
    def createWalletCard(self):
        walletCard = QFrame()
        walletCard.setStyleSheet("border:2px solid lightblue; border-radius: 15px; padding: 10px;")
        walletCard.setFixedSize(300, 200)
        layout = QVBoxLayout(walletCard)
        label = QLabel("My Wallet")
        label.setStyleSheet("color: lightgreen; font-size: 16px;background-color: lightblue;color:black;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.walletDropdown = QComboBox()
        self.walletDropdown.setStyleSheet("border:1px solid #ccc; background-color: #555;")
        self.walletDropdown.setFixedWidth(200)
        layout.addWidget(self.walletDropdown, alignment=Qt.AlignCenter)

        convertButton = QPushButton("Convert Crypto")
        convertButton.clicked.connect(self.openConvertWindow)
        convertButton.setFixedWidth(150)
        layout.addWidget(convertButton, alignment=Qt.AlignCenter)

        return walletCard

    def logOut(self):
        QApplication.exit(123)

    def populateWalletDropdown(self):
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        self.walletDropdown.clear()
        for crypto, amount in holdings.items():
            # Exclude _id and username from the dropdown items
            if crypto.lower() not in ["_id", "username"]:
                self.walletDropdown.addItem(f"{crypto.upper()}: {amount}")
        self.walletDropdown.repaint()

    def setupSecurity(self):
        security = QWidget()
        securityLayout = QVBoxLayout()

        self.securityTabWidget = QTabWidget()

        self.securityTabWidget.setStyleSheet("""
               QTabBar::tab {
                   padding: 10px;
                   margin-left: 130px;
               }
           """)

        # Change Password Tab
        changePasswordTab = QWidget()
        changePasswordLayout = QVBoxLayout()

        groupBox = QGroupBox("")
        groupBox.setFixedWidth(600)  # Adjust the width as needed

        groupBoxLayout = QFormLayout()
        groupBoxLayout.setVerticalSpacing(30)

        currentPasswordLabel = QLabel("Current Password")
        self.currentPasswordInput = QLineEdit()
        self.currentPasswordInput.setEchoMode(QLineEdit.Password)
        self.currentPasswordInput.textChanged.connect(self.verifyCurrentPassword)
        self.currentPasswordInput.setToolTip("Enter your current password.")

        self.currentPasswordStatusLabel = QLabel("")
        self.currentPasswordStatusLabel.setStyleSheet("color: lightgreen; font-size: 14px;")  # Smaller text

        newPasswordLabel = QLabel("New Password")
        self.newPasswordInput = QLineEdit()
        self.newPasswordInput.setEchoMode(QLineEdit.Password)
        self.newPasswordInput.textChanged.connect(self.checkPasswordStrength)
        self.newPasswordInput.setToolTip(
            "Enter a new password (at least 8 characters, one capital letter, one special character).")

        confirmNewPasswordLabel = QLabel("Confirm New Password")
        self.confirmNewPasswordInput = QLineEdit()
        self.confirmNewPasswordInput.setEchoMode(QLineEdit.Password)
        self.confirmNewPasswordInput.textChanged.connect(self.checkPasswordStrength)
        self.confirmNewPasswordInput.setToolTip("Re-enter your new password.")

        self.passwordMatchStatusLabel = QLabel("")
        self.passwordMatchStatusLabel.setStyleSheet("color: red; font-size: 14px;")  # Smaller text

        self.newPasswordErrorLabel = QLabel("")
        self.newPasswordErrorLabel.setStyleSheet("color: red; font-size: 14px;")

        # Password Strength Indicator
        self.passwordStrengthLabel = QLabel("")
        self.passwordStrengthLabel.setStyleSheet("font-size: 16px;")  # Smaller text
        self.passwordStrengthBar = QProgressBar()
        self.passwordStrengthBar.setRange(0, 100)
        self.passwordStrengthBar.setTextVisible(False)
        self.passwordStrengthBar.setFixedHeight(10)  # Smaller height

        groupBoxLayout.addRow(currentPasswordLabel, self.currentPasswordInput)
        groupBoxLayout.addRow("", self.currentPasswordStatusLabel)
        groupBoxLayout.addRow(newPasswordLabel, self.newPasswordInput)
        groupBoxLayout.addRow(confirmNewPasswordLabel, self.confirmNewPasswordInput)
        groupBoxLayout.addRow("", self.passwordMatchStatusLabel)
        groupBoxLayout.addRow(self.passwordStrengthLabel, self.passwordStrengthBar)
        groupBoxLayout.addRow("", self.newPasswordErrorLabel)

        groupBox.setLayout(groupBoxLayout)
        changePasswordLayout.addWidget(groupBox, alignment=Qt.AlignCenter)

        # Centered Change Password Button
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        self.changePasswordButton = QPushButton("Change Password")
        self.changePasswordButton.clicked.connect(self.changePassword)
        self.changePasswordButton.setFixedWidth(150)
        self.changePasswordButton.setEnabled(True)  # Initially enabled
        buttonLayout.addWidget(self.changePasswordButton, alignment=Qt.AlignCenter)
        buttonLayout.addStretch(1)

        changePasswordLayout.addLayout(buttonLayout)
        changePasswordTab.setLayout(changePasswordLayout)

        # Change Email Tab
        changeEmailTab = QWidget()
        changeEmailLayout = QVBoxLayout()

        emailGroupBox = QGroupBox("")
        emailGroupBox.setFixedWidth(600)  # Adjust the width as needed
        emailGroupBoxLayout = QFormLayout()
        emailGroupBoxLayout.setVerticalSpacing(30)

        currentEmailLabel = QLabel("Current Email:")
        self.currentEmailInput = QLineEdit()
        self.currentEmailInput.setToolTip("Enter your current email address.")
        self.currentEmailInput.textChanged.connect(self.verifyCurrentEmail)

        self.currentEmailStatusLabel = QLabel("")
        self.currentEmailStatusLabel.setStyleSheet("color: lightgreen; font-size: 14px;")  # Smaller text

        newEmailLabel = QLabel("New Email:")
        self.newEmailInput = QLineEdit()
        self.newEmailInput.textChanged.connect(self.checkEmailValidity)
        self.newEmailInput.setToolTip("Enter your new email address.")

        confirmNewEmailLabel = QLabel("Confirm New Email:")
        self.confirmNewEmailInput = QLineEdit()
        self.confirmNewEmailInput.textChanged.connect(self.checkEmailValidity)
        self.confirmNewEmailInput.setToolTip("Re-enter your new email address.")

        self.emailMatchStatusLabel = QLabel("")
        self.emailMatchStatusLabel.setStyleSheet("color: red; font-size: 14px;")  # Smaller text

        emailGroupBoxLayout.addRow(currentEmailLabel, self.currentEmailInput)
        emailGroupBoxLayout.addRow("", self.currentEmailStatusLabel)
        emailGroupBoxLayout.addRow(newEmailLabel, self.newEmailInput)
        emailGroupBoxLayout.addRow(confirmNewEmailLabel, self.confirmNewEmailInput)
        emailGroupBoxLayout.addRow("", self.emailMatchStatusLabel)

        emailGroupBox.setLayout(emailGroupBoxLayout)
        changeEmailLayout.addWidget(emailGroupBox, alignment=Qt.AlignCenter)

        # Centered Change Email Button
        buttonEmailLayout = QHBoxLayout()
        buttonEmailLayout.addStretch(1)
        self.changeEmailButton = QPushButton("Change Email")
        self.changeEmailButton.clicked.connect(self.changeEmail)
        self.changeEmailButton.setFixedWidth(150)
        buttonEmailLayout.addWidget(self.changeEmailButton, alignment=Qt.AlignCenter)
        buttonEmailLayout.addStretch(1)

        changeEmailLayout.addLayout(buttonEmailLayout)
        changeEmailTab.setLayout(changeEmailLayout)

        # Device History Tab
        deviceHistoryTab = QWidget()
        deviceHistoryLayout = QVBoxLayout()

        self.deviceHistoryTable = QTableWidget(0, 3)
        self.deviceHistoryTable.setHorizontalHeaderLabels(['Date & Time', 'Device', 'Location'])
        self.deviceHistoryTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.deviceHistoryTable.verticalHeader().hide()
        self.deviceHistoryTable.setEditTriggers(QTableWidget.NoEditTriggers)

        deviceHistoryLayout.addWidget(self.deviceHistoryTable)
        deviceHistoryTab.setLayout(deviceHistoryLayout)
        self.securityTabWidget.addTab(deviceHistoryTab, "Device History")

        self.populateDeviceHistory()

        # Add tabs to the QTabWidget
        self.securityTabWidget.addTab(changePasswordTab, "Change Password")
        self.securityTabWidget.addTab(changeEmailTab, "Change Email")
        self.securityTabWidget.addTab(deviceHistoryTab, "Device History")

        securityLayout.addWidget(self.securityTabWidget)
        security.setLayout(securityLayout)
        self.contentStack.addWidget(security)

    def populateDeviceHistory(self):
        user_device_history = list(self.device_history_collection.find({"username": self.username}))

        self.deviceHistoryTable.setRowCount(len(user_device_history))
        for row, entry in enumerate(user_device_history):
            datetime_item = QTableWidgetItem(entry['timestamp'])
            device_item = QTableWidgetItem(entry['device'])
            location_item = QTableWidgetItem(entry['location'])

            self.deviceHistoryTable.setItem(row, 0, datetime_item)
            self.deviceHistoryTable.setItem(row, 1, device_item)
            self.deviceHistoryTable.setItem(row, 2, location_item)

        self.deviceHistoryTable.resizeColumnsToContents()

    def verifyCurrentEmail(self):
        current_email = self.currentEmailInput.text()
        if current_email == self.email:
            self.currentEmailStatusLabel.setText("Correct Email")
            self.currentEmailStatusLabel.setStyleSheet("color: lightgreen; font-size: 14px;")
        else:
            self.currentEmailStatusLabel.setText("Incorrect Email")
            self.currentEmailStatusLabel.setStyleSheet("color: red; font-size: 14px;")

    def checkEmailValidity(self):
        new_email = self.newEmailInput.text()
        confirm_email = self.confirmNewEmailInput.text()

        if new_email != confirm_email:
            self.emailMatchStatusLabel.setText("Emails do not match")
            self.emailMatchStatusLabel.setStyleSheet("color: red; font-size: 14px;")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            self.emailMatchStatusLabel.setText("Invalid email format")
            self.emailMatchStatusLabel.setStyleSheet("color: red; font-size: 14px;")
        elif new_email == self.email:
            self.emailMatchStatusLabel.setText("New email cannot be the same as the current email")
            self.emailMatchStatusLabel.setStyleSheet("color: red; font-size: 14px;")
        else:
            self.emailMatchStatusLabel.setText("")
            self.emailMatchStatusLabel.setStyleSheet("")

    def changeEmail(self):
        current_email = self.currentEmailInput.text()
        new_email = self.newEmailInput.text()
        confirm_new_email = self.confirmNewEmailInput.text()

        if current_email != self.email:
            QMessageBox.warning(self, 'Error', 'Current email is incorrect.')
            return

        if new_email != confirm_new_email:
            QMessageBox.warning(self, 'Error', 'New emails do not match.')
            return

        if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            QMessageBox.warning(self, 'Error', 'Invalid email format.')
            return

        if new_email == self.email:
            QMessageBox.warning(self, 'Error', 'New email cannot be the same as the current email.')
            return

        confirm_msg = QMessageBox()
        confirm_msg.setIcon(QMessageBox.Question)
        confirm_msg.setWindowTitle("Confirm E-mail Change")
        confirm_msg.setText("Please Confirm E-mail Change")
        confirm_msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm_msg.setDefaultButton(QMessageBox.Ok)
        result = confirm_msg.exec_()

        if result == QMessageBox.Ok:
            self.users_collection.update_one(
                {"username": self.username},
                {"$set": {"email": new_email}}
            )
            QMessageBox.information(self, 'Success', 'Email changed successfully.')
        else:
            pass

    def verifyCurrentPassword(self):
        current_password = self.currentPasswordInput.text()
        if self.authenticate_user(self.username, current_password):
            self.currentPasswordStatusLabel.setText("Correct Password")
            self.currentPasswordStatusLabel.setStyleSheet("color: lightgreen; font-size: 14px;")
        else:
            self.currentPasswordStatusLabel.setText("Incorrect Password")
            self.currentPasswordStatusLabel.setStyleSheet("color: red; font-size: 14px;")

        self.checkFormValidity()

    def checkPasswordStrength(self):
        password = self.newPasswordInput.text()
        strength = self.calculatePasswordStrength(password)
        self.passwordStrengthBar.setValue(strength)

        if strength < 50:
            self.passwordStrengthLabel.setText("Password strength: Weak")
            self.passwordStrengthLabel.setStyleSheet("color: red; font-size: 14px;")
        elif strength < 75:
            self.passwordStrengthLabel.setText("Password strength: Moderate")
            self.passwordStrengthLabel.setStyleSheet("color: orange; font-size: 14px;")
        else:
            self.passwordStrengthLabel.setText("Password strength: Strong")
            self.passwordStrengthLabel.setStyleSheet("color: green; font-size: 14px;")

        self.checkPasswordMatch()
        self.checkFormValidity()

    def checkPasswordMatch(self):
        new_password = self.newPasswordInput.text()
        confirm_password = self.confirmNewPasswordInput.text()
        if new_password != confirm_password:
            self.passwordMatchStatusLabel.setText("Passwords do not match")
        else:
            self.passwordMatchStatusLabel.setText("")

    def checkFormValidity(self):
        is_current_password_correct = self.currentPasswordStatusLabel.text() == "Correct Password"
        new_password = self.newPasswordInput.text()
        is_passwords_matching = new_password == self.confirmNewPasswordInput.text()
        is_password_valid = self.isPasswordValid(new_password)
        is_password_strength_sufficient = self.passwordStrengthBar.value() >= 50
        are_fields_filled = all([self.currentPasswordInput.text(), self.newPasswordInput.text(), self.confirmNewPasswordInput.text()])
        is_new_password_different = new_password != self.currentPasswordInput.text()

        if not is_new_password_different:
            self.newPasswordErrorLabel.setText("Can not use the same password")
        else:
            self.newPasswordErrorLabel.setText("")

    def isPasswordValid(self, password):
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[^\w\s]|[.]', password):  # Includes "." as a special character
            return False
        return True

    def calculatePasswordStrength(self, password):
        length = len(password)
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[^\w\s.]', password))  # Includes "." as a special character

        strength = length * 10
        strength += 10 if has_upper else 0
        strength += 10 if has_lower else 0
        strength += 10 if has_digit else 0
        strength += 10 if has_special else 0

        return min(strength, 100)

    def changePassword(self):
        current_password = self.currentPasswordInput.text()
        new_password = self.newPasswordInput.text()
        confirm_new_password = self.confirmNewPasswordInput.text()

        if self.currentPasswordStatusLabel.text() == "Incorrect Password":
            QMessageBox.warning(self, 'Error', 'Current password is incorrect.')
            return

        if new_password == current_password:
            QMessageBox.warning(self, 'Error', 'New password cannot be the same as the current password.')
            return

        if new_password != confirm_new_password:
            QMessageBox.warning(self, 'Error', 'New passwords do not match.')
            return

        if not self.isPasswordValid(new_password):
            QMessageBox.warning(self, 'Error', 'New password does not meet the requirements.')
            return

        self.users_collection.update_one(
            {"username": self.username},
            {"$set": {"password": new_password}}
        )
        QMessageBox.information(self, 'Success', 'Password changed successfully.')

    def authenticate_user(self, username, password):
        user = self.users_collection.find_one({"username": username, "password": password})
        return user is not None

    def setupTransactionHistory(self):
        transactionHistory = QWidget()
        layout = QVBoxLayout()

        self.tabWidget = QTabWidget()

        # Add spacing between the tabs
        self.tabWidget.setStyleSheet("""
            QTabBar::tab {
                padding: 10px;
                margin-left: 10px;
            }
        """)

        self.cryptoTransactionsTab = QWidget()
        self.assetTransactionsTab = QWidget()
        self.assetCreatedDeletedTab = QWidget()
        self.conversionsHistoryTab = QWidget()  # Add Conversions History Tab
        self.withdrawHistoryTab = QWidget()  # Add Withdraw History Tab

        self.tabWidget.addTab(self.cryptoTransactionsTab, "Crypto Transactions")
        self.tabWidget.addTab(self.assetCreatedDeletedTab, "Asset Created")
        self.tabWidget.addTab(self.conversionsHistoryTab, "Conversions History")  # Add Tab to the Tab Widget
        self.tabWidget.addTab(self.withdrawHistoryTab, "Withdraw History")  # Add Withdraw History Tab

        self.setupCryptoTransactionsTab()
        self.setupAssetCreatedDeletedTab()
        self.setupConversionsHistoryTab()  # Setup Conversions History Tab
        self.setupWithdrawHistoryTab()  # Setup Withdraw History Tab

        layout.addWidget(self.tabWidget)
        transactionHistory.setLayout(layout)
        self.contentStack.addWidget(transactionHistory)

    def setupWithdrawHistoryTab(self):
        layout = QVBoxLayout()

        self.withdrawHistoryTable = QTableWidget(0, 4)  # Adjusted for columns
        self.withdrawHistoryTable.setHorizontalHeaderLabels(['ID', 'Date', 'Amount', 'Method'])
        self.withdrawHistoryTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.withdrawHistoryTable.verticalHeader().hide()
        self.withdrawHistoryTable.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.withdrawHistoryTable)
        self.withdrawHistoryTab.setLayout(layout)
        self.populateWithdrawHistory()

    def setupConversionsHistoryTab(self):
        layout = QVBoxLayout()

        self.conversionsHistoryTable = QTableWidget(0, 6)  # Adjusted for columns
        self.conversionsHistoryTable.setHorizontalHeaderLabels(['ID', 'Date', 'Crypto', 'Amount', 'GBP Amount', 'Fee'])
        self.conversionsHistoryTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.conversionsHistoryTable.verticalHeader().hide()
        self.conversionsHistoryTable.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.conversionsHistoryTable)
        self.conversionsHistoryTab.setLayout(layout)
        self.populateConversionsHistory()

    def populateWithdrawHistory(self):
        user_withdraws = list(self.withdraws_collection.find({"username": self.username}))

        self.withdrawHistoryTable.setRowCount(len(user_withdraws))
        for row, withdraw in enumerate(user_withdraws):
            id_item = QTableWidgetItem(withdraw['id'])
            datetime_item = QTableWidgetItem(withdraw['date_time'])
            amount_item = QTableWidgetItem(f"{float(withdraw['amount']):.2f} GBP")
            method_item = QTableWidgetItem(withdraw['method'])

            # Center align the items
            id_item.setTextAlignment(Qt.AlignCenter)
            datetime_item.setTextAlignment(Qt.AlignCenter)
            amount_item.setTextAlignment(Qt.AlignCenter)
            method_item.setTextAlignment(Qt.AlignCenter)

            # Set alternating column colors
            color1 = QColor('#3b5998')  # Dark blue
            color2 = QColor('#2e8b57')  # Dark green

            id_item.setBackground(color1)
            datetime_item.setBackground(color2)
            amount_item.setBackground(color1)
            method_item.setBackground(color2)

            self.withdrawHistoryTable.setItem(row, 0, id_item)
            self.withdrawHistoryTable.setItem(row, 1, datetime_item)
            self.withdrawHistoryTable.setItem(row, 2, amount_item)
            self.withdrawHistoryTable.setItem(row, 3, method_item)

        self.withdrawHistoryTable.resizeColumnToContents(0)
        self.withdrawHistoryTable.setColumnHidden(0, True)  # Hide the ID column

    def populateConversionsHistory(self):
        user_conversions = list(self.conversions_collection.find({"username": self.username}))

        self.conversionsHistoryTable.setRowCount(len(user_conversions))
        for row, conversion in enumerate(user_conversions):
            id_item = QTableWidgetItem(conversion['id'])
            datetime_item = QTableWidgetItem(conversion['datetime'])
            crypto_item = QTableWidgetItem(conversion['crypto'])
            amount_item = QTableWidgetItem(f"{conversion['amount']:.2f}")
            gbp_amount_item = QTableWidgetItem(f"{conversion['gbp_amount']:.2f} GBP")
            fee_item = QTableWidgetItem(f"{conversion['fee']:.2f} USDT")
            fee_item.setForeground(QColor('#5c0303'))

            # Center align the items
            id_item.setTextAlignment(Qt.AlignCenter)
            datetime_item.setTextAlignment(Qt.AlignCenter)
            crypto_item.setTextAlignment(Qt.AlignCenter)
            amount_item.setTextAlignment(Qt.AlignCenter)
            gbp_amount_item.setTextAlignment(Qt.AlignCenter)
            fee_item.setTextAlignment(Qt.AlignCenter)

            # Set alternating column colors
            color1 = QColor('#3b5998')  # Dark blue
            color2 = QColor('#2e8b57')  # Dark green

            id_item.setBackground(color1)
            datetime_item.setBackground(color2)
            crypto_item.setBackground(color1)
            amount_item.setBackground(color2)
            gbp_amount_item.setBackground(color1)
            fee_item.setBackground(color2)

            self.conversionsHistoryTable.setItem(row, 0, id_item)
            self.conversionsHistoryTable.setItem(row, 1, datetime_item)
            self.conversionsHistoryTable.setItem(row, 2, crypto_item)
            self.conversionsHistoryTable.setItem(row, 3, amount_item)
            self.conversionsHistoryTable.setItem(row, 4, gbp_amount_item)
            self.conversionsHistoryTable.setItem(row, 5, fee_item)

        self.conversionsHistoryTable.resizeColumnToContents(0)
        self.conversionsHistoryTable.setColumnHidden(0, True)  # Hide the ID column

    def setupCryptoTransactionsTab(self):
        layout = QVBoxLayout()

        self.cryptoTransactionsTable = QTableWidget(0, 6)  # Adjusted for columns
        self.cryptoTransactionsTable.setHorizontalHeaderLabels(['Date', 'Crypto', 'Amount', 'Price', 'Fee', 'Type'])
        self.cryptoTransactionsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cryptoTransactionsTable.verticalHeader().hide()
        self.cryptoTransactionsTable.setEditTriggers(QTableWidget.NoEditTriggers)

        self.cryptoTransactionsTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cryptoTransactionsTable.horizontalHeader().setStretchLastSection(False)

        layout.addWidget(self.cryptoTransactionsTable)
        self.cryptoTransactionsTab.setLayout(layout)
        self.populateCryptoTransactions()

    def populateCryptoTransactions(self):
        transaction_type_mapping = {
            'create_asset': 'Asset Creation',
            'crypto_purchase': 'Crypto Purchase',
            'asset_buy': 'Acquired Asset',
            'withdraw': 'Withdraw',
            'asset_sell': 'Sold Asset'
        }

        # Fetch transactions from the transaction_history collection
        user_transactions = list(self.db['transaction_history'].find({"username": self.username}))

        self.cryptoTransactionsTable.setRowCount(len(user_transactions))
        for row, transaction in enumerate(user_transactions):
            datetime_item = QTableWidgetItem(transaction.get('datetime', ''))
            crypto_item = QTableWidgetItem(transaction.get('crypto', ''))

            amount = transaction.get('amount', 0)
            amount_item = QTableWidgetItem(f"{amount:.2f}")

            if transaction.get('type') in ['crypto_purchase', 'asset_sell']:
                color = QColor('lightgreen')
                amount_item.setText(f"+{amount:.2f}")
            else:
                color = QColor('#5c0303')
                amount_item.setText(f"{amount:.2f}")

            amount_item.setForeground(color)

            # Center align the items
            datetime_item.setTextAlignment(Qt.AlignCenter)
            crypto_item.setTextAlignment(Qt.AlignCenter)
            amount_item.setTextAlignment(Qt.AlignCenter)

            # Handle NoneType for price
            price = transaction.get('price', 0.00)
            price_item = QTableWidgetItem(f"{price:.2f}")
            price_item.setTextAlignment(Qt.AlignCenter)

            fee_item = QTableWidgetItem(f"{transaction.get('fee', 0.00):.2f} USDT")
            fee_item.setForeground(QColor('#5c0303'))  # Make the fee red
            fee_item.setTextAlignment(Qt.AlignCenter)

            type_description = transaction_type_mapping.get(transaction.get('type'), transaction.get('type', 'Unknown'))
            type_item = QTableWidgetItem(type_description)
            type_item.setTextAlignment(Qt.AlignCenter)

            # Set alternating column colors
            color1 = QColor('#3b5998')  # Dark blue
            color2 = QColor('#2e8b57')  # Dark green

            datetime_item.setBackground(color1)
            crypto_item.setBackground(color2)
            amount_item.setBackground(color1)
            price_item.setBackground(color2)
            fee_item.setBackground(color1)
            type_item.setBackground(color2)

            self.cryptoTransactionsTable.setItem(row, 0, datetime_item)
            self.cryptoTransactionsTable.setItem(row, 1, crypto_item)
            self.cryptoTransactionsTable.setItem(row, 2, amount_item)
            self.cryptoTransactionsTable.setItem(row, 3, price_item)
            self.cryptoTransactionsTable.setItem(row, 4, fee_item)
            self.cryptoTransactionsTable.setItem(row, 5, type_item)

        self.cryptoTransactionsTable.resizeColumnToContents(0)




    def setupAssetCreatedDeletedTab(self):
        layout = QVBoxLayout()

        self.assetCreatedDeletedTable = QTableWidget(0, 7)  # Adjusted for columns
        self.assetCreatedDeletedTable.setHorizontalHeaderLabels(
            ['Date', 'Asset Name', 'Asset ID', 'Owner', 'Public Key', 'Signature', 'Fee'])
        self.assetCreatedDeletedTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.assetCreatedDeletedTable.verticalHeader().hide()
        self.assetCreatedDeletedTable.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.assetCreatedDeletedTable)
        self.assetCreatedDeletedTab.setLayout(layout)
        self.populateAssetCreatedDeleted()

    def extract_key_part(self, public_key):
        match = re.search(r"-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----", public_key, re.DOTALL)
        if match:
            extracted_key = match.group(1).strip().replace("\n", "")
            specific_part = extracted_key[-8:]  # Extract the last 8 characters or adjust as needed
            return specific_part
        return ""


    def populateAssetCreatedDeleted(self):
        user_assets = list(self.ledger_collection.find({"owner": self.username}))

        self.assetCreatedDeletedTable.setRowCount(len(user_assets))
        for row, asset in enumerate(user_assets):
            timestamp_item = QTableWidgetItem(asset.get('timestamp', ''))
            asset_item = QTableWidgetItem(asset.get('asset', ''))
            token_id_item = QTableWidgetItem(str(asset.get('id', '')))
            owner_item = QTableWidgetItem(asset.get('owner', ''))
            public_key_item = QTableWidgetItem(self.extract_key_part(asset.get('owner_public_key', '')))
            signature_item = QTableWidgetItem(asset.get('signature', ''))
            fee_item = QTableWidgetItem(f"{asset.get('fee', 0):.2f} USDT")
            fee_item.setForeground(QColor('#5c0303'))  # Make the fee red

            # Center align the items
            timestamp_item.setTextAlignment(Qt.AlignCenter)
            asset_item.setTextAlignment(Qt.AlignCenter)
            token_id_item.setTextAlignment(Qt.AlignCenter)
            owner_item.setTextAlignment(Qt.AlignCenter)
            public_key_item.setTextAlignment(Qt.AlignCenter)
            signature_item.setTextAlignment(Qt.AlignCenter)
            fee_item.setTextAlignment(Qt.AlignCenter)

            # Set alternating column colors
            color1 = QColor('#3b5998')  # Dark blue
            color2 = QColor('#2e8b57')  # Dark green

            timestamp_item.setBackground(color1)
            asset_item.setBackground(color2)
            token_id_item.setBackground(color1)
            owner_item.setBackground(color2)
            public_key_item.setBackground(color1)
            signature_item.setBackground(color2)
            fee_item.setBackground(color1)

            self.assetCreatedDeletedTable.setItem(row, 0, timestamp_item)
            self.assetCreatedDeletedTable.setItem(row, 1, asset_item)
            self.assetCreatedDeletedTable.setItem(row, 2, token_id_item)
            self.assetCreatedDeletedTable.setItem(row, 3, owner_item)
            self.assetCreatedDeletedTable.setItem(row, 4, public_key_item)
            self.assetCreatedDeletedTable.setItem(row, 5, signature_item)
            self.assetCreatedDeletedTable.setItem(row, 6, fee_item)

        self.assetCreatedDeletedTable.resizeColumnToContents(0)
        self.assetCreatedDeletedTable.setColumnHidden(2, True)  # Hide the Asset ID column
        self.assetCreatedDeletedTable.setColumnHidden(3, True)  # Hide the Owner column

    def displaySection(self, index):
        self.contentStack.setCurrentIndex(index)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def viewAssets(self):
        self.assetsWindow = AssetsWindow(self.username)
        self.mainApp.connectAssetDeletedSignal(self.assetsWindow)  # Connect the assetDeleted signal
        self.assetsWindow.assetUpdated.connect(self.mainApp.refreshDisplayTokensTab)  # Connect assetUpdated signal

        self.assetsWindow.show()

    def updateWallet(self):
        self.populateWalletDropdown()

    def showEvent(self, event):
        super().showEvent(event)
        self.updateWallet()
        self.totalGbpDisplay.setText(f"{self.get_user_gbp():,}£")  # Refresh GBP amount

    def get_user_gbp(self):
        user_gbp = self.gbp_collection.find_one({"username": self.username})
        return user_gbp.get("amount", 0) if user_gbp else 0

    def openConvertWindow(self):
        """Open the Convert Crypto window as a standalone window."""
        self.convertWindow = ConvertCryptoTab(self.username, self.back_payment_handler)
        self.convertWindow.show()

    def openWithdrawWindow(self):
        """Open the Withdraw GBP window as a standalone window."""
        self.withdrawWindow = WithdrawCryptoTab(self.username, self.back_payment_handler)
        self.withdrawWindow.show()


if __name__ == '__main__':
    app = QApplication([])
    userProfileWindow = UserProfileWindow(None, "testuser", "testuser@example.com")
    userProfileWindow.show()
    sys.exit(app.exec_())
