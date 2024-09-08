import re
import nltk
from pdfminer.high_level import extract_text

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

# Define keywords for each section
SECTION_HEADERS = {
    'skills': ['skills', 'technical skills', 'soft skills'],
    'projects': ['projects', 'project work', 'project details'],
    'education': ['education', 'academic qualifications', 'educational background', 'academic achievements'],
    'certifications': ['certifications', 'courses', 'trainings'],
    'experience': ['experience', 'work experience', 'professional experience'],
    'training': ['training', 'internships'],
}

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

# Extract text for a specific section
def extract_section_text(input_text, section_key):
    lines = input_text.split('\n')
    section_text = []
    is_in_section = False
    for line in lines:
        stripped_line = line.strip().lower()
        if any(header in stripped_line for header in SECTION_HEADERS[section_key]):
            is_in_section = True
            continue
        if is_in_section and any(header in stripped_line for header in SECTION_HEADERS if header != section_key):
            break
        if is_in_section:
            section_text.append(line.strip())

    return ' '.join(section_text)

# Extract detailed education information
def extract_education_details(education_text):
    education_details = []
    education_patterns = {
        '10th': re.compile(r'(?i)(matriculation|10th|schooling)'),
        '12th': re.compile(r'(?i)(12th|intermediate)'),
        'bachelor': re.compile(r'(?i)(bachelor|graduation|degree)'),
        'percentage': re.compile(r'(\d{1,2}\.\d{1,2}%|\d{2,3}%|cgpa\s*[\d\.]+)'),
    }

    for line in education_text.split('.'):
        for level, pattern in education_patterns.items():
            if pattern.search(line):
                education_details.append((level, line.strip()))
                break

    return education_details

# Main function to extract all relevant sections
def extract_resume_sections(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    extracted_data = {}

    for section in SECTION_HEADERS.keys():
        section_text = extract_section_text(text, section)
        extracted_data[section] = section_text

        if section == 'education':
            extracted_data['education_details'] = extract_education_details(section_text)

    return extracted_data

if __name__ == '__main__':
    resume_path = ''  # Change this to your resume PDF path
    extracted_data = extract_resume_sections(resume_path)

    # Print extracted sections
    for section, content in extracted_data.items():
        print(f"--- {section.upper()} ---")
        print(content)
