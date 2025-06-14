import json
from statistics import median

# Load your full JSON file
with open("merged_subsidy_applications.json", "r") as f:
    data = json.load(f)

# Extract valid household income values
incomes = [
    entry["household_income"]
    for entry in data
    if isinstance(entry.get("household_income"), (int, float))
]

# Calculate median
if incomes:
    median_income = median(incomes)
    print(f"Median household income: €{median_income}")
    print(f"Based on {len(incomes)} valid records.")

    from statistics import mean

    incomes.sort()
    min_income = incomes[0]
    max_income = incomes[-1]
    mean_income = mean(incomes)
    q1 = incomes[len(incomes) // 4]
    q3 = incomes[(len(incomes) * 3) // 4]
    iqr = q3 - q1
    uqr = q3 - median_income

    print(f"Minimum income: €{min_income}")
    print(f"Maximum income: €{max_income}")
    print(f"Mean household income: €{mean_income:.2f}")
    print(f"Lower quartile (Q1): €{q1}")
    print(f"Upper quartile (Q3): €{q3}")
    print(f"IQR (Q3 - Q1): €{iqr}")
    print(f"UQR (Q3 - median): €{uqr}")
else:
    print("No valid income entries found.")