from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtGui import QFont

class HowToTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        howToLabel = QLabel("How To Use This System")
        howToLabel.setFont(QFont("Arial", 18, QFont.Bold))  # Set a larger font size and bold style

        howToContent = QTextEdit()
        howToContent.setReadOnly(True)
        howToContent.setStyleSheet("""
            QTextEdit {
                background-color: #1d2129;  # Dark background color
                color: white;  # White text color
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        howToContent.setPlainText(
            "Instructions on how to use the tokenization system:\n\n"
            "1. **Login**:\n"
            "   - Enter your username and password.\n"
            "   - If you have forgotten your password, use the 'Reset Password' link.\n\n"
            "2. **Create Token**:\n"
            "   - Navigate to the 'Create Token' tab.\n"
            "   - Fill in all the required fields such as owner name, asset title, category, country, city, and description.\n"
            "   - Enter the asset valuation and select the currency.\n"
            "   - Upload the necessary documentation.\n"
            "   - Optionally, you can list the asset on the market.\n"
            "   - Click 'Create Token' to finalize.\n\n"
            "3. **View Tokens**:\n"
            "   - Navigate to the 'View Tokens' tab.\n"
            "   - Use the sort dropdown to filter tokens by value or recent additions.\n"
            "   - Click on 'Click To View' for more details or 'Buy Asset' to purchase.\n\n"
            "4. **Buy Assets**:\n"
            "   - Ensure you have enough balance in your account.\n"
            "   - Click on 'Buy Asset' for the desired token.\n"
            "   - Verify your email if prompted.\n"
            "   - Confirm the purchase to transfer ownership.\n\n"
            "5. **Convert Crypto**:\n"
            "   - Navigate to the 'Convert Crypto' tab.\n"
            "   - Select the cryptocurrency you want to convert.\n"
            "   - Enter the amount and see the equivalent in GBP.\n"
            "   - Ensure you have enough balance and USDT for conversion fees.\n"
            "   - Click 'Convert Crypto' to proceed.\n\n"
            "6. **Asset Management**:\n"
            "   - Navigate to the 'My Assets' tab.\n"
            "   - View, edit, or delete your owned assets.\n"
            "   - Ensure to confirm any changes or deletions.\n\n"
            "For further assistance, please refer to the Help Center tab or contact support at support@example.com."
        )

        layout.addWidget(howToLabel)
        layout.addWidget(howToContent)

        self.setLayout(layout)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = HowToTab()
    window.show()
    sys.exit(app.exec_())
