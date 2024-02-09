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
                    "content": "You are assisting Aphasic patients with their speech. Return the most appropriate word based on the context and only return the word. The text will contain stutters or repetitions.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        completion = response.choices[0].message.content.strip()
        return completion
    except Exception as e:
        return str(e)


"""
Stutter detection
"""


def detect_stutter_patterns(transcribed_text):
    repetition_pattern = r"(\b\w+\b)(?:\s+\1\b)+"  # Words repeated consecutively
    prolongation_pattern = r"(\w)\1{2,}"  # Characters repeated more than twice
    interjection_pattern = r"\b(uh|um|ah)\b"  # Common interjections

    # Detect
    repetitions = re.findall(repetition_pattern, transcribed_text)
    prolongations = re.findall(prolongation_pattern, transcribed_text)
    interjections = re.findall(interjection_pattern, transcribed_text)

    # Return detected patterns
    detected = {
        "repetitions": repetitions,
        "prolongations": prolongations,
        "interjections": interjections,
    }
    return any(detected.values())


"""
Word retrieval after stutter detection
"""


def handle_stutter_detection():
    combined_text = " ".join(transcription_buffer)
    response = get_completion(combined_text)
    print(response)
    # Clear the buffer after processing
    transcription_buffer.clear()
    return response


"""
Processing chunks of audio
"""


def process_transcription_chunk(audio_chunk_path):
    global transcription_buffer
    transcribed_text = transcribe_audio(audio_chunk_path)
    stutter_detected = detect_stutter_patterns(transcribed_text)
    print("Transcribed text: ", transcribed_text)
    print("Stutter detected: ", stutter_detected)

    # Append transcription to a buffer for potentially accumulating more context
    transcription_buffer.append(transcribed_text)

    return transcribed_text, stutter_detected


"""
Front End Code below
"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/record", methods=["POST"])
def record():
    if "audio-file" not in request.files:
        print("No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400

    # Save the incoming audio chunk to a temporary file
    audio_file = request.files["audio-file"]
    _, temp_path = tempfile.mkstemp(suffix=".wav")
    audio_file.save(temp_path)

    try:
        # Transcribe the audio chunk
        transcribed_text, stutter_detected = process_transcription_chunk(temp_path)

        # If a stutter is detected, call get_completion
        if stutter_detected:
            suggestion = handle_stutter_detection()
        else:
            suggestion = "No significant stutter detected or speech is clear."

        os.remove(temp_path)  # Clean up the temporary file after processing

        # Respond with the transcription and any detected stutter patterns
        return jsonify({"transcription": transcribed_text, "suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
