# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

###
chatbox = st.container(height=500)

for message in st.session_state.messages:
  if message["role"] == "model":
    temp_role = "ai"
  else:
    temp_role = "user"
  chatbox.chat_message(temp_role).markdown(message["parts"])

if prompt := st.chat_input("What is up?"):
  st.session_state.messages.append({"role": "user", "parts": prompt})
  chatbox.chat_message("user").markdown(prompt)

  response = chat_session.send_message(prompt)
  chatbox.chat_message("ai").write_stream(stream_like(response.text))
  st.session_state.messages.append({"role": "model", "parts": response.text})
###
