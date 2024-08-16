import streamlit as st
import google.generativeai as genai
import time
import fitz
import os
import base64

st.set_page_config(layout="wide")
st.title("Quiz Generator")

genai.configure(api_key=st.secrets["API_KEY"])

if "model" not in st.session_state:
  st.session_state["model"] = "gemini-1.5-flash"

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 2048,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name=st.session_state["model"],
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  system_instruction = "You are a very skilled virtual assistant, here to help people create quizzes from the PDF files they upload. You will generate exercises and display each question for users to answer, helping them review the knowledge contained in the provided file. You will explain clearly and thoroughly so that they understand the questions and the knowledge in the file."
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

if "messages" not in st.session_state:
  st.session_state.messages = [{"role": "model", "parts": "Hi there!👋 How can I help you?"}]

chat_session = model.start_chat(
  history=st.session_state.messages
)

def stream_like(content):
  for word in content.split():
    yield word + " "
    time.sleep(0.05)

uploaded_files = st.file_uploader("Chọn các file PDF", type=["pdf"], accept_multiple_files=True)

### init
if "quiz_displayed" not in st.session_state:
  st.session_state.quiz_displayed = []

# Tạo file lưu tạm thời
if not os.path.exists("tempDir"):
  os.makedirs("tempDir")

if "quiz_content" not in st.session_state:
  st.session_state.quiz_content = ""

if "questions" not in st.session_state:
  st.session_state.questions = []

if "answers" not in st.session_state:
  st.session_state.answers = None
if "question_index" not in st.session_state:
  st.session_state.question_index = 0
if "correct" not in st.session_state:
  st.session_state.correct = [""]
###

# Function để đọc nội dung PDF
def read_pdf(file_path):
  doc = fitz.open(file_path)
  text = ""
  for page in doc:
    text += page.get_text()
  return text

# Function để gộp PDF
def merge_pdfs(pdf_paths, output_path):
    pdf_writer = fitz.open()  # Tạo một tài liệu PDF mới
    for path in pdf_paths:
        pdf_reader = fitz.open(path)  # Mở file PDF
        pdf_writer.insert_pdf(pdf_reader)  # Gộp file PDF
    pdf_writer.save(output_path)  # Lưu file PDF gộp
    pdf_writer.close()

format = {
  "Multiple choice": 
  "<Question>: A) <Choice 1>; B) <Choice 2>; C) <Choice 3>; D) <Choice 4>;"
}
example = {
  "Multiple choice":
  """
  Question 1: What is the capital of France? A) Paris; B) London; C) Berlin; D) Rome;
Question 2: What is the capital of Vietnam? A) Ho Chi Minh; B) Hai Phong; C) Ha Noi; D) Ca Mau;
Question 3: Which is the largest continent in the world? A) Asia; B) Europe; C) America; D) Antarctica;
  """
}

def generate_quiz(text, quiz_type, number_of_questions):
  string_format = format[quiz_type]
  string_example = example[quiz_type]
  if quiz_type == "Multiple choice":
    prompt = f"Generate a multiple-choice quiz consists of {number_of_questions} from the following text:\n```\n{text}\n```\nFollow this format:\n```\n{string_format}\n```\nHere are some examples:\n```\n{string_example}\n```\n Don't say anything else, just write the response in plain text no bold or italics characters and line breaks in each question only."
  elif quiz_type == "Cloze test":
    prompt = f"Generate a cloze test from the following text:\n{text}"
  elif quiz_type == "Summary with quiz":
    prompt = f"Summarize the following text and create a quiz:\n{text}"
  #st.markdown(prompt)
  #st.session_state.messages.append({"role": "user", "parts": prompt}) #temp
  response = chat_session.send_message(prompt)
  #st.session_state.messages.append({"role": "model", "parts": response.text}) #temp
  return response.text  

def get_question(quiz_content, quiz_type):
  if quiz_type == "Multiple choice":
    get_questions = []
    for question in quiz_content.strip().split('Question ')[1:]:
      parts = question.split('; ')
      question_text = parts[0].strip().split("?")
      question_text = question_text[0]
      answer_A = parts[0].strip().rsplit("A)", 1)
      answer_A = "A) " + answer_A[1]
      options = {part[0]: part for part in parts[1:] if part}
      get_questions.append({"question": f"Question {question_text}","A": answer_A, **options})
  return get_questions

def next_question():
  st.session_state.question_index += 1

def count_correct():
    cnt = 0
    for r in st.session_state.correct:
      if r.strip().startswith("1. **Correct**"):
        cnt += 1
    return cnt

