import os
import logging
import pdfplumber
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai  import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from .forms import PDFUploadForm

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyA_pk0BORIx4jxlRRDaJxYw0Dz-vrg16-Y") 

# Initialize the language model
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=API_KEY
)

def remove_text(text):

    return text.replace('*', '').replace('\n', ' ').strip()

def extract_from_pdf(pdf_file):
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        logging.error(f"Error reading PDF: {e}")
    return remove_text(text)

def chat_view(request):
    response = ""
    conversation = request.session.get('conversation', [])
    uploaded_file_name = request.session.get('uploaded_file_name', "")
    pdf_text = request.session.get('pdf_text', "")

    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            # Handle PDF upload
            pdf_file = request.FILES['pdf_file']
            uploaded_file_name = pdf_file.name
            pdf_text = extract_from_pdf(pdf_file)

            if pdf_text:
                request.session['pdf_text'] = pdf_text
                request.session['uploaded_file_name'] = uploaded_file_name
                request.session['conversation'] = []  # Clear conversation
                response = "PDF uploaded successfully. You can now ask questions."
            else:
                response = "The uploaded PDF is empty or cannot be read."

        elif 'question' in request.POST:
            # Handle questions
            question = request.POST.get('question')

            if pdf_text:
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", "You are a chatbot knowledgeable about the provided document."),
                        ("human", f"Question: {question}\nContext: {pdf_text}")
                    ]
                )
                output_parser = StrOutputParser()
                chain = prompt | llm | output_parser

                try:
                    answer = chain.invoke({'question': question, 'context': pdf_text})
                    answer = remove_text(answer)
                    conversation.append({'question': question, 'response': answer})
                    request.session['conversation'] = conversation
                except Exception as e:
                    response = f"Error while querying the API: {e}"
            else:
                response = "Please upload a PDF first."

    else:
        # Initialize form if not a POST request
        form = PDFUploadForm()

    return render(request, 'chatbot/chat.html', {  # Update to your template
        'form': PDFUploadForm(),  # Render the upload form
        'conversation': conversation,
        'response': response,
        'uploaded_file_name': uploaded_file_name,
    })
