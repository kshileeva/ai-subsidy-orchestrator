# ai-subsidy-orchestrator

**ServiceNow Challenge: Ethical AI Agents for Public Services**

This project demonstrates a pipeline for ethically evaluating childcare subsidy applications using AI agents built on the [TapeAgents](https://github.com/ServiceNow/TapeAgents) framework.

The agents simulate a human-in-the-loop decision process by:
- Extracting features from subsidy applications
- Reasoning through eligibility, vulnerability and policy rules
- Logging all steps in a structured and explainable format
- Saving decisions and full history to a SQLite database

## Project Structure

- `example_cases/` – JSON files containing input applications
- `demo.py` – runs a single application through the agent pipeline
- `test_demo.py` – loops through multiple cases for batch processing
- `subsidy_applications.db` – SQLite database to persist decisions
## Agent flow

Each application is wrapped in a DialogTape, which logs every interaction (user prompt, model output, decisions).

### Case agent
Evaluates the subsidy application through these steps:
- observe: extract structured features from the raw JSON
- think: run multi-factor reasoning across eligibility, need, policy rules
- act: output a decision label and justification
How to act in each case is predetermined in the [`labeled_tree.txt`](https://github.com/kshileeva/ai-subsidy-orchestrator/blob/main/labeled_tree.txt) 

### History agent
Wraps the final tape to summarize prior steps, generate a readable decision history and send it all to the database

## LLM Integration

Agents use OpenrouterLLM, which wraps calls to OpenRouter’s API for `deepseek-chat-v3-0324` model inference. Each step passes a prompt to the model and expects structured output.
