from utils.helpers import extract_text_from_pdf
from utils.db import get_mongo_collection
from llm.groq import llm, extraction_prompt, ranking_prompt, JOB_DESCRIPTION

def process_resume(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    prompt_text = extraction_prompt.format(human_input=text)
    response = llm.invoke(prompt_text)
    return response.content.strip()

def rank_candidates(candidates_info):
    candidate_texts = "\n\n".join([c["info"] for c in candidates_info])
    prompt_text = ranking_prompt.format(job_desc=JOB_DESCRIPTION, candidate_infos=candidate_texts)
    response = llm.invoke(prompt_text)
    return response.content.strip()

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
    collection.insert_one(data_dict)
    return data_dict

def process_resume_file(filename, file_path):
    candidate_info = {
        "file": filename,
        "info": process_resume(file_path)
    }
    collection = get_mongo_collection()
    all_candidates = list(collection.find({}, {'_id': 0}))
    all_candidates.append(candidate_info)
    ranking_text = rank_candidates(all_candidates)
    return process_and_store_candidate(candidate_info, ranking_text)

def get_all_candidates():
    collection = get_mongo_collection()
    return list(collection.find({}, {'_id': 0}))

def get_candidate_by_filename(filename):
    collection = get_mongo_collection()
    return collection.find_one({'file_name': filename}, {'_id': 0})