def display_quiz(quiz_type, questions, text):
  if quiz_type == "Multiple choice":
    # Hiển thị câu hỏi
    #st.write(st.session_state.question_index)
    for i,q in enumerate(questions[:st.session_state.question_index+1]):
      st.write(q["question"])
      for key in ['A', 'B', 'C', 'D']:
        st.write(q[key])    
      
      with st.form(key=f"answer_form_{i}"):
        # Lưu câu trả lời đã chọn
        st.session_state.answers[i] = st.selectbox(
          "Chọn câu trả lời của bạn",
          ["A", "B", "C", "D"],
          index=None if st.session_state.answers[i] is None else ["A", "B", "C", "D"].index(st.session_state.answers[i]),
          key=f"question_{i}"
        )

        #temp = ""
        if st.form_submit_button("Submit"):
          #st.session_state.correct[i]=""
          prompt = f"""
  Please confirm whether the answer is correct and explain why based on the following text:
  ```
  {text}
  ```
  This is a multiple choice question, there is only one correct answer in those available options. If the answer the user chooses is the most correct answer among the available answers, assume they are right and agree with that answer:
  Question: {q["question"]}
  Available options:
  {q["A"]}
  {q["B"]}
  {q["C"]}
  {q["D"]}
  The user's answer is {st.session_state.answers[i]}
  Please respond in the following format: 
  1. Correct or incorrect
  2. Explanation
  """
          response = chat_session.send_message(prompt)
          #temp = response.text
          #if st.session_state.correct[i]=="":
          st.session_state.correct[i] = response.text
        st.write(st.session_state.correct[i])
        
    #st.write(st.session_state.correct)
    #st.write(st.session_state.answers)

    if st.session_state.question_index<len(questions) - 1:
      if st.button("Next", on_click=next_question):
        st.write("")
    elif st.session_state.question_index==len(questions)-1 and st.session_state.answers[st.session_state.question_index]!=None:
      st.success("Bạn đã hoàn thành tất cả các câu hỏi!")
      correct_count = count_correct()
      st.success(f"Số câu trả lời đúng: {correct_count}/{len(questions)}")

combined_text = ""
if uploaded_files:
  pdf_paths = []
  for uploaded_file in uploaded_files:
    # Lưu file tạm thời
    file_path = os.path.join("tempDir", uploaded_file.name)
    with open(file_path, "wb") as f:
      f.write(uploaded_file.getbuffer())
      
    pdf_paths.append(file_path)  # Lưu đường dẫn file PDF
    # Đọc nội dung từ file PDF
    pdf_text = read_pdf(file_path)
    combined_text += pdf_text

  # Gộp các file PDF lại
  merged_pdf_path = os.path.join("tempDir", "merged.pdf")
  merge_pdfs(pdf_paths, merged_pdf_path)
  
  # Hiển thị file PDF gộp lại
  with open(merged_pdf_path, "rb") as f:
    merged_base64 = base64.b64encode(f.read()).decode("utf-8")
    merged_pdf_display = f'<embed src="data:application/pdf;base64,{merged_base64}" width="700" height="750" type="application/pdf">'
    st.markdown(merged_pdf_display, unsafe_allow_html=True)
  
  st.success("Đã đọc xong nội dung từ file PDF!")

  # Chọn loại quiz
  quiz_type = st.selectbox("Hãy chọn loại quiz bạn muốn tôi tạo cho bạn:", ["Multiple choice"])
  number_of_questions = st.slider("Số lượng câu hỏi:", 1, 100, 10)
  if st.button("Generate quiz"):
    #st.write("HI, IT'S RESET")
    st.session_state.quiz_content = ""
    st.session_state.answers = [None] * number_of_questions
    st.session_state.question_index = 0
    st.session_state.correct = [""] * number_of_questions
    with st.spinner("Generating quiz..."):
      st.session_state.quiz_content = generate_quiz(combined_text, quiz_type, number_of_questions)
      st.session_state.questions = get_question(st.session_state.quiz_content, quiz_type)
  display_quiz(quiz_type, st.session_state.questions, combined_text)

with st.sidebar:
  st.title("Chat with AI")
  chatbox = st.container(height=566)

  for message in st.session_state.messages:
    if message["role"] == "model":
      temp_role = "ai"
    else:
      temp_role = "user"
    chatbox.chat_message(temp_role).write(message["parts"])
  
  if prompt := st.chat_input("How can I help you?"):
    st.session_state.messages.append({"role": "user", "parts": prompt})
    chatbox.chat_message("user").write(prompt)

    prompt = prompt + f"\nanswer the question above based on the following text:\n{combined_text}"

    response = chat_session.send_message(prompt)
    chatbox.chat_message("ai").write_stream(stream_like(response.text))
    st.session_state.messages.append({"role": "model", "parts": response.text})