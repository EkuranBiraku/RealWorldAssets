import sys
from PyQt5.QtWidgets import (
    QHBoxLayout, QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QMessageBox, QCheckBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from registration import RegistrationWindow
from token_app import TokenApp
from qtawesome import icon
from resetpassword import ResetPasswordWindow
from header_widget import HeaderWidget
import platform
import requests
import json
from datetime import datetime

from pymongo import MongoClient
import os


class PasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.toggleButton = QPushButton(clicked=self.togglePasswordVisibility)
        self.toggleButton.setCursor(Qt.PointingHandCursor)
        self.toggleButton.setIcon(icon('fa.eye'))
        self.toggleButton.setStyleSheet("border: none; background-color: #f0ecec; padding: 5px;")
        self.toggleButton.setFixedSize(24, 24)  # Adjust size to fit within the text box
        self.toggleButton.setFlat(True)

        layout = QHBoxLayout()
        layout.addStretch(6)  # Reduce the stretch factor to move the button closer to the left
        layout.addWidget(self.toggleButton)
        layout.addStretch(1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setEchoMode(QLineEdit.Password)

    def togglePasswordVisibility(self):
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
            self.toggleButton.setIcon(icon('fa.eye-slash'))
        else:
            self.setEchoMode(QLineEdit.Password)
            self.toggleButton.setIcon(icon('fa.eye'))


class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tokenApp = None

        # MongoDB setup
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']  # Database name remains 'admin'
        self.users_collection = self.db['users']
        self.device_history_collection = self.db['device_history']
        self.credentials_collection = self.db['credentials']

        self.initUI()
        self.loadCredentials()

    def initUI(self):
        self.setWindowTitle('Login')
        self.setFixedSize(500, 600)  # Increased height to ensure all elements fit
        layout = QVBoxLayout()

        logoLayout = QVBoxLayout()
        logoLabel = QLabel(self)
        pixmap = QPixmap('logo.jpeg').scaled(200, 200, Qt.KeepAspectRatio)
        logoLabel.setPixmap(pixmap)
        logoLabel.setAlignment(Qt.AlignCenter)
        logoLayout.addWidget(logoLabel)


        layout.addLayout(logoLayout)

        self.usernameInput = QLineEdit()
        self.passwordInput = PasswordLineEdit()
        self.passwordInput.setEchoMode(QLineEdit.Password)

        self.usernameInput.setClearButtonEnabled(True)
        self.usernameInput.addAction(icon('fa.user'), QLineEdit.LeadingPosition)
        self.passwordInput.setClearButtonEnabled(True)
        self.passwordInput.addAction(icon('fa.lock'), QLineEdit.LeadingPosition)
        # Connect the "Enter" key press signal to the onLogin method
        self.usernameInput.returnPressed.connect(self.onLogin)
        self.passwordInput.returnPressed.connect(self.onLogin)
        self.loginButton = QPushButton('Login', clicked=self.onLogin)
        self.loginButton.setMinimumSize(100, 40)  # Set a minimum size for the button

        layout.addWidget(QLabel('Username'), alignment=Qt.AlignCenter)
        self.usernameInput.setMinimumWidth(350)
        layout.addWidget(self.usernameInput, alignment=Qt.AlignCenter)

        layout.addWidget(QLabel('Password'), alignment=Qt.AlignCenter)
        self.passwordInput.setMinimumWidth(350)
        layout.addWidget(self.passwordInput, alignment=Qt.AlignCenter)
        layout.addSpacing(5)  # Add space between the password field and the login button
        self.rememberMeCheckbox = QCheckBox('Remember Me')
        layout.addWidget(self.rememberMeCheckbox, alignment=Qt.AlignCenter)
        layout.addWidget(self.loginButton, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        # Container Widget
        linksContainer = QWidget()
        linksLayout = QHBoxLayout()  # Change to QHBoxLayout for horizontal alignment
        linksContainer.setLayout(linksLayout)
        linksContainer.setStyleSheet("""
            background-color: #2c2f33;  # Dark background color for the container
            border-radius: 10px;       # Rounded corners
            padding: 10px;             # Padding inside the container
        """)

        # Register Button
        registerButton = QPushButton("Register Here")
        registerButton.setStyleSheet("""
            QPushButton {
                color: #add8e6; 
                font-size: 15px; 
                text-decoration: none; 
                background: none; 
                border: 1px solid #add8e6;
                border-radius: 10px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #3a3f44;
            }
        """)
        registerButton.clicked.connect(self.openRegistrationWindow)
        registerButton.setCursor(Qt.PointingHandCursor)
        linksLayout.addWidget(registerButton, alignment=Qt.AlignCenter)

        # Spacer
        spacer = QWidget()
        spacer.setFixedWidth(30)
        linksLayout.addWidget(spacer)

        # Forgot Password Button
        forgotPasswordButton = QPushButton("Reset Password")
        forgotPasswordButton.setStyleSheet("""
            QPushButton {
                color: #add8e6; 
                font-size: 15px; 
                text-decoration: none; 
                background: none; 
                border: 1px solid #add8e6;
                border-radius: 10px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #3a3f44;
            }
        """)
        forgotPasswordButton.clicked.connect(lambda: self.openPasswordResetPage("forgot_password"))
        forgotPasswordButton.setCursor(Qt.PointingHandCursor)
        linksLayout.addWidget(forgotPasswordButton, alignment=Qt.AlignCenter)

        # Add the container to the main layout
        layout.addWidget(linksContainer, alignment=Qt.AlignCenter)

    def onLogin(self):
        username = self.usernameInput.text()
        password = self.passwordInput.text()
        remember_me = self.rememberMeCheckbox.isChecked()

        if self.authenticate_user(username, password):
            email = self.get_user_email(username)
            self.saveDeviceHistory(username)
            self.openMainApp(username, email)
            if remember_me:
                self.saveCredentials(username, password)
            else:
                self.clearCredentials()
        else:
            QMessageBox.warning(self, 'Login Error', 'Username or Password is wrong.')

    def saveDeviceHistory(self, username):
        device = platform.platform()
        location = self.getLocation()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        history = {
            'username': username,
            'device': device,
            'location': location,
            'timestamp': now
        }

        try:
            self.device_history_collection.insert_one(history)
        except Exception as e:
            print(f"Error saving device history: {e}")

    def getLocation(self):
        try:
            response = requests.get('https://ipinfo.io')
            data = response.json()
            return f"{data.get('city')}, {data.get('region')}, {data.get('country')}"
        except Exception as e:
            return "Unknown location"

    def authenticate_user(self, username, password):
        user = self.users_collection.find_one({"username": username, "password": password})
        return user is not None

    def get_user_email(self, username):
        user = self.users_collection.find_one({"username": username})
        return user.get('email') if user else None

    def openMainApp(self, username, email):
        if not self.tokenApp:
            self.tokenApp = TokenApp(username, email)
        self.tokenApp.show()
        self.hide()

    def openRegistrationWindow(self):
        self.registrationWindow = RegistrationWindow()
        self.registrationWindow.show()

    def openPasswordResetPage(self, link):
        if link == "forgot_password":
            reset_window = ResetPasswordWindow()
            reset_window.exec_()

    def saveCredentials(self, username, password):
        credentials = {'username': username, 'password': password}
        self.credentials_collection.update_one({}, {"$set": credentials}, upsert=True)

    def clearCredentials(self):
        self.credentials_collection.delete_one({})

    def loadCredentials(self):
        credentials = self.credentials_collection.find_one({})
        if credentials:
            username = credentials.get('username', '')
            password = credentials.get('password', '')
            self.usernameInput.setText(username)
            self.passwordInput.setText(password)
            self.rememberMeCheckbox.setChecked(True)


def restart_app():
    QApplication.exit(123)


if __name__ == '__main__':
    currentExitCode = 123
    while currentExitCode == 123:
        app = QApplication(sys.argv)
        with open('style.qss', 'r') as f:
            style = f.read()
        app.setStyleSheet(style)
        loginWindow = LoginWindow()
        loginWindow.show()
        currentExitCode = app.exec_()
        app = None
