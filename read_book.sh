#!/bin/bash
# Convenient launcher for The Augmented Programmer Book Reader

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment and run the reader
source "$SCRIPT_DIR/book_reader_env/bin/activate"
python "$SCRIPT_DIR/book_reader.py" "$@"
