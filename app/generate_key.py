import secrets

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

def add_api_key_to_file(api_key: str, filename: str = "keys.txt"):
    """Append the generated API key to the file."""
    with open(filename, "a") as f:
        f.write(api_key + "\n")

if __name__ == "__main__":
    new_key = generate_api_key()
    add_api_key_to_file(new_key)
    print(f"New API Key generated and saved to file: {new_key}")
