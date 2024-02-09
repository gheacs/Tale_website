from flask import Flask, render_template, request, jsonify
import openai
import re
import threading
import tempfile
import os

app = Flask(__name__)

# Initialize OpenAI client
openai.api_key = "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"

# Variables to manage state
transcription_buffer = []
delay_timer = None
processing_lock = threading.Lock()

"""
Transcription through whisper
"""
def transcribe_audio(file_path):
    try:
        response = openai.Audio.create(
            file=open(file_path, "rb"),
            model="whisper-1",
            return_transcription=True
        )
        return response.transcription
    except Exception as e:
        return str(e)

"""
GPT word retrieval 
"""  
def get_completion(prompt):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt="You are assisting Aphasic patients with their speech. Return the most appropriate word based on the context and only return the word. The text will contain stutters or repetitions. Your text: " + prompt
        )   
        completion = response.choices[0].text.strip()
        return completion
    except Exception as e:
        return str(e)

"""
Stutter detection
"""
def detect_stutter_patterns(transcribed_text):

    repetition_pattern = r'(\b\w+\b)(?:\s+\1\b)+'  # Words repeated consecutively
    prolongation_pattern = r'(\w)\1{2,}'  # Characters repeated more than twice
    interjection_pattern = r'\b(uh|um|ah)\b'  # Common interjections
    
    repetitions = re.findall(repetition_pattern, transcribed_text)
    prolongations = re.findall(prolongation_pattern, transcribed_text)
    interjections = re.findall(interjection_pattern, transcribed_text)
    
    detected = {
        "repetitions": repetitions,
        "prolongations": prolongations,
        "interjections": interjections
    }
    return detected

"""
Word retrieval after stutter detection
"""
def handle_stutter_detection():
    combined_text = " ".join(transcription_buffer)
    response = get_completion(combined_text)
    transcription_buffer.clear()

"""
Processing chunks of audio
"""
def process_transcription_chunk(audio_chunk_path):
    global delay_timer
    transcribed_text = transcribe_audio(audio_chunk_path)
    transcription_buffer.append(transcribed_text)
    
    if detect_stutter_patterns(transcribed_text):
        if delay_timer is None or not delay_timer.is_alive():
            delay_timer = threading.Timer(5.0, handle_stutter_detection)
            delay_timer.start()

"""
Front End Code below
"""
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/record', methods=['POST'])
def record():
    if 'audio-file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio-file']
    _, temp_path = tempfile.mkstemp(suffix=".wav")
    audio_file.save(temp_path)

    try:
        transcribed_text = transcribe_audio(temp_path)
        detected_patterns = detect_stutter_patterns(transcribed_text)
        
        # Get AI suggestion
        ai_suggestion = ""
        if detected_patterns:
            ai_suggestion = get_completion(transcribed_text)

        os.remove(temp_path)

        return jsonify({
            "transcription": transcribed_text,
            "detected_patterns": detected_patterns,
            "ai_suggestion": ai_suggestion  # Include AI suggestion in the response
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
