import argparse
import sys
import os
from pathlib import Path
from dockershrink import optimizer

VERSION = "0.0.1"  # Update this as needed

def main():
    parser = argparse.ArgumentParser(
        description="Dockershrink optimizes your NodeJS Docker images."
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    subparsers.required = True

    # Version subcommand
    version_parser = subparsers.add_parser("version", help="Show the version of Dockershrink")
    version_parser.set_defaults(func=version_command)

    # Optimize subcommand
    optimize_parser = subparsers.add_parser("optimize", help="Optimize your Docker project")
    optimize_parser.add_argument(
        "--dockerfile",
        type=str,
        default="Dockerfile",
        help="Path to the Dockerfile"
    )
    optimize_parser.add_argument(
        "--dockerignore",
        type=str,
        default=".dockerignore",
        help="Path to the .dockerignore file"
    )
    optimize_parser.add_argument(
        "--package-json",
        type=str,
        default=None,
        help="Path to the package.json file"
    )
    optimize_parser.add_argument(
        "--output-dir",
        type=str,
        default="dockershrink.optimized",
        help="Directory to save optimized files"
    )
    optimize_parser.add_argument(
        "--openai-api-key",
        type=str,
        default=None,
        help="OpenAI API key for AI-powered optimizations"
    )
    optimize_parser.set_defaults(func=optimize_command)

    # Parse the arguments
    args = parser.parse_args()

    # Call the appropriate function based on the subcommand
    args.func(args)

def version_command(args):
    print(f"Dockershrink CLI version {VERSION}")

def optimize_command(args):
    # Get OpenAI API key
    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")

    # Read Dockerfile (mandatory)
    dockerfile_path = Path(args.dockerfile)
    if dockerfile_path.is_file():
        print(f"Using {dockerfile_path}")
        with open(dockerfile_path, "r") as f:
            dockerfile_content = f.read()
    else:
        print(f"Error: Dockerfile not found at {dockerfile_path}")
        sys.exit(1)

    # Read .dockerignore (optional)
    dockerignore_path = Path(args.dockerignore)
    if dockerignore_path.is_file():
        print(f"Using {dockerignore_path}")
        with open(dockerignore_path, "r") as f:
            dockerignore_content = f.read()
    else:
        print(f"No .dockerignore found at {dockerignore_path}")
        dockerignore_content = None

    # Read package.json (optional)
    package_json_content = None
    if args.package_json:
        package_json_paths = [Path(args.package_json)]
    else:
        # Default paths: current directory and ./src
        package_json_paths = [Path("package.json"), Path("src/package.json")]

    for path in package_json_paths:
        if path.is_file():
            print(f"Using {path}")
            with open(path, "r") as f:
                package_json_content = f.read()
            break
    else:
        print("No package.json found in the default paths")
        package_json_content = None

    if openai_api_key:
        print("Using OpenAI API key for AI-powered optimizations")
    else:
        print("No OpenAI API key provided; proceeding without AI-powered optimizations")

    # Call the optimizer
    try:
        optimized_project, actions_taken, recommendations = optimizer.optimize_project(
            dockerfile_content=dockerfile_content,
            dockerignore_content=dockerignore_content,
            package_json_content=package_json_content,
            openai_api_key=openai_api_key
        )
    except Exception as e:
        print(f"Error during optimization: {e}")
        sys.exit(1)

    # Save optimized files
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in optimized_project.items():
        output_path = output_dir / filename
        with open(output_path, "w") as f:
            f.write(content)
        print(f"Optimized {filename} saved to {output_path}")

    # Display actions taken and recommendations
    if actions_taken:
        print("\nActions Taken:")
        for action in actions_taken:
            print(f"- {action['title']} ({action['filename']}): {action['description']}")

    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"- {rec['title']} ({rec['filename']}): {rec['description']}")

    if not actions_taken and not recommendations:
        print("Docker image is already optimized; no further actions were taken.")

if __name__ == "__main__":
    main()
