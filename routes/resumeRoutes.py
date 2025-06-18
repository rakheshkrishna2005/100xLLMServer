from flask import Blueprint, request, jsonify
import zipfile, os, uuid, traceback
from datetime import datetime
from utils.helpers import process_resumes_in_folder, rank_candidates 
from utils.db import append_ranks_to_candidates
from threading import Thread

resumeProcessBlueprint = Blueprint('resume_api', __name__)

tasks = {}

def background_resume_process(session_id, temp_dir, query):
    try:
        tasks[session_id]["status"] = 0
        candidates_info = process_resumes_in_folder(temp_dir)

        tasks[session_id]["status"] = 1
        # ranking_text = rank_candidates(candidates_info, query)
        ranking_text = rank_candidates(candidates_info)
        tasks[session_id]["status"] = 2
        append_ranks_to_candidates(candidates_info, ranking_text, session_id)

        tasks[session_id]["status"] = 3
        tasks[session_id]["result"] = {
            'summary': 'Resume analysis complete',
            'query_used': query,
            'num_files': len(os.listdir(temp_dir))
        }
    except Exception as e:
        tasks[session_id]["status"] = "Error"
        tasks[session_id]["result"] = {"error": str(e)}
        traceback.print_exc()
    finally:
        # Clean up
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)
        print(f"[{datetime.now()}] [INFO] Cleaned up temp dir: {temp_dir}")

@resumeProcessBlueprint.route('/analyze_resumes', methods=['POST'])
def analyze_resumes():
    try:
        session_id = str(uuid.uuid4())
        tasks[session_id] = {"status": "Starting", "result": None}
        print(f"[{datetime.now()}] [INFO] Session started: {session_id}")

        if 'resumes_zip' not in request.files or 'query' not in request.form:
            return jsonify({'status': 'error', 'message': 'Missing resumes_zip or query parameter'}), 400

        zip_file = request.files['resumes_zip']
        query = request.form['query']

        temp_dir = f'temp_resumes_{session_id}'
        os.makedirs(temp_dir, exist_ok=True)

        with zipfile.ZipFile(zip_file) as zip_ref:
            zip_ref.extractall(temp_dir)

        # Start background thread
        thread = Thread(target=background_resume_process, args=(session_id, temp_dir, query))
        thread.start()

        return jsonify({
            'status': 'processing',
            'session_id': session_id,
            'message': 'Resume processing started.'
        }), 202

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': 'Internal Server Error',
            'details': str(e)
        }), 500

@resumeProcessBlueprint.route('/status/<session_id>', methods=['GET'])
def check_status(session_id):
    task = tasks.get(session_id)
    if not task:
        return jsonify({'error': 'Invalid session_id'}), 404
    return jsonify({'status': task["status"]})

@resumeProcessBlueprint.route('/result/<session_id>', methods=['GET'])
def get_result(session_id):
    task = tasks.get(session_id)
    if not task or task["status"] != "Completed":
        return jsonify({'error': 'Result not ready'}), 400
    return jsonify(task["result"])


