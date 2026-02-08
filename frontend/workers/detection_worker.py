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
except (ImportError, OSError, Exception) as e:
    YOLO_AVAILABLE = False
    print(f"⚠️ WARNING: YOLO unavailable ({type(e).__name__}: {e}). Security monitoring disabled.")


class DetectionWorker(QThread):
    """
    Worker thread for real-time object detection using YOLOv8.
    Monitors for unauthorized persons and cell phones.
    """
    
    # Signals
    person_detected = pyqtSignal(bool)  # True if person detected, False if no person
    phone_detected = pyqtSignal(dict)  # Emits detection details
    low_lighting_detected = pyqtSignal(bool)  # True if low lighting detected
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
        
        # YOLO class IDs (COCO dataset)
        self.PERSON_CLASS_ID = 0
        self.CELL_PHONE_CLASS_ID = 67
        
        # Persistence settings - require multiple consecutive detections
        self.phone_detection_threshold = 2  # Frames with phone before triggering (faster response)
        self.phone_detection_count = 0  # Current consecutive phone detections
        self.no_person_detection_threshold = 5  # Frames without person before blocking
        self.no_person_detection_count = 0  # Current consecutive no-person frames
        self.phone_alert_emitted = False  # Track if we already emitted phone alert this session
        
        # Confidence thresholds (balanced for speed and accuracy)
        self.person_confidence = 0.35  # 35% confidence for person
        self.phone_confidence = 0.25  # 25% confidence for phone (more sensitive)
        
        # Low lighting detection settings
        self.brightness_threshold = 50  # Minimum average brightness (0-255) — 50 catches genuinely dark scenes
        self.low_lighting_detection_threshold = 15  # Consecutive frames before triggering (allows auto-exposure to adjust)
        self.low_lighting_detection_count = 0  # Current consecutive low light frames
        self.low_lighting_active = False  # Track current low lighting state
        
    def initialize_camera(self):
        """Initialize the webcam."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.camera_error.emit("Failed to open camera. Please check if a camera is connected.")
                return False
            
            # Set camera properties — 640x480 is sufficient since YOLO resizes internally
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus if available
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Enable auto exposure
            
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
            # Load YOLOv8 nano model — fastest for real-time webcam detection
            self.detection_status.emit("🔄 Loading YOLOv8 model...")
            self.model = YOLO('yolov8n.pt')  # Nano version for real-time performance
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
        detection_interval = 2  # Process every 2nd frame for lower latency
        
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
    
    def check_lighting(self, frame):
        """Check if the frame has adequate lighting."""
        try:
            # Convert to grayscale and calculate average brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            
            if avg_brightness < self.brightness_threshold:
                self.low_lighting_detection_count += 1
                if self.low_lighting_detection_count >= self.low_lighting_detection_threshold:
                    if not self.low_lighting_active:
                        self.low_lighting_active = True
                        self.low_lighting_detected.emit(True)
                        self.detection_status.emit(f"⚠️ Low lighting detected (brightness: {avg_brightness:.0f}/255) - Screen blocked")
                    return False  # Low lighting
            else:
                self.low_lighting_detection_count = 0
                if self.low_lighting_active:
                    self.low_lighting_active = False
                    self.low_lighting_detected.emit(False)
                    self.detection_status.emit("✅ Lighting restored - Monitoring active")
            return True  # Adequate lighting
        except Exception as e:
            print(f"Error checking lighting: {e}")
            return True  # Assume adequate lighting on error
    
    def process_frame(self, frame):
        """Process a single frame for detections."""
        try:
            # First check lighting conditions
            if not self.check_lighting(frame):
                return  # Skip detection if low lighting
            
            # Run YOLOv8 inference — use the lowest confidence threshold so per-class
            # thresholds (person_confidence, phone_confidence) are not silently pre-filtered
            results = self.model(frame, verbose=False,
                                 conf=min(self.person_confidence, self.phone_confidence),
                                 iou=0.5)
            
            person_found = False
            phone_found = False
            phone_confidence = 0.0
            
            # Parse detections
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # Check for person with configurable confidence
                    if class_id == self.PERSON_CLASS_ID and confidence > self.person_confidence:
                        person_found = True
                        self.last_person_time = time.time()
                    
                    # Check for cell phone with configurable confidence
                    if class_id == self.CELL_PHONE_CLASS_ID and confidence > self.phone_confidence:
                        phone_found = True
                        phone_confidence = max(phone_confidence, confidence)
            
            # Handle person detection with persistence
            current_time = time.time()
            
            if person_found:
                self.no_person_detection_count = 0  # Reset no-person counter
                self.person_detected.emit(True)
                self.detection_status.emit("✅ Person detected - Monitoring active")
            else:
                self.no_person_detection_count += 1
                # Only block after consecutive frames without person
                if self.no_person_detection_count >= self.no_person_detection_threshold:
                    time_since_person = current_time - self.last_person_time
                    if time_since_person > self.person_timeout:
                        self.person_detected.emit(False)
                        self.detection_status.emit("⚠️ No person detected - Screen blocked")
            
            # Handle phone detection with persistence
            if phone_found:
                self.phone_detection_count += 2  # Increase by 2 when found
                # Cap at reasonable max to prevent overflow
                self.phone_detection_count = min(self.phone_detection_count, 20)
                
                # Trigger alert ONLY ONCE after threshold reached
                if self.phone_detection_count >= self.phone_detection_threshold and not self.phone_alert_emitted:
                    self.phone_alert_emitted = True  # Mark as emitted
                    detection_data = {
                        'timestamp': datetime.now().isoformat(),
                        'confidence': phone_confidence,
                        'type': 'cell_phone',
                        'consecutive_frames': self.phone_detection_count
                    }
                    self.phone_detected.emit(detection_data)
                    self.detection_status.emit(f"🚨 PHONE DETECTED ({phone_confidence:.0%} confidence) - Security alert!")
            else:
                # Gradual decay instead of immediate reset
                if self.phone_detection_count > 0:
                    self.phone_detection_count -= 1
                
                # Reset alert flag when count drops to zero (phone fully gone)
                if self.phone_detection_count == 0:
                    self.phone_alert_emitted = False
                
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
