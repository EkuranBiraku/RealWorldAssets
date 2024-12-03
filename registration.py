from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QMessageBox,
    QLabel, QLineEdit, QCheckBox, QDesktopWidget, QFrame
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer
import re
from captcha.image import ImageCaptcha
import qtawesome as qta
from pymongo import MongoClient

class PasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.toggleButton = QPushButton(clicked=self.togglePasswordVisibility)
        self.toggleButton.setCursor(Qt.PointingHandCursor)
        self.toggleButton.setIcon(QIcon(qta.icon('fa.eye')))
        self.toggleButton.setFixedSize(30, 30)  # Set a fixed size for the button to fit within the QLineEdit
        self.toggleButton.setStyleSheet("border: none; background-color: white; padding: 0px; margin-right:10px;")
        self.toggleButton.setFlat(True)

        layout = QHBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.toggleButton)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignRight)  # Align the button to the right
        self.setLayout(layout)
        self.setEchoMode(QLineEdit.Password)

    def togglePasswordVisibility(self):
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
            self.toggleButton.setIcon(QIcon(qta.icon('fa.eye-slash')))
        else:
            self.setEchoMode(QLineEdit.Password)
            self.toggleButton.setIcon(QIcon(qta.icon('fa.eye')))

class RegistrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Registration')
        self.setFixedSize(600, 900)
        self.center()
        self.setupUI()
        self.setupValidationTimers()

        # MongoDB setup
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['admin']
        self.users_collection = self.db['users']

    def setupUI(self):
        mainLayout = QVBoxLayout()
        mainLayout.setSpacing(20)
        mainLayout.setContentsMargins(40, 40, 40, 40)
        self.setStyleSheet("""
            QLabel {
                font-family: Arial;
                font-size: 16px;
            }
            QLineEdit, QCheckBox {
                font-family: Arial;
                font-size: 16px;
                padding: 5px;
            }
            QLineEdit:focus, QCheckBox:focus {
                border-color: #66afe9;
                outline: none;
            }
            QPushButton {
                font-family: Arial;
                font-size: 16px;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                background-color: #007BFF;
                color: white;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            .error-label {
                color: red;
                font-size: 12px;
            }
            QFrame#container {
                border: 2px solid #007BFF;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        # Logo and title setup
        logoLabel = QLabel(self)
        pixmap = QPixmap('logo.jpeg').scaledToWidth(200).scaledToHeight(150)
        logoLabel.setPixmap(pixmap)
        logoLabel.setAlignment(Qt.AlignCenter)



        logoLayout = QVBoxLayout()
        logoLayout.addWidget(logoLabel)
        logoLayout.setAlignment(Qt.AlignCenter)
        mainLayout.addLayout(logoLayout)

        # Container for form elements
        container = QFrame()
        containerLayout = QVBoxLayout()
        container.setLayout(containerLayout)
        container.setObjectName('container')

        formLayout = QGridLayout()
        formLayout.setSpacing(15)

        # Input fields and labels with placeholders
        self.usernameInput = QLineEdit()
        self.usernameInput.setPlaceholderText("Enter your username")
        self.usernameErrorLabel = QLabel("")
        self.usernameErrorLabel.setObjectName('error-label')

        self.passwordInput = PasswordLineEdit()
        self.passwordInput.setPlaceholderText("Create a password")
        self.passwordErrorLabel = QLabel("")
        self.passwordErrorLabel.setObjectName('error-label')

        self.confirmPasswordInput = PasswordLineEdit()
        self.confirmPasswordInput.setPlaceholderText("Confirm your password")
        self.confirmPasswordErrorLabel = QLabel("")
        self.confirmPasswordErrorLabel.setObjectName('error-label')

        self.emailInput = QLineEdit()
        self.emailInput.setPlaceholderText("Enter your email address")
        self.emailErrorLabel = QLabel("")
        self.emailErrorLabel.setObjectName('error-label')

        self.agreeCheckBox = QCheckBox('I agree to accept conditions & policy')
        self.agreeCheckBox.setStyleSheet("font-size: 16px;")

        # CAPTCHA
        self.imageCaptcha = ImageCaptcha(width=280, height=250)
        self.captchaText = self.generateCaptchaText()
        self.captchaImage = self.imageCaptcha.generate(self.captchaText)
        self.captchaLabel = QLabel(self)
        self.captchaPixmap = QPixmap()
        self.captchaPixmap.loadFromData(self.captchaImage.getvalue())
        self.captchaLabel.setPixmap(self.captchaPixmap)
        self.captchaInput = QLineEdit()
        self.captchaInput.setPlaceholderText("Enter CAPTCHA here")
        self.captchaInput.setFixedWidth(280)
        self.captchaInput.setFixedHeight(60)

        self.refreshCaptchaButton = QPushButton()
        refresh_icon = qta.icon('fa.refresh', color='white')
        self.refreshCaptchaButton.setIcon(refresh_icon)
        self.refreshCaptchaButton.clicked.connect(self.refreshCaptcha)
        self.refreshCaptchaButton.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 14px;
                border: none;
                border-radius: 5px;
                max-width:20px;
                margin-right:100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        captchaLayout = QHBoxLayout()
        captchaLayout.addWidget(self.captchaLabel)
        captchaLayout.addWidget(self.refreshCaptchaButton)

        # Form layout with grid
        formLayout.addWidget(QLabel("Username:"), 0, 0)
        formLayout.addWidget(self.usernameInput, 0, 1)
        formLayout.addWidget(self.usernameErrorLabel, 1, 1)

        formLayout.addWidget(QLabel("Password:"), 2, 0)
        formLayout.addWidget(self.passwordInput, 2, 1)
        formLayout.addWidget(self.passwordErrorLabel, 3, 1)

        formLayout.addWidget(QLabel("Re-enter Password:"), 4, 0)
        formLayout.addWidget(self.confirmPasswordInput, 4, 1)
        formLayout.addWidget(self.confirmPasswordErrorLabel, 5, 1)

        formLayout.addWidget(QLabel("Email:"), 6, 0)
        formLayout.addWidget(self.emailInput, 6, 1)
        formLayout.addWidget(self.emailErrorLabel, 7, 1)
        formLayout.addLayout(captchaLayout, 8, 0, 1, 2)
        formLayout.addWidget(self.captchaInput, 9, 0, 1, 2)
        formLayout.addWidget(self.agreeCheckBox, 10, 0, 1, 2)

        containerLayout.addLayout(formLayout)
        mainLayout.addWidget(container)

        self.registerButton = QPushButton('Register', clicked=self.onRegister)
        self.registerButton.setStyleSheet("""
            QPushButton {
                background-color:#666 ;
                color: white;
                font-size: 20px;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: lightblue;
                color: black;
            }
        """)
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.registerButton)
        buttonLayout.addStretch()

        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

    def refreshCaptcha(self):
        self.captchaText = self.generateCaptchaText()
        self.captchaImage = self.imageCaptcha.generate(self.captchaText)
        self.captchaPixmap.loadFromData(self.captchaImage.getvalue())
        self.captchaLabel.setPixmap(self.captchaPixmap)
        self.captchaInput.clear()

    def setupValidationTimers(self):
        # Timers for asynchronous validation
        self.usernameTimer = QTimer(self)
        self.usernameTimer.setSingleShot(True)
        self.usernameTimer.timeout.connect(self.validateUsernameUnique)

        self.emailTimer = QTimer(self)
        self.emailTimer.setSingleShot(True)
        self.emailTimer.timeout.connect(self.validateEmailUnique)

        self.passwordTimer = QTimer(self)
        self.passwordTimer.setSingleShot(True)
        self.passwordTimer.timeout.connect(self.validatePassword)

        self.confirmPasswordTimer = QTimer(self)
        self.confirmPasswordTimer.setSingleShot(True)
        self.confirmPasswordTimer.timeout.connect(self.validateConfirmPassword)

        # Connect text changes to reset timers
        self.usernameInput.textChanged.connect(lambda: self.usernameTimer.start(500))
        self.emailInput.textChanged.connect(lambda: self.emailTimer.start(500))
        self.passwordInput.textChanged.connect(lambda: self.passwordTimer.start(500))
        self.confirmPasswordInput.textChanged.connect(lambda: self.confirmPasswordTimer.start(500))

    def validateUsernameUnique(self):
        username = self.usernameInput.text().strip()
        if username:
            user = self.users_collection.find_one({"username": username})
            if user:
                self.usernameErrorLabel.setText("Username already exists.")
            else:
                self.usernameErrorLabel.setText("")

    def validateEmailUnique(self):
        email = self.emailInput.text().strip()
        if email:
            user = self.users_collection.find_one({"email": email})
            if user:
                self.emailErrorLabel.setText("Email already exists.")
            else:
                self.emailErrorLabel.setText("")

    def onRegister(self):
        # Gather inputs
        username = self.usernameInput.text().strip()
        password = self.passwordInput.text().strip()
        confirm_password = self.confirmPasswordInput.text().strip()
        email = self.emailInput.text().strip()
        agree = self.agreeCheckBox.isChecked()

        # Clear previous error messages
        self.clearErrorMessages()

        # Validate all inputs including CAPTCHA
        inputs_valid = self.validateInputs(username, password, confirm_password, email, agree)
        captcha_valid = self.validateCaptcha()

        if not inputs_valid or not captcha_valid:
            if not captcha_valid:
                QMessageBox.warning(self, 'Validation Error', 'Incorrect CAPTCHA, please try again.')
            return

        # Process registration if all validations are passed
        if self.processRegistration(username, password, email):
            QMessageBox.information(self, 'Success', 'Registration successful!')
            self.accept()

    def clearErrorMessages(self):
        self.usernameErrorLabel.setText("")
        self.passwordErrorLabel.setText("")
        self.confirmPasswordErrorLabel.setText("")
        self.emailErrorLabel.setText("")

    def validateInputs(self, username, password, confirm_password, email, agree):
        valid = True
        if not username:
            self.usernameErrorLabel.setText("Username field cannot be empty.")
            valid = False
        if not self.isValidPassword(password):
            valid = False
        if password != confirm_password:
            self.confirmPasswordErrorLabel.setText("Passwords do not match.")
            valid = False
        if not email:
            self.emailErrorLabel.setText("Email field cannot be empty.")
            valid = False
        if not self.isValidEmail(email):
            self.emailErrorLabel.setText("Invalid email address.")
            valid = False
        if not agree:
            QMessageBox.warning(self, 'Validation Error', 'You must agree to the terms and conditions.')
            valid = False
        return valid

    def processRegistration(self, username, password, email):
        user = self.users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
        if user:
            if user.get("username") == username:
                self.usernameErrorLabel.setText("Username already exists.")
            if user.get("email") == email:
                self.emailErrorLabel.setText("Email already exists.")
            return False

        new_user = {
            'username': username,
            'password': password,
            'email': email
        }
        self.users_collection.insert_one(new_user)
        return True

    def isValidPassword(self, password):
        if len(password) < 6:
            self.passwordErrorLabel.setText("Password must be at least 6 characters long.")
            return False
        if not any(char.isupper() for char in password):
            self.passwordErrorLabel.setText("Password must contain at least one uppercase letter.")
            return False
        if not re.search(r'[?.!,]', password):
            self.passwordErrorLabel.setText("Password must contain at least one special character (.?!,).")
            return False
        self.passwordErrorLabel.setText("")
        return True

    def validatePassword(self):
        password = self.passwordInput.text().strip()
        if password and not self.isValidPassword(password):
            return
        self.passwordErrorLabel.setText("")

    def validateConfirmPassword(self):
        confirm_password = self.confirmPasswordInput.text().strip()
        password = self.passwordInput.text().strip()
        if confirm_password and confirm_password != password:
            self.confirmPasswordErrorLabel.setText("Passwords do not match.")
            return
        self.confirmPasswordErrorLabel.setText("")

    def isValidEmail(self, email):
        pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        if not pattern.match(email):
            return False
        return True

    def validateCaptcha(self):
        enteredCaptcha = self.captchaInput.text()
        return enteredCaptcha == self.captchaText

    def generateCaptchaText(self):
        from random import choices
        import string
        characters = string.ascii_uppercase + string.digits
        return ''.join(choices(characters, k=6))

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = RegistrationWindow()
    window.show()
    sys.exit(app.exec_())
