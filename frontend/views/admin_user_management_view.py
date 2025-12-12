from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QMessageBox, QComboBox, QFrame, QScrollArea, QDialogButtonBox)
from PyQt6.QtCore import Qt
import qtawesome as qta
from api.client import APIClient

class AdminUserManagementView(QDialog):
    """Admin-only dialog for creating new user accounts."""
    
    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.departments = []
        self.setWindowTitle("Create New User")
        self.setModal(True)
        self.resize(550, 600)
        self.setup_ui()
        self.load_departments()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_icon = qta.icon('fa5s.user-plus', color='#27ae60')
        icon_label = QLabel()
        icon_label.setPixmap(title_icon.pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        title = QLabel("Create New User")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QLabel("As an administrator, you can create new user accounts for the system.")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(subtitle)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #bdc3c7;")
        main_layout.addWidget(separator)
        
        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # Form card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e4e7;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        
        input_style = """
            QLineEdit, QComboBox {
                padding: 12px 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #27ae60;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """
        
        # Email
        email_label = QLabel("Email Address *")
        email_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        self.email_input.setStyleSheet(input_style)
        card_layout.addWidget(self.email_input)
        
        # First Name
        fname_label = QLabel("First Name *")
        fname_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(fname_label)
        
        self.firstname_input = QLineEdit()
        self.firstname_input.setPlaceholderText("John")
        self.firstname_input.setStyleSheet(input_style)
        card_layout.addWidget(self.firstname_input)
        
        # Last Name
        lname_label = QLabel("Last Name *")
        lname_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(lname_label)
        
        self.lastname_input = QLineEdit()
        self.lastname_input.setPlaceholderText("Doe")
        self.lastname_input.setStyleSheet(input_style)
        card_layout.addWidget(self.lastname_input)
        
        # Username
        username_label = QLabel("Username *")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("johndoe")
        self.username_input.setStyleSheet(input_style)
        card_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password *")
        password_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter secure password")
        self.password_input.setStyleSheet(input_style)
        card_layout.addWidget(self.password_input)
        
        # Confirm Password
        confirm_label = QLabel("Confirm Password *")
        confirm_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(confirm_label)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Re-enter password")
        self.confirm_password_input.setStyleSheet(input_style)
        card_layout.addWidget(self.confirm_password_input)
        
        # Department
        dept_label = QLabel("Department")
        dept_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(dept_label)
        
        self.department_combo = QComboBox()
        self.department_combo.setStyleSheet(input_style)
        card_layout.addWidget(self.department_combo)
        
        # Role
        role_label = QLabel("User Role *")
        role_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px;")
        card_layout.addWidget(role_label)
        
        self.role_combo = QComboBox()
        self.role_combo.addItem("Regular User", "user")
        self.role_combo.addItem("Administrator", "admin")
        self.role_combo.setStyleSheet(input_style)
        card_layout.addWidget(self.role_combo)
        
        # Warning for admin role
        admin_warning = QLabel("⚠️ Administrators have full access to all system features including user management and logs.")
        admin_warning.setStyleSheet("""
            background-color: #fff3cd;
            color: #856404;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            border: 1px solid #ffeaa7;
        """)
        admin_warning.setWordWrap(True)
        card_layout.addWidget(admin_warning)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Save
        )
        button_box.accepted.connect(self.create_user)
        button_box.rejected.connect(self.reject)
        
        # Style the buttons
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Create User")
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 30px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover { background-color: #229954; }
                QPushButton:pressed { background-color: #1e8449; }
            """)
        
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 30px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
                QPushButton:pressed { background-color: #6c7a7b; }
            """)
        
        form_layout.addWidget(card)
        form_layout.addStretch()
        
        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll)
        
        # Add buttons outside scroll area
        main_layout.addWidget(button_box)

    def load_departments(self):
        """Load departments from API."""
        try:
            self.departments = self.api_client.get_departments()
            self.department_combo.addItem("No Department", None)
            if self.departments:
                for dept in self.departments:
                    self.department_combo.addItem(dept['name'], dept['id'])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load departments: {e}")

    def create_user(self):
        """Create a new user account."""
        # Validate inputs
        email = self.email_input.text().strip()
        firstname = self.firstname_input.text().strip()
        lastname = self.lastname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        department_id = self.department_combo.currentData()
        role = self.role_combo.currentData()
        
        if not all([email, firstname, lastname, username, password, confirm_password]):
            QMessageBox.warning(self, "Validation Error", "Please fill in all required fields (*).")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters long.")
            return
        
        # Confirm admin creation
        if role == "admin":
            reply = QMessageBox.question(
                self, 
                "Confirm Admin Creation",
                f"Are you sure you want to create '{username}' as an Administrator?\n\n"
                "Administrators have full system access including:\n"
                "• Creating and managing users\n"
                "• Viewing all logs\n"
                "• Accessing all documents",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Create user via API
        try:
            success, message = self.api_client.admin_create_user(
                username=username,
                password=password,
                email=email,
                first_name=firstname,
                last_name=lastname,
                role=role,
                department_id=department_id
            )
            
            if success:
                self.accept()  # Close dialog on success
            else:
                QMessageBox.warning(self, "Creation Failed", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while creating the user:\n{str(e)}")

    def clear_form(self):
        """Clear all form inputs."""
        self.email_input.clear()
        self.firstname_input.clear()
        self.lastname_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
        self.department_combo.setCurrentIndex(0)
        self.role_combo.setCurrentIndex(0)
        self.email_input.setFocus()

    def refresh_data(self):
        """Refresh view data (reload departments)."""
        self.load_departments()
