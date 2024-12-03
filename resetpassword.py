import re
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from pymongo import MongoClient

class ResetPasswordWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Reset Password')
        layout = QVBoxLayout()

        # MongoDB setup
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['admin']
        self.users_collection = self.db['users']

        # Add logo
        logoLayout = QVBoxLayout()
        logoLabel = QLabel()
        pixmap = QPixmap('logo.jpeg').scaledToWidth(200).scaledToHeight(200)
        logoLabel.setPixmap(pixmap)
        logoLabel.setAlignment(Qt.AlignCenter)
        logoLayout.addWidget(logoLabel)


        layout.addLayout(logoLayout)

        # Email input
        emailLabel = QLabel("Enter your E-mail for verification")
        layout.addWidget(emailLabel)

        self.emailInput = QLineEdit()
        layout.addWidget(self.emailInput)

        # Add a button for sending email
        sendButton = QPushButton("Send Email", clicked=self.sendEmail)
        layout.addWidget(sendButton)

        self.setLayout(layout)

    def sendEmail(self):
        email = self.emailInput.text()
        if not self.validateEmail(email):
            QMessageBox.warning(self, 'Invalid Email', 'Please enter a valid email address.')
            return

        # Check if email exists in the users collection
        if not self.isEmailExists(email):
            QMessageBox.warning(self, 'Email Not Found', 'The provided email does not exist.')
            return

        # Add logic to send email and open confirmation window
        confirmationWindow = self.EmailConfirmationWindow(email, self.users_collection)
        confirmationWindow.passwordResetSuccess.connect(self.closeWindows)
        confirmationWindow.exec_()

    def validateEmail(self, email):
        # Regular expression to validate email format
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email)

    def isEmailExists(self, email):
        user = self.users_collection.find_one({"email": email})
        return user is not None

    def closeWindows(self):
        self.close()

    class EmailConfirmationWindow(QDialog):
        passwordResetSuccess = pyqtSignal()

        def __init__(self, email, users_collection):
            super().__init__()
            self.setWindowTitle('Reset Password')
            self.email = email
            self.users_collection = users_collection
            layout = QVBoxLayout()

            # Add logo
            logoLabel = QLabel(self)
            pixmap = QPixmap('logo.jpeg').scaledToWidth(200).scaledToHeight(100)
            logoLabel.setPixmap(pixmap)
            logoLabel.setAlignment(Qt.AlignCenter)
            layout.addWidget(logoLabel)

            # Add title
            titleLabel = QLabel("Choose Password")
            titleLabel.setAlignment(Qt.AlignCenter)
            titleLabel.setStyleSheet("font-size: 18px; font-weight: bold;")
            layout.addWidget(titleLabel)

            # Add password fields
            newPasswordLabel = QLabel("New Password:")
            newPasswordLabel.setAlignment(Qt.AlignLeft)
            layout.addWidget(newPasswordLabel)

            self.newPasswordInput = QLineEdit()
            self.newPasswordInput.setEchoMode(QLineEdit.Password)
            layout.addWidget(self.newPasswordInput)

            confirmPasswordLabel = QLabel("Confirm New Password:")
            confirmPasswordLabel.setAlignment(Qt.AlignLeft)
            layout.addWidget(confirmPasswordLabel)

            self.confirmPasswordInput = QLineEdit()
            self.confirmPasswordInput.setEchoMode(QLineEdit.Password)
            layout.addWidget(self.confirmPasswordInput)

            # Add button
            resetButton = QPushButton("Reset Password")
            resetButton.clicked.connect(self.resetPassword)
            layout.addWidget(resetButton)

            self.setLayout(layout)

        def resetPassword(self):
            newPassword = self.newPasswordInput.text()
            confirmPassword = self.confirmPasswordInput.text()

            if not self.isValidPassword(newPassword):
                return

            if newPassword != confirmPassword:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return

            # Reset password logic here
            result = self.users_collection.update_one(
                {"email": self.email},
                {"$set": {"password": newPassword}}
            )

            if result.matched_count > 0:
                QMessageBox.information(self, "Success", "Password Successfully changed")
                self.passwordResetSuccess.emit()  # Emit signal for password reset success
                self.close()  # Close the window after password reset
            else:
                QMessageBox.warning(self, "Error", "User not found.")

        def isValidPassword(self, password):
            if len(password) < 6:
                QMessageBox.warning(self, "Error", "Password must be at least 6 characters long.")
                return False
            if not any(char.isupper() for char in password):
                QMessageBox.warning(self, "Error", "Password must contain at least one uppercase letter.")
                return False
            if not re.search(r'[?.!,]', password):
                QMessageBox.warning(self, "Error", "Password must contain at least one special character (.?!,).")
                return False
            return True


if __name__ == '__main__':
    app = QApplication([])
    window = ResetPasswordWindow()
    window.exec_()
