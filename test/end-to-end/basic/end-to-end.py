import json
import os

import requests

# API configuration
API_URL = "http://localhost:5000/api/v1/optimize"
API_TOKEN = "df30dceb79d588a2689fe9ab08bfed868fed458082137026b4a0a051711eafe6"


def read_file_contents(filename):
    """Read and return the contents of a file."""
    try:
        with open(filename, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
        return None


def main():
    # Read file contents
    dockerfile_content = read_file_contents('Dockerfile')
    dockerignore_content = read_file_contents('.dockerignore')

    package_json_content = read_file_contents('package.json')
    package_json_content = json.loads(package_json_content)

    # Prepare the payload
    payload = {
        "Dockerfile": dockerfile_content,
        ".dockerignore": dockerignore_content,
        "package.json": package_json_content,
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
    }

    # Remove None values from payload
    payload = {k: v for k, v in payload.items() if v is not None}

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": API_TOKEN
    }

    try:
        # Send POST request to the API
        response = requests.post(API_URL, json=payload, headers=headers)

        # Check if the request was successful
        response.raise_for_status()

        # Parse and print the optimization results
        optimization_results = response.json()
        print("Optimization Results:")
        print(json.dumps(optimization_results, indent=4))

        print("**************** modified project ********************\n")
        modified = optimization_results.get("modified_project", {})
        for filename in modified:
            print(f"[{filename}]\n")
            print(modified[filename])
            print("\n\n")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")


if __name__ == "__main__":
    main()
