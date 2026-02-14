"""
YOLOv8-based security monitoring worker for detecting unauthorized persons and cell phones.
This worker runs in a separate thread to continuously monitor the webcam feed.

Performance optimization strategy (auto-detected, best-first):
  1. CUDA GPU  — fastest (~3-5ms/frame)
  2. OpenVINO  — fast on Intel CPUs (~8-15ms/frame)
  3. PyTorch CPU — fallback (~50-100ms/frame)
"""
from PyQt6.QtCore import QThread, pyqtSignal
import cv2
import numpy as np
from datetime import datetime
import time
import os
from pathlib import Path


try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    YOLO_AVAILABLE = False
    print(f"⚠️ WARNING: YOLO unavailable ({type(e).__name__}: {e}). Security monitoring disabled.")


def _detect_best_device():
    """Auto-detect the best available inference backend.
    
    Returns:
        tuple: (device_str, use_half, backend_name)
            - device_str: 'cuda:0', 'cpu', etc.
            - use_half: whether to use FP16 half-precision
            - backend_name: human-readable name for logging
    """
    print("\n" + "="*50)
    print("🔍 AUTO-DETECTING INFERENCE BACKEND")
    print("="*50)
    
    # 1. Try CUDA GPU
    try:
        import torch
        print(f"  [CHECK] PyTorch version: {torch.__version__}")
        print(f"  [CHECK] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  ✅ SELECTED: CUDA GPU — {gpu_name}")
            print("="*50 + "\n")
            return ('cuda:0', True, f'CUDA GPU ({gpu_name})')
        else:
            print("  [SKIP] No CUDA GPU detected, checking CPU options...")
    except Exception as e:
        print(f"  [SKIP] PyTorch CUDA check failed: {e}")
    
    # 2. OpenVINO and plain CPU both use device='cpu' —
    #    the distinction is which model file we load (handled in initialize_model)
    print("  [INFO] Will use CPU — OpenVINO check happens during model load")
    print("="*50 + "\n")
    return ('cpu', False, 'CPU')


def _get_openvino_model_path(pt_model_name='yolov8m.pt'):
    """Get the path where the cached OpenVINO model should live.
    
    The exported model is stored next to the .pt file so it persists across runs.
    """
    # Ultralytics exports to a folder named <stem>_openvino_model/
    stem = Path(pt_model_name).stem  # 'yolov8m'
    return Path(stem + '_openvino_model')


def _is_openvino_available():
    """Check if OpenVINO runtime is installed."""
    try:
        import openvino  # noqa: F401
        return True
    except ImportError:
        return False


