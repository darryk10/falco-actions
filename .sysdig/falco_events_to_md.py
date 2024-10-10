import argparse
from datetime import datetime
import logging
import json
import re

def markdown_escape(text):
    # List of Markdown special characters to escape
    special_chars = r'([\*\_\{\}\[\]\(\)\#\+\-\.\!\|>])'
    
    # Use regex to add a backslash before each special character
    return re.sub(special_chars, r'\\\1', text)

def get_step_name(fired_at, timeline):
    # Correlate the fired rule with the job step
    # Since we are working with seconds granularity, we can have multiple matching steps
    # In that case, we return them all as an indication of where the event might have occurred
    matching_steps = []
    for step in timeline:
        if step["started_at"] <= fired_at <= step["completed_at"]:
            matching_steps.append(step["step_name"])
    return matching_steps

def falco_timestamp_to_datetime(timestamp):
    # Trim fractional seconds to 6 digits and replace 'Z' with '+00:00'
    index = timestamp.find('.')
    
    iso_time_str_fixed = timestamp[:index] + '+00:00'

    # Parse the fixed ISO string
    return datetime.fromisoformat(iso_time_str_fixed)

def main():
    # Set up argument parsing

    parser = argparse.ArgumentParser(description="Convert JSON Falco events to a Markdown table.")
    parser.add_argument('file', type=str, help='Path to the file containing the JSON Falco events data')
    parser.add_argument('correlation_file', type=str, help='Path to the file containing job steps timestamps')

    # Parse arguments
    args = parser.parse_args()

    # Open and read the file
    with open(args.file, "r") as file:
        lines = file.readlines()

    output = []
    timeline = []

    # Open and read the correlation file
    # Populate the timeline list with the job steps timestamps
    with open(args.correlation_file, "r") as file:
        data = file.readlines()
        for line in data:
            try:
                obj = json.loads(line)
            except:
                print(f"Error parsing JSON: {line}")
                print("Exiting ...")
                exit(1)

            try:
                if obj["steps"]["status"] != "completed":
                    continue
            except KeyError:
                continue

            try: 
                step_name = obj["steps"]["name"]
                started_at = datetime.fromisoformat(str(obj["steps"]["started_at"]).replace("Z", "+00:00"))
                completed_at = datetime.fromisoformat(str(obj["steps"]["completed_at"]).replace("Z", "+00:00"))
                timeline.append({'step_name': step_name, 'started_at': started_at, 'completed_at': completed_at})
            except Exception as e:
                logging.error(f"Error parsing correlation data: {e}")
                continue

    # Append the Markdown table header
    output.append("| Timestamp | Step | Rule | Output | Priority |")
    output.append("|-----------|------|------|--------|----------|")

    for line in lines:
        try:
            obj = json.loads(line)
        except:
            print(f"Error parsing JSON: {line}")
            print("Exiting ...")
            exit(1)

        # Append formatted Markdown row
        fired_at = falco_timestamp_to_datetime(obj["time"])
        rule = obj["rule"]
        out = markdown_escape(obj["output"])
        priority = obj["priority"]
        matching_steps = get_step_name(fired_at, timeline)
        if len(matching_steps) == 0:
            steps = "N/A"
        else:
            steps = ", ".join(matching_steps)

        output.append(f"| {fired_at} | {steps} | {rule} | {out} | {priority} | ")

    for line in output:
        print(line)

if __name__ == "__main__":
    main()