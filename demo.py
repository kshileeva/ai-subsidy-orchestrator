import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
from dotenv import load_dotenv
load_dotenv()

import json
import os
import argparse
from tapeagents.llms import OpenrouterLLM
from tapeagents.agent import Agent
from tapeagents.dialog_tape import DialogTape, UserStep
from tapeagents.nodes import StandardNode
from tapeagents.core import FinalStep
print("Using OpenRouter API key:", os.getenv("OPENROUTER_API_KEY"))

llm = OpenrouterLLM(
    model_name="deepseek/deepseek-chat-v3-0324:free",
    api_token=os.getenv("OPENROUTER_API_KEY"),
    parameters={"temperature": 0.2}
)

def observation_prompt(app):
    return f"""You are an ethical municipal AI agent evaluating childcare subsidy applications. Extract all features from this application:

{json.dumps(app, indent=2)}
""".strip()

def reasoning_prompt():
    return """START

├── ELIGIBILITY CHECKS:
│   ├── applicant['residency_months'] ≥ 6
│   ├── (
│       applicant['employment_status'] in ["employed", "part-time", "self-employed", "student", "freelancer"]
│       OR applicant['partner_employed'] == True
│     )
│   ├── applicant['household_income'] < UQR
│   ├── applicant['flags']['incomplete_docs'] == False
│   ├── applicant['flags']['income_mismatch'] == False
│   ├── any(age < 12 for age in applicant['child_ages'])

└── IF ANY FAIL → reject
    ELSE → continue
    │
    ├── VULNERABILITY CHECK:
    │   ├── applicant['partner_employed'] == False
    │   ├── applicant['flags']['social_support_flagged'] == True
    │   ├── applicant['recent_municipal_support'] is not empty
    │   ├── applicant['housing_situation'] in ["municipal housing", "temporary shelter"]

    └── IF ANY TRUE → check_by_human
        ELSE → continue
        │
        ├── SUBSIDY CALCULATION IN EUROS:
        │   ├── applicant['household_income'] percentile (based on EU municipality with median income ≈ €40,000):
        │   │   ├── < 25 → maximum 85% coverage (not higher)
        │   │   ├── 25–50 → maximum 60% coverage
        │   │   ├── 50–75 → maximum 30% coverage
        │   │   ├── > 75 → likely ineligible

        ├── CAP ENFORCEMENT:
        │   ├── max_reimbursed_children = min(2, applicant['num_children']) provide subsidy for maximum 2 minors of a guardian

        └── HARD CASE CHECK:
            ├── applicant['num_children']
            ├── AND applicant['household_income'] < 25th percentile
            └── → human_evaluation
                ELSE → approve""".strip()

def decision_prompt():
    return """Assign final classification:
- 'rejected' if any disqualifier.
- 'check_by_human' if vulnerable.
- 'human_evaluation' if hard case.
- 'approved' if all criteria met.
State the assigned label explicitly and explain the reason. Even for 'check_by_human' or 'human_evaluation', provide a rough subsidy percentage estimate.""".strip()

def recall_prompt():
    return """
You are a system-level function that returns only JSON.

TASK: Summarize the decision history for this application.

FORMAT: Return **only** a valid JSON string matching this schema:

{
  "application_id": "A###",
  "summary": "Concise, one-paragraph summary of the decision reasoning, including key facts and final classification."
}

RESTRICTIONS:
- Do NOT include any markdown, code blocks, or additional commentary.
- Your output MUST start with `{` and end with `}` — it must be a valid JSON object.
""".strip()

case_agent = Agent.create(
    llms=llm,
    nodes=[
        StandardNode(
            name="observe",
            system_prompt="Observe and extract features.",
            use_known_actions=True,
            guidance="You are an ethical municipal AI agent. Extract features from the user application."
        ),
        StandardNode(
            name="think",
            system_prompt="Analyze and classify.",
            use_known_actions=True,
            use_function_calls=True,
            guidance="Think step-by-step through eligibility, vulnerability, subsidy rules, and edge cases.",
            output_type="AssistantThought"
        ),
        StandardNode(
            name="act",
            system_prompt="Give final label.",
            use_known_actions=True,
            use_function_calls=True,
            guidance="Label the case based on your reasoning: rejected, check_by_human, human_evaluation, or approved. Justify your label.",
            steps=FinalStep,
            output_type="AssistantThought"
        )
    ]
)

