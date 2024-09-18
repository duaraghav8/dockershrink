import os

# Define the necessary files/directories to be in .dockerignore
required_entries = {".git", "node_modules", "npm_debug.log"}


def ensure_dockerignore(path='.'):
    """
    Ensure that a .dockerignore file exists, contains required entries, and
    modifies/creates the file if necessary.

    Parameters:
        path (str): The directory path where the Dockerfile and .dockerignore are located. Default is current directory.
    """
    dockerignore_path = os.path.join(path, '.dockerignore')

    # Check if the .dockerignore file exists
    if not os.path.exists(dockerignore_path):
        # If it doesn't exist, create it and add required entries
        print(f".dockerignore file not found. Creating one with necessary entries.")
        with open(dockerignore_path, 'w') as f:
            for entry in required_entries:
                f.write(entry + '\n')
        print(f".dockerignore file created with required entries: {required_entries}")
    else:
        # If the file exists, read its contents
        with open(dockerignore_path, 'r') as f:
            existing_entries = set(line.strip() for line in f if line.strip())

        # Check if required entries are missing
        missing_entries = required_entries - existing_entries
        if missing_entries:
            # If there are missing entries, append them to the file
            print(f"Adding missing entries to .dockerignore: {missing_entries}")
            with open(dockerignore_path, 'a') as f:
                for entry in missing_entries:
                    f.write(entry + '\n')
            print(f"Missing entries added: {missing_entries}")
        else:
            print(f".dockerignore already contains all required entries.")


if __name__ == "__main__":
    # Call the function to ensure .dockerignore compliance
    ensure_dockerignore()
