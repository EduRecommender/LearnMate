# utils/context_loader.py

import fitz  # PyMuPDF
import os
import sys
import re

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return f"Error loading {os.path.basename(pdf_path)}: {str(e)}"

def load_scientific_context():
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")
    context_list = []
    
    print(f"Looking for scientific context in: {folder}")
    
    if not os.path.exists(folder):
        print(f"Warning: Knowledge base folder not found at {folder}")
        return ["No scientific context available."]
    
    try:
        files = os.listdir(folder)
        print(f"Found {len(files)} files in knowledge base")
        
        for filename in files:
            filepath = os.path.join(folder, filename)
            print(f"Processing {filename}...")
            try:
                if filename.endswith(".pdf"):
                    context_list.append(extract_text_from_pdf(filepath))
                elif filename.endswith(".txt"):
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        context_list.append(f.read())
                else:
                    print(f"Skipping unsupported file type: {filename}")
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
                context_list.append(f"Error loading {filename}: {str(e)}")
                
        print(f"Successfully loaded {len(context_list)} context documents")
    except Exception as e:
        print(f"Error loading scientific context: {e}")
        context_list = ["Error loading scientific context."]
    
    return context_list

def extract_syllabus_topics(syllabus_content):
    """
    Extract a list of topics from a syllabus.
    This function is used by the resources agent to search for topic-specific resources.
    """
    if not syllabus_content or not isinstance(syllabus_content, dict):
        return []
    
    # Extract topics from the syllabus content
    topics = []
    
    # Try to extract from topics list first
    if "topics" in syllabus_content and isinstance(syllabus_content["topics"], list):
        topics.extend(syllabus_content["topics"])
    
    # Try to extract from schedule if available
    if "schedule" in syllabus_content and isinstance(syllabus_content["schedule"], list):
        # Schedule items often contain topics
        for item in syllabus_content["schedule"]:
            if isinstance(item, str):
                # Try to extract topic from schedule item
                # Look for patterns like "Topic: X" or similar
                topic_match = re.search(r'(?i)(?:topic|subject|content)(?:\s*:)?\s+(.+?)(?:\.|$)', item)
                if topic_match:
                    topics.append(topic_match.group(1).strip())
    
    # Clean up topics
    cleaned_topics = []
    for topic in topics:
        if isinstance(topic, str) and topic.strip():
            # Remove any numbering or bullets
            cleaned = re.sub(r'^\s*\d+\.\s*|\s*[•*-]\s*', '', topic.strip())
            if cleaned:
                cleaned_topics.append(cleaned)
    
    return cleaned_topics

