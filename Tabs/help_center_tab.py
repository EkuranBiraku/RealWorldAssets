from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtGui import QFont

class HelpCenterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        helpLabel = QLabel("Help Center")
        helpLabel.setFont(QFont("Arial", 18, QFont.Bold))  # Set a larger font size and bold style

        helpContent = QTextEdit()
        helpContent.setReadOnly(True)
        helpContent.setStyleSheet("""
            QTextEdit {
                background-color: #1d2129;  # Dark background color
                color: white;  # White text color
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        helpContent.setPlainText(
            "Welcome to the Help Center.\n\n"
            "Here you can find information on how to use the application:\n\n"
            "1. **Login**: Enter your username and password to login.\n"
            "2. **Create Token**: Navigate to the 'Create Token' tab to create a new token. Fill in all required fields and upload documentation.\n"
            "3. **View Tokens**: In the 'View Tokens' tab, you can browse all available tokens. Use the sort options to filter tokens as needed.\n"
            "4. **Buy Assets**: To buy an asset, click on the 'Buy Asset' button. Ensure you have enough balance to complete the transaction.\n"
            "5. **Convert Crypto**: Use the 'Convert Crypto' tab to convert your cryptocurrency to GBP.\n"
            "6. **Asset Management**: In the 'My Assets' tab, you can view, edit, or delete your owned assets.\n\n"
            "For further assistance, please contact support at support@example.com."
        )

        layout.addWidget(helpLabel)
        layout.addWidget(helpContent)

        self.setLayout(layout)
