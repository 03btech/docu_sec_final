import fitz  # PyMuPDF
from docx import Document as DocxDocument
import os
import re
from typing import Dict, List, Tuple
from transformers import pipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy load the zero-shot classification pipeline
classifier = None

def get_classifier():
    global classifier
    if classifier is None:
        logger.info("Loading zero-shot classification pipeline...")
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        logger.info("Pipeline loaded successfully.")
    return classifier

# Enhanced keyword patterns for classification
CLASSIFICATION_KEYWORDS = {
    "confidential": [
        # Explicit confidentiality markers
        r"\b(confidential|classified|restricted|proprietary|private)\b",
        r"\b(top secret|secret|sensitive|privileged)\b",
        r"\b(do not distribute|internal use only|not for public)\b",
        
        # Financial/Legal sensitive terms
        r"\b(salary|wage|compensation|budget|revenue|profit|loss)\b",
        r"\b(ssn|social security|tax id|ein|bank account|credit card)\b",
        r"\b(merger|acquisition|layoff|termination|disciplinary)\b",
        r"\b(lawsuit|legal action|settlement|litigation)\b",
        
        # Personal/HR sensitive data
        r"\b(medical|health|disability|personal information)\b",
        r"\b(performance review|disciplinary action|termination)\b",
        
        # Business sensitive
        r"\b(trade secret|intellectual property|patent|proprietary)\b",
        r"\b(client list|customer data|pricing strategy|business plan)\b"
    ],
    
    "internal": [
        # Internal operations
        r"\b(internal|employee only|staff only|team|department)\b",
        r"\b(meeting notes|agenda|minutes|internal memo|memo)\b",
        r"\b(policy|procedure|guideline|handbook|manual)\b",
        r"\b(project plan|roadmap|timeline|milestone|sprint)\b",
        
        # Organizational terms
        r"\b(hr|human resources|it|information technology)\b",
        r"\b(admin|administration|operations|logistics)\b",
        r"\b(training|onboarding|orientation|internal training)\b",
        
        # Internal communications
        r"\b(all hands|company wide|organization|corporate|quarterly)\b",
        r"\b(performance|evaluation|review|assessment)\b",
        r"\b(company-wide|organization-wide|internal announcement)\b"
    ],
    
    "public": [
        # Public-facing content
        r"\b(public|announcement|press release|news|external)\b",
        r"\b(marketing|advertisement|promotion|campaign)\b",
        r"\b(website|blog|social media|public event)\b",
        r"\b(customer|client|visitor|guest|general public)\b",
        
        # General information
        r"\b(general|common|standard|basic|open to all)\b",
        r"\b(faq|frequently asked|help|support|public info)\b",
        r"\b(welcome|introduction|overview|summary)\b",
        
        # Public events
        r"\b(conference|seminar|workshop|presentation|picnic)\b",
        r"\b(event|celebration|party|gathering|open house)\b",
        r"\b(families|everyone|all welcome|public invitation)\b"
    ]
}

# Confidence thresholds for classification
CONFIDENCE_THRESHOLDS = {
    "high": 0.7,
    "medium": 0.5,
    "low": 0.1
}

def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF, DOCX, or TXT files with better error handling."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return extract_text_pdf(file_path)
        elif ext == '.docx':
            return extract_text_docx(file_path)
        elif ext == '.txt':
            return extract_text_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_pdf(file_path: str) -> str:
    """Enhanced PDF text extraction with better handling."""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc):
                try:
                    page_text = page.get_text()  # type: ignore
                    if page_text.strip():  # Only add non-empty pages
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error opening PDF {file_path}: {e}")
        return ""
    return text.strip()

def extract_text_docx(file_path: str) -> str:
    """Enhanced DOCX text extraction including headers, footers, and tables."""
    text_parts = []
    try:
        doc = DocxDocument(file_path)
        
        # Extract main document text
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        # Extract table content
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                if row_text:
                    text_parts.append(" | ".join(row_text))
                    
    except Exception as e:
        logger.error(f"Error extracting DOCX {file_path}: {e}")
        return ""
    
    return "\n".join(text_parts)

def extract_text_txt(file_path: str) -> str:
    """Enhanced text file reading with encoding detection."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            break
    
    return ""

def preprocess_text(text: str) -> str:
    """Clean and preprocess text for better classification."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common noise patterns
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
    
    # Remove page numbers and headers/footers patterns
    text = re.sub(r'--- Page \d+ ---', '', text)
    text = re.sub(r'\bPage \d+\b', '', text)
    
    return text.strip()

def calculate_keyword_scores(text: str) -> Dict[str, float]:
    """Calculate classification scores based on keyword matching."""
    text_lower = text.lower()
    scores = {"confidential": 0.0, "internal": 0.0, "public": 0.0}
    
    for classification, patterns in CLASSIFICATION_KEYWORDS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            # Weight by frequency and pattern specificity
            score_increment = len(matches) * 0.1
            scores[classification] += score_increment
    
    # Normalize scores
    max_score = max(scores.values()) if any(scores.values()) else 1.0
    if max_score > 0:
        scores = {k: v / max_score for k, v in scores.items()}
    
    return scores

