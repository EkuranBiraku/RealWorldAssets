from PyQt5.QtWidgets import (QHBoxLayout, QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QScrollArea, QGridLayout,
                             QFrame, QMessageBox, QDialog, QLineEdit, QComboBox, QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QDoubleValidator, QColor, QPainter, QBrush
from pymongo import MongoClient
import re
import sys


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

        # Draw rounded rectangle
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 12.5, 12.5)

        # Draw circle
        circle_rect = QRect(2, 2, 21, 21) if not self.isChecked() else QRect(25, 2, 21, 21)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(circle_rect)

        painter.end()

    def mouseReleaseEvent(self, event):
        # Toggle the checked state
        self.setChecked(not self.isChecked())  # Corrected from !self.isChecked() to not self.isChecked()
        self.update()  # Trigger a repaint to update the visual state
        super().mouseReleaseEvent(event)


class AssetCard(QFrame):
    assetDeleted = pyqtSignal()  # Signal to notify asset deletion
    assetUpdated = pyqtSignal()  # Signal to notify asset updates (new signal)

    def __init__(self, asset, delete_callback, edit_callback):
        super().__init__()
        self.asset = asset
        self.delete_callback = delete_callback
        self.edit_callback = edit_callback
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #ADD8E6; /* Light blue border */
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
                background-color: #1d2129;
            }
            QLabel {
                font-size: 14px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton#btn_edit {
                background-color: lightblue;
                color:black;
            }
            QPushButton#btn_edit:hover {
                background-color: #31b0d5;
                color:black;
            }
        """)

        layout = QVBoxLayout()

        asset_name_label = QLabel(f"Art Name: {self.asset.get('asset', 'Unknown')}")
        asset_value_label = QLabel(f"Art Value: {self.asset.get('asset_valuation', 'N/A')}")
        public_key_part_label = QLabel(f"Public Key:  ...{self.extract_public_key_part(self.asset.get('owner_public_key', ''))}")
        asset_description_label = QLabel(f"Description: {self.asset.get('asset_description', 'No description provided')}")

        market_status = self.asset.get('for_sale', False)
        market_status_label = QLabel(f"{'Listed on Market' if market_status else 'Not Listed on Market'}")
        market_status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {'lightgreen' if market_status else 'lightcoral'};
                color: black;
                padding: 5px;
                border-radius: 4px;
            }}
        """)

        btn_delete = QPushButton('Delete')
        btn_delete.clicked.connect(lambda: self.delete_callback(self.asset['id']))

        btn_edit = QPushButton('Edit')
        btn_edit.setObjectName("btn_edit")  # Set the object name for styling

        btn_edit.clicked.connect(lambda: self.edit_callback(self.asset))

        layout.addWidget(asset_name_label)
        layout.addWidget(asset_value_label)
        layout.addWidget(asset_description_label)
        layout.addWidget(market_status_label)
        layout.addWidget(public_key_part_label)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

    def extract_public_key_part(self, public_key):
        match = re.search(r"-----BEGIN PUBLIC KEY-----(.*?)-----END PUBLIC KEY-----", public_key, re.DOTALL)
        if match:
            extracted_key = match.group(1).strip().replace("\n", "")
            last_eight = extracted_key[-8:]
            return last_eight
        return ""


