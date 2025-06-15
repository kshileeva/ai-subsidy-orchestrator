from dotenv import load_dotenv
load_dotenv()

import json
import os
from tapeagents.llms import OpenrouterLLM
from tapeagents.agent import Agent
from tapeagents.dialog_tape import DialogTape, UserStep
from tapeagents.nodes import StandardNode
from tapeagents.core import FinalStep
print("Using OpenRouter API key:", os.getenv("OPENROUTER_API_KEY"))

llm = OpenrouterLLM(
    model_name="deepseek/deepseek-chat-v3-0324:free",
    api_token=os.getenv("OPENROUTER_API_KEY"),
    parameters={"temperature": 0.1}
)

def observation_prompt(app):
    return f"""You are an ethical municipal AI agent evaluating childcare subsidy applications. Extract all necessary features from this application:

{json.dumps(app, indent=2)}
"""

def reasoning_prompt():
    return """Based on CSAR 2025 regulations, reason step-by-step:
- Check eligibility: residency, employment/student status, income, docs, child age.
- If ineligible: reject.
- Else check vulnerability: single parent or flagged.
- If so: check_by_human.
- Else calculate subsidy, apply child cap, check if hard case.
- If hard case: human_evaluation. Else: approve.
"""

def decision_prompt():
    return """Assign final classification:
- 'rejected' if any disqualifier.
- 'check_by_human' if vulnerable.
- 'human_evaluation' if hard case.
- 'approved' if all criteria met.
Explain the decision and estimate subsidy percentage if relevant."""

def recall_prompt():
    return "Retrieve and summarize full decision history for this application."

case_agent = Agent.create(
    llms=llm,
    nodes=[
        StandardNode(
            name="observe",
            system_prompt="Observe and extract features.",
            use_function_calls=True,
            guidance="You are an ethical municipal AI agent. Extract features from the user application."
        ),
        StandardNode(
            name="think",
            system_prompt="Analyze and classify.",
            use_known_actions=True,
            use_function_calls=True,
            guidance="Think step-by-step through eligibility, vulnerability, subsidy rules, and edge cases."
        ),
        StandardNode(
            name="act",
            system_prompt="Give final label.",
            use_known_actions=True,
            use_function_calls=True,
            guidance="Label the case based on your reasoning: rejected, check_by_human, human_evaluation, or approved. Justify your label.",
            steps=FinalStep
        )
    ]
)

history_agent = Agent.create(
    llms=llm,
    nodes=[
        StandardNode(
            name="recall",
            system_prompt="Recall previous decisions.",
            use_function_calls=True,
            guidance=recall_prompt(),
            steps=FinalStep
        )
    ]
)

example_application = {
    "application_id": "A999",
    "applicant_name": "Example",
    "residency_months": 8,
    "employment_status": "part-time",
    "partner_employed": False,
    "household_income": 19500,
    "num_children": 4,
    "child_ages": [1, 3, 5, 7],
    "requested_hours": 95,
    "flags": {
        "incomplete_docs": False,
        "high_hours_request": False,
        "income_mismatch": False,
        "social_support_flagged": True
    }
}

start_tape = DialogTape(steps=[UserStep(content="Please evaluate this application:\n" + json.dumps(example_application, indent=2))])
final_tape = case_agent.run(start_tape).get_final_tape()

print("\n--- FINAL AGENT DECISION ---\n")
print(final_tape.model_dump_json(indent=2))