class DetectionWorker(QThread):
    """
    Worker thread for real-time object detection using YOLOv8.
    Monitors for unauthorized persons and cell phones.
    
    Automatically selects the fastest inference backend:
    CUDA GPU → OpenVINO (Intel CPU) → plain PyTorch CPU.
    """
    
    # Signals
    person_detected = pyqtSignal(bool)  # True if person detected, False if no person
    phone_detected = pyqtSignal(dict)  # Emits detection details
    low_lighting_detected = pyqtSignal(bool)  # True if low lighting detected
    camera_error = pyqtSignal(str)  # Emits error messages
    detection_status = pyqtSignal(str)  # Status updates
    model_initialized = pyqtSignal(bool)  # True if model loaded successfully, False if failed
    
    # Inference image size — 480px gives good accuracy for phone detection
    # while still being fast on OpenVINO.
    INFERENCE_IMG_SIZE = 480
    
    # Target FPS for the detection loop (caps how fast we run, saves CPU)
    TARGET_FPS = 15
    
    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.cap = None
        self.model = None
        
        # Backend info (populated during initialize_model)
        self._device = 'cpu'
        self._use_half = False
        self._backend_name = 'CPU'
        
        # Detection settings
        self.person_timeout = 1.5  # Seconds without person before blocking (fast response)
        self.last_person_time = time.time()
        
        # YOLO class IDs (COCO dataset)
        self.PERSON_CLASS_ID = 0
        self.CELL_PHONE_CLASS_ID = 67
        
        # Persistence settings - require multiple consecutive detections
        self.phone_detection_threshold = 2  # Frames with phone before triggering (faster response)
        self.phone_detection_count = 0  # Current consecutive phone detections
        self.no_person_detection_threshold = 3  # Frames without person before blocking (reduced for speed)
        self.no_person_detection_count = 0  # Current consecutive no-person frames
        self.phone_alert_emitted = False  # Track if we already emitted phone alert this session
        
        # Confidence thresholds (balanced for speed and accuracy)
        self.person_confidence = 0.35  # 35% confidence for person
        self.phone_confidence = 0.45  # 45% confidence for phone (raised to reduce false positives)
        
        # Low lighting detection settings
        self.brightness_threshold = 50  # Minimum average brightness (0-255) — 50 catches genuinely dark scenes
        self.low_lighting_detection_threshold = 5  # Consecutive frames before triggering (fast response)
        self.low_lighting_detection_count = 0  # Current consecutive low light frames
        self.low_lighting_active = False  # Track current low lighting state
        
    def initialize_camera(self):
        """Initialize the webcam."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.camera_error.emit("Failed to open camera. Please check if a camera is connected.")
                return False
            
            # Set camera properties — 1280x720 for wider field of view
            # (YOLO resizes to 320px internally so no performance impact)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus if available
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Enable auto exposure
            
            self.detection_status.emit("✅ Camera initialized successfully")
            return True
        except Exception as e:
            self.camera_error.emit(f"Camera initialization error: {str(e)}")
            return False
    
    def initialize_model(self):
        """Initialize YOLOv8 model with the best available backend.
        
        Tries in order: CUDA GPU → OpenVINO → plain PyTorch CPU.
        """
        if not YOLO_AVAILABLE:
            self.camera_error.emit("YOLOv8 not available. Please install: pip install ultralytics")
            self.model_initialized.emit(False)
            return False
        
        try:
            self.detection_status.emit("🔄 Detecting best inference backend...")
            print("\n🔄 Initializing YOLOv8 model...")
            
            # Detect best device (CUDA or CPU)
            self._device, self._use_half, self._backend_name = _detect_best_device()
            
            is_cuda = self._device.startswith('cuda')
            openvino_available = _is_openvino_available()
            
            if is_cuda:
                # ── CUDA GPU path ──
                print(f"  🎮 Loading YOLOv8s on {self._backend_name}...")
                self.detection_status.emit(f"🔄 Loading YOLOv8s on {self._backend_name}...")
                self.model = YOLO('yolov8m.pt')
                print(f"  ✅ GPU model loaded with FP16 half-precision")
                
            elif openvino_available:
                # ── OpenVINO path (Intel CPU optimized) ──
                ov_model_path = _get_openvino_model_path()
                
                if ov_model_path.exists():
                    # Use cached OpenVINO model
                    print(f"  📦 Found cached OpenVINO model at: {ov_model_path}")
                    self.detection_status.emit("🔄 Loading cached OpenVINO model...")
                    self.model = YOLO(str(ov_model_path), task='detect')
                else:
                    # Export to OpenVINO on first run (one-time cost)
                    print(f"  🔧 First run — exporting YOLOv8s to OpenVINO format...")
                    self.detection_status.emit("🔄 First run: exporting YOLOv8s to OpenVINO format (one-time)...")
                    pt_model = YOLO('yolov8m.pt')
                    pt_model.export(format='openvino', imgsz=self.INFERENCE_IMG_SIZE)
                    self.model = YOLO(str(ov_model_path), task='detect')
                    print(f"  ✅ OpenVINO model exported and cached at: {ov_model_path}")
                
                self._backend_name = 'OpenVINO (Intel CPU optimized)'
                self._use_half = False  # OpenVINO handles precision internally
                print(f"  ✅ Using OpenVINO — Intel CPU optimized inference")
                
            else:
                # ── Plain PyTorch CPU fallback ──
                print("  ⚠️ OpenVINO not installed — using plain PyTorch CPU (slower)")
                print("  💡 TIP: Install OpenVINO for 2-4x speedup: pip install openvino")
                self.detection_status.emit("🔄 Loading YOLOv8s on CPU (install openvino for 2-4x speedup)...")
                self.model = YOLO('yolov8m.pt')
                self._backend_name = 'PyTorch CPU'
            
            print(f"\n{'='*50}")
            print(f"✅ BACKEND SELECTED: {self._backend_name}")
            print(f"   Inference size: {self.INFERENCE_IMG_SIZE}px")
            print(f"   Half-precision: {self._use_half}")
            print(f"   Target FPS: {self.TARGET_FPS}")
            print(f"{'='*50}\n")
            self.detection_status.emit(f"✅ YOLOv8 model loaded — backend: {self._backend_name}")
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
        
        self.detection_status.emit(f"🔍 Monitoring started ({self._backend_name}) - checking for person presence...")
        self.last_person_time = time.time()
        
        frame_count = 0
        detection_interval = 2  # Process every 2nd frame for lower latency
        target_frame_time = 1.0 / self.TARGET_FPS  # Minimum time per loop iteration
        
        while self.running:
            try:
                loop_start = time.time()
                
                ret, frame = self.cap.read()
                if not ret:
                    self.camera_error.emit("Failed to read frame from camera")
                    break
                
                frame_count += 1
                
                # Process every Nth frame to improve performance
                if frame_count % detection_interval == 0:
                    self.process_frame(frame)
                
                # Dynamic sleep: only sleep if we're faster than TARGET_FPS
                # This replaces the old fixed time.sleep(0.03) which wasted time
                elapsed = time.time() - loop_start
                remaining = target_frame_time - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                
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
            
            # Build inference kwargs — optimized per backend
            infer_kwargs = dict(
                verbose=False,
                conf=min(self.person_confidence, self.phone_confidence),
                iou=0.5,
                imgsz=self.INFERENCE_IMG_SIZE,
            )
            
            # Use GPU device explicitly if CUDA is available
            if self._device.startswith('cuda'):
                infer_kwargs['device'] = self._device
            
            # Use half-precision on GPU for ~2x speedup
            if self._use_half:
                infer_kwargs['half'] = True
            
            infer_start = time.time()
            results = self.model(frame, **infer_kwargs)
            infer_ms = (time.time() - infer_start) * 1000
            
            person_found = False
            phone_found = False
            phone_confidence = 0.0
            
            # Parse detections and log all raw results
            all_detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = result.names.get(class_id, f'class_{class_id}')
                    all_detections.append(f"{class_name}:{confidence:.0%}")
                    
                    # Check for person with configurable confidence
                    if class_id == self.PERSON_CLASS_ID and confidence > self.person_confidence:
                        person_found = True
                        self.last_person_time = time.time()
                    
                    # Check for cell phone with configurable confidence
                    if class_id == self.CELL_PHONE_CLASS_ID and confidence > self.phone_confidence:
                        phone_found = True
                        phone_confidence = max(phone_confidence, confidence)
            
            # Debug log: inference time + all detections
            det_str = ', '.join(all_detections) if all_detections else 'none'
            print(f"[DETECT] {infer_ms:.0f}ms | objects: [{det_str}] | person={person_found} phone={phone_found}")
            
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
