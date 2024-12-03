from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize, pyqtSignal

from cart import CartWindow
from myprofile import UserProfileWindow
from backpayment import BackPaymentHandler


class HeaderWidget(QWidget):
    basketCleared = pyqtSignal()  # Define the signal to indicate basket is cleared

    def __init__(self, mainApp, username=None, email=None, back_payment_handler=None, parent=None):
        super().__init__(parent)
        self.mainApp = mainApp
        self.username = username
        self.email = email
        self.back_payment_handler = back_payment_handler

        self.userProfileWindow = None
        self.basket_count = 0  # Initialize basket count
        self.mainApp.displayTokensTab.basketUpdated.connect(self.updateBasketCount)

        self.initUI()

    def initUI(self):
        layout = QGridLayout()

        # Add logo
        logoLabel = QLabel(self)
        pixmap = QPixmap('logo.jpeg').scaledToWidth(500).scaledToHeight(170)
        logoLabel.setPixmap(pixmap)
        logoLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(logoLabel, 0, 0, 1, 0)

        # Remove the title code entirely (was here)

        # Add icons for My Profile and Basket
        myProfileButton = QPushButton()
        myProfileButton.setIcon(QIcon('myprofile.png'))
        myProfileButton.setIconSize(QSize(30, 30))  # Increase the icon size
        myProfileButton.setFixedSize(50, 50)  # Increase the button size
        myProfileButton.setToolTip('My Profile')
        myProfileButton.clicked.connect(self.showUserProfile)  # Connect to profile method

        # Basket icon button
        self.basketButton = QPushButton()
        self.updateBasketIcon()  # Set the initial basket icon
        self.basketButton.setIconSize(QSize(30, 30))  # Increase the icon size
        self.basketButton.setFixedSize(50, 50)  # Increase the button size
        self.basketButton.setToolTip('View Basket')
        self.basketButton.clicked.connect(self.showBasket)

        layout.addWidget(myProfileButton, 0, 1)
        layout.addWidget(self.basketButton, 0, 2)

        layout.setColumnStretch(0, 1)
        layout.setContentsMargins(0, 0, 10, 0)

        self.setLayout(layout)

    def updateBasketIcon(self):
        print(f"Current basket count: {self.basket_count}")  # Debugging

        icon_pixmap = QPixmap('cart.png').scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        painter = QPainter(icon_pixmap)

        if self.basket_count > 0:
            print("Drawing badge on basket icon")  # Debug statement
            badge_size = 40
            badge_x = icon_pixmap.width() - 35
            badge_y = -5
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)

            painter.setPen(QColor(255, 255, 255))
            font = QFont('Arial', 12, QFont.Bold)
            font.setPointSize(14)
            painter.setFont(font)

            text_x = badge_x
            text_y = badge_y
            painter.drawText(text_x, text_y, badge_size, badge_size, Qt.AlignCenter, str(self.basket_count))
        else:
            print("No items in the basket, not drawing badge")  # Debug statement

        painter.end()
        self.basketButton.setIcon(QIcon(icon_pixmap))

    def updateBasketCount(self, count):
        print(f"Updating basket count to: {count}")  # Debugging
        self.basket_count = count  # Ensure this is updating properly
        self.updateBasketIcon()  # Call method to redraw the icon

    def showUserProfile(self):
        if not self.userProfileWindow:
            self.userProfileWindow = UserProfileWindow(self.mainApp, self.username, self.email,
                                                       self.back_payment_handler)
        self.userProfileWindow.show()

    def showBasket(self):
        # Create an instance of the CartWindow with the basket from the main app
        cart_window = CartWindow(self.mainApp.displayTokensTab.basket, self.username, self.back_payment_handler, self)

        cart_window.basketCleared.connect(self.updateBasketAfterClear)  # Update the basket count after item removal
        cart_window.basketCleared.connect(
            self.mainApp.displayTokensTab.updateTokenTable)  # Update the token table when the basket is cleared
        cart_window.appUpdated.connect(
            self.updateBasketCountAfterItemChange)  # Refresh basket count after trade completion

        cart_window.exec_()

    def updateBasketCountAfterItemChange(self):
        # Reload the basket directly from the database
        updated_basket = self.mainApp.displayTokensTab.loadCartFromDatabase()

        # Update the basket count based on the new basket data
        self.updateBasketCount(len(updated_basket))

    def updateBasketAfterClear(self):
        # Update the basket count after clearing or removing items
        self.updateBasketCount(len(self.mainApp.displayTokensTab.basket))

    def clearBasket(self):
        """Method to handle clearing of the basket."""
        self.basket_count = 0  # Reset basket count
        self.updateBasketIcon()  # Update the basket icon
        self.basketCleared.emit()  # Emit the basketCleared signal to update other components
