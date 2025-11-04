# %%
import pandas as pd
import glob
import os
import time
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


# %%

# ✅ Load Qwen model
model_name = "Qwen/Qwen2.5-3B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
llm = pipeline("text-generation", model=model, tokenizer=tokenizer)

print("✅ LLM model loaded:", model_name)

# %%

# =============================
# LLM PROMPT FUNCTION
# =============================

def ask_llm(question, options, answer):
    prompt = f"""
You are a dataset quality checker for multiple-choice questions.

Question: {question}
Options: {options}
Correct Answer: {answer}

Evaluate:
1. Is the question factually and logically correct and does it checks cultural knowledge of sport of a country  ?
2. Is the provided answer correct?
3. Does the question make sense as a valid MCQ?

Respond in the format below (strictly):
Score: 1 or 0 ( o means error 1 means correct)
If  0 :Mistake: (describe issue or "no mistake") : Update the question with the improvement(Minimal chnges please)
If 1 : reply with "No improvement needed"

    """

    out = llm(prompt, max_length=350, do_sample=False)
    return out[0]["generated_text"].strip()


# %%
base_path = "/DATA/rohan_kirti/niladri/pks/"  # main folder containing all countries
output_file = "/DATA/rohan_kirti/niladri/pks/2final_llm_results.csv"
# =============================
# CONFIGURATION
# =============================



# ✅ Regional language column mapping (update if needed)
COL_QUESTION = "প্রশ্ন"
COL_OPTIONS  = "অপশন"
COL_ANSWER   = "উত্তর"
print("✅ Column mapping set.")

# %%
# ✅ If output file doesn’t exist → write header
import csv
if not os.path.exists(output_file):
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["country", "file", "sheet",
                         "question", "option", "answer", "llm_output"])

# ✅ Load already processed rows (to skip on restart)
processed = set()
df_existing = pd.read_csv(output_file, encoding="utf-8-sig")
for i, row in df_existing.iterrows():
    processed.add((row["file"], row["sheet"], row["question"]))


# %%

# =============================
# MAIN PROCESS
# =============================

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
                llm_response = ask_llm(q, option, ans)
            except Exception as e:
                llm_response = f"ERROR: {e}"

            # ✅ WRITE IMMEDIATELY to CSV
            with open(output_file, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([country, os.path.basename(file), sheet,
                                 q, option, ans, llm_response])

            processed.add(key)

            print(f"✅ Saved → {country} | {sheet} | Row {idx}")
            # time.sleep(0.3)  # prevent overload

print("\n✅ COMPLETE!")
print("📄 Live-updating CSV:", output_file)




