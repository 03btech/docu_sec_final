"""
YOLOv8-based security monitoring worker for detecting unauthorized persons and cell phones.
This worker runs in a separate thread to continuously monitor the webcam feed.
"""
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np
from datetime import datetime
import time

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ WARNING: ultralytics not installed. YOLOv8 detection will not work.")


class DetectionWorker(QThread):
    """
    Worker thread for real-time object detection using YOLOv8.
    Monitors for unauthorized persons and cell phones.
    """
    
    # Signals
    person_detected = pyqtSignal(bool)  # True if person detected, False if no person
    phone_detected = pyqtSignal(dict)  # Emits detection details
    camera_error = pyqtSignal(str)  # Emits error messages
    detection_status = pyqtSignal(str)  # Status updates
    model_initialized = pyqtSignal(bool)  # True if model loaded successfully, False if failed
    
    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.cap = None
        self.model = None
        
        # Detection settings
        self.person_timeout = 3.0  # Seconds without person before blocking
        self.last_person_time = time.time()
        self.phone_cooldown = 2.0  # Seconds between phone alerts
        self.last_phone_alert = 0
        
        # YOLO class IDs (COCO dataset)
        self.PERSON_CLASS_ID = 0
        self.CELL_PHONE_CLASS_ID = 67
        
    def initialize_camera(self):
        """Initialize the webcam."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.camera_error.emit("Failed to open camera. Please check if a camera is connected.")
                return False
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.detection_status.emit("✅ Camera initialized successfully")
            return True
        except Exception as e:
            self.camera_error.emit(f"Camera initialization error: {str(e)}")
            return False
    
    def initialize_model(self):
        """Initialize YOLOv8 model."""
        if not YOLO_AVAILABLE:
            self.camera_error.emit("YOLOv8 not available. Please install: pip install ultralytics")
            self.model_initialized.emit(False)
            return False
        
        try:
            # Load YOLOv8 nano model (lightweight and fast)
            self.detection_status.emit("🔄 Loading YOLOv8 model...")
            self.model = YOLO('yolov8n.pt')  # Nano version for speed
            self.detection_status.emit("✅ YOLOv8 model loaded successfully")
            self.model_initialized.emit(True)
            return True
        except Exception as e:
            self.camera_error.emit(f"Failed to load YOLOv8 model: {str(e)}")
            self.model_initialized.emit(False)
            return False
    
    def run(self):
        """Main detection loop."""
        self.running = True
        
        # Initialize camera
        if not self.initialize_camera():
            return
        
        # Initialize YOLOv8 model
        if not self.initialize_model():
            self.cap.release()
            return
        
        self.detection_status.emit("🔍 Monitoring started - checking for person presence...")
        self.last_person_time = time.time()
        
        frame_count = 0
        detection_interval = 10  # Process every 10th frame for performance
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.camera_error.emit("Failed to read frame from camera")
                    break
                
                frame_count += 1
                
                # Process every Nth frame to improve performance
                if frame_count % detection_interval == 0:
                    self.process_frame(frame)
                
                # Small delay to prevent CPU overuse
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                self.camera_error.emit(f"Detection error: {str(e)}")
                break
        
        # Cleanup
        self.cleanup()
    
    def process_frame(self, frame):
        """Process a single frame for detections."""
        try:
            # Run YOLOv8 inference
            results = self.model(frame, verbose=False, conf=0.5)
            
            person_found = False
            phone_found = False
            
            # Parse detections
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # Check for person
                    if class_id == self.PERSON_CLASS_ID and confidence > 0.5:
                        person_found = True
                        self.last_person_time = time.time()
                    
                    # Check for cell phone
                    if class_id == self.CELL_PHONE_CLASS_ID and confidence > 0.4:
                        phone_found = True
            
            # Emit person detection status
            current_time = time.time()
            time_since_person = current_time - self.last_person_time
            
            if time_since_person > self.person_timeout:
                # No person detected for too long
                self.person_detected.emit(False)
                self.detection_status.emit("⚠️ No person detected - Screen blocked")
            else:
                self.person_detected.emit(True)
                if person_found:
                    self.detection_status.emit("✅ Person detected - Monitoring active")
            
            # Emit phone detection continuously (every detection, no cooldown for blocking)
            # But use cooldown for status messages to avoid spam
            if phone_found:
                detection_data = {
                    'timestamp': datetime.now().isoformat(),
                    'confidence': 0.4,  # Minimum confidence used
                    'type': 'cell_phone'
                }
                # Emit signal every time (secure viewer will handle continuous blocking)
                self.phone_detected.emit(detection_data)
                
                # Update status message only periodically to avoid spam
                if (current_time - self.last_phone_alert) > self.phone_cooldown:
                    self.last_phone_alert = current_time
                    self.detection_status.emit("🚨 PHONE DETECTED - Security alert!")
                
        except Exception as e:
            print(f"Error processing frame: {e}")
    
    def stop(self):
        """Stop the detection worker."""
        self.running = False
        self.detection_status.emit("⏹️ Monitoring stopped")
    
    def cleanup(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
        self.detection_status.emit("✅ Camera released")
