import argparse
import json
import sys
import os
from pathlib import Path

import openai

import dockershrink
from openai import OpenAI

from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

VERSION = "0.0.1"  # Update this as needed


def main():
    parser = argparse.ArgumentParser(
        description="Dockershrink optimizes your NodeJS Docker images."
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    subparsers.required = True

    # Version subcommand
    version_parser = subparsers.add_parser(
        "version", help="Show the version of Dockershrink"
    )
    version_parser.set_defaults(func=version_command)

    # Optimize subcommand
    optimize_parser = subparsers.add_parser(
        "optimize", help="Optimize your Docker project"
    )
    optimize_parser.add_argument(
        "--dockerfile", type=str, default="Dockerfile", help="Path to the Dockerfile"
    )
    optimize_parser.add_argument(
        "--dockerignore",
        type=str,
        default=".dockerignore",
        help="Path to the .dockerignore file",
    )
    optimize_parser.add_argument(
        "--package-json", type=str, default=None, help="Path to the package.json file"
    )
    optimize_parser.add_argument(
        "--output-dir",
        type=str,
        default="dockershrink.optimized",
        help="Directory to save optimized files",
    )
    optimize_parser.add_argument(
        "--openai-api-key",
        type=str,
        default=None,
        help="OpenAI API key for AI-powered optimizations",
    )
    optimize_parser.set_defaults(func=optimize_command)

    # Parse the arguments
    args = parser.parse_args()

    # Call the appropriate function based on the subcommand
    args.func(args)


def version_command(args):
    print(f"{Fore.CYAN}Dockershrink CLI version {VERSION}")


def optimize_command(args):
    # Get optional OpenAI API key
    ai_service = None
    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        ai_service = dockershrink.AIService(openai_client)

    # Read required Dockerfile
    dockerfile: dockershrink.Dockerfile

    dockerfile_path = Path(args.dockerfile)
    if not dockerfile_path.is_file():
        print(f"{Fore.RED}Error: Dockerfile not found at {dockerfile_path}")
        sys.exit(1)

    print(f"{Fore.GREEN}Using {dockerfile_path}")
    with open(dockerfile_path, "r") as f:
        dockerfile_content = f.read()
        dockerfile = dockershrink.Dockerfile(dockerfile_content)

    # Read optional .dockerignore
    dockerignore_path = Path(args.dockerignore)
    if dockerignore_path.is_file():
        print(f"{Fore.GREEN}Using {dockerignore_path}")
        with open(dockerignore_path, "r") as f:
            dockerignore_content = f.read()
    else:
        print(f"{Fore.YELLOW}No .dockerignore found at {dockerignore_path}")
        dockerignore_content = None

    dockerignore = dockershrink.Dockerignore(dockerignore_content)

    # Read optional package.json
    package_json = None

    if args.package_json:
        package_json_paths = [Path(args.package_json)]
    else:
        # Default paths searched: current directory and ./src
        package_json_paths = [Path("package.json"), Path("src/package.json")]

    for path in package_json_paths:
        if path.is_file():
            print(f"{Fore.GREEN}Using {path}")

            try:
                with open(path, "r") as f:
                    package_json_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"{Fore.RED}Error decoding JSON from {path}: {e}")
                sys.exit(1)

            if not type(package_json_data) == dict:
                print(
                    f"{Fore.RED}{path}: expected dict, received {type(package_json_data)}"
                )
                sys.exit(1)

            package_json = dockershrink.PackageJSON(package_json_data)

            break
        else:
            print(f"{Fore.YELLOW}No package.json found in the default paths")

    project = dockershrink.Project(
        dockerfile=dockerfile,
        dockerignore=dockerignore,
        package_json=package_json,
    )

    try:
        response = project.optimize_docker_image(ai_service)
    except openai.APIStatusError as e:
        print(
            f"{Fore.RED}Error: Request to OpenAI API failed with Status {e.status_code}: {e.body}"
        )
        sys.exit(1)
    except openai.APIError as e:
        print(f"{Fore.RED}Error: Request to OpenAI API failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}An error occured while optimizing the project: {e}")
        sys.exit(1)

    actions_taken = response["actions_taken"]
    recommendations = response["recommendations"]
    optimized_project = response["modified_project"]

    # Save optimized files
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in optimized_project.items():
        output_path = output_dir / filename
        with open(output_path, "w") as f:
            f.write(content)
        print(f"{Fore.GREEN}Optimized {filename} saved to {output_path}")

    # Display actions taken and recommendations
    if actions_taken:
        print(f"\n{Style.BRIGHT}Actions Taken:")
        for action in actions_taken:
            print(
                f"{Fore.BLUE}- {action['title']} ({action['filename']}): {action['description']}"
            )

    if recommendations:
        print(f"\n{Style.BRIGHT}Recommendations:")
        for rec in recommendations:
            print(
                f"{Fore.CYAN}- {rec['title']} ({rec['filename']}): {rec['description']}"
            )

    if not actions_taken and not recommendations:
        print(
            f"{Fore.GREEN}Docker image is already optimized; no further actions were taken."
        )


if __name__ == "__main__":
    main()
