from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QWidget, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from api.client import APIClient
import requests

class SignupWindow(QDialog):
    signup_successful = pyqtSignal()

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Create Account")
        self.setFixedSize(480, 780)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.departments = []
        self.setup_ui()
        self.load_departments()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        background = QWidget()
        background.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f2f5, stop:1 #e8eaf0);
            }
        """)
        
        container_layout = QVBoxLayout(background)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card = QFrame()
        card.setFixedSize(400, 720)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #e0e4e7;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)
        
        title_label = QLabel("Create Account")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
                border: none;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)
        
        input_style = """
            QLineEdit, QComboBox {
                padding: 12px 20px;
                border: 2px solid #bdc3c7;
                border-radius: 25px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #27ae60;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(assets/icons/down_arrow.png); 
            }
        """

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setStyleSheet(input_style)
        card_layout.addWidget(self.email_input)

        self.firstname_input = QLineEdit()
        self.firstname_input.setPlaceholderText("Firstname")
        self.firstname_input.setStyleSheet(input_style)
        card_layout.addWidget(self.firstname_input)

        self.lastname_input = QLineEdit()
        self.lastname_input.setPlaceholderText("Lastname")
        self.lastname_input.setStyleSheet(input_style)
        card_layout.addWidget(self.lastname_input)

        self.department_combo = QComboBox()
        self.department_combo.setStyleSheet(input_style)
        card_layout.addWidget(self.department_combo)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(input_style)
        card_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setStyleSheet(input_style)
        card_layout.addWidget(self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setStyleSheet(input_style)
        card_layout.addWidget(self.confirm_password_input)

        card_layout.addSpacing(20)

        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
            QPushButton:pressed { background-color: #1e8449; }
        """)
        self.signup_button.clicked.connect(self.signup)
        card_layout.addWidget(self.signup_button)

        card_layout.addSpacing(20)

        links_layout = QHBoxLayout()
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        login_label = QLabel("Already have an account?")
        login_label.setStyleSheet("color: #7f8c8d; font-size: 14px; border: none;")
        
        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #27ae60;
                font-size: 14px;
                text-decoration: underline;
                padding: 0;
            }
            QPushButton:hover { color: #229954; }
        """)
        self.login_button.clicked.connect(self.accept)

        links_layout.addWidget(login_label)
        links_layout.addWidget(self.login_button)
        
        card_layout.addLayout(links_layout)
        
        container_layout.addWidget(card)
        main_layout.addWidget(background)
        self.setLayout(main_layout)

    def load_departments(self):
        try:
            self.departments = self.api_client.get_departments()
            self.department_combo.addItem("Select Department", None)
            if self.departments:
                for dept in self.departments:
                    self.department_combo.addItem(dept['name'], dept['id'])
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the server. Please check your connection and try again.")
            self.departments = []
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred while loading departments: {e}")
            self.departments = []

    def signup(self):
        try:
            email = self.email_input.text().strip()
            firstname = self.firstname_input.text().strip()
            lastname = self.lastname_input.text().strip()
            username = self.username_input.text().strip()
            password = self.password_input.text()
            confirm_password = self.confirm_password_input.text()
            department_id = self.department_combo.currentData()

            if not all([email, firstname, lastname, username, password, confirm_password]):
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return

            if password != confirm_password:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return

            success, message = self.api_client.signup(
                username, password, email, firstname, lastname, department_id
            )

            if success:
                # Try automatic login after successful signup
                if self.api_client.login(username, password):
                    self.signup_successful.emit()
                    self.accept()
                else:
                    QMessageBox.information(self, "Success", "Account created successfully. Please login.")
                    self.accept()
            else:
                QMessageBox.warning(self, "Signup Failed", message)
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the server. Please check your connection and try again.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred during signup: {e}")

    def show_login(self):
        self.accept()
