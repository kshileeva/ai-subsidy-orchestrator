import json
import os
from tapeagents.dialog_tape import DialogTape, UserStep
from demo import case_agent

def classify_prompt(application_json):
    return f"""
You are an ethical municipal AI agent evaluating childcare subsidy applications.
Classify the following case as one of:
- accept (if all rules are met and subsidy is computable)
- reject (if there are clear disqualifiers)
- human evaluation (if ambiguous or risky)

Then explain the reasoning and estimate the subsidy if applicable.

Application:
{application_json}
""".strip()

# Load all applications
with open("data/merged_subsidy_applications.json") as f:
    applications = json.load(f)

os.makedirs("example_cases", exist_ok=True)

def test_all_applications(apps):
    results = []
    for i, app in enumerate(apps):
        app_id = app.get("application_id", f"index_{i}")
        print(f"\n--- Application #{i+1} ({app_id}) ---")

        prompt_text = classify_prompt(json.dumps(app, indent=2))
        tape = DialogTape(steps=[UserStep(content=prompt_text)])

        try:
            final_tape = case_agent.run(tape).get_final_tape()
            print(final_tape.model_dump_json(indent=2))
            result = {
                "application_id": app_id,
                "response": final_tape.model_dump()
            }
            results.append(result)

            with open(f"example_cases/{app_id}.json", "w") as out_file:
                json.dump(result["response"], out_file, indent=2)

        except Exception as e:
            print(f"⚠️ Error processing {app_id}: {e}")
            with open(f"example_cases/{app_id}_error.txt", "w") as err_file:
                err_file.write(str(e))

    return results


test_all_applications(applications)