from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QWidget, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QThread, pyqtSlot
from PyQt6.QtGui import QPalette, QFont, QIcon
from api.client import APIClient


class LoginWorker(QThread):
    """Worker to perform login on a background thread."""
    success = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, api_client, username, password):
        super().__init__()
        self.api_client = api_client
        self.username = username
        self.password = password

    def run(self):
        try:
            if self.api_client.login(self.username, self.password):
                self.success.emit()
            else:
                self.failed.emit("Invalid credentials. Please try again.")
        except Exception as e:
            self.failed.emit(f"Connection error: {str(e)}")


class LoginWindow(QDialog):
    login_successful = pyqtSignal()

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self._login_worker = None
        self.setWindowTitle("Document Security")
        self.setFixedSize(480, 540)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # For window dragging
        self.dragging = False
        self.drag_position = QPoint()
        
        self.setup_ui()

    def setup_ui(self):
        # Main layout with gradient background
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Custom Title Bar
        title_bar = QWidget()
        title_bar.setFixedHeight(35)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 5, 0)
        title_bar_layout.setSpacing(0)
        
        # Title label
        title_label = QLabel("Document Security - Login")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addStretch()
        
        # Window control buttons
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
                min-width: 35px;
                max-width: 35px;
                min-height: 25px;
                max-height: 25px;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        
        close_button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
                min-width: 35px;
                max-width: 35px;
                min-height: 25px;
                max-height: 25px;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """
        
        # Minimize button
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setStyleSheet(button_style)
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.minimize_btn.setToolTip("Minimize")
        title_bar_layout.addWidget(self.minimize_btn)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet(close_button_style)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("Close")
        title_bar_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(title_bar)
        
        # Background widget with gradient
        background = QWidget()
        background.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f2f5, stop:1 #e8eaf0);
            }
        """)
        
        # Container for centering the card
        container_layout = QVBoxLayout(background)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Login card
        card = QFrame()
        card.setFixedSize(380, 440)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        # Card layout
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 25)
        card_layout.setSpacing(12)
        
        # Welcome title
        welcome_label = QLabel("Welcome")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #1f2937;
                margin-bottom: 4px;
                border: none;
            }
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(welcome_label)
        
        # Subtitle
        subtitle_label = QLabel("Please sign in to continue")
        subtitle_label.setStyleSheet("""
            QLabel {
                border: none;
                font-size: 14px;
                color: #6b7280;
                margin-bottom: 8px;
            }
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle_label)

        # Shared input style
        input_style = """
            QLineEdit {
                padding: 14px 20px 14px 10px;
                border: 2px solid #d1d5db;
                border-radius: 10px;
                font-size: 14px;
                background-color: white;
                color: #1f2937;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
                outline: none;
            }
        """
        
        # Email/Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet(input_style)
        self.username_input.addAction(QIcon('assets/icons/user.png'), QLineEdit.ActionPosition.LeadingPosition)
        self.username_input.returnPressed.connect(self.login)
        card_layout.addWidget(self.username_input)
        card_layout.addSpacing(8)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setStyleSheet(input_style)
        self.password_input.addAction(QIcon('assets/icons/lock.png'), QLineEdit.ActionPosition.LeadingPosition)
        self.password_input.returnPressed.connect(self.login)
        card_layout.addWidget(self.password_input)

        # Status label for loading state
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
                border: none;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        card_layout.addWidget(self.status_label)

        card_layout.addSpacing(16)
        
        # Login button
        self.login_button = QPushButton("Log In")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 25px;
                font-size: 16px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #d1d5db;
                color: #9ca3af;
            }
        """)
        self.login_button.clicked.connect(self.login)
        card_layout.addWidget(self.login_button)
        
        card_layout.addSpacing(20)
        
        # Info text for account creation
        info_label = QLabel("Contact your administrator to create an account")
        info_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 12px;
                border: none;
            }
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(info_label)
        
        # Add card to container
        container_layout.addWidget(card)
        
        # Add background to main layout
        main_layout.addWidget(background)
        
        self.setLayout(main_layout)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return

        # Show loading state
        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.status_label.setText("Connecting to server...")
        self.status_label.setVisible(True)

        # Run login in background thread
        self._login_worker = LoginWorker(self.api_client, username, password)
        self._login_worker.success.connect(self._on_login_success)
        self._login_worker.failed.connect(self._on_login_failed)
        self._login_worker.start()

    @pyqtSlot()
    def _on_login_success(self):
        """Handle successful login from worker thread."""
        self._reset_login_ui()
        self.login_successful.emit()
        self.accept()

    @pyqtSlot(str)
    def _on_login_failed(self, message: str):
        """Handle failed login from worker thread."""
        self._reset_login_ui()
        QMessageBox.warning(self, "Login Failed", message)

    def _reset_login_ui(self):
        """Reset login form to idle state."""
        self.login_button.setEnabled(True)
        self.login_button.setText("Log In")
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.status_label.setVisible(False)

    def close_window(self):
        self.close()
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 35:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging."""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
