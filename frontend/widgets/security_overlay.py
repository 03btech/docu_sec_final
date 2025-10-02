"""
Security overlay widget that blocks the screen when security conditions are not met.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QPalette, QColor, QPainter, QFont
from datetime import datetime
import socket


class SecurityBlockOverlay(QWidget):
    """
    Full-screen overlay that blocks access when security conditions aren't met.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Setup UI
        self.setup_ui()
        
        # Initially hidden
        self.hide()
    
    def setup_ui(self):
        """Setup the blocking overlay UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set dark red background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(139, 0, 0, 0.95);
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)
        
        # Warning icon and text
        icon_label = QLabel("🚨")
        icon_label.setStyleSheet("font-size: 80px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Main message
        self.message_label = QLabel("SECURITY ALERT")
        self.message_label.setStyleSheet("font-size: 36px; padding: 20px;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Details label
        self.details_label = QLabel("Unauthorized activity detected")
        self.details_label.setStyleSheet("font-size: 20px; padding: 10px;")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.details_label)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 16px; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def show_person_missing_block(self):
        """Show overlay when no person is detected."""
        self.message_label.setText("⚠️ NO PERSON DETECTED")
        self.details_label.setText("You must be present to view this confidential document")
        self.status_label.setText("Please position yourself in front of the camera")
        self.show()
        self.raise_()
    
    def show_phone_detected_block(self):
        """Show overlay when phone is detected."""
        self.message_label.setText("🚨 PHONE DETECTED")
        self.details_label.setText("Cell phones are not allowed while viewing confidential documents")
        self.status_label.setText("Please remove the phone to continue")
        self.show()
        self.raise_()
    
    def hide_block(self):
        """Hide the blocking overlay."""
        self.hide()
    
    def resizeEvent(self, event):
        """Ensure overlay covers the entire parent."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)


class SecurityStatusBar(QWidget):
    """
    Status bar showing security monitoring status.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the status bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("🔒 Security monitoring: Initializing...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                color: #495057;
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
                border: 1px solid #dee2e6;
            }
        """)
        layout.addWidget(self.status_label)
    
    def update_status(self, status: str):
        """Update the status message."""
        self.status_label.setText(f"🔒 {status}")
        
        # Color code based on status
        if "error" in status.lower() or "blocked" in status.lower() or "alert" in status.lower():
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    border: 1px solid #f5c6cb;
                }
            """)
        elif "detected" in status.lower() and "person" in status.lower():
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    border: 1px solid #c3e6cb;
                }
            """)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    color: #856404;
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    border: 1px solid #ffeaa7;
                }
            """)


class WatermarkOverlay(QWidget):
    """
    Transparent overlay that displays dynamic watermarks over document content.
    The watermark includes user information, timestamp, and IP address for traceability.
    """
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        
        # Make the widget transparent and pass-through for mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Get user information
        self.user_info = self._get_user_info()
        
        # Timer to update timestamp
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)  # Update every second
        
        # Position the overlay on top
        self.show()
        self.raise_()
    
    def _get_user_info(self) -> dict:
        """Get current user information for watermark."""
        user_data = {}
        
        # Try to get full user info from API
        if self.api_client:
            try:
                current_user = self.api_client.get_current_user()
                if current_user:
                    # Get full name
                    first_name = current_user.get('first_name', '')
                    last_name = current_user.get('last_name', '')
                    username = current_user.get('username', 'Unknown User')
                    
                    # Build full name display
                    if first_name and last_name:
                        user_data['display_name'] = f"{first_name} {last_name}"
                    elif first_name:
                        user_data['display_name'] = first_name
                    elif last_name:
                        user_data['display_name'] = last_name
                    else:
                        user_data['display_name'] = username
                    
                    # Store username separately for reference
                    user_data['username'] = username
                    
                    # Get user ID
                    user_data['user_id'] = current_user.get('id', 'N/A')
                    
                    # Get email (optional additional info)
                    user_data['email'] = current_user.get('email', '')
                else:
                    # Fallback if API call fails
                    user_data['display_name'] = 'Unknown User'
                    user_data['username'] = 'Unknown User'
                    user_data['user_id'] = 'N/A'
                    user_data['email'] = ''
            except Exception as e:
                print(f"Error fetching user info: {e}")
                # Fallback values
                user_data['display_name'] = 'Unknown User'
                user_data['username'] = 'Unknown User'
                user_data['user_id'] = 'N/A'
                user_data['email'] = ''
        else:
            # No API client available
            user_data['display_name'] = 'Unknown User'
            user_data['username'] = 'Unknown User'
            user_data['user_id'] = 'N/A'
            user_data['email'] = ''
        
        # Get IP address
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            user_data['ip'] = ip_address
        except:
            user_data['ip'] = 'N/A'
        
        return user_data
    
    def paintEvent(self, event):
        """Paint dynamic watermarks across the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up semi-transparent text
        painter.setPen(QColor(200, 0, 0, 60))  # Semi-transparent red
        
        # Font for watermark
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Create watermark text with dynamic information
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use full name (display_name) instead of username
        display_name = self.user_info.get('display_name', 'Unknown User')
        user_id = self.user_info.get('user_id', 'N/A')
        ip_address = self.user_info.get('ip', 'N/A')
        
        watermark_text = (
            f"CONFIDENTIAL\n"
            f"User: {display_name} (ID: {user_id})\n"
            f"IP: {ip_address}\n"
            f"{timestamp}"
        )
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        
        # Draw watermarks in a diagonal grid pattern
        spacing_x = 400
        spacing_y = 300
        
        painter.save()
        painter.translate(width / 2, height / 2)
        painter.rotate(-45)  # Diagonal watermark
        
        # Calculate the number of watermarks needed
        rotated_width = int((width ** 2 + height ** 2) ** 0.5)
        rotated_height = int((width ** 2 + height ** 2) ** 0.5)
        
        for x in range(-rotated_width // 2, rotated_width // 2, spacing_x):
            for y in range(-rotated_height // 2, rotated_height // 2, spacing_y):
                painter.drawText(
                    QRect(x - 200, y - 100, 400, 200),
                    Qt.AlignmentFlag.AlignCenter,
                    watermark_text
                )
        
        painter.restore()
        
    def resizeEvent(self, event):
        """Ensure watermark overlay covers the entire parent."""
        if self.parent():
            parent_widget = self.parent()
            if hasattr(parent_widget, 'rect'):
                self.setGeometry(parent_widget.rect())
        super().resizeEvent(event)
