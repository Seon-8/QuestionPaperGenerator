import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def clean_json_response(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def generate_questions_with_ai(subject, topic, difficulty, bloom_level, marks, count):
    prompt = prompt = f"""
    Generate {count} exam questions.

    Subject: {subject}
    Topic: {topic}
    Difficulty: {difficulty}
    Bloom Level: {bloom_level}
    Marks: {marks}

    Return only valid JSON in this format:
    [
      {{
        "question_text": "...",
        "expected_answer": "...",
        "marks": {marks},
        "difficulty": "{difficulty}",
        "bloom_level": "{bloom_level}"
      }}
    ]

    Important:
    - Return only JSON.
    - Do not use markdown.
    - Do not wrap the JSON in triple backticks.
    - Do not add explanation.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    cleaned_text = clean_json_response(text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return []
    

def split_missing_marks(missing_marks,missing_count):
    if missing_count <= 0:
        return []

    base_mark = missing_marks // missing_count
    remainder = missing_marks % missing_count

    marks_list = []

    for index in range(missing_count):
        mark = base_mark

        if index < remainder:
            mark += 1

        marks_list.append(mark)

    return marks_list

def generate_missing_questions_with_ai(subject,topic,difficulty,bloom_level,missing_marks,missing_count):
    marks_list = split_missing_marks(missing_marks,missing_count)

    prompt = f"""
    Generate exam questions to fill missing marks in a question paper.

    Subject: {subject}
    Topic: {topic}
    Difficulty: {difficulty}
    Bloom Level: {bloom_level}

    Required question marks list:
    {marks_list}

    Generate exactly {len(marks_list)} questions.
    Each question's marks must match the marks list in order.

    Return only valid JSON in this format:
    [
      {{
        "question_text": "...",
        "expected_answer": "...",
        "marks": 5
      }}
    ]

    Important rules:
    - Return only JSON.
    - Do not use markdown.
    - Do not wrap the JSON in triple backticks.
    - Do not add explanation.
    - Do not create duplicate questions.
    - Questions should be exam-appropriate.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    cleaned_text = clean_json_response(text)

    try:
        data = json.loads(cleaned_text)

        if not isinstance(data, list):
            return []

        cleaned_questions = []

        for index, item in enumerate(data):
            if index >= len(marks_list):
                break

            question_text = item.get("question_text", "").strip()

            if not question_text:
                continue

            cleaned_questions.append({
                "question_text": question_text,
                "expected_answer": item.get("expected_answer", "").strip(),
                "marks": marks_list[index],
            })

        return cleaned_questions

    except:
        return []

