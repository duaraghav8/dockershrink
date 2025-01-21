import argparse
import json
import sys
import os
import traceback
from pathlib import Path
from openai import OpenAI
import openai

import dockershrink

from colorama import init, Fore, Style


# Initialize colorama
init(autoreset=True)

VERSION = "0.1.6"


def add_common_arguments(parser):
    """Add arguments shared between commands"""
    parser.add_argument(
        "--package-json",
        type=str,
        default=None,
        help="Path to package.json (default: ./package.json or ./src/package.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="dockershrink.optimized",
        help="Directory to save files (default: ./dockershrink.optimized)",
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        default=None,
        help="OpenAI API key (alternatively, set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print complete stack trace in case of failures",
    )


def setup_ai_service(args, required: bool = False):
    """Initialize OpenAI client if API key is provided"""
    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")

    if openai_api_key:
        return dockershrink.AIService(OpenAI(api_key=openai_api_key))
    if required:
        print(f"{Fore.RED}OpenAI API key not provided")
        sys.exit(1)


def read_package_json(paths):
    """Read and parse package.json from given paths"""
    pj_path: Path = None
    for path in paths:
        if path.is_file():
            pj_path = path
            break

    if pj_path is None:
        print(
            f"{Fore.RED}Error: No package.json found in paths: {', '.join(str(p) for p in paths)}"
        )
        return None

    try:
        with open(pj_path, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                print(f"{Fore.RED}Error: {pj_path}: expected dict, got {type(data)}")
                sys.exit(1)
            return dockershrink.PackageJSON(data)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Error decoding JSON from {pj_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error reading {pj_path}: {e}")
        sys.exit(1)


def handle_openai_api_error(e, verbose=False):
    """Handle OpenAI API errors"""
    if isinstance(e, openai.APIStatusError):
        print(f"{Fore.RED}Error: OpenAI API Status {e.status_code}: {e.body}")
    elif isinstance(e, openai.APIError):
        print(f"{Fore.RED}Error: OpenAI API failed: {e}")
    if verbose:
        print(os.linesep + traceback.format_exc())
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Dockershrink: Reduce the size of your NodeJS Docker images"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    version_parser.set_defaults(func=version_command)

    # Optimize command
    optimize_parser = subparsers.add_parser(
        "optimize", help="Optimize existing Dockerfile and related files"
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
    add_common_arguments(optimize_parser)
    optimize_parser.set_defaults(func=optimize_command)

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate new Dockerfile for NodeJS project",
        description="""
        Analyzes your NodeJS project and generates:
        - Optimized multi-stage Dockerfile
        - .dockerignore file
        - Build instructions
        """,
    )
    add_common_arguments(generate_parser)
    generate_parser.set_defaults(func=generate_command)

    args = parser.parse_args()
    args.func(args)


def version_command(args):
    print(f"{Fore.CYAN}Dockershrink CLI version {VERSION}")


def optimize_command(args):
    ai_service = setup_ai_service(args, required=False)

    # Read Dockerfile
    dockerfile_path = Path(args.dockerfile)
    if not dockerfile_path.is_file():
        print(f"{Fore.RED}Error: Dockerfile not found at {dockerfile_path}")
        sys.exit(1)

    print(f"{Fore.LIGHTGREEN_EX}{Style.DIM}* Reading {dockerfile_path}")
    with open(dockerfile_path, "r") as f:
        dockerfile = dockershrink.Dockerfile(f.read())

    # Read .dockerignore
    dockerignore_path = Path(args.dockerignore)
    dockerignore_content = None
    if dockerignore_path.is_file():
        print(f"{Fore.LIGHTGREEN_EX}{Style.DIM}* Reading {dockerignore_path}")
        with open(dockerignore_path, "r") as f:
            dockerignore_content = f.read()
    else:
        print(f"{Fore.YELLOW}{Style.DIM}* No .dockerignore file found")

    dockerignore = dockershrink.Dockerignore(dockerignore_content)

    # Read package.json
    package_json_paths = (
        [Path(args.package_json)]
        if args.package_json
        else [Path("package.json"), Path("src/package.json")]
    )
    package_json = read_package_json(package_json_paths)
    if not package_json:
        print(f"{Fore.YELLOW}{Style.DIM}* No package.json found")

    print(os.linesep)

    # Optimize project
    project = dockershrink.Project(
        dockerfile=dockerfile,
        dockerignore=dockerignore,
        package_json=package_json,
    )

    try:
        response = project.optimize_docker_image(ai_service)

    except (openai.APIStatusError, openai.APIError) as e:
        handle_openai_api_error(e, args.verbose)
    except Exception as e:
        print(f"{Fore.RED}Error: Failed to optimize project: {e}")
        if args.verbose:
            print(os.linesep + traceback.format_exc())
        sys.exit(1)

    # Save optimized files
    if response["actions_taken"]:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in response["modified_project"].items():
            output_path = output_dir / filename
            with open(output_path, "w") as f:
                if filename == "package.json":
                    json.dump(content, f, indent=4)
                else:
                    f.write(content)

        print(f"{Fore.GREEN}* Optimized files saved to {output_dir}/")

        # Show actions taken
        print(f"\n{Style.BRIGHT}============ Actions Taken ============")
        for action in response["actions_taken"]:
            print(f"{Fore.LIGHTBLACK_EX}File: {Fore.BLUE}{action['filename']}")
            print(f"{Fore.LIGHTBLACK_EX}Title: {Fore.GREEN}{action['title']}")
            print(f"{Fore.LIGHTBLACK_EX}Description: {action['description']}")
            print("-" * 40)

    # Show recommendations
    if response["recommendations"]:
        print(f"\n{Style.BRIGHT}============ Recommendations ============")
        for rec in response["recommendations"]:
            print(f"{Fore.LIGHTBLACK_EX}File: {Fore.BLUE}{rec['filename']}")
            print(f"{Fore.LIGHTBLACK_EX}Title: {Fore.GREEN}{rec['title']}")
            print(f"{Fore.LIGHTBLACK_EX}Description: {rec['description']}")
            print("-" * 40)

    if not response["actions_taken"] and not response["recommendations"]:
        print(f"{Fore.GREEN}{Style.BRIGHT}Docker image is already optimized.")


def generate_command(args):
    ai_service = setup_ai_service(args, required=True)

    package_json_paths = (
        [Path(args.package_json)]
        if args.package_json
        else [Path("package.json"), Path("src/package.json")]
    )
    package_json = read_package_json(package_json_paths)
    if not package_json:
        print(f"{Fore.RED}Error: package.json required for generate command")
        sys.exit(1)
    analysis = package_json.analyze()

    try:
        generator = dockershrink.Generator(ai_service)
        files = generator.generate_docker_files(analysis)

        # Save generated files
        output_dir = Path(".")
        # output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in files.items():
            output_path = output_dir / filename
            with open(output_path, "w") as f:
                f.write(content)
                print(f"{Fore.GREEN}* Generated {filename}")

        print(f"\n{Fore.CYAN}Files generated successfully in {output_dir}/")
        print(f"{Fore.CYAN}Build instructions added as comments in Dockerfile")
    except (openai.APIStatusError, openai.APIError) as e:
        handle_openai_api_error(e, args.verbose)
    except Exception as e:
        print(f"{Fore.RED}Error generating Docker files: {e}")
        if args.verbose:
            print(os.linesep + traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
