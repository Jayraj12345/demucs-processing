import os
import subprocess
from flask import Flask, request, jsonify
from supabase import create_client, Client
from werkzeug.utils import secure_filename

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
UPLOAD_FOLDER = "downloads"
OUTPUT_FOLDER = "separated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/process", methods=["POST"])
def process_audio():
    data = request.json
    filename = data.get("filename")
    
    # Download file from Supabase Storage
    response = supabase.storage.from_("music-uploads").download(filename)
    if response is None:
        return jsonify({"error": "File download failed"}), 500
    
    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    with open(file_path, "wb") as f:
        f.write(response)
    
    # Run Demucs
    command = f"demucs -d cpu --model=htdemucs {file_path}"
    subprocess.run(command, shell=True, check=True)

    output_folder = os.path.join(OUTPUT_FOLDER, "htdemucs", os.path.splitext(filename)[0])
    stems = {stem: os.path.join(output_folder, f"{stem}.wav") for stem in ["drums", "bass", "vocals", "other"]}
    
    # Upload stems to Supabase Storage
    stem_urls = {}
    for stem, path in stems.items():
        with open(path, "rb") as f:
            response = supabase.storage.from_("separated-stems").upload(f"stems/{filename}_{stem}.wav", f)
        
        stem_urls[stem] = f"{SUPABASE_URL}/storage/v1/object/public/separated-stems/stems/{filename}_{stem}.wav"
    
    return jsonify({"message": "Processing complete", "stems": stem_urls})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