class AssetsWindow(QWidget):
    assetDeleted = pyqtSignal()  # Signal to notify asset deletion
    assetUpdated = pyqtSignal()  # Signal to notify asset updates (new signal)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']
        self.initUI()

    def initUI(self):
        self.setWindowTitle("My Digital Art Assets")
        self.resize(700, 600)  # Adjusted size for the new layout

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main container widget for the scroll area
        container = QWidget()
        self.grid_layout = QGridLayout(container)
        self.grid_layout.setSpacing(10)

        scroll_area.setWidget(container)

        # No assets label
        self.noAssetsLabel = QLabel("No Digital Art Assets to View")
        self.noAssetsLabel.setAlignment(Qt.AlignCenter)
        self.noAssetsLabel.hide()

        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        layout.addWidget(self.noAssetsLabel)
        self.setLayout(layout)

        self.loadAssets()

    def loadAssets(self):
        assets = self.fetchUserAssets(self.username)
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        if not assets:
            self.noAssetsLabel.show()
        else:
            self.noAssetsLabel.hide()
            for i, asset in enumerate(assets):
                asset_card = AssetCard(asset, self.confirmDeleteAsset, self.editAsset)
                self.grid_layout.addWidget(asset_card, i // 2, i % 2)

    def fetchUserAssets(self, username):
        user_assets = list(self.ledger_collection.find({'owner': username, 'asset_category': 'Art'}))
        return user_assets

    def confirmDeleteAsset(self, asset_id):
        reply = QMessageBox.question(self, 'Delete Asset', 'Are you sure you want to delete this digital art asset?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.deleteAsset(asset_id)

    def deleteAsset(self, asset_id):
        self.ledger_collection.delete_one({'id': asset_id})
        self.loadAssets()
        self.assetDeleted.emit()  # Emit the signal after asset deletion

    def editAsset(self, asset):
        edit_dialog = EditAssetDialog(asset, self)
        edit_dialog.assetUpdated.connect(self.loadAssets)  # Connect the signal to refresh assets
        edit_dialog.assetUpdated.connect(self.assetUpdated.emit)  # Emit the assetUpdated signal after edit
        edit_dialog.exec_()


class EditAssetDialog(QDialog):
    assetUpdated = pyqtSignal()  # Signal to notify that the asset was updated

    def __init__(self, asset, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['admin']
        self.ledger_collection = self.db['ledger']
        self.setWindowTitle("Edit Digital Art Asset")
        self.setFixedSize(400, 600)  # Adjust the size as needed
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Image
        self.imageLabel = QLabel(self)
        pixmap = QPixmap(self.asset['image_file_path']).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.imageLabel)

        # Asset Name
        layout.addWidget(QLabel("Art Name"))
        self.assetNameInput = QLineEdit(self.asset['asset'])
        self.assetNameInput.setMaxLength(30)
        self.assetNameInput.setReadOnly(True)  # Make the input read-only
        layout.addWidget(self.assetNameInput)

        # Asset Description
        layout.addWidget(QLabel(" Description"))
        self.assetDescriptionInput = QTextEdit(self.asset['asset_description'])
        self.assetDescriptionInput.setFixedHeight(80)
        layout.addWidget(self.assetDescriptionInput)

        # Asset Valuation
        layout.addWidget(QLabel("Asset Valuation"))
        valuationLayout = QHBoxLayout()
        self.assetValuationInput = QLineEdit()
        self.assetValuationInput.setValidator(QDoubleValidator(0.99, 9999999999.99, 2))  # Set range and decimal places
        self.assetValuationInput.setFixedWidth(200)

        self.currencyComboBox = QComboBox()
        self.currencyComboBox.addItems(['USDT', 'BTC', 'ETH'])
        valuationLayout.addWidget(self.assetValuationInput)
        valuationLayout.addWidget(self.currencyComboBox)
        layout.addLayout(valuationLayout)

        # Set initial values for valuation input and currency
        valuation_value, currency = self.asset['asset_valuation'].split()
        self.assetValuationInput.setText(valuation_value)
        self.currencyComboBox.setCurrentText(currency)

        # Toggle button for listing on market
        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("List on market")
        toggle_label.setStyleSheet("font-size: 16px;")  # Set the font size
        self.listOnMarketToggle = ToggleSwitch()
        self.listOnMarketToggle.setChecked(self.asset.get('for_sale', False))
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addWidget(self.listOnMarketToggle)
        toggle_layout.addStretch()
        toggle_layout.setContentsMargins(0, 0, 0, 0)  # Remove any margins
        layout.addLayout(toggle_layout)

        # Save button
        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.saveAsset)
        layout.addWidget(saveButton)

        self.setLayout(layout)

    def saveAsset(self):
        # Update the asset data
        self.asset['asset'] = self.assetNameInput.text()
        self.asset['asset_description'] = self.assetDescriptionInput.toPlainText()
        self.asset['asset_valuation'] = f"{self.assetValuationInput.text()} {self.currencyComboBox.currentText()}"
        self.asset['for_sale'] = self.listOnMarketToggle.isChecked()

        # Save the updated asset to the ledger
        try:
            self.ledger_collection.update_one({'id': self.asset['id']}, {'$set': self.asset})
            self.assetUpdated.emit()  # Emit the signal to notify that the asset was updated
            self.accept()  # Close the dialog
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred while saving the asset: {str(e)}')


if __name__ == '__main__':
    app = QApplication([])
    assetsWindow = AssetsWindow("username")
    assetsWindow.show()
    sys.exit(app.exec_())
