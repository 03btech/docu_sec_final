"""
Security overlay widget that blocks the screen when security conditions are not met.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QPalette, QColor, QPainter, QFont
from datetime import datetime
import socket


import threading

class SecurityBlockOverlay(QWidget):
    """
    Full-screen overlay that blocks access when security conditions aren't met.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Disable transparency - we want solid black
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        
        # Set solid black background via palette
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.setPalette(palette)
        
        # Setup UI
        self.setup_ui()
        
        # Initially hidden
        self.hide()
    
    def setup_ui(self):
        """Setup the blocking overlay UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set solid black background for maximum security
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(0, 0, 0);
            }
            QLabel {
                color: white;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        
        # Warning icon and text
        icon_label = QLabel("🚨")
        icon_label.setStyleSheet("font-size: 100px; background-color: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Main message
        self.message_label = QLabel("SECURITY ALERT")
        self.message_label.setStyleSheet("font-size: 48px; padding: 20px; color: #ff4444; background-color: transparent;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Details label
        self.details_label = QLabel("Unauthorized activity detected")
        self.details_label.setStyleSheet("font-size: 24px; padding: 10px; color: #ffffff; background-color: transparent;")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.details_label)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 18px; padding: 10px; color: #cccccc; background-color: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Security notice
        self.notice_label = QLabel("⚠️ This security event has been logged")
        self.notice_label.setStyleSheet("font-size: 14px; padding: 20px; color: #888888; background-color: transparent;")
        self.notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.notice_label)
    
    def show_person_missing_block(self):
        """Show overlay when no person is detected."""
        self.message_label.setText("⚠️ NO PERSON DETECTED")
        self.message_label.setStyleSheet("font-size: 48px; padding: 20px; color: #ffaa00; background-color: transparent;")
        self.details_label.setText("You must be present to view this confidential document")
        self.status_label.setText("Please position yourself in front of the camera")
        self.notice_label.setText("⚠️ Document access suspended until presence is confirmed")
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self.update()  # Force repaint
    
    def show_phone_detected_block(self):
        """Show overlay when phone is detected."""
        self.message_label.setText("🚨 PHONE DETECTED")
        self.message_label.setStyleSheet("font-size: 48px; padding: 20px; color: #ff4444; background-color: transparent;")
        self.details_label.setText("Cell phones are NOT allowed while viewing confidential documents")
        self.status_label.setText("Please remove the phone from view to continue")
        self.notice_label.setText("⚠️ This security violation has been logged and reported")
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self.update()  # Force repaint
    
    def show_low_lighting_block(self):
        """Show overlay when low lighting is detected."""
        self.message_label.setText("💡 LOW LIGHTING DETECTED")
        self.message_label.setStyleSheet("font-size: 48px; padding: 20px; color: #ff9900; background-color: transparent;")
        self.details_label.setText("Adequate lighting is required to view confidential documents")
        self.status_label.setText("Please increase the lighting in your environment")
        self.notice_label.setText("⚠️ Viewer will close in 10 seconds if lighting is not improved")
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self.update()  # Force repaint
    
    def hide_block(self):
        """Hide the blocking overlay."""
        self.hide()
    
    def paintEvent(self, event):
        """Paint solid black background."""
        painter = QPainter()
        if painter.begin(self):
            painter.fillRect(self.rect(), QColor(0, 0, 0))
            painter.end()
        super().paintEvent(event)
    
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
        
        # Initialize default user info
        self.user_info = {
            'display_name': 'Loading...',
            'username': 'Loading...',
            'user_id': '...',
            'email': '',
            'ip': '...'
        }
        
        # Get user information asynchronously
        self._get_user_info_async()
        
        # Timer to update timestamp
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)  # Update every second
        
        # Position the overlay on top
        self.show()
        self.raise_()
    
    def _get_user_info_async(self):
        """Start background thread to get user info."""
        threading.Thread(target=self._fetch_user_info, daemon=True).start()

    def _fetch_user_info(self):
        """Fetch user info in background and update UI."""
        user_data = self._get_user_info()
        self.user_info = user_data
        # Trigger update on main thread (safe since we're just setting a dict and requesting repaint)
        # Ideally we should use signals/slots but for a simple dict update and repaint request it's usually fine
        # or we can rely on the timer to pick it up next second.
        # But to be safe with UI updates from threads:
        # We'll let the timer pick up the change, or we can force an update if we had a signal.
        # Since we have a 1s timer, it will update shortly.
    
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
        # Ensure widget has valid size before painting
        if self.width() <= 0 or self.height() <= 0:
            return
        
        # Check if widget is properly realized (has a valid window handle)
        if not self.winId():
            return
            
        # Create painter and verify it's active before proceeding
        painter = QPainter()
        if not painter.begin(self):
            return
            
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
            # Get widget dimensions
            width = self.width()
            height = self.height()
            
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
            
            # Draw multiple layers of watermarks for better visibility
            # Layer 1: Semi-transparent red diagonal watermarks
            painter.setPen(QColor(200, 0, 0, 50))
            font = QFont("Arial", 14, QFont.Weight.Bold)
            painter.setFont(font)
            
            spacing_x = 350
            spacing_y = 250
            
            painter.save()
            painter.translate(width / 2, height / 2)
            painter.rotate(-45)
            
            rotated_size = int((width ** 2 + height ** 2) ** 0.5)
            
            for x in range(-rotated_size // 2, rotated_size // 2, spacing_x):
                for y in range(-rotated_size // 2, rotated_size // 2, spacing_y):
                    painter.drawText(
                        QRect(x - 200, y - 100, 400, 200),
                        Qt.AlignmentFlag.AlignCenter,
                        watermark_text
                    )
            
            painter.restore()
            
            # Layer 2: Smaller gray watermarks at different angle for redundancy
            painter.setPen(QColor(100, 100, 100, 35))
            small_font = QFont("Arial", 10, QFont.Weight.Normal)
            painter.setFont(small_font)
            
            short_watermark = f"{display_name} | {timestamp}"
            
            painter.save()
            painter.translate(width / 2, height / 2)
            painter.rotate(45)  # Opposite angle
            
            for x in range(-rotated_size // 2, rotated_size // 2, 300):
                for y in range(-rotated_size // 2, rotated_size // 2, 200):
                    painter.drawText(
                        QRect(x - 150, y - 20, 300, 40),
                        Qt.AlignmentFlag.AlignCenter,
                        short_watermark
                    )
            
            painter.restore()
            
            # Layer 3: Corner stamps with full details (harder to crop out)
            painter.setPen(QColor(150, 0, 0, 70))
            corner_font = QFont("Consolas", 9, QFont.Weight.Bold)
            painter.setFont(corner_font)
            
            corner_text = f"[{display_name}] [{ip_address}] [{timestamp}]"
            
            # Draw in all four corners
            margin = 10
            painter.drawText(QRect(margin, margin, 400, 20), Qt.AlignmentFlag.AlignLeft, corner_text)
            painter.drawText(QRect(width - 410, margin, 400, 20), Qt.AlignmentFlag.AlignRight, corner_text)
            painter.drawText(QRect(margin, height - 30, 400, 20), Qt.AlignmentFlag.AlignLeft, corner_text)
            painter.drawText(QRect(width - 410, height - 30, 400, 20), Qt.AlignmentFlag.AlignRight, corner_text)
            
        finally:
            painter.end()
        
    def resizeEvent(self, event):
        """Ensure watermark overlay covers the entire parent."""
        if self.parent():
            parent_widget = self.parent()
            if hasattr(parent_widget, 'rect'):
                self.setGeometry(parent_widget.rect())
        super().resizeEvent(event)
