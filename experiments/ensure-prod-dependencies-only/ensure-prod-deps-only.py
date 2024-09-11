import os
import json
import re


def check_node_env_in_dockerfile(dockerfile_content):
    """
    Checks if NODE_ENV is set to 'production' in the Dockerfile.

    Returns:
        bool: True if NODE_ENV=production is found, False otherwise.
    """
    for line in dockerfile_content:
        if re.search(r'ENV\s+NODE_ENV\s*=\s*production', line):
            return True
    return False


def check_base_image_for_node_env(dockerfile_content):
    """
    Heuristically checks if the base image might set NODE_ENV to 'production'.
    Currently, it checks if the base image is an official Node.js image.

    Returns:
        bool: True if the base image might set NODE_ENV=production, False otherwise.
    """
    for line in dockerfile_content:
        match = re.match(r'^FROM\s+([\w:/.-]+)', line)
        if match:
            base_image = match.group(1)
            # Check if the base image is an official Node.js image
            if 'node' in base_image:
                print(f"Detected custom Node.js base image: {base_image}. Assuming NODE_ENV=production.")
                return True
    return False


def get_final_stage_commands(dockerfile_content):
    """
    Extracts the commands for the final stage of a multi-stage Dockerfile.

    Parameters:
        dockerfile_content (list): List of lines from the Dockerfile.

    Returns:
        list: Lines of commands related to the final stage.
    """
    stages = []
    current_stage = []

    for line in dockerfile_content:
        # Detect new stages (indicated by the `FROM` keyword)
        if line.strip().startswith("FROM"):
            if current_stage:
                stages.append(current_stage)
            current_stage = [line]
        else:
            current_stage.append(line)

    # Add the final stage
    if current_stage:
        stages.append(current_stage)

    # Return the commands of the final stage only
    return stages[-1] if stages else []


def ensure_dependencies_only(dockerfile_path='Dockerfile', package_json_path='package.json'):
    """
    Ensure that the Dockerfile only installs `dependencies` from package.json,
    excluding `devDependencies`, and handles custom scenarios like NODE_ENV, --omit=dev, and multistage builds.

    Parameters:
        dockerfile_path (str): The path to the Dockerfile. Default is 'Dockerfile'.
        package_json_path (str): The path to the package.json file. Default is 'package.json'.
    """
    # Check if package.json exists
    if not os.path.exists(package_json_path):
        raise FileNotFoundError(f"{package_json_path} not found.")

    # Load package.json
    with open(package_json_path, 'r') as f:
        package_json = json.load(f)

    # Ensure dependencies section exists
    dependencies = package_json.get('dependencies', {})
    if not dependencies:
        print("No dependencies found in package.json.")
        return

    # Check if Dockerfile exists
    if not os.path.exists(dockerfile_path):
        raise FileNotFoundError(f"{dockerfile_path} not found.")

    # Read the Dockerfile content
    with open(dockerfile_path, 'r') as f:
        dockerfile_content = f.readlines()

    # Extract commands from the final stage of a multistage Dockerfile
    final_stage_commands = get_final_stage_commands(dockerfile_content)

    # Check if NODE_ENV=production is set in the final stage
    node_env_set = check_node_env_in_dockerfile(final_stage_commands)
    node_env_in_base = check_base_image_for_node_env(final_stage_commands)

    npm_install_pattern = re.compile(r"RUN\s+npm\s+install(\s+--production)?(\s+--omit=dev)?")
    npm_ci_pattern = re.compile(r"RUN\s+npm\s+ci(\s+--omit=dev)?")
    yarn_install_pattern = re.compile(r"RUN\s+yarn\s+install(\s+--production=true)?")

    found_install = False
    modified = False

    for i, line in enumerate(final_stage_commands):
        npm_match = npm_install_pattern.search(line)
        npm_ci_match = npm_ci_pattern.search(line)
        yarn_match = yarn_install_pattern.search(line)

        # Handle npm install case
        if npm_match:
            found_install = True
            # Check for --production or --omit=dev flags
            if not npm_match.group(1) and not npm_match.group(2):
                # Modify only if NODE_ENV isn't already set to production
                if not node_env_set and not node_env_in_base:
                    print("Found `npm install` without `--production` or `--omit=dev`. Modifying the Dockerfile.")
                    final_stage_commands[i] = re.sub(r"npm install", "npm install --production", line)
                    modified = True

        # Handle npm ci case
        elif npm_ci_match:
            found_install = True
            # Modify only if --omit=dev is not present and NODE_ENV isn't production
            if not npm_ci_match.group(1):
                if not node_env_set and not node_env_in_base:
                    print("Found `npm ci` without `--omit=dev`. Modifying the Dockerfile.")
                    final_stage_commands[i] = re.sub(r"npm ci", "npm ci --omit=dev", line)
                    modified = True

        # Handle yarn install case
        elif yarn_match:
            found_install = True
            if not yarn_match.group(1):
                if not node_env_set and not node_env_in_base:
                    print("Found `yarn install` without `--production=true`. Modifying the Dockerfile.")
                    final_stage_commands[i] = re.sub(r"yarn install", "yarn install --production=true", line)
                    modified = True

    if not found_install:
        raise ValueError(
            "No `npm install`, `npm ci`, or `yarn install` command found in the final stage of the Dockerfile.")

    if modified:
        # Write back the modified final stage to the Dockerfile
        with open(dockerfile_path, 'w') as f:
            f.writelines(final_stage_commands)
        print("Dockerfile has been modified to optimize for production dependencies in the final stage.")
    else:
        print("Dockerfile already correctly installs production dependencies only in the final stage.")


if __name__ == "__main__":
    ensure_dependencies_only()
