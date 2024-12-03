import re

from PyQt5.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QComboBox, \
    QFileDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QGroupBox, QDateEdit
from PyQt5.QtGui import QColor, QFont, QPixmap, QImage, QPainter, QBrush
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QSize, QRect, QDate
from PyQt5.QtGui import QRegExpValidator, QDoubleValidator
from pymongo import MongoClient
import os
from token_system import create_token
from backpayment import BackPaymentHandler
import qtawesome as qta
from Tabs.payment import PaymentTab
import pytesseract
from PIL import Image
import fitz  # PyMuPDF



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

        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 12.5, 12.5)

        circle_rect = QRect(2, 2, 21, 21) if not self.isChecked() else QRect(25, 2, 21, 21)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(circle_rect)

        painter.end()

    def mouseReleaseEvent(self, event):
        self.setChecked(not self.isChecked())
        self.update()  # Trigger a repaint to update the visual state
        super().mouseReleaseEvent(event)


class CreateTokenTab(QWidget):
    tokenCreated = pyqtSignal()  # Signal emitted when a token is created
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    def __init__(self, username=None, back_payment_handler=None):
        super().__init__()
        self.username = username  # Store the username
        self.back_payment_handler = back_payment_handler or BackPaymentHandler()  # Use provided handler or create new

        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']

        self.image_label = None
        self.image_placeholder = QLabel()
        self.upload_button = QPushButton()
        self.upload_button.setIcon(qta.icon('fa.plus', color='white', scale_factor=1))  # Set the plus icon with white color and bigger size

        self.file_path = ""
        # Add the Buy USDT button
        self.buy_usdt_button = QPushButton("Buy USDT Here")
        self.buy_usdt_button.setStyleSheet("font-size: 17px; color: white;")
        self.buy_usdt_button.setFixedSize(160, 50)  # Adjust size if needed
        self.buy_usdt_button.clicked.connect(self.onBuyUSDT)
        self.buy_usdt_button.setVisible(False)  # Hidden by default, shown only if USDT < 10

        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)  # Change to QVBoxLayout to stack containers vertically

        containers_layout = QHBoxLayout()  # Create a layout to hold the two containers

        left_group = QGroupBox("Token Information")
        left_layout = QVBoxLayout(left_group)
        left_layout.setAlignment(Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        form_layout.setAlignment(Qt.AlignCenter)
        labels = ['Owner', 'Art Title', 'Artist Name', 'Location', 'Creation Date', 'Art Description']
        placeholders = ['Enter owner name', 'Enter title of the art', 'Enter artist name', 'Enter location of the art',
                        'Enter date of creation', 'Enter art description']

        self.inputFields = {}

        for label_text, placeholder_text in zip(labels, placeholders):
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 10, QFont.Bold))

            if label_text == 'Creation Date':
                input_field = QDateEdit()
                input_field.setCalendarPopup(True)
                input_field.setDisplayFormat("dd-MM-yyyy")  # Display format
                input_field.setStyleSheet("""
                    background-color: white;
                    color: black;
                    text-align: center;  /* Center the text */
                    padding-left: 100px;  /* Optional: add some padding to the left */
                """)
                input_field.setFixedWidth(300)
                input_field.setDate(QDate.currentDate())  # Set default date to today

            else:
                input_field = QLineEdit()
                input_field.setPlaceholderText(placeholder_text)
                input_field.setFixedWidth(300)  # Set fixed width for the input fields
                if label_text in ['Art Title', 'Artist Name', 'Location']:
                    input_field.setMaxLength(100)
                if label_text == 'Owner':
                    input_field.setText(self.username)  # Set the username
                    input_field.setReadOnly(True)  # Make it read-only
                if label_text == 'Art Description':
                    input_field.setFixedHeight(60)

            self.inputFields[label_text] = input_field

            container_layout = QVBoxLayout()
            container_layout.addWidget(label, alignment=Qt.AlignCenter)
            container_layout.addWidget(input_field, alignment=Qt.AlignCenter)
            form_layout.addLayout(container_layout)

        art_valuation_container = QVBoxLayout()
        art_valuation_label = QLabel("Art Valuation")
        art_valuation_label.setStyleSheet("margin-top:10px;")
        art_valuation_label.setFont(QFont("Arial", 10, QFont.Bold))
        art_valuation_container.addWidget(art_valuation_label, alignment=Qt.AlignCenter)
        self.assetValuationWidget = AssetValuationWidget()
        art_valuation_container.addWidget(self.assetValuationWidget, alignment=Qt.AlignCenter)
        form_layout.addLayout(art_valuation_container)

        left_layout.addLayout(form_layout)

        right_group = QGroupBox("Upload Artwork")
        right_layout = QVBoxLayout(right_group)
        right_layout.setAlignment(Qt.AlignTop)  # Align the right layout to the top

        right_layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        upload_button_layout = QHBoxLayout()
        self.upload_button.clicked.connect(self.onUploadDocumentation)
        self.upload_button.setIconSize(QSize(80, 80))  # Set icon size to 64x64
        self.upload_button.setStyleSheet("border: none; background: none;")

        right_layout.addLayout(upload_button_layout)


        self.image_layout = QVBoxLayout()
        self.image_placeholder.setFixedSize(300, 300)
        self.image_placeholder.setStyleSheet("border: 2px dotted white; border-radius: 10px;")
        self.image_layout.addWidget(self.image_placeholder, alignment=Qt.AlignCenter)
        right_layout.addLayout(self.image_layout)

        self.image_placeholder_layout = QVBoxLayout(self.image_placeholder)
        self.image_placeholder_layout.addWidget(self.upload_button, alignment=Qt.AlignCenter)

        self.replace_button = QPushButton("Replace File")
        self.replace_button.setStyleSheet("font-size: 16px; margin-bottom: 20px;")
        self.replace_button.clicked.connect(self.onDeleteDocumentation)
        self.replace_button.setVisible(False)

        right_layout.addSpacerItem(QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.Fixed))
        right_layout.addWidget(self.replace_button, alignment=Qt.AlignCenter)
        right_layout.addSpacerItem(QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Certification Upload Section
        self.cert_upload_button = QPushButton("Upload Certification")
        self.cert_upload_button.clicked.connect(self.onUploadCertification)
        self.cert_upload_button.setIconSize(QSize(80, 80))
        self.cert_upload_button.setStyleSheet("border:1px")

        # Label to Display Uploaded File Name
        self.cert_file_label = QLabel("No file uploaded")
        self.cert_file_label.setStyleSheet("color: white; font-size: 18px;border:1px;")
        self.cert_file_label.setAlignment(Qt.AlignCenter)

        # Layout for Certification Upload
        cert_layout = QVBoxLayout()
        cert_layout.addWidget(self.cert_upload_button, alignment=Qt.AlignCenter)
        cert_layout.addWidget(self.cert_file_label, alignment=Qt.AlignCenter)

        # Add the certification upload layout to the right layout (right side of the UI)
        right_layout.addLayout(cert_layout)
        right_layout.addSpacerItem(QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Add the Buy USDT button above the 5 USDT Fee label
        right_layout.addWidget(self.buy_usdt_button, alignment=Qt.AlignCenter)

        self.fee_label = QLabel('3 USDT Fee')
        self.fee_label.setStyleSheet('color:yellow;font-size:16px;')
        right_layout.addWidget(self.fee_label, alignment=Qt.AlignCenter)

        spacer_item = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        right_layout.addSpacerItem(spacer_item)

        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("List it on Market")
        toggle_label.setStyleSheet("color: white; font-size:20px;margin-bottom:8px;")
        self.list_on_market_checkbox = ToggleSwitch()
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addWidget(self.list_on_market_checkbox)
        toggle_layout.setAlignment(Qt.AlignCenter)
        right_layout.addLayout(toggle_layout)

        containers_layout.addWidget(left_group)
        containers_layout.addWidget(right_group)

        main_layout.addLayout(containers_layout)

        create_button = QPushButton('Create Token')
        create_button.setFixedSize(150, 50)
        create_button.setStyleSheet("margin-top:10px;font-size:16px;")
        create_button.clicked.connect(self.onCreateToken)
        main_layout.addWidget(create_button, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)

    def onTabSelected(self):
        """This method will be called when the user navigates to the Create Asset tab."""
        self.checkUSDTBalance()  # Check balance when the tab is selected

    def checkUSDTBalance(self):
        # Use get_user_holdings to get all the holdings, including USDT
        holdings = self.back_payment_handler.get_user_holdings(self.username)

        # Check if USDT is in the holdings and get its balance
        usdt_balance = holdings.get('tether', 0)  # Default to 0 if USDT is not found

        if usdt_balance < 3:
            # Create a custom QMessageBox with "Buy USDT" option
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('Low USDT Balance')
            msg_box.setText('You do not have enough USDT (Tether) to create an asset.')
            msg_box.setInformativeText('Would you like to buy USDT?')

            # Add buttons: Yes (to buy USDT) and No (to close the dialog)
            buy_button = msg_box.addButton("Buy USDT", QMessageBox.AcceptRole)
            close_button = msg_box.addButton(QMessageBox.No)

            msg_box.exec_()

            # If "Buy USDT" button is clicked, trigger the payment window
            if msg_box.clickedButton() == buy_button:
                self.onBuyUSDT()

        if usdt_balance < 10:
            self.buy_usdt_button.setVisible(False)  # We are moving the button functionality to the pop-up

    def onBuyUSDT(self):
        # Check if the payment window already exists
        if not hasattr(self, 'payment_window') or self.payment_window is None:
            self.payment_window = PaymentTab(self.username, self.back_payment_handler)  # Initialize PaymentTab
        self.payment_window.show()  # Show the payment window

    def onUploadDocumentation(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            self.removePreviousImage()
            image = QImage(self.file_path)
            pixmap = QPixmap.fromImage(image).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label = QLabel()
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_layout.addWidget(self.image_label)
            self.image_placeholder.hide()
            self.upload_button.setEnabled(False)
            self.replace_button.setVisible(True)

    def onDeleteDocumentation(self):
        self.removePreviousImage()
        self.upload_button.setEnabled(True)
        self.replace_button.setVisible(False)

    def removePreviousImage(self):
        if hasattr(self, 'image_label') and self.image_label is not None:
            self.image_layout.removeWidget(self.image_label)
            self.image_label.deleteLater()
            self.image_label = None
            self.image_placeholder.show()

    def asset_exists(self, art_title):
        """Check if an art token with the given title exists in the asset_history collection."""
        return self.db['asset_history'].find_one({"asset": art_title}) is not None

    def onCreateToken(self):
        try:
            # Ensure all required fields are filled
            if all((field.text().strip() if isinstance(field, QLineEdit) else field.date().toString(
                    "yyyy-MM-dd").strip()) for field in self.inputFields.values()) and self.file_path:

                # Retrieve input field values
                owner = self.inputFields['Owner'].text().strip()
                art_title = self.inputFields['Art Title'].text().strip()
                artist_name = self.inputFields['Artist Name'].text().strip()
                location = self.inputFields['Location'].text().strip()  # Get the location field value
                creation_date = self.inputFields['Creation Date'].date().toString("yyyy-MM-dd")
                art_description = self.inputFields['Art Description'].text().strip()
                art_valuation_input = self.assetValuationWidget.assetValuationInput.text().strip()
                currency = self.assetValuationWidget.currencyComboBox.currentText()
                art_valuation = f"{art_valuation_input} {currency}"

                for_sale = self.list_on_market_checkbox.isChecked()

                # Validation checks
                if self.asset_exists(art_title):
                    QMessageBox.warning(self, 'Validation Error', 'This art title already exists in the database.')
                    return

                if len(art_title) > 100 or len(artist_name) > 100 or len(location) > 100:
                    QMessageBox.warning(self, 'Validation Error',
                                        'Art Title, Artist Name, and Location must not exceed 100 characters.')
                    return

                if not re.match(r'\d{4}-\d{2}-\d{2}', creation_date):
                    QMessageBox.warning(self, 'Validation Error', 'Creation Date must be in the format yyyy-mm-dd.')
                    return

                if len(art_description) > 500 or len(art_description) < 20:
                    QMessageBox.warning(self, 'Validation Error',
                                        'Art Description must be between 20 and 500 characters.')
                    return

                # Ensure a certification document has been uploaded
                if not hasattr(self, 'cert_file_path') or not self.cert_file_path:
                    QMessageBox.warning(self, 'Validation Error', 'Please upload a certification document.')
                    return

                # Ensure certification document was validated during upload
                if not hasattr(self, 'is_valid_certification') or not self.is_valid_certification:
                    QMessageBox.warning(self, 'Validation Error', 'The uploaded certification document is not valid.')
                    return

                # Ensure art_valuation_input is a valid number according to the set validator
                if not self.assetValuationWidget.assetValuationInput.hasAcceptableInput():
                    QMessageBox.warning(self, 'Validation Error', f'Invalid art valuation for {currency}.')
                    return

                # Check USDT balance and create token
                if self.back_payment_handler.check_and_reduce_tether(owner, 3):
                    token = create_token(owner, art_title, artist_name, creation_date, art_valuation,
                                         art_description, self.file_path, for_sale, location=location,
                                         cert_file_path=self.cert_file_path)  # Pass the certification file path
                    self.back_payment_handler.record_transaction(owner, 'tether', -3, 'create_art_token', token['id'])
                    QMessageBox.information(self, 'Success', 'Art token created successfully!')
                    self.clearFields()  # Clear all fields except Owner
                    self.tokenCreated.emit()
                else:
                    QMessageBox.warning(self, 'Insufficient Balance', 'You do not have enough USDT to create a token.')

            else:
                QMessageBox.warning(self, 'Validation Error',
                                    'All art token information must be provided, including an image.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred: {str(e)}')
    def clearFields(self):
        for key, field in self.inputFields.items():
            if key != 'Owner':  # Skip the Owner field
                if isinstance(field, QLineEdit):
                    field.clear()
                elif isinstance(field, QComboBox):
                    field.setCurrentIndex(0)
                elif isinstance(field, QDateEdit):
                    field.setDate(QDate.currentDate())  # Reset to today's date
        self.assetValuationWidget.assetValuationInput.clear()
        self.assetValuationWidget.currencyComboBox.setCurrentIndex(0)
        self.removePreviousImage()
        self.upload_button.setEnabled(True)
        self.replace_button.setVisible(False)
        self.list_on_market_checkbox.setChecked(False)

    def onUploadCertification(self):
        # Open file dialog for the user to upload certification
        cert_dialog = QFileDialog()
        cert_dialog.setFileMode(QFileDialog.ExistingFile)
        cert_dialog.setNameFilter("Images and PDFs (*.png *.jpg *.jpeg *.pdf)")

        if cert_dialog.exec_():
            self.cert_file_path = cert_dialog.selectedFiles()[0]
            # Update the file label to show the uploaded file's name
            self.cert_file_label.setText(f"Uploaded: {os.path.basename(self.cert_file_path)}")
            print("Uploaded certification file:", self.cert_file_path)

            extracted_text = ""

            # Handle PDFs
            if self.cert_file_path.lower().endswith(".pdf"):
                try:
                    pdf_document = fitz.open(self.cert_file_path)
                    for page_number in range(len(pdf_document)):
                        page_text = pdf_document[page_number].get_text()
                        extracted_text += page_text
                    pdf_document.close()

                except Exception as e:
                    QMessageBox.critical(self, 'Error', f"Failed to process PDF: {str(e)}")
                    self.is_valid_certification = False  # Mark as invalid
                    return

            # Handle images
            else:
                extracted_text = self.extract_text_from_certification()

            if not extracted_text:
                QMessageBox.warning(self, 'Validation Error',
                                    'The certification document could not be read. Please try a different file or ensure the image is clear.')
                self.is_valid_certification = False  # Mark as invalid
                return

            # Validate the certification content
            self.is_valid_certification = self.validate_certification(extracted_text)

            if not self.is_valid_certification:
                QMessageBox.warning(self, 'Validation Error',
                                    'Certification validation failed. The provided document is not recognized as legitimate.')
                return

            QMessageBox.information(self, 'Certification Verified',
                                    'The certification document has been verified as legitimate.')

    def extract_text_from_certification(self):
        if hasattr(self, 'cert_file_path'):
            extracted_text = pytesseract.image_to_string(Image.open(self.cert_file_path))
            return extracted_text
        else:
            return None

    def validate_certification(self, extracted_text):
        # Define stricter regular expressions for "Certificate No." to match only numeric values followed by whitespace or end of line
        required_patterns = [
            r"Certificate of Authenticity",
            r"Certificate\s*No\.\s*[:\.\-]?\s*(\d+)(?:\s|$)",
            # Strict pattern for numeric certificate number followed by whitespace or end of line
            r"Issued by:\s*[\w\s]+",
            rf"Title:\s*{re.escape(self.inputFields['Art Title'].text())}",
            rf"Artist:\s*{re.escape(self.inputFields['Artist Name'].text())}",
            r"Date of Creation:\s*\d{4}-\d{2}-\d{2}",
            r"Medium:\s*\w+",
            r"Dimensions:\s*\d+\s*x\s*\d+\s*inches",
            r"This certifies that the artwork titled",
            r"Signature:\s*\w+",
        ]

        for pattern in required_patterns:
            match = re.search(pattern, extracted_text, re.IGNORECASE)
            if not match:
                return False  # Fail validation if any required pattern is missing

            # Additional check for certificate number to ensure it's strictly numeric and in range
            if pattern == r"Certificate\s*No\.\s*[:\.\-]?\s*(\d+)(?:\s|$)":
                certificate_number = match.group(1)  # Capture the matched certificate number

                # Ensure the certificate number is strictly numeric
                if not certificate_number.isdigit():
                    return False

                # Convert to integer and check the range
                certificate_number = int(certificate_number)
                if not (20 <= certificate_number <= 10000000):
                    return False

        return True  # Pass validation if all patterns are matched


class AssetValuationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()

        self.assetValuationInput = QLineEdit()
        self.assetValuationInput.setPlaceholderText('Enter art valuation')
        self.assetValuationInput.setFixedWidth(200)

        self.currencyComboBox = QComboBox()
        self.currencyComboBox.addItems(['USDT', 'BTC', 'ETH'])
        self.currencyComboBox.currentTextChanged.connect(self.updateValidator)  # Connect to updateValidator method

        layout.addWidget(self.assetValuationInput)
        layout.addWidget(self.currencyComboBox)

        self.setLayout(layout)

        self.updateValidator()  # Set initial validator based on default currency

    def updateValidator(self):
        """Update the validator based on the selected currency."""
        currency = self.currencyComboBox.currentText()
        if currency == 'USDT':
            validator = QDoubleValidator(0.01, 10000000.00, 2)  # Up to 10,000,000.00 USDT
        elif currency == 'BTC':
            validator = QDoubleValidator(0.00001, 1000.00, 5)  # Up to 1,000.00000 BTC
        elif currency == 'ETH':
            validator = QDoubleValidator(0.00001, 3000.00, 5)  # Up to 3,000.00000 ETH

        validator.setNotation(QDoubleValidator.StandardNotation)
        self.assetValuationInput.setValidator(validator)
