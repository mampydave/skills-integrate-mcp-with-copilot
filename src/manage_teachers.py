import argparse
from getpass import getpass

from .teacher_auth import DEFAULT_TEACHERS_FILE, save_teacher


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a teacher login")
    parser.add_argument("username", help="Teacher username")
    args = parser.parse_args()

    password = getpass("Password (at least 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")

    try:
        save_teacher(args.username, password)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Teacher account saved to {DEFAULT_TEACHERS_FILE}")


if __name__ == "__main__":
    main()