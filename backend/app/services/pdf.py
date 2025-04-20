import os
import logging
import tempfile
from typing import Optional, Dict, Any
import PyPDF2
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Process a PDF file to extract its content and metadata
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary containing extracted content and metadata
    """
    try:
        logger.info(f"Processing PDF file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"PDF file not found at path: {file_path}")
            return {
                "success": False,
                "error": "File not found",
                "content": None
            }
        
        # Get file size
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        logger.info(f"PDF file size: {file_size:.2f} MB")
        
        # Extract content using PyPDF2
        content = extract_pdf_content(file_path)
        
        # Extract metadata
        metadata = extract_pdf_metadata(file_path)
        
        # Try to detect if this is a syllabus
        is_syllabus = detect_syllabus(content)
        
        # Process syllabus if detected
        syllabus_data = {}
        if is_syllabus:
            logger.info("Detected file as a syllabus, extracting structured data")
            syllabus_data = extract_syllabus_structure(content)
        
        return {
            "success": True,
            "content": content,
            "metadata": metadata,
            "is_syllabus": is_syllabus,
            "syllabus_data": syllabus_data,
            "file_size_mb": file_size
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "content": None
        }

def extract_pdf_content(file_path: str) -> str:
    """Extract text content from a PDF file"""
    text = ""
    
    try:
        with open(file_path, 'rb') as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get number of pages
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            # Extract text from each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
                
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        return f"Error extracting content: {str(e)}"

def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a PDF file"""
    try:
        with open(file_path, 'rb') as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get metadata
            metadata = pdf_reader.metadata
            
            if metadata:
                # Convert to a regular dict with string values
                return {
                    "title": metadata.get('/Title', ''),
                    "author": metadata.get('/Author', ''),
                    "subject": metadata.get('/Subject', ''),
                    "creator": metadata.get('/Creator', ''),
                    "producer": metadata.get('/Producer', ''),
                    "pages": len(pdf_reader.pages)
                }
            else:
                return {"pages": len(pdf_reader.pages)}
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {str(e)}")
        return {"error": str(e)}

def detect_syllabus(content: str) -> bool:
    """Detect if a document is likely a syllabus"""
    # Common keywords found in syllabi
    syllabus_keywords = [
        "syllabus", "course outline", "course schedule", "learning objectives",
        "required text", "course description", "grading policy", "office hours",
        "lecture schedule", "class schedule", "reading assignments", "prerequisites",
        "assessment criteria", "academic integrity", "attendance policy"
    ]
    
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()
    
    # Count occurrences of syllabus keywords
    keyword_count = sum(1 for keyword in syllabus_keywords if keyword in content_lower)
    
    # If at least 3 keywords are found, it's likely a syllabus
    return keyword_count >= 3

def extract_syllabus_structure(content: str) -> Dict[str, Any]:
    """Extract structured data from a syllabus"""
    syllabus_data = {
        "course_name": "",
        "instructor": "",
        "session_content": [],
        "topics": [],
        "assessment": []
    }
    
    # Extract course name
    course_patterns = [
        r"(?:Course|Class)(?:\s+Title)?:\s*([^\n]+)",
        r"(?:Course|Class)(?:\s+Name)?:\s*([^\n]+)"
    ]
    
    for pattern in course_patterns:
        matches = re.findall(pattern, content)
        if matches:
            syllabus_data["course_name"] = matches[0].strip()
            break
    
    # Extract instructor information
    instructor_patterns = [
        r"(?:Instructor|Professor|Teacher)(?:'s Name)?:\s*([^\n]+)",
        r"(?:Taught|Led) by:\s*([^\n]+)"
    ]
    
    for pattern in instructor_patterns:
        matches = re.findall(pattern, content)
        if matches:
            syllabus_data["instructor"] = matches[0].strip()
            break
    
    # Extract session content
    session_patterns = [
        r"(?:Session|Week|Module|Lecture|Class)\s*(\d+)[:\s]+([^\n]+)",
        r"(?:Day|Session)\s*(\d+)(?:\n|\r\n|\r)([^\n]+)"
    ]
    
    for pattern in session_patterns:
        matches = re.findall(pattern, content)
        if matches:
            for session_num, topic in matches:
                syllabus_data["session_content"].append({
                    "session": session_num.strip(),
                    "topic": topic.strip()
                })
    
    # Extract topics (may overlap with sessions)
    topic_patterns = [
        r"(?:Topic|Subject)[:\s]+([^\n]+)",
        r"•\s+([^\n•]+)"
    ]
    
    for pattern in topic_patterns:
        matches = re.findall(pattern, content)
        if matches:
            for topic in matches:
                if len(topic.strip()) > 3:  # Filter out too short matches
                    syllabus_data["topics"].append(topic.strip())
    
    # Extract assessment information
    assessment_patterns = [
        r"(?:Assessment|Grading|Evaluation)[:\s]+([^\n]+)",
        r"(?:Assignment|Quiz|Exam|Test)[:\s]+([^\n]+)",
        r"(\d+)%\s+([^\n]+)"
    ]
    
    for pattern in assessment_patterns:
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    # Handle tuple results from regex groups
                    syllabus_data["assessment"].append(" ".join([m.strip() for m in match]))
                else:
                    syllabus_data["assessment"].append(match.strip())
    
    return syllabus_data 