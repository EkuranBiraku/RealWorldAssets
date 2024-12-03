from PyQt5.QtWidgets import QSizePolicy, QSpacerItem, QWidget, QVBoxLayout, QTabWidget, QDesktopWidget
from header_widget import HeaderWidget
from Tabs.create_token_tab import CreateTokenTab
from Tabs.display_tokens_tab import DisplayTokensTab
from Tabs.how_to_tab import HowToTab
from Tabs.help_center_tab import HelpCenterTab
from Tabs.payment import PaymentTab
from backpayment import BackPaymentHandler


class TokenApp(QWidget):
    def __init__(self, username=None, email=None):
        super().__init__()
        self.username = username
        self.email = email
        self.back_payment_handler = BackPaymentHandler()  # Initialize the back payment handler

        # Initialize DisplayTokensTab once
        self.displayTokensTab = DisplayTokensTab(self.username, self.email)

        self.initUI()
        self.displayTokensTab.basketUpdated.emit(len(self.displayTokensTab.basket))  # Emit signal with basket count


    def initUI(self):
        self.setWindowTitle('Digital Art Tokenization System')

        # Header widget with username, email, and back payment handler
        self.headerWidget = HeaderWidget(self, self.username, self.email, self.back_payment_handler)
        self.displayTokensTab.basketUpdated.connect(self.headerWidget.updateBasketCount)

        self.setFixedSize(1250, 1000)  # Set a fixed size for the window
        self.documentationList = None

        # Tab widget to hold all tabs
        self.tabWidget = QTabWidget()

        # Create Token Tab (for Digital Art)
        self.createTokenTab = CreateTokenTab(self.username, self.back_payment_handler)

        # Payment Tab (Buy Cryptocurrency)
        self.paymentTab = PaymentTab(self.username, self.back_payment_handler)

        # Withdraw Crypto Tab (Withdraw to GBP)

        # Convert Crypto Tab (Convert Cryptocurrency)

        # How To Tab (Instructions and Guides)
        self.howToTab = HowToTab()

        # Help Center Tab (Support and FAQs)
        self.helpCenterTab = HelpCenterTab()

        # Connect the basketCleared signal to update the header basket count when items are removed
        self.displayTokensTab.basketUpdated.connect(self.headerWidget.updateBasketCount)

        # Layout for main window
        layout = QVBoxLayout()
        layout.addWidget(self.headerWidget)  # Add header widget to the layout
        layout.addWidget(self.tabWidget)
        self.setLayout(layout)

        # Adding tabs to the tab widget
        self.tabWidget.addTab(self.createTokenTab, 'Create Digital Art')
        self.tabWidget.addTab(self.displayTokensTab, 'Art Marketplace')  # Only use the existing instance
        self.tabWidget.addTab(self.paymentTab, 'Buy Cryptocurrency')
        self.tabWidget.addTab(self.howToTab, 'How To')
        self.tabWidget.addTab(self.helpCenterTab, 'Help Center')

        # Set the default tab to the Buy Cryptocurrency tab
        self.tabWidget.setCurrentWidget(self.paymentTab)

        # Connect signals between tabs
        self.createTokenTab.tokenCreated.connect(self.displayTokensTab.updateTokenTable)

        # Connect the basketUpdated signal to the header widget's updateBasketCount method
        self.displayTokensTab.basketUpdated.connect(self.headerWidget.updateBasketCount)

        # Connect the basketCleared signal to update the tokens tab buttons
        self.headerWidget.basketCleared.connect(self.displayTokensTab.updateButtonsAfterClear)

        # Connect the tab change signal to detect when the "Create Digital Art" tab is selected
        self.tabWidget.currentChanged.connect(self.onTabChanged)

    def onTabChanged(self, index):
        # Trigger USDT check only when the Create Digital Art tab is selected
        if self.tabWidget.tabText(index) == 'Create Digital Art':
            self.createTokenTab.onTabSelected()

    def refreshDisplayTokensTab(self):
        """Refresh the display tokens tab to reflect changes."""
        self.displayTokensTab.updateTokenTable()

    def showEvent(self, event):
        """Center the window on the screen when shown."""
        super().showEvent(event)
        self.center()

    def center(self):
        """Center the application window on the screen."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def connectAssetDeletedSignal(self, assetsWindow):
        # Connect the assetDeleted signal from AssetsWindow to refresh the display tokens tab
        assetsWindow.assetDeleted.connect(self.refreshDisplayTokensTab)