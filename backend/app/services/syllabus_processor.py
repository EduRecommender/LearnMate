import re

import pdfplumber


def extract_syllabus_info(pdf_path):
    course_name = None
    session_content = []

    excluded_sections = [
        "office hours",
        "professor",
        "email",
        "biography",
        "teaching methodology",
        "ai policy",
        "assessment",
        "grading",
        "re-take",
        "bibliography",
        "ethics",
        "attendance",
        "plagiarism",
        "student privacy",
        "decisions about grades",
        "evaluation criteria",
    ]

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        first_text = first_page.extract_text()

        if first_text:
            lines = [line.strip() for line in first_text.split("\n") if line.strip()]

            for line in lines:
                if not any(excluded in line.lower() for excluded in excluded_sections):
                    course_name = line
                    break

            for line in lines:
                match = re.search(r"^(Course Name:|AI:|Bachelor in .*|BCSAI SEP.*)(.+)", line, re.IGNORECASE)
                if match:
                    course_name = match.group(2).strip()
                    break

        extracting_sessions = False
        for page in pdf.pages:
            page_text = page.extract_text()
            if not page_text:
                continue

            lines = [line.strip() for line in page_text.split("\n") if line.strip()]
            for line in lines:
                if re.search(r"\bPROGRAM\b", line, re.IGNORECASE) or re.search(r"\bSESSION\s*1\b", line, re.IGNORECASE):
                    extracting_sessions = True
                    continue

                if any(excluded in line.lower() for excluded in excluded_sections):
                    extracting_sessions = False

                if extracting_sessions:
                    line = re.sub(r"\(LIVE IN-PERSON\)", "", line, flags=re.IGNORECASE).strip()

                    session_match = re.match(r"Session\s*\d+:\s*(.+)", line, re.IGNORECASE)
                    if session_match:
                        session_content.append(session_match.group(1))
                    else:
                        topic_match = re.match(r"^\s*[\-•]?\s*([A-Za-z].+)", line)
                        if topic_match:
                            session_content.append(topic_match.group(1))

    return course_name, session_content


def process_uploaded_syllabus(pdf_file):
    course_name, session_content = extract_syllabus_info(pdf_file)
    return {
        "course_name": course_name,
        "session_content": session_content,
    }
