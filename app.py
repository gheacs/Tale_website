from flask import Flask, render_template, request, jsonify
import openai
import speech_recognition as sr
from openai import OpenAI
import re
import threading
import tempfile
import os

# Variables to manage state
transcription_buffer = []  # Buffer to hold continuous transcriptions
delay_timer = None  # Timer object for implementing the delay

# Initialize any required global variables
transcription_accumulator = []  # Accumulates transcription text from each chunk
processing_lock = threading.Lock()  # Ensures thread-safe operations on the accumulator


app = Flask(__name__)

# Initialize OpenAI client
openai.api_key = "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"


"""
Transcription through whisper
"""
def transcribe_audio(file_path):
    try:
        response = openai.audio.transcriptions.create(
            file=open(file_path, "rb"),
            model="whisper-1",
            prompt="So uhm, yeaah. ehm, uuuh. like.",
        )
        print(response.text)
        return response.text
    except Exception as e:
        return str(e)
 
"""
GPT word retrieval 
"""  
def get_completion(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                "role": "system",
                "content": "You are assisting Aphasic patients with their speech. Return the most appropriate word based on the context and only return the word. The text will contain stutters or repetitions."
      },
                {"role": "user", "content": prompt}
            ]
        )   
        completion = response.choices[0].message.content.strip()
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
    
    # Detect
    repetitions = re.findall(repetition_pattern, transcribed_text)
    prolongations = re.findall(prolongation_pattern, transcribed_text)
    interjections = re.findall(interjection_pattern, transcribed_text)
    
    # Return detected patterns
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
    print(response)
    # Clear the buffer after processing
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
            # start or reset the delay timer
            delay_timer = threading.Timer(5.0, handle_stutter_detection)  # 5-second delay
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
        print("No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400

    # Save the incoming audio chunk to a temporary file
    audio_file = request.files['audio-file']
    _, temp_path = tempfile.mkstemp(suffix=".wav")
    audio_file.save(temp_path)

    try:
        # Transcribe the audio chunk
        transcribed_text = process_transcription_chunk(temp_path)
        detected_patterns = detect_stutter_patterns(transcribed_text)  # Detect stutter patterns

        suggestion_response = "No stutter detected."
        if any(detected_patterns.values()):  # If any stutter patterns are detected
            suggestion_response = get_completion(transcribed_text)  # Get completion for stuttered text
        
        os.remove(temp_path)  # Cleanup the temporary file

        # Respond with the transcription and any detected stutter patterns
        return jsonify({
            "transcription": transcribed_text,
            "detected_patterns": detected_patterns,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)
