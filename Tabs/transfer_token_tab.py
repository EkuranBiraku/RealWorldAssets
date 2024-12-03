import logging

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QGroupBox, QHBoxLayout,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsOpacityEffect,
                             QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon
from pymongo import MongoClient

from Tabs.payment import PaymentTab
from backpayment import BackPaymentHandler
import re

from token_system import transfer_token


class TransferTokenTab(QWidget):
    assetTransferred = pyqtSignal()

    def __init__(self, username=None, back_payment_handler=None):
        super().__init__()
        self.username = username
        self.back_payment_handler = back_payment_handler or BackPaymentHandler()

        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']
        self.users_collection = self.db['users']

        self.main_layout = QVBoxLayout(self)
        self.token_selection_widget = None
        self.transfer_details_widget = None

        self.createTokenSelectionGroup()
        self.createTransferDetailsGroup()

        self.showTokenSelection()

    def checkCryptoBalance(self):
        # Determine the selected network and corresponding currency
        selected_network = self.networkComboBox.currentText()
        if "Bitcoin" in selected_network:
            currency = 'bitcoin'
            required_balance = 0.0001  # Required BTC balance for transfer
        elif "Ethereum" in selected_network:
            currency = 'ethereum'
            required_balance = 0.001  # Required ETH balance for transfer
        else:
            QMessageBox.warning(self, 'Network Error', 'Please select a valid network.')
            return

        # Fetch the user's holdings and get the balance for the selected currency
        holdings = self.back_payment_handler.get_user_holdings(self.username)
        balance = holdings.get(currency, 0)  # Default to 0 if currency is not found

        # Check if the user has enough balance for the transfer
        if balance < required_balance:
            # Create a custom QMessageBox with "Buy" option
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle(f'Low {currency.upper()} Balance')
            msg_box.setText(f'You do not have enough {currency.upper()} to transfer an asset.')
            msg_box.setInformativeText(f'Would you like to buy {currency.upper()}?')

            # Add buttons: Yes (to buy currency) and No (to close the dialog)
            buy_button = msg_box.addButton(f"Buy {currency.upper()}", QMessageBox.AcceptRole)
            close_button = msg_box.addButton(QMessageBox.No)

            msg_box.exec_()

            # If "Buy" button is clicked, trigger the payment window
            if msg_box.clickedButton() == buy_button:
                self.onBuyCrypto(currency)  # Modify this method to handle different crypto purchases

            self.transferButton.setEnabled(False)  # Disable the transfer button
        else:
            self.transferButton.setEnabled(True)  # Enable the transfer button

    def onBuyCrypto(self, currency):
        # Check if the payment window already exists
        if not hasattr(self, 'payment_window') or self.payment_window is None:
            self.payment_window = PaymentTab(self.username, self.back_payment_handler)  # Initialize PaymentTab
        self.payment_window.show()  # Show the payment window



    def createTokenSelectionGroup(self):
        self.token_selection_widget = QWidget()
        token_selection_layout = QVBoxLayout(self.token_selection_widget)
        token_selection_layout.setContentsMargins(0, 0, 0, 0)
        token_selection_layout.setSpacing(0)

        # Token selection group
        token_group = QGroupBox("Art To Transfer")
        token_group.setFixedWidth(600)  # Set fixed width for the box container

        font = token_group.font()
        font.setPointSize(30)  # Set font size for the group box title
        token_group.setFont(font)
        token_layout = QVBoxLayout(token_group)
        token_layout.setContentsMargins(10, 30, 10, 30)
        token_layout.setSpacing(30)

        asset_label = QLabel('🎨 Art Title')
        asset_label.setAlignment(Qt.AlignCenter)  # Center align the label
        self.tokenIdComboBox = QComboBox()  # Use a combo box to list assets
        self.tokenIdComboBox.setFixedWidth(250)  # Reduce the width of the dropdown menu

        self.populateTokenIdComboBox()  # Populate the combo box with user-specific assets

        asset_layout = QVBoxLayout()
        asset_layout.setAlignment(Qt.AlignCenter)  # Center align the layout
        asset_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        asset_layout.setSpacing(5)  # Reduce the spacing
        asset_layout.addWidget(asset_label)
        asset_layout.addWidget(self.tokenIdComboBox)

        token_layout.addLayout(asset_layout)

        # Add View Art and Reset buttons
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)  # Center align the buttons
        button_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        button_layout.setSpacing(20)  # Reduce the spacing
        self.viewAssetButton = QPushButton('View Art')
        self.viewAssetButton.setFixedWidth(115)  # Reduce the width of the button
        self.viewAssetButton.clicked.connect(self.onViewAsset)
        self.resetButton = QPushButton('Reset')
        self.resetButton.setFixedWidth(115)  # Reduce the width of the button
        self.resetButton.clicked.connect(self.onResetView)
        button_layout.addWidget(self.viewAssetButton)
        button_layout.addWidget(self.resetButton)

        token_layout.addLayout(button_layout)

        # Art details layout (Keep the number of rows to 6)
        self.assetDetailsTable = QTableWidget(6, 1)  # Create a table with 6 rows and 1 column
        self.assetDetailsTable.setVerticalHeaderLabels(
            ['Artist', 'Art Title', 'Creation Date', 'Valuation', 'Location',
             'Public Key'])  # Removed 'Description', added 'Location'
        self.assetDetailsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.assetDetailsTable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.assetDetailsTable.horizontalHeader().setVisible(False)  # Hide the horizontal header row
        self.assetDetailsTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide the vertical scroll bar

        # Adjust the row height explicitly
        row_height = self.assetDetailsTable.verticalHeader().sectionSize(0)
        total_height = row_height * 6  # Adjust the total height to 6 rows
        self.assetDetailsTable.setFixedHeight(total_height)

        token_layout.addWidget(self.assetDetailsTable, alignment=Qt.AlignCenter)

        token_selection_layout.addWidget(token_group, alignment=Qt.AlignCenter)

        token_selection_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.nextButton = QPushButton('Next →')
        self.nextButton.setFixedWidth(100)  # Adjust button width
        self.nextButton.clicked.connect(self.showTransferDetails)
        token_selection_layout.addWidget(self.nextButton, alignment=Qt.AlignCenter)

        self.main_layout.addWidget(self.token_selection_widget, alignment=Qt.AlignCenter)

    def createTransferDetailsGroup(self):
        self.transfer_details_widget = QWidget()
        transfer_details_layout = QVBoxLayout(self.transfer_details_widget)
        transfer_details_layout.setContentsMargins(0, 20, 0, 0)
        transfer_details_layout.setSpacing(10)  # Adjust spacing between sections if needed

        # Define a fixed width for the group boxes
        fixed_width = 600
        field_width = 270  # Define a fixed width for the input fields

        owner_group = QGroupBox("")
        owner_group.setFixedWidth(fixed_width)
        owner_layout = QVBoxLayout(owner_group)
        owner_layout.setContentsMargins(20, 20, 20, 20)
        owner_layout.setSpacing(10)

        owner_label = QLabel('📝 Enter new owner\'s name')
        owner_label.setAlignment(Qt.AlignCenter)
        self.newOwnerInput = QLineEdit()
        self.newOwnerInput.setPlaceholderText("Owner Name")
        self.newOwnerInput.setFixedWidth(field_width)  # Set fixed width
        self.checkOwnerButton = QPushButton('Check for Owner')
        self.checkOwnerButton.setToolTip('Check if owner exists')
        self.checkOwnerButton.clicked.connect(self.onCheckOwner)

        owner_layout.addWidget(owner_label, alignment=Qt.AlignCenter)
        owner_layout.addWidget(self.newOwnerInput, alignment=Qt.AlignCenter)
        owner_layout.addWidget(self.checkOwnerButton, alignment=Qt.AlignCenter)

        transfer_details_layout.addWidget(owner_group, alignment=Qt.AlignCenter)

        # Network group with icons and fees
        network_group = QGroupBox("")
        network_group.setFixedWidth(fixed_width)
        network_layout = QVBoxLayout(network_group)
        network_layout.setContentsMargins(20, 20, 20, 20)
        network_layout.setSpacing(10)

        network_label = QLabel('🌐 Please choose network for the transfer')
        network_label.setAlignment(Qt.AlignCenter)
        self.networkComboBox = QComboBox()
        self.networkComboBox.setFixedWidth(field_width)  # Set fixed width

        # Update the labels with the correct fees for BTC and ETH
        bitcoin_icon = QIcon('btc.png')  # Replace with your actual path
        ethereum_icon = QIcon('eth.png')  # Replace with your actual path

        self.networkComboBox.addItem(bitcoin_icon, 'Bitcoin Network  Fee: 0.0001 BTC')
        self.networkComboBox.addItem(ethereum_icon, 'Ethereum Network  Fee: 0.001 ETH')

        network_layout.addWidget(network_label, alignment=Qt.AlignCenter)
        network_layout.addWidget(self.networkComboBox, alignment=Qt.AlignCenter)

        transfer_details_layout.addWidget(network_group, alignment=Qt.AlignCenter)

        email_group = QGroupBox("")
        email_group.setFixedWidth(fixed_width)
        email_layout = QVBoxLayout(email_group)
        email_layout.setContentsMargins(20, 20, 20, 20)
        email_layout.setSpacing(10)

        email_label = QLabel('✉️ Enter your E-mail to Verify Transaction')
        email_label.setAlignment(Qt.AlignCenter)
        self.emailInput = QLineEdit()
        self.emailInput.setPlaceholderText("Your Email")
        self.emailInput.setFixedWidth(field_width)  # Set fixed width
        self.verifyButton = QPushButton('Verify Transaction')
        self.verifyButton.setToolTip('Verify your email address')
        self.verifyButton.clicked.connect(self.onVerifyTransaction)

        email_layout.addWidget(email_label, alignment=Qt.AlignCenter)
        email_layout.addWidget(self.emailInput, alignment=Qt.AlignCenter)
        email_layout.addWidget(self.verifyButton, alignment=Qt.AlignCenter)

        transfer_details_layout.addWidget(email_group, alignment=Qt.AlignCenter)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(20)  # Adjust spacing between buttons if needed
        button_layout.setAlignment(Qt.AlignCenter)

        self.backButton = QPushButton('← Back')
        self.backButton.clicked.connect(self.showTokenSelection)
        self.transferButton = QPushButton('Transfer Art')
        self.transferButton.setEnabled(False)
        self.transferButton.clicked.connect(self.onTransferToken)

        button_layout.addWidget(self.backButton)
        button_layout.addWidget(self.transferButton)

        transfer_details_layout.addWidget(button_widget, alignment=Qt.AlignCenter)

        self.main_layout.addWidget(self.transfer_details_widget)

    def showTransferDetails(self):
        # Check the crypto balance before showing transfer details
        self.checkCryptoBalance()
        self.switchWidget(self.transfer_details_widget)

    def showTokenSelection(self):
        self.updateAssetDetails()  # Ensure asset details are updated
        self.switchWidget(self.token_selection_widget)

    def updateAssetDetails(self):
        token_id = self.tokenIdComboBox.currentData()  # Get the current selected item\'s data
        if token_id:
            asset_details = self.get_assets_by_owner(self.username)  # Use the class method to get asset details
            asset_details = next((item for item in asset_details if item['id'] == token_id), None)
            if asset_details:
                self.populateAssetDetails(asset_details)
            else:
                self.clearAssetDetails()
        else:
            self.clearAssetDetails()  # Clear details if no valid token is selected

    def switchWidget(self, widget):
        self.opacityEffect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacityEffect)

        self.fadeOutAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeOutAnimation.setDuration(500)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)
        self.fadeOutAnimation.finished.connect(lambda: self.showNextWidget(widget))
        self.fadeOutAnimation.start()

    def showNextWidget(self, widget):
        self.token_selection_widget.setVisible(False)
        self.transfer_details_widget.setVisible(False)
        widget.setVisible(True)
        self.opacityEffect.setOpacity(0.0)  # Ensure the opacity is set to 0 initially
        widget.repaint()  # Ensure the widget is repainted
        self.fadeInAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeInAnimation.setDuration(500)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)
        self.fadeInAnimation.start()

    def populateTokenIdComboBox(self):
        """Populate the ComboBox with assets belonging to the user."""
        self.tokenIdComboBox.clear()  # Clear existing items
        assets = self.get_assets_by_owner(self.username)
        for asset in assets:
            try:
                # Use 'asset' and 'id' keys since 'art_title' is stored as 'asset'
                art_title = asset.get('asset')  # Use 'asset' instead of 'art_title'
                if art_title:
                    self.tokenIdComboBox.addItem(art_title, asset['id'])  # Use 'id' instead of 'token_id'
                else:
                    raise KeyError(f"Asset with token ID {asset['token_id']} is missing a valid 'asset' key.")
            except KeyError as e:
                logging.error(f"Error populating ComboBox: {e}")
                QMessageBox.warning(self, 'Data Error', f"Failed to add asset to ComboBox: {e}")

    def get_assets_by_owner(self, owner_name):
        try:
            return list(self.ledger_collection.find({"owner": owner_name}))
        except Exception as e:
            QMessageBox.warning(self, 'Database Error', f'An error occurred: {str(e)}')
            return []

    def updateTokenIdComboBox(self):
        self.tokenIdComboBox.clear()  # Clear existing items
        assets = self.get_assets_by_owner(self.username)
        for asset in assets:
            self.tokenIdComboBox.addItem(asset['asset'], asset['id'])

    def onViewAsset(self):
        """Handle the event to view selected asset details."""
        token_id = self.tokenIdComboBox.currentData()  # Get the current selected item's data
        if token_id:
            asset_details = self.get_assets_by_owner(self.username)  # Use the class method to get asset details
            # Filter the assets to find the one with the selected token_id
            asset_details = next((item for item in asset_details if item['id'] == token_id),
                                 None)  # Use 'id' instead of 'token_id'
            if asset_details:
                self.populateAssetDetails(asset_details)
            else:
                QMessageBox.information(self, 'Art Not Found',
                                        'No art found with the given token ID or not owned by you.')
                self.clearAssetDetails()
        else:
            QMessageBox.warning(self, 'Invalid Input', 'Please select an art to view.')
        self.token_selection_widget.repaint()  # Ensure the widget is repainted after viewing art

    def extract_public_key_part(self, public_key):
        # Extract the last six characters from the actual public key part
        match = re.search(r"-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----", public_key, re.DOTALL)
        if match:
            return match.group(1).strip().replace("\n", "")[-8:]
        return ""

    def populateAssetDetails(self, asset):
        """Fill the asset details in the table."""
        self.assetDetailsTable.setRowCount(6)  # Ensure there are 6 rows

        def create_non_clickable_item(text, row):
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)  # Center align the text
            label.setStyleSheet("font-size: 16px;")  # Set the desired font size

            self.assetDetailsTable.setCellWidget(row, 0, label)  # Set the QLabel as the cell widget
            item = QTableWidgetItem()
            item.setFlags(Qt.NoItemFlags)  # Make the item non-clickable and non-selectable
            return item

        # Use the get() method to safely access fields, with default values if missing
        artist_name = asset.get('artist_name', 'N/A')
        art_title = asset.get('asset', 'N/A')  # 'asset' key is used for the art title
        creation_date = asset.get('creation_date', 'N/A')
        valuation = asset.get('asset_valuation', 'N/A')
        location = asset.get('location', 'N/A')  # Default to 'N/A' if 'location' is missing
        public_key = self.extract_public_key_part(asset.get('owner_public_key', ''))

        # Populate the table rows with appropriate values
        self.assetDetailsTable.setItem(0, 0, create_non_clickable_item(artist_name, 0))
        self.assetDetailsTable.setItem(1, 0, create_non_clickable_item(art_title, 1))
        self.assetDetailsTable.setItem(2, 0, create_non_clickable_item(creation_date, 2))
        self.assetDetailsTable.setItem(3, 0, create_non_clickable_item(valuation, 3))
        self.assetDetailsTable.setItem(4, 0, create_non_clickable_item(location, 4))  # Using default if missing
        self.assetDetailsTable.setItem(5, 0, create_non_clickable_item(public_key, 5))

    def clearAssetDetails(self):
        for row in range(
                self.assetDetailsTable.rowCount()):  # Iterate over all rows, now including the new location row
            self.assetDetailsTable.removeCellWidget(row, 0)  # Remove the QLabel from the cell
            self.assetDetailsTable.setItem(row, 0, QTableWidgetItem(""))  # Set an empty item

    def onCheckOwner(self):
        owner_name = self.newOwnerInput.text().strip()
        if owner_name:
            exists = self.check_owner_exists(owner_name)
            if exists:
                QMessageBox.information(self, 'Owner Check', 'The owner exists.')
            else:
                QMessageBox.information(self, 'Owner Check', 'The owner does not exist.')
        else:
            QMessageBox.warning(self, 'Validation Error', 'Please enter an owner name to check.')

    def check_owner_exists(self, owner_name):
        try:
            return self.users_collection.find_one({"username": owner_name}) is not None
        except Exception as e:
            QMessageBox.warning(self, 'Database Error', f'An error occurred: {str(e)}')
            return False

    def onResetView(self):
        self.tokenIdComboBox.setCurrentIndex(0)  # Reset the combo box to the first item
        self.clearAssetDetails()  # Clear the asset details view

    def onTransferToken(self):
        token_id = self.tokenIdComboBox.currentData()  # Get the currently selected token's ID from the combo box
        new_owner = self.newOwnerInput.text().strip()
        selected_network = self.networkComboBox.currentText()  # Get selected network

        # Define network fees for BTC and ETH
        btc_fee = 0.0001
        eth_fee = 0.001

        # Determine the fee and currency based on the selected network
        if "Bitcoin" in selected_network:
            fee = btc_fee
            currency = "bitcoin"
        elif "Ethereum" in selected_network:
            fee = eth_fee
            currency = "ethereum"
        else:
            QMessageBox.warning(self, 'Network Selection Error', 'Please choose a valid network for the transfer.')
            return

        try:
            if token_id is not None and new_owner:  # Check that token_id is not None and new_owner is not empty
                # Check if user has enough BTC or ETH to cover the fee
                if not self.back_payment_handler.check_and_reduce_balance(self.username, currency, fee):
                    QMessageBox.warning(self, f'Insufficient {currency.upper()} Balance',
                                        f'You do not have enough {currency.upper()} to cover the network fee.')
                    return

                # Log the transfer attempt with network information
                logging.info(f"Attempting to transfer token ID {token_id} to {new_owner} via {selected_network}")

                # Call transfer_token with the appropriate fee
                transferred_token = transfer_token(token_id, new_owner, fee)

                if transferred_token:
                    QMessageBox.information(self, 'Success', 'Token transferred successfully!')
                    logging.info(f"Transfer successful for token ID {token_id} to {new_owner} on {selected_network}")

                    # Emit the assetTransferred signal
                    self.assetTransferred.emit()
                else:
                    QMessageBox.warning(self, 'Transfer Failed', 'Failed to transfer token.')
                    logging.error(f"Transfer failed for token ID {token_id} to {new_owner} on {selected_network}")
            else:
                # Display a warning message if either the token ID or new owner field is empty
                QMessageBox.warning(self, 'Validation Error', 'Token ID and new owner fields cannot be empty.')
                logging.error("Validation error: Token ID and new owner fields cannot be empty.")
        except Exception as e:
            # Display an error message if an exception occurs during the transfer process
            QMessageBox.critical(self, 'Error', f'Error transferring token: {str(e)}')
            logging.error(f"Error transferring token ID {token_id} to {new_owner} on {selected_network}: {str(e)}")

    def transferToken(self, token_id, new_owner):
        try:
            token = self.ledger_collection.find_one({'id': token_id})
            if not token:
                return False

            token['owner'] = new_owner
            self.ledger_collection.update_one({'id': token_id}, {'$set': token})
            return True
        except Exception as e:
            QMessageBox.warning(self, 'Database Error', f'An error occurred: {str(e)}')
            return False

    def onVerifyTransaction(self):
        email = self.emailInput.text().strip()
        if self.validate_email(email):
            QMessageBox.information(self, 'Verification Successful', 'Successful Verification.')
            self.transferButton.setEnabled(True)  # Enable the Transfer Button
        else:
            QMessageBox.warning(self, 'Verification Failed', 'No such email found. Please check and try again.')
            self.transferButton.setEnabled(False)  # Keep the Transfer Button disabled

    def validate_email(self, email):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return False
        try:
            # Check if the entered email belongs to the user who is currently logged in
            return self.users_collection.find_one({"email": email, "username": self.username}) is not None
        except Exception as e:
            QMessageBox.warning(self, 'Database Error', f'An error occurred: {str(e)}')
            return False
