from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QComboBox, QLabel, QFrame, \
    QGraphicsOpacityEffect, QPushButton, QMessageBox, QDialog, QGridLayout
from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QPixmap
from pymongo import MongoClient
from backpayment import BackPaymentHandler


class DisplayTokensTab(QWidget):
    basketUpdated = pyqtSignal(int)  # Signal for basket updates

    def __init__(self, username, user_email):
        super().__init__()
        self.username = username
        self.user_email = user_email
        self.back_payment_handler = BackPaymentHandler()
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']
        self.cart_collection = self.db['cart']  # Reference to the cart collection in MongoDB

        self.basket = self.loadCartFromDatabase() or []



        self.initUI()
        # Emit signal with the current basket count on initialization
        self.basketUpdated.emit(len(self.basket))  # Emit the signal

    def initUI(self):
        layout = QVBoxLayout()

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        scroll_area.setWidget(self.scroll_content)

        # Hide the scroll bar
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Sort Dropdown Layout
        dropdown_layout = QHBoxLayout()
        self.sortDropdown = QComboBox()
        self.sortDropdown.addItems(['Sort by Valuation (Low to High)', 'Sort by Valuation (High to Low)', 'Recent'])
        self.sortDropdown.setFixedWidth(250)  # Set the width to 250 pixels or adjust as needed

        self.sortDropdown.currentIndexChanged.connect(self.onSortOrderChanged)
        dropdown_layout.addWidget(QLabel(''))
        dropdown_layout.addWidget(self.sortDropdown)

        layout.addLayout(dropdown_layout)
        layout.addWidget(scroll_area)
        self.setLayout(layout)

        self.updateTokenTable()  # Call this method to display tokens immediately

        # Connect basketCleared signal to update buttons
        parent_widget = self.parentWidget()  # Get reference to the parent widget (HeaderWidget)
        if parent_widget and hasattr(parent_widget, 'basketCleared'):
            parent_widget.basketCleared.connect(self.updateButtonsAfterClear)

    def updateTokenTable(self):
        self.clearLayout(self.scroll_layout)  # Clear the layout before updating

        self.ledger = list(self.ledger_collection.find({"for_sale": True}))  # Refresh the tokens for sale
        self.scroll_layout.setAlignment(Qt.AlignTop)
        row_layout = QHBoxLayout()
        for index, token in enumerate(self.ledger):
            if index % 4 == 0 and index != 0:
                self.scroll_layout.addLayout(row_layout)
                row_layout = QHBoxLayout()
            self.addTokenToLayout(token, row_layout)

        if row_layout.count() > 0:
            self.scroll_layout.addLayout(row_layout)

        # Update the buttons after the table is updated
        self.updateButtonsAfterClear()

    def updateButtonsAfterClear(self):
        # Change all buttons back to "Add to Cart" after clearing the basket
        for i in range(self.scroll_layout.count()):
            row_layout = self.scroll_layout.itemAt(i)
            if row_layout:
                for j in range(row_layout.count()):
                    frame = row_layout.itemAt(j).widget()
                    if frame and isinstance(frame, QFrame):
                        buttons = frame.findChildren(QPushButton)
                        for button in buttons:
                            if button.text() == "Remove from Cart":
                                button.setText("Add to Cart")
                                button.setStyleSheet("""
                                    QPushButton {
                                        background-color: lightblue;
                                        color: black;
                                        border: none;
                                        padding: 5px 10px;
                                        border-radius: 4px;
                                    }
                                    QPushButton:hover {
                                        background-color: #87CEEB;
                                    }
                                """)

    def addTokenToLayout(self, token, layout):
        # Create a frame for each token
        token_frame = QFrame()
        token_frame.setFrameShape(QFrame.StyledPanel)
        token_frame.setFixedSize(288, 250)  # Set fixed size to make cells square
        token_layout = QVBoxLayout(token_frame)

        # Add image
        image_label = QLabel()
        pixmap = QPixmap(token['image_file_path']).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        token_layout.addWidget(image_label)

        # Add view and basket buttons but initially hide them
        button_layout = QHBoxLayout()
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        button_widget.setGraphicsEffect(QGraphicsOpacityEffect(button_widget))
        button_widget.setVisible(True)  # Keep buttons widget visible

        btn_view = QPushButton("Click To View", token_frame)
        btn_view.setFixedSize(110, 40)  # Set fixed size
        btn_view.clicked.connect(lambda checked, token=token: self.showImageDialog(token))
        button_layout.addWidget(btn_view, alignment=Qt.AlignCenter)

        if token['owner'] != self.username:  # Only show the basket button if the user is not the owner
            btn_add_to_basket = QPushButton("Add to Cart", token_frame)
            btn_add_to_basket.setFixedSize(150, 40)  # Set fixed size
            btn_add_to_basket.setStyleSheet("""
                               QPushButton {
                                   background-color: lightblue;
                                   color: black;
                                   border: none;
                                   padding: 5px 10px;
                                   border-radius: 4px;
                               }
                               QPushButton:hover {
                                   background-color: #87CEEB;
                               }
                           """)
            btn_add_to_basket.clicked.connect(
                lambda checked, token=token, btn=btn_add_to_basket: self.toggleBasket(token, btn))
            button_layout.addWidget(btn_add_to_basket, alignment=Qt.AlignCenter)

            # Set initial button state if the token is already in the basket
            if token in self.basket:
                btn_add_to_basket.setText("Remove from Cart")
                btn_add_to_basket.setStyleSheet("""
                                   QPushButton {
                                       background-color: #ff6666;
                                       color: black;
                                       border: none;
                                       padding: 5px 10px;
                                       border-radius: 4px;
                                   }
                                   QPushButton:hover {
                                       background-color: #ff9999;
                                   }
                               """)

        token_layout.addWidget(button_widget)

        # Set initial opacity to 0 to hide buttons initially
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0)
        button_widget.setGraphicsEffect(opacity_effect)

        # Add hover event to token frame to show/hide buttons
        token_frame.enterEvent = lambda event: self.fadeInButtons(button_widget)
        token_frame.leaveEvent = lambda event: self.fadeOutButtons(button_widget)

        layout.addWidget(token_frame)

        # Modify the toggleBasket function to handle MongoDB saving
        def toggleBasket(self, token, btn):
            if token in self.basket:
                self.basket.remove(token)
                btn.setText("Add to Cart")
                btn.setStyleSheet(""" 
                    QPushButton { 
                        background-color: lightblue;
                        color: black;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #87CEEB;
                    }
                """)
                QMessageBox.information(self, 'Removed from Cart', f"{token['asset']} has been removed from your cart.")
            else:
                self.basket.append(token)
                btn.setText("Remove from Cart")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6666;
                        color: black;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #ff9999;
                    }
                """)
                QMessageBox.information(self, 'Added to Cart', f"{token['asset']} has been added to your cart.")

            self.saveCartToDatabase()  # Save the updated cart to MongoDB
            self.basketUpdated.emit(len(self.basket))  # Emit signal with updated basket count
    def updateButtonsAfterClear(self):
        # Change all buttons back to "Add to Basket" after clearing the basket
        for i in range(self.scroll_layout.count()):
            row_layout = self.scroll_layout.itemAt(i)
            if row_layout:
                for j in range(row_layout.count()):
                    frame = row_layout.itemAt(j).widget()
                    if frame and isinstance(frame, QFrame):
                        buttons = frame.findChildren(QPushButton)
                        for button in buttons:
                            if button.text() == "Remove from Cart":
                                button.setText("Add to Cart")
                                button.setStyleSheet("""
                                   QPushButton {
                                       background-color: lightblue;
                                       color: black;
                                       border: none;
                                       padding: 5px 10px;
                                       border-radius: 4px;
                                   }
                                   QPushButton:hover {
                                       background-color: #87CEEB;
                                   }
                               """)

    def fadeInButtons(self, widget):
        widget.setVisible(True)
        opacity_effect = widget.graphicsEffect()
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(500)  # Duration in milliseconds
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
        widget.animation = animation  # Keep a reference to avoid garbage collection

    def fadeOutButtons(self, widget):
        opacity_effect = widget.graphicsEffect()
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(500)  # Duration in milliseconds
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.finished.connect(lambda: widget.setVisible(True))
        animation.start()
        widget.animation = animation  # Keep a reference to avoid garbage collection

    def onSortOrderChanged(self):
        sort_order = self.sortDropdown.currentIndex()
        if sort_order == 2:  # Recent
            self.sortTableByRecent()
        else:
            ascending = sort_order == 0
            self.sortTableByValuation(ascending)

    def sortTableByRecent(self):
        self.ledger.sort(key=lambda x: x['_id'], reverse=True)
        self.updateTokenTable()

    def sortTableByValuation(self, ascending=True):
        self.ledger.sort(key=lambda x: float(x['art_valuation'].split()[0]), reverse=not ascending)
        self.updateTokenTable()

    def clearLayout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clearLayout(child.layout())

    def showImageDialog(self, token):
        dialog = ImageDialog(token, self)
        dialog.exec_()

    def addToBasket(self, token):
        # Logic to add the art to the user's basket
        self.basket.append(token)
        QMessageBox.information(self, 'Added to Basket', f"{token['asset']} has been added to your basket.")
        self.basketUpdated.emit(len(self.basket))  # Emit signal with updated basket count

    def clearBasket(self):
        """Clear the basket and reset all buttons to 'Add to Basket'."""
        self.basket.clear()  # Clear the basket list
        self.updateTokenTable()  # Update the table to reset the buttons
        self.basketUpdated.emit(len(self.basket))  # Emit the updated basket count
    def loadCartFromDatabase(self):
        if self.username:
            user_cart = self.cart_collection.find_one({"username": self.username})
            if user_cart and "basket" in user_cart:
                return user_cart["basket"]
        return list(self.db['cart'].find({"user": self.username}))

        # New method to save the cart to MongoDB

    def toggleBasket(self, token, btn):
        if token in self.basket:
            self.basket.remove(token)
            btn.setText("Add to Cart")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: lightblue;
                    color: black;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #87CEEB;
                }
            """)
            QMessageBox.information(self, 'Removed from Cart', f"{token['asset']} has been removed from your cart.")
        else:
            self.basket.append(token)
            btn.setText("Remove from Cart")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff6666;
                    color: black;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #ff9999;
                }
            """)
            QMessageBox.information(self, 'Added to Cart', f"{token['asset']} has been added to your cart.")

        self.saveCartToDatabase()  # Save the updated basket to MongoDB
        self.basketUpdated.emit(len(self.basket))  # Emit signal with updated basket count

    # New method to save the basket to MongoDB
    def saveCartToDatabase(self):
        if self.username:
            self.cart_collection.update_one(
                {"username": self.username},
                {"$set": {"basket": self.basket}},
                upsert=True  # Create document if it doesn't exist
            )


class ImageDialog(QDialog):
    def __init__(self, token, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("View Art")
        self.setFixedSize(800, 800)  # Set the dialog size
        self.setupUI(token)
        self.setupAnimation()

    def setupUI(self, token):
        # Setup UI components
        self.imageLabel = QLabel(self)
        self.imageLabel.setPixmap(QPixmap(token['image_file_path']).scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.imageLabel.setAlignment(Qt.AlignCenter)  # Ensure the label is centered

        # Create a main layout
        main_layout = QVBoxLayout()

        # Add the image to the main layout
        main_layout.addWidget(self.imageLabel, alignment=Qt.AlignCenter)

        # Add an empty widget to create space between the image and the labels
        spacer_widget = QWidget()
        spacer_widget.setFixedHeight(40)  # Adjust the height as needed
        main_layout.addWidget(spacer_widget)

        # Create a grid layout for the details
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(20, 20, 20, 20)  # Add margins around the grid
        grid_layout.setHorizontalSpacing(60)  # Add spacing between columns
        grid_layout.setVerticalSpacing(20)  # Add spacing between rows

        # Add data to the grid layout with emojis
        data = [
            ("🎨 Art Title", token['asset']),
            ("👨‍🎨️ Artist", token['artist_name']),
            ("🗓️ Creation Date", token['creation_date']),
            ("💲 Valuation", token['asset_valuation']),
            ("📝 Description", token['asset_description']),
        ]

        for index, (label_text, valuation_text) in enumerate(data):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 18px; text-align: center;")
            valuation = QLabel(valuation_text)
            valuation.setStyleSheet("font-size: 16px; text-align: center;color:white;")

            vertical_layout = QVBoxLayout()
            vertical_layout.addWidget(label, alignment=Qt.AlignCenter)
            vertical_layout.addWidget(valuation, alignment=Qt.AlignCenter)

            frame = QFrame()
            frame.setLayout(vertical_layout)
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setStyleSheet("color:lightblue;")

            row = index // 2
            col = index % 2

            grid_layout.addWidget(frame, row, col, alignment=Qt.AlignTop)

        main_layout.addLayout(grid_layout)
        main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(main_layout)

    def setupAnimation(self):
        # Setup the opacity animation
        self.opacityAnimation = QPropertyAnimation(self, b'windowOpacity')
        self.opacityAnimation.setDuration(500)  # Duration in milliseconds
        self.opacityAnimation.setStartValue(0)  # Start fully transparent
        self.opacityAnimation.setEndValue(1)  # End fully opaque
        self.opacityAnimation.setEasingCurve(QEasingCurve.Linear)

    def showEvent(self, event):
        # Start the fade-in animation when the dialog shows
        self.opacityAnimation.start()
        super().showEvent(event)

    def closeEvent(self, event):
        # Start the fade-out animation when the dialog closes
        self.opacityAnimation.setDirection(QPropertyAnimation.Backward)
        self.opacityAnimation.finished.connect(self.accept)  # Close the dialog after animation completes
        self.opacityAnimation.start()
        event.ignore()  # Ignore the initial close event to allow animation to complete
        # New method to load the cart from MongoDB

