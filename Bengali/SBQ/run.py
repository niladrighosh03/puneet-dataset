# %%
import pandas as pd
import glob
import os
import time
from dotenv import load_dotenv
import os
import requests
import json

# %%

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("API_KEY")

# %%

# =============================
# LLM PROMPT FUNCTION
# =============================
url = 'https://cloud.olakrutrim.com/v1/chat/completions'

def ask_llm(question, options, answer):
    prompt = f"""
You are a dataset quality checker for multiple-choice sports MCQs.

Question: {question}
Options: {options}
Correct Answer: {answer}

Evaluate the MCQ on the following:
1. Is the question factually and logically correct?
2. Is the provided answer correct?
3. Does the question make sense as a valid MCQ?
4. How to improve the question?
5. How to improve the options?

Note:  ( 0 means error 1 means correct)

Respond ONLY in JSON format (strictly):
{{
  "score": 1 or 0,
  "mistake": "Describe the issue, or 'no mistake' if everything is correct",
  "improved_question": "If score = 1, respond 'no correction needed'. If score = 0, rewrite the question with minimal changes",
  "improved_options": "If score = 1, respond 'no correction needed'. If score = 0, provide corrected options list",
}}
"""

    model="Qwen3-Next-80B-A3B-Instruct"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    # Parse JSON returned by model
    try:
        data = json.loads(content)
        return (
            data.get("score"),
            data.get("mistake"),
            data.get("improved_question"),
            data.get("improved_options")
        )
    except json.JSONDecodeError:
        print("Failed to decode JSON from model:", content)
        return None, None, None, None, None


# %%
# score, mistake, improved_question, improved_options  = ask_llm(
#     "In chess, how many files?", "A) Four, B) Eight, C) Ten", "C"
# )

# print(score, mistake, improved_question, improved_options)


# %%
base_path = "/DATA/rohan_kirti/niladri/pks/Bengali/SBQ/"  # main folder containing all countries
output_file = "/DATA/rohan_kirti/niladri/pks/Bengali/SBQ/Results_SBQ.csv"



# Input CSV file path
input_csv = "/DATA/rohan_kirti/niladri/pks/Bengali/SBQ/Results_SBQ.csv"

# Output Excel file path
output_excel = "/DATA/rohan_kirti/niladri/pks/Bengali/SBQ/Results_SBQ.xlsx"
# =============================
# CONFIGURATION
# =============================



# ✅ Regional language column mapping (update if needed)
COL_QUESTION = "প্রশ্ন"
COL_OPTIONS  = "অপশন"
COL_ANSWER   = "উত্তর"


# %%
# ✅ If output file doesn’t exist → write header
import csv
if not os.path.exists(output_file):
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["country", "file", "sheet",
                         "question", "option", "answer", "score",
                         "What's wrong in Question", "How can I improve the question", "How can I improve the Options"])

# ✅ Load already processed rows (to skip on restart)
processed = set()
df_existing = pd.read_csv(output_file, encoding="utf-8-sig")
for i, row in df_existing.iterrows():
    processed.add((row["file"], row["sheet"], row["question"]))


# %%

# =============================
# MAIN PROCESS
# =============================
from datetime import datetime

start_time = datetime.now()
print("Started at:", start_time.strftime("%H:%M:%S"))



excel_files = glob.glob(os.path.join(base_path, "**/*.xlsx"), recursive=True)

for file in excel_files:
       
    country = os.path.basename(os.path.dirname(file))
    xls = pd.ExcelFile(file)
    print(f"\n📌 Processing: {file}")

    for sheet in xls.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet)

        if COL_QUESTION not in df.columns:
            continue

        df = df[[COL_QUESTION, COL_OPTIONS, COL_ANSWER]].dropna(how="all")

        for idx, row in df.iterrows():
            key = (os.path.basename(file), sheet, row[COL_QUESTION])

            if key in processed:
                continue

            q, option, ans = row[COL_QUESTION], row[COL_OPTIONS], row[COL_ANSWER]

            try:
                # llm_response = ask_llm(q, option, ans)
                score, mistake, improved_question, improved_options= ask_llm(q, option, ans)
            except Exception as e:
                score, mistake, improved_question, improved_options = f"ERROR: {e}"

            # ✅ WRITE IMMEDIATELY to CSV
            with open(output_file, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([country, os.path.basename(file), sheet,
                                 q, option, ans, score, mistake, improved_question, improved_options])

            processed.add(key)

            print(f"✅ Saved → {country} | {sheet} | Row {idx}")
            # time.sleep(0.3)  # prevent overload

print("\n✅ COMPLETE!")
print("📄 Live-updating CSV:", output_file)


end_time = datetime.now()
print("Ended at:", end_time.strftime("%H:%M:%S"))
print("Total Duration:", end_time - start_time)


'''CConvert CSV to Excel with separate sheets'''



# Read the CSV file
df = pd.read_csv(input_csv)

# Columns to remove
columns_to_remove = ["country", "file", "sheet"]

# Create Excel writer
with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    # Group by the 'sheet' column
    for sheet_name, sheet_data in df.groupby("sheet"):
        # Drop unnecessary columns
        sheet_data = sheet_data.drop(columns=columns_to_remove, errors="ignore")
        
        # Write each sheet to the Excel file
        sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"✅ Successfully created '{output_excel}'")