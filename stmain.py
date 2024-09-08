import streamlit as st
from pdfminer.high_level import extract_text
import re
import nltk
import tabula
import os

# Download required NLTK resources
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

# Define keywords for each section (excluding 'education details')
SECTION_HEADERS = {
    'education': ['education', 'academic qualifications', 'educational background'],
    'certifications': ['certifications', 'courses', 'participations', 'certificates', 'certificate'],
    'internship_experience': ['internship', 'work experience', 'professional experience', 'training', 'internships'],
    'projects': ['projects', 'project work', 'project details'],
}

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

# Function to detect and convert tables to line-by-line format if present
def detect_and_convert_tables(pdf_path):
    try:
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        if tables:
            text = ""
            for table in tables:
                text += table.to_string(index=False, header=False)
            return text
    except Exception as e:
        st.error(f"Error reading tables from PDF: {e}")
    return None

# Function to extract the name (assuming it's the first line of the text)
def extract_name(resume_text):
    lines = resume_text.split('\n')
    for line in lines:
        if re.match(r'[A-Za-z\s]+', line):
            return line.strip()

# Function to extract phone numbers from text
PHONE_REG = re.compile(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]')
def extract_phone_number(resume_text):
    phone = re.findall(PHONE_REG, resume_text)
    if phone:
        number = ''.join(phone[0])
        if len(number) < 16:
            return number
    return None

# Function to extract emails from text
EMAIL_REG = re.compile(r'[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+')
def extract_emails(resume_text):
    return re.findall(EMAIL_REG, resume_text)

# Function to extract text for a specific section
def extract_section_text(input_text, section_key):
    lines = input_text.split('\n')
    section_text = []
    is_in_section = False
    for line in lines:
        stripped_line = line.strip().lower()
        if any(header in stripped_line for header in SECTION_HEADERS[section_key]):
            is_in_section = True
            section_text.append(line.strip())  # Add the heading line
            continue
        if is_in_section:
            # Check if the line belongs to a different section
            if any(header in stripped_line for header in SECTION_HEADERS if header != section_key):
                break
            section_text.append(line.strip())

    return '\n'.join(section_text)

# Function to refine and extract education-related text with headings
def refine_education_section(education_text):
    refined_text = []
    current_heading = None
    previous_heading = None
    last_institution = None

    for line in education_text.split('\n'):
        line_clean = re.sub(r'\s+', ' ', line.strip())  # Remove extra spaces between words
        line_lower = line_clean.lower()

        # Detect degree level and add heading
        if any(keyword in line_lower for keyword in ['b. tech', 'bachelor', 'graduate', 'b.tech', 'graduation','college of engineering']):
            if current_heading != "Bachelor's Degree:":
                previous_heading = current_heading
                current_heading = "Bachelor's Degree:"
                refined_text.append("\n" + current_heading)  # Add a newline before the heading
            last_institution = None
            refined_text.append(line_clean)
        elif any(keyword in line_lower for keyword in ['master', 'postgraduate', 'phd']):
            if current_heading != "Master's/PhD Degree:":
                previous_heading = current_heading
                current_heading = "Master's/PhD Degree:"
                refined_text.append("\n" + current_heading)  # Add a newline before the heading
            last_institution = None
            refined_text.append(line_clean)
        elif any(keyword in line_lower for keyword in ['class xii', '12th', 'hsc', 'intermediate', '(xii)', 'academy', 'college', 'sec school']):
            if current_heading != "Class XII:":
                previous_heading = current_heading
                current_heading = "Class XII:"
                refined_text.append("\n" + current_heading)  # Add a newline before the heading
            last_institution = None
            refined_text.append(line_clean)
        elif any(keyword in line_lower for keyword in ['class x', '10th', 'schooling', 'xth', 'school', 'high school']):
            if current_heading != "Class X:":
                previous_heading = current_heading
                current_heading = "Class X:"
                refined_text.append("\n" + current_heading)  # Add a newline before the heading
            last_institution = None
            refined_text.append(line_clean)
        # Add the institution/college/school name directly under the respective heading
        elif current_heading and any(keyword in line_lower for keyword in ['university', 'institute', 'school', 'college']):
            if line_clean != last_institution:
                refined_text.append("    " + line_clean)  # Indent institution/college/school name
                last_institution = line_clean
        # Add percentages, CGPA, or duration under the respective heading
        elif current_heading and any(keyword in line_lower for keyword in ['cgpa', 'percentage', '%', 'years', 'year', 'duration', 'sgpa']):
            if not any(keyword in line_lower for keyword in ['university', 'institute', 'school', 'college']):
                refined_text.append("    " + line_clean)  # Indent percentages, CGPA, etc.

    return '\n'.join(refined_text).strip()

# Function to extract skills (technical and soft skills)
def extract_skills(resume_text):
    skills = []
    skills_section_keywords = ['skills', 'technical skills', 'technologies', 'proficiencies','soft skills', 'industry skills']
    skill_keywords = [
        'machine learning', 'data science', 'python', 'java', 'excel', 'sql', 'javascript', 'c++', 'html', 'css', 'AWS', 'microsoft azure', 'DOCKER', 'bootstrap',
        'HTML-5', 'CSS-3', 'JAVASCRIPT', 'BOOTSTRAP', 'DJANGO', 'MYSQL','soft skills', 'web technologies', 'Database Tools', 'Cloud Technologies', 'javascript', 'django'
    ]
    in_skills_section = False
    
    for line in resume_text.split('\n'):
        line_lower = line.strip().lower()
        if any(keyword in line_lower for keyword in skills_section_keywords):
            in_skills_section = True
            continue
        
        if in_skills_section:
            if any(skill in line_lower for skill in skill_keywords):
                skills.append(line.strip())
            if re.match(r'^\s*(projects|certifications|courses)\b', line_lower, re.IGNORECASE):
                in_skills_section = False

    return skills

# Function to extract all relevant sections
def extract_resume_sections(input_text):
    extracted_data = {}

    for section in SECTION_HEADERS.keys():
        section_text = extract_section_text(input_text, section)
        if section == 'education':
            section_text = refine_education_section(section_text)
        elif section == 'internship_experience':  # Combine internship, experience, and training
            if section_text:
                section_text = "\n".join([f"- {line.strip()}" for line in section_text.split('\n') if line.strip()])
        extracted_data[section] = section_text

    return extracted_data

# Streamlit App
st.title("Resume Parser")

uploaded_files = st.file_uploader("Upload one or more resumes (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.subheader(f"Results for {uploaded_file.name}")
        
        # Save uploaded file to a temporary path
        with open(f"temp_{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Check if the resume has tables and convert them to text if found
        table_text = detect_and_convert_tables(f"temp_{uploaded_file.name}")
        
        if table_text:
            text = table_text
        else:
            text = extract_text_from_pdf(f"temp_{uploaded_file.name}")

        # Extract and display name
        name = extract_name(text)
        st.header("Name")
        st.write(name)

        # Extract and display phone number
        phone_number = extract_phone_number(text)
        st.header("Phone Number")
        st.write(phone_number)

        # Extract and display email
        emails = extract_emails(text)
        st.header("Email")
        st.write(', '.join(emails))

        # Extract and display skills
        skills = extract_skills(text)
        st.header("Skills")
        for skill in skills:
            st.write(skill)

        # Extract and display sections
        sections = extract_resume_sections(text)

        for section, content in sections.items():
            if content:
                st.header(section.capitalize())
                st.text(content)

        # Remove temporary file
        os.remove(f"temp_{uploaded_file.name}")
