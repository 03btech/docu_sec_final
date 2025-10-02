from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QPalette, QFont, QIcon
from api.client import APIClient

class LoginWindow(QDialog):
    login_successful = pyqtSignal()

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Document Security")
        self.setFixedSize(480, 520)
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
                background-color: #2c3e50;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 5, 0)
        title_bar_layout.setSpacing(0)
        
        # Title label
        title_label = QLabel("📂 Document Security - Login")
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
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        
        minimize_button_style = button_style
        maximize_button_style = button_style
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
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """
        
        # Minimize button
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setStyleSheet(minimize_button_style)
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.minimize_btn.setToolTip("Minimize")
        title_bar_layout.addWidget(self.minimize_btn)
        
        # Maximize/Restore button
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setStyleSheet(maximize_button_style)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.maximize_btn.setToolTip("Maximize")
        title_bar_layout.addWidget(self.maximize_btn)
        
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
        card.setFixedSize(360, 420)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #e0e4e7;
            }
        """)
        
        # Card layout
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)
        
        # Welcome title
        welcome_label = QLabel("Welcome")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
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
                color: #7f8c8d;
                margin-bottom: 10px;
            }
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle_label)
        
        # Email/Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 18px 25px 18px 10px;
                border: 2px solid #27ae60;
                border-radius: 30px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
                outline: none;
            }
        """)
        # add user icon on the left
        self.username_input.addAction(QIcon('assets/icons/user.png'), QLineEdit.ActionPosition.LeadingPosition)
        # Bind Enter key to login
        self.username_input.returnPressed.connect(self.login)
        card_layout.addWidget(self.username_input)
        # space between email and password
        card_layout.addSpacing(12)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 18px 25px 18px 10px;
                border: 2px solid #bdc3c7;
                border-radius: 30px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #27ae60;
                outline: none;
            }
        """)
        # add lock icon on the left
        self.password_input.addAction(QIcon('assets/icons/lock.png'), QLineEdit.ActionPosition.LeadingPosition)
        # Bind Enter key to login
        self.password_input.returnPressed.connect(self.login)
        card_layout.addWidget(self.password_input)

        # Add some spacing before button
        card_layout.addSpacing(25)
        
        # Login button
        self.login_button = QPushButton("Log In")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: 2px solid #bdc3c7;
                border-radius: 30px;
                padding: 18px 25px;
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
        """)
        self.login_button.clicked.connect(self.login)
        card_layout.addWidget(self.login_button)
        
        # Add some spacing at bottom
        card_layout.addSpacing(30)
        
        # Info text for account creation
        info_label = QLabel("Contact your administrator to create an account")
        info_label.setStyleSheet("""
            QLabel {
                color: #95a5a6;
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

        if self.api_client.login(username, password):
            print("Login successful, redirecting to dashboard")
            self.login_successful.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid credentials. Please try again.")

    def close_window(self):
        self.close()

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setText("□")
            self.maximize_btn.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")
            self.maximize_btn.setToolTip("Restore")
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only allow dragging from the top area (title bar region)
            if event.position().y() < 35:  # Title bar height
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