def get_text_segments(text: str, max_length: int = 512) -> List[str]:
    """Split text into overlapping segments for better context analysis."""
    if len(text) <= max_length:
        return [text]
    
    segments = []
    overlap = max_length // 4  # 25% overlap
    
    for i in range(0, len(text), max_length - overlap):
        segment = text[i:i + max_length]
        if segment.strip():
            segments.append(segment)
        if i + max_length >= len(text):
            break
    
    return segments

def classify_text_enhanced(text: str) -> Tuple[str, float]:
    """Enhanced text classification with multiple strategies."""
    if not text.strip():
        return "unclassified", 0.0
    
    # Preprocess text
    processed_text = preprocess_text(text)
    if not processed_text:
        return "unclassified", 0.0
    
    # Calculate keyword-based scores
    keyword_scores = calculate_keyword_scores(processed_text)
    
    # Get text segments for ML analysis
    segments = get_text_segments(processed_text, max_length=512)
    
    # ML-based classification on segments
    candidate_labels = ["confidential", "internal", "public"]
    ml_scores = {"confidential": 0.0, "internal": 0.0, "public": 0.0}
    
    try:
        for segment in segments[:3]:  # Analyze up to 3 segments to balance accuracy vs performance
            result = get_classifier()(segment, candidate_labels)
            for label, score in zip(result['labels'], result['scores']):
                ml_scores[label] += score
        
        # Average ML scores across segments
        if segments:
            ml_scores = {k: v / len(segments[:3]) for k, v in ml_scores.items()}
            
    except Exception as e:
        logger.error(f"Error in ML classification: {e}")
        # Fallback to keyword-based classification only
        ml_scores = {"confidential": 0.0, "internal": 0.0, "public": 0.0}
    
    # Combine keyword and ML scores with adaptive weights
    # If keyword scores are strong, give them more weight
    max_keyword_score = max(keyword_scores.values())
    if max_keyword_score > 0.5:
        keyword_weight = 0.6  # Strong keyword signals get more weight
        ml_weight = 0.4
    else:
        keyword_weight = 0.3  # Weak keyword signals, rely more on ML
        ml_weight = 0.7
    
    combined_scores = {}
    for label in candidate_labels:
        combined_scores[label] = (
            keyword_weight * keyword_scores.get(label, 0.0) +
            ml_weight * ml_scores.get(label, 0.0)
        )
    
    # Apply business logic adjustments
    # If "company-wide" or "announcement" without "internal" → likely internal
    text_lower = processed_text.lower()
    if ("company-wide" in text_lower or "quarterly" in text_lower) and "public" not in text_lower:
        combined_scores["internal"] += 0.2
        combined_scores["public"] *= 0.8
    
    # If "families" or "open to all" → likely public
    if "families" in text_lower or "open to all" in text_lower or "everyone" in text_lower:
        combined_scores["public"] += 0.3
        combined_scores["internal"] *= 0.7
    
    # Determine final classification
    best_label = max(combined_scores.keys(), key=lambda k: combined_scores[k])
    best_score = combined_scores[best_label]
    
    # Apply confidence thresholds
    if best_score >= CONFIDENCE_THRESHOLDS["high"]:
        confidence = best_score
    elif best_score >= CONFIDENCE_THRESHOLDS["medium"]:
        confidence = best_score * 0.8  # Reduce confidence for medium scores
    elif best_score >= CONFIDENCE_THRESHOLDS["low"]:
        confidence = best_score * 0.6  # Further reduce for low scores
    else:
        # Very low confidence, default to unclassified
        return "unclassified", best_score
    
    logger.info(f"Classification: {best_label} (confidence: {confidence:.3f}, keyword: {keyword_scores[best_label]:.3f}, ml: {ml_scores[best_label]:.3f})")
    
    return best_label, confidence

def classify_text(text: str) -> str:
    """Backward compatibility wrapper for enhanced classification."""
    classification, confidence = classify_text_enhanced(text)
    return classification

def classify_document(file_path: str) -> str:
    """Enhanced document classification pipeline."""
    try:
        # Extract text
        text = extract_text_from_file(file_path)
        logger.info(f"Extracted text length: {len(text)} for {os.path.basename(file_path)}")
        if len(text) > 0:
            logger.info(f"First 200 chars: {text[:200]}")
        if not text:
            logger.warning(f"No text extracted from {file_path}")
            return "unclassified"
        
        # Classify
        classification, confidence = classify_text_enhanced(text)
        
        logger.info(f"Document {os.path.basename(file_path)} classified as '{classification}' with confidence {confidence:.3f}")
        
        return classification
        
    except Exception as e:
        logger.error(f"Error classifying document {file_path}: {e}")
        return "unclassified"
