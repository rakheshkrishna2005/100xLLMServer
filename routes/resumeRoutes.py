from flask import Blueprint, request, jsonify
import zipfile, os, uuid, traceback
from datetime import datetime, timedelta
from utils.helpers import process_resumes_in_folder, rank_candidates 
from utils.db import append_ranks_to_candidates
from threading import Thread
import gc
from utils.memory_tracker import log_memory, memory_tracker

resumeProcessBlueprint = Blueprint('resume_api', __name__)

# Add session expiry time
SESSION_EXPIRY = timedelta(hours=1)
tasks = {}

def cleanup_old_sessions():
    current_time = datetime.now()
    expired_sessions = [
        session_id for session_id, task in tasks.items()
        if current_time - task.get("timestamp", current_time) > SESSION_EXPIRY
    ]
    for session_id in expired_sessions:
        del tasks[session_id]
    log_memory("After session cleanup")

@memory_tracker
def background_resume_process(session_id, temp_dir, query):
    try:
        tasks[session_id]["status"] = 0
        log_memory("Starting resume processing")
        
        # Process resumes in smaller batches
        batch_size = 5
        total_files = len(os.listdir(temp_dir))
        
        for i in range(0, total_files, batch_size):
            batch_files = os.listdir(temp_dir)[i:i+batch_size]
            log_memory(f"Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size}")
            
            candidates_info = process_resumes_in_folder(temp_dir, batch_files)
            tasks[session_id]["status"] = 1
            
            log_memory("Before ranking candidates")
            ranking_text = rank_candidates(candidates_info)
            log_memory("After ranking candidates")
            
            tasks[session_id]["status"] = 2
            append_ranks_to_candidates(candidates_info, ranking_text, session_id)
            log_memory("After storing candidates")
            
            # Force garbage collection after each batch
            gc.collect()

        tasks[session_id]["status"] = 3
        tasks[session_id]["result"] = {
            'summary': 'Resume analysis complete',
            'query_used': query,
            'num_files': total_files
        }
    except Exception as e:
        tasks[session_id]["status"] = "Error"
        tasks[session_id]["result"] = {"error": str(e)}
        traceback.print_exc()
    finally:
        # Clean up
        for file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, file))
            except Exception:
                pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
        log_memory("After cleanup")
        tasks[session_id]["timestamp"] = datetime.now()

@resumeProcessBlueprint.route('/analyze_resumes', methods=['POST'])
@memory_tracker
def analyze_resumes():
    try:
        cleanup_old_sessions()
        
        session_id = str(uuid.uuid4())
        tasks[session_id] = {
            "status": "Starting",
            "result": None,
            "timestamp": datetime.now()
        }
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


