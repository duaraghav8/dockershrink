import argparse
import json
import sys
import os
import traceback
from pathlib import Path

import openai

import dockershrink
from openai import OpenAI

from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

VERSION = "0.1.5"


def main():
    parser = argparse.ArgumentParser(
        description="""Dockershrink is a CLI tool that helps you reduce the size of your NodeJS Docker images.
It applies best practices and optimizations to your Dockerfile and related code files.
The CLI is the primary way to interact with Dockershrink's functionality.
""",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    subparsers.required = True

    # Version subcommand
    version_parser = subparsers.add_parser(
        "version", help="Display Dockershrink Version Information"
    )
    version_parser.set_defaults(func=version_command)

    # Optimize subcommand
    optimize_parser = subparsers.add_parser(
        "optimize", help="Optimize your NodeJS Docker project to reduce image size"
    )
    optimize_parser.add_argument(
        "--dockerfile",
        type=str,
        default="Dockerfile",
        help="Path to Dockerfile (default: ./Dockerfile)",
    )
    optimize_parser.add_argument(
        "--dockerignore",
        type=str,
        default=".dockerignore",
        help="Path to .dockerignore (default: ./.dockerignore)",
    )
    optimize_parser.add_argument(
        "--package-json",
        type=str,
        default=None,
        help="Path to package.json (default: ./package.json or ./src/package.json)",
    )
    optimize_parser.add_argument(
        "--output-dir",
        type=str,
        default="dockershrink.optimized",
        help="Directory to save optimized files (default: ./dockershrink.optimized)",
    )
    optimize_parser.add_argument(
        "--openai-api-key",
        type=str,
        default=None,
        help="Your OpenAI API key to enable Generative AI features (alternatively, set the OPENAI_API_KEY environment variable)",
    )
    optimize_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print complete stack trace in case of failures",
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
        print(f"{Fore.RED}Error: Dockerfile not found")
        sys.exit(1)

    print(f"{Fore.LIGHTGREEN_EX}{Style.DIM}* Reading {dockerfile_path}")
    with open(dockerfile_path, "r") as f:
        dockerfile_content = f.read()
        dockerfile = dockershrink.Dockerfile(dockerfile_content)

    # Read optional .dockerignore
    dockerignore_path = Path(args.dockerignore)
    if dockerignore_path.is_file():
        print(f"{Fore.LIGHTGREEN_EX}{Style.DIM}* Reading {dockerignore_path}")
        with open(dockerignore_path, "r") as f:
            dockerignore_content = f.read()
    else:
        print(f"{Fore.YELLOW}{Style.DIM}* No .dockerignore file found")
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
        if not path.is_file():
            continue

        print(f"{Fore.LIGHTGREEN_EX}{Style.DIM}* Reading {path}")

        try:
            with open(path, "r") as f:
                package_json_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}Error decoding JSON from {path}: {e}")
            sys.exit(1)

        if not type(package_json_data) == dict:
            print(
                f"{Fore.RED}Error: {path}: expected dict, received {type(package_json_data)}"
            )
            sys.exit(1)

        package_json = dockershrink.PackageJSON(package_json_data)

    if package_json is None:
        print(f"{Fore.YELLOW}{Style.DIM}* No package.json found in the default paths")

    print(os.linesep)

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
        if args.verbose:
            print(os.linesep + traceback.format_exc())
        sys.exit(1)
    except openai.APIError as e:
        print(f"{Fore.RED}Error: Request to OpenAI API failed: {e}")
        if args.verbose:
            print(os.linesep + traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error: Failed to optimize the project: {e}")
        if args.verbose:
            print(os.linesep + traceback.format_exc())
        sys.exit(1)

    actions_taken = response["actions_taken"]
    recommendations = response["recommendations"]
    optimized_project = response["modified_project"]

    if actions_taken:
        # Save optimized files
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in optimized_project.items():
            output_path = output_dir / filename
            with open(output_path, "w") as f:
                if filename == "package.json":
                    # package.json content is a python dict, must be written
                    # as json string
                    json.dump(content, f, indent=4)
                else:
                    f.write(content)

        print(f"{Fore.GREEN}* Optimized files saved to {output_dir}/")

        # Display actions taken
        print(
            f"{os.linesep}{Style.BRIGHT}============ {len(actions_taken)} Action(s) Taken ============"
        )
        for action in actions_taken:
            print(f"{Fore.LIGHTBLACK_EX}File: " + f"{Fore.BLUE}{action['filename']}")
            print(f"{Fore.LIGHTBLACK_EX}Title: " + f"{Fore.GREEN}{action['title']}")
            print(
                f"{Fore.LIGHTBLACK_EX}Description: "
                + f"{Fore.WHITE}{action['description']}"
            )
            print("---------------------------------")

    # Display Recommendations
    if recommendations:
        print(
            f"{os.linesep*2}{Style.BRIGHT}============ {len(recommendations)} Recommendation(s) ============"
        )
        for rec in recommendations:
            print(f"{Fore.LIGHTBLACK_EX}File: " + f"{Fore.BLUE}{rec['filename']}")
            print(f"{Fore.LIGHTBLACK_EX}Title: " + f"{Fore.GREEN}{rec['title']}")
            print(
                f"{Fore.LIGHTBLACK_EX}Description: "
                + f"{Fore.WHITE}{rec['description']}"
            )
            print("---------------------------------")

    if not actions_taken and not recommendations:
        print(
            f"{Fore.GREEN}{Style.BRIGHT}Docker image is already optimized, no further actions were taken."
        )


if __name__ == "__main__":
    main()
