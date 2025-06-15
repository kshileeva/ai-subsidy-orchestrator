import json
import os
import random
import subprocess


with open("data/merged_subsidy_applications.json") as f:
    applications = json.load(f)
os.makedirs("example_cases", exist_ok=True)

def test_all_applications(apps):
    for i, app in enumerate(apps):
        app_id = app.get("application_id", f"index_{i}")
        input_path = f"example_cases/{app_id}.json"

        with open(input_path, "w") as f:
            json.dump(app, f, indent=2)

        print(f"\n--- Running demo for Application #{i+1} ({app_id}) ---")
        try:
            subprocess.run(["python", "demo.py", "--case", app_id], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running demo for {app_id}: {e}")

selected_apps = applications
test_all_applications(selected_apps)
