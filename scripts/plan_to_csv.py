import csv
import os
import warnings

import yaml

warnings.warn(
    "scripts/plan_to_csv.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
# Paths
PLAN_YAML = "generation-inputs/uiao_project_plan_v1.0.yaml"
PLAN_CSV = "docs/modernization_atlas_planner_import.csv"


def yaml_to_planner_csv():
    if not os.path.exists(PLAN_YAML):
        print(f"Error: {PLAN_YAML} not found.")
        return

    with open(PLAN_YAML) as file:
        data = yaml.safe_load(file)

    # MS Planner Import Headers
    headers = ["Task Name", "Bucket", "Progress", "Priority", "Start Date", "Due Date", "Description"]

    with open(PLAN_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for phase in data["project_plan"]["phases"]:
            for task in phase["tasks"]:
                writer.writerow(
                    {
                        "Task Name": task["name"],
                        "Bucket": task["bucket"],
                        "Progress": "Not started",
                        "Priority": "Medium",
                        "Start Date": task["start"],
                        "Due Date": task["due"],
                        "Description": f"Phase: {phase['phase']} | Owner: {task['owner']}",
                    }
                )

    print(f"Successfully exported project plan to: {PLAN_CSV}")


if __name__ == "__main__":
    yaml_to_planner_csv()
