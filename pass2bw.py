#!/usr/bin/env python3

import argparse
import csv
import re
import os

import gnupg

from defaults import CSV_FIELDS, FIELD_DEFAULTS, FIELD_FUNCTIONS, FIELD_PATTERNS

DOMAIN_REGEX_RAW = "^((?!-)[A-Za-z0-9-]" + "{1,63}(?<!-)\\.)" + "+[A-Za-z]{2,6}"
DOMAIN_REGEX = re.compile(DOMAIN_REGEX_RAW)


def traverse(directory: str) -> list:
    """
    Traverse the directory and return all files.

    Args:
        directory (str): Directory to traverse.

    Returns:
        _type_: Files in the directory.
    """
    pass_files = []

    for root, dirs, files in os.walk(directory):
        if ".git" in dirs:
            dirs.remove(".git")

        for name in files:
            pass_files.append(os.path.join(root, name))

    return pass_files


def decrypt(files: list[str], binary: str, agent: str) -> list:
    """Decrypt the files using GPG.

    Args:
        files (list[str]): List of files to decrypt.
        binary (str): gpg Binary path.
        agent (str): Agent to use.

    Returns:
        _type_: _description_
    """
    gpg = gnupg.GPG(gpgbinary=binary, use_agent=True)
    gpg.encoding = "utf-8"

    datas = []

    for path in files:
        file = os.path.splitext(path)[0]
        extension = os.path.splitext(path)[1]

        if extension == ".gpg":
            with open(path, "rb") as gpg_file:
                decrypted = {"path": file, "data": str(gpg.decrypt_file(gpg_file))}

                datas.append(decrypted)

    return datas


def _guess_uri(row: str) -> str:
    """Check if the name is a domain and return it.

    Args:
        row (str): String to check.

    Returns:
        _type_: Login URI if it's a domain.
    """
    if "login_uri" in row:
        if re.search(DOMAIN_REGEX, row["name"]):
            return row["name"]
    return ""


def parse(base_dir: str, files: list[dict]) -> list:
    """Parse the files and return the CSV data.

    Args:
        base_dir (str): Base directory.
        files (list[dict]): List of files.

    Returns:
        _type_: List of parsed data.
    """
    parsed = []

    for file in files:
        row = {}

        for field in CSV_FIELDS:
            if field in FIELD_DEFAULTS:
                row[field] = FIELD_DEFAULTS[field]
            elif field in FIELD_FUNCTIONS:
                row[field] = FIELD_FUNCTIONS[field](
                    base_dir, file["path"], file["data"]
                )
            elif field in FIELD_PATTERNS:
                try:
                    row[field] = re.search(
                        FIELD_PATTERNS[field], file["data"], re.I | re.M
                    ).group(1)
                except AttributeError:
                    row[field] = ""
            else:
                row[field] = ""

        if row["login_uri"] == "":
            row["login_uri"] = _guess_uri(row)
        parsed.append(row)

    return parsed


def write(data: list, output_file: str) -> None:
    """Write the data to a CSV file.

    Args:
        data (list): Content to write.
        output_file (str): Output file.
    """
    with open(output_file, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)

        writer.writeheader()

        for row in data:
            writer.writerow(row)


def main() -> None:
    """
    Start the script.
    """
    parser = argparse.ArgumentParser(
        description="Export password-store data to Bitwarden CSV format."
    )

    parser.add_argument(
        "--directory",
        "-d",
        default="~/.password-store",
        help="Directory of the password store.",
    )
    parser.add_argument(
        "--gpg-binary",
        "-b",
        dest="binary",
        default="/usr/bin/gpg",
        help="Path to the GPG binary.",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        dest="output",
        default="pass.csv",
        help="File to write the CSV in.",
    )
    parser.add_argument(
        "--gpg-agent", "-a", dest="agent", help="Use GPG agent.", action="store_true"
    )

    args = parser.parse_args()

    password_store = os.path.expanduser(args.directory)

    encrypted_files = traverse(password_store)
    decrypted_files = decrypt(encrypted_files, args.binary, args.agent)

    csv_data = parse(password_store, decrypted_files)

    write(csv_data, args.output)


if __name__ == "__main__":
    main()
