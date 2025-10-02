from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
import qtawesome as qta

class DocumentTable(QTableWidget):
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        vertical_header = self.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)

        header = self.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(len(self.headers) - 1, QHeaderView.ResizeMode.ResizeToContents)

    def set_documents(self, documents, action_callbacks):
        self.setRowCount(len(documents))
        for row, doc in enumerate(documents):
            # Skip ID column - start from filename
            self.setItem(row, 0, QTableWidgetItem(doc.get('filename', '')))
            self.setItem(row, 1, QTableWidgetItem(doc.get('classification', '')))
            
            owner = doc.get('owner')
            print(f"DEBUG Table: Row {row}, owner = {owner}, type = {type(owner)}")
            if owner and isinstance(owner, dict):
                username = owner.get('username', '')
                print(f"DEBUG Table: Setting owner username = {username}")
                self.setItem(row, 2, QTableWidgetItem(username))
            elif owner:
                self.setItem(row, 2, QTableWidgetItem(str(owner)))
            else:
                self.setItem(row, 2, QTableWidgetItem(''))

            self.setItem(row, 3, QTableWidgetItem(doc.get('upload_date', '').split('T')[0]))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)

            if 'view' in action_callbacks:
                view_button = QPushButton(qta.icon('fa5s.eye', color='blue'), "")
                view_button.setToolTip("View Document")
                view_button.clicked.connect(lambda _, r=row: action_callbacks['view'](r))
                actions_layout.addWidget(view_button)

            if 'download' in action_callbacks:
                download_button = QPushButton(qta.icon('fa5s.download', color='green'), "")
                download_button.setToolTip("Download Document")
                download_button.clicked.connect(lambda _, r=row: action_callbacks['download'](r))
                actions_layout.addWidget(download_button)

            if 'share' in action_callbacks:
                share_button = QPushButton(qta.icon('fa5s.share', color='orange'), "")
                share_button.setToolTip("Share Document")
                share_button.clicked.connect(lambda _, r=row: action_callbacks['share'](r))
                actions_layout.addWidget(share_button)
            
            if 'delete' in action_callbacks:
                delete_button = QPushButton(qta.icon('fa5s.trash', color='red'), "")
                delete_button.setToolTip("Delete Document")
                delete_button.clicked.connect(lambda _, r=row: action_callbacks['delete'](r))
                actions_layout.addWidget(delete_button)

            self.setCellWidget(row, len(self.headers) - 1, actions_widget)
