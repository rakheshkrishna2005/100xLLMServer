# Resume Processing Backend

This Flask backend service processes resumes, extracts candidate information using LLM, and ranks candidates based on job descriptions.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```
GROQ_API_KEY=your_groq_api_key
MONGODB_URI=your_mongodb_connection_string
```

4. Create the following directories:
```bash
mkdir -p resume output prompts
```

5. Copy the prompt files from the original project to the `prompts` directory:
- job_description.txt
- extraction_prompt.txt
- ranking_prompt.txt

## Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### 1. Upload Resume
- **URL**: `/api/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `file`: PDF resume file
- **Response**: 
  ```json
  {
    "message": "Resume processed successfully",
    "data": {
      "file_name": "resume.pdf",
      "name": "John Doe",
      "mail": "john@example.com",
      "linkedin": "linkedin.com/in/johndoe",
      "education": "Bachelor's in Computer Science",
      "work_experience": "5 years as Software Engineer",
      "skills": ["Python", "JavaScript", "React"],
      "rank": 1,
      "score": 85
    }
  }
  ```

### 2. Get All Candidates
- **URL**: `/api/candidates`
- **Method**: `GET`
- **Response**: Array of candidate objects

### 3. Get Specific Candidate
- **URL**: `/api/candidates/<filename>`
- **Method**: `GET`
- **Response**: Single candidate object

## Error Handling

All endpoints return appropriate HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses follow the format:
```json
{
  "error": "Error message"
}
``` 