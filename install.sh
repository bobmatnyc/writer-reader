#!/bin/bash
# Installation script for The Augmented Programmer Book Reader

echo "Installing The Augmented Programmer Book Reader..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv book_reader_env

# Activate virtual environment
echo "Activating virtual environment..."
source book_reader_env/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Make the script executable
chmod +x book_reader.py

# Create a convenient launcher script
cat > read_book.sh << 'EOF'
#!/bin/bash
# Convenient launcher for The Augmented Programmer Book Reader

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment and run the reader
source "$SCRIPT_DIR/book_reader_env/bin/activate"
python "$SCRIPT_DIR/book_reader.py" "$@"
EOF

chmod +x read_book.sh

echo "Installation complete!"
echo ""
echo "Usage options:"
echo "  1. Direct execution: source book_reader_env/bin/activate && python book_reader.py"
echo "  2. Convenient launcher: ./read_book.sh"
echo ""
echo "Examples:"
echo "  ./read_book.sh                 # Start interactive reader"
echo "  ./read_book.sh --chapter 5     # Jump to chapter 5"
echo "  ./read_book.sh --toc           # Show table of contents"
echo ""
echo "Run './read_book.sh --help' for more options."