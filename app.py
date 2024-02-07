from flask import Flask, render_template, request
import speech_recognition as sr
from openai import OpenAI
import tempfile
import pydub
from gtts import gTTS

app = Flask(__name__)

# Initialize OpenAI client
openai_api_key = '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'
openai_client = OpenAI(api_key=openai_api_key)

# Initialize Speech Recognition
recognizer = sr.Recognizer()

# Function to capture speech
def capture_speech():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    return audio

# Function to convert speech to text using Speech Recognition
def speech_to_text(audio):
    text = recognizer.recognize_google(audio)
    return text

# Function to generate suggestions using OpenAI model
def generate_suggestions(prompt):
    suggestions = openai_client.completions.create(
        model="davinci-002",  # Use the recommended replacement model
        prompt=prompt,
        max_tokens=50  # Set the maximum number of tokens for the generated text
    )
    return suggestions.choices[0].text.strip()

# Function to provide real-time feedback
def provide_feedback(messages):
    print("Feedback:")
    # Generate suggestions based on the user's input
    suggestions = generate_suggestions(messages[-1]["content"])
    print(suggestions)
    return suggestions

# Function to convert text to speech and play in real-time
def text_to_speech(text):
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        tts = gTTS(text=text, lang="en")
        tts.save(fp.name)
        sound = pydub.AudioSegment.from_mp3(fp.name)
        pydub.playback.play(sound)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/record', methods=['POST'])
def record():
    audio = capture_speech()
    try:
        text = speech_to_text(audio)
        feedback_text = provide_feedback([{"role": "user", "content": text}])
        text_to_speech(feedback_text)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Error with the service: {e}")
    return "OK"

if __name__ == "__main__":
    app.run(debug=True)