history_agent = Agent.create(
    llms=llm,
    nodes=[
        StandardNode(
            name="recall",
            system_prompt="Summarize the decision history for this application.",
            guidance="Look at all prior steps and summarize the key points that led to the final decision.",
            use_function_calls=False,
            steps=FinalStep
        )
    ]
)


parser = argparse.ArgumentParser()
parser.add_argument("--case", type=str, help="Application ID or path")
args = parser.parse_args()
case_file = os.path.join("example_cases", f"{args.case}.json")
if not os.path.exists(case_file):
    raise FileNotFoundError(f"Case file not found: {case_file}")

with open(case_file, "r", encoding="utf-8") as f:
    example_application = json.load(f)

start_tape = DialogTape(steps=[UserStep(content="Please evaluate this application:\n" + json.dumps(example_application, indent=2))])


final_tape = case_agent.run(start_tape).get_final_tape()

final_tape.steps.append(UserStep(content="Please retrieve and summarize the decision history."))

# Only pass the last user step (the summary request) to the history agent
try:
    recall_tape = history_agent.run(DialogTape(steps=final_tape.steps[-1:])).get_final_tape()
    history_step = recall_tape.steps[-1]
    if hasattr(history_step, "reason"):
        history_summary = history_step.reason.strip()
    else:
        history_summary = "[no summary available]"
except Exception as e:
    print("Failed to parse recall response:", e)
    print("Raw output:\n", history_step.reason if 'history_step' in locals() else "[no output]")
    history_summary = "[parse error]"

import sqlite3
# get vals
app_id = example_application["application_id"]
dialog_json = final_tape.model_dump_json(indent=2)
label_step = next((s for s in reversed(final_tape.steps)
                   if s.kind == "final_step" and hasattr(s, "reason")), None)
final_label = ""
justification = ""

if label_step:
    reason_text = label_step.reason.strip()
    if reason_text.lower().startswith("label:"):
        parts = reason_text.split("\n", 1)
        final_label = parts[0].replace("Label:", "").strip()
        justification = parts[1].strip() if len(parts) > 1 else ""
    else:
        justification = reason_text

conn = sqlite3.connect("tapedata.sqlite")
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS application_logs (
        application_id TEXT PRIMARY KEY,
        dialog_formatted TEXT,
        final_label TEXT,
        justification TEXT
    )
''')
c.execute('''
    INSERT OR REPLACE INTO application_logs (application_id, dialog_formatted, final_label, justification)
    VALUES (?, ?, ?, ?)
''', (app_id, dialog_json, final_label, justification))
conn.commit()
conn.close()

chat_transcript = []
for step in final_tape.steps:
    role = "User" if step.kind == "user" else f"Agent step ({getattr(step.metadata, 'node', 'unknown')}):"

    if step.kind == "final_step":
        content = step.reason.strip() if hasattr(step, "reason") else "[no reason provided]"
        if content.lower().startswith("label:"):
            label_line, *rest = content.split("\n", 1)
            content = f"Assigned Label: {label_line.replace('Label:', '').strip()}"
            if rest:
                content += f"\nReason: {rest[0].strip()}"
    elif hasattr(step, 'content'):
        content = step.content.strip()
    elif hasattr(step, 'reasoning'):
        content = step.reasoning.strip()
    else:
        content = "[no content]"

    chat_transcript.append(f"{role}\n{content}\n{'-' * 40}")

chat_output = "\n".join(chat_transcript)

# save to  DB as well
conn_teammate = sqlite3.connect("subsidy_applications.db")
cursor_teammate = conn_teammate.cursor()


# Assign application_status and dialog_text before DB operation
application_status = final_label or "Pending"
dialog_text = chat_output + "\n\n--- Summary by History Agent ---\n" + history_summary

cursor_teammate.execute("""
    INSERT OR REPLACE INTO applications (
        application_nr, date, user_name, employment_status, household_income,
        childcare_hours, num_children, ages_of_children, history, application_status
    ) VALUES (?, DATE('now'), ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    app_id,
    example_application.get("applicant_name", "unknown"),
    example_application.get("employment_status", "unknown"),
    example_application.get("household_income", 0),
    example_application.get("childcare_hours_requested", 0),
    example_application.get("num_children", 0),
    json.dumps(example_application.get("child_ages", [])),
    dialog_text,
    application_status
))

conn_teammate.commit()
conn_teammate.close()

print("\n--- CHAT TRANSCRIPT ---\n")
print(chat_output)


print(f"\n--- Application ID: {app_id} processed and saved ---\n")
conn_teammate.close()
