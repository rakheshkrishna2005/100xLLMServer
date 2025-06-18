from utils.helpers import extract_text_from_pdf
from utils.db import get_mongo_collection
from llm.groq import llm, extraction_prompt, ranking_prompt, JOB_DESCRIPTION
from utils.memory_tracker import log_memory, memory_tracker
import gc

@memory_tracker
def process_resume(pdf_path):
    try:
        log_memory("Before PDF extraction")
        text = extract_text_from_pdf(pdf_path)
        log_memory("After PDF extraction")
        
        prompt_text = extraction_prompt.format(human_input=text)
        log_memory("Before LLM processing")
        response = llm.invoke(prompt_text)
        log_memory("After LLM processing")
        return response.content.strip()
    finally:
        # Clear any large variables
        del text, prompt_text
        gc.collect()

@memory_tracker
def rank_candidates(candidates_info):
    try:
        log_memory(f"Starting ranking for {len(candidates_info)} candidates")
        # Process candidates in smaller chunks if there are many
        if len(candidates_info) > 10:
            chunks = [candidates_info[i:i+10] for i in range(0, len(candidates_info), 10)]
            all_rankings = []
            for i, chunk in enumerate(chunks, 1):
                log_memory(f"Processing chunk {i}/{len(chunks)}")
                candidate_texts = "\n\n".join([c["info"] for c in chunk])
                prompt_text = ranking_prompt.format(job_desc=JOB_DESCRIPTION, candidate_infos=candidate_texts)
                response = llm.invoke(prompt_text)
                all_rankings.append(response.content.strip())
                del candidate_texts, prompt_text  # Clear large strings
                gc.collect()
            return "\n\n".join(all_rankings)
        else:
            candidate_texts = "\n\n".join([c["info"] for c in candidates_info])
            prompt_text = ranking_prompt.format(job_desc=JOB_DESCRIPTION, candidate_infos=candidate_texts)
            response = llm.invoke(prompt_text)
            return response.content.strip()
    finally:
        gc.collect()
        log_memory("After ranking completion")

def process_and_store_candidate(candidate_info, ranking_text):
    lines = candidate_info["info"].splitlines()
    data_dict = {
        "file_name": candidate_info["file"],
        "name": "",
        "mail": "",
        "linkedin": "",
        "education": "",
        "work_experience": "",
        "skills": [],
        "rank": 0,
        "score": 0
    }

    for line in lines:
        key = line.split(":")[0].strip().lower()
        value = ":".join(line.split(":")[1:]).strip()
        if key == "name": data_dict["name"] = value
        elif key == "mail": data_dict["mail"] = value
        elif key == "linkedin id": data_dict["linkedin"] = value
        elif key == "education": data_dict["education"] = value
        elif key == "work experience": data_dict["work_experience"] = value
        elif key == "skills": data_dict["skills"] = [s.strip() for s in value.split(",")]

    for block in ranking_text.strip().split("\n\n"):
        name, score = "", ""
        for line in block.strip().splitlines():
            if line.lower().startswith("name:"):
                name = line[5:].strip().lower()
            elif line.lower().startswith("score:"):
                score = line[6:].strip()
        if name == data_dict["name"].lower():
            data_dict["score"] = int(score)
            break

    collection = get_mongo_collection()
    try:
        collection.insert_one(data_dict)
    except Exception as e:
        print(f"Error storing candidate: {e}")
    return data_dict

def process_resume_file(filename, file_path):
    candidate_info = {
        "file": filename,
        "info": process_resume(file_path)
    }
    collection = get_mongo_collection()
    try:
        all_candidates = list(collection.find({}, {'_id': 0}))
        all_candidates.append(candidate_info)
        ranking_text = rank_candidates(all_candidates)
        return process_and_store_candidate(candidate_info, ranking_text)
    except Exception as e:
        print(f"Error processing resume file: {e}")
        return None

def get_all_candidates():
    collection = get_mongo_collection()
    try:
        return list(collection.find({}, {'_id': 0}))
    except Exception as e:
        print(f"Error getting candidates: {e}")
        return []

def get_candidate_by_filename(filename):
    collection = get_mongo_collection()
    try:
        return collection.find_one({'file_name': filename}, {'_id': 0})
    except Exception as e:
        print(f"Error getting candidate by filename: {e}")
        return None

