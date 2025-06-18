import os
import fitz
from langchain_core.prompts import PromptTemplate
from llm.groq import initialize_llm 
from langchain.chains import RetrievalQA

def read_prompt_file(filename):
    with open(os.path.join("prompts", filename), "r", encoding="utf-8") as f:
        return f.read().strip()

JOB_DESCRIPTION = read_prompt_file("job_description.txt")
EXTRACTION_PROMPT_TEMPLATE = read_prompt_file("extraction_prompt.txt")
RANKING_PROMPT_TEMPLATE = read_prompt_file("ranking_prompt.txt")

llm = initialize_llm()

extraction_prompt = PromptTemplate(
    input_variables=["human_input"],
    template=EXTRACTION_PROMPT_TEMPLATE
)

ranking_prompt = PromptTemplate(
    input_variables=["job_desc", "candidate_infos"],
    template=RANKING_PROMPT_TEMPLATE
)


# PDF extraction
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        all_text.append(page.get_text())
    return "\n".join(all_text)

# Resume processing
def process_resumes_in_folder(folder_path="resume"):
    print("Resume Process started")
    candidates_info = []
    os.makedirs("output", exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            extracted_text = extract_text_from_pdf(pdf_path)
            prompt_text = extraction_prompt.format(human_input=extracted_text)
            response = llm.invoke(prompt_text)
            cleaned_output = response.content.strip()
            candidates_info.append({
                "file": filename,
                "info": cleaned_output
            })
    return candidates_info

# Ranking candidates
def rank_candidates(candidates_info):
    print("Ranking Starts")
    candidate_texts = "\n\n".join([c["info"] for c in candidates_info])
    prompt_text = ranking_prompt.format(job_desc=JOB_DESCRIPTION, candidate_infos=candidate_texts)
    response = llm.invoke(prompt_text)
    cleaned_output = response.content.strip()
    with open(os.path.join("output", "candidate_ranking.txt"), "w", encoding="utf-8") as f:
        f.write(cleaned_output)
    return cleaned_output

def from_chain(vectorstore):
    return RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())


