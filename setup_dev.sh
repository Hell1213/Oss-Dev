#!/bin/bash
set -e

echo "🚀 Setting up OSS Dev Agent development environment..."
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Check if Python 3.8+
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "   ✅ Virtual environment created"
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📥 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "   ✅ Core dependencies installed"
else
    echo "   ⚠️  requirements.txt not found"
fi

# Check for Git
echo ""
echo "🔍 Checking system dependencies..."
if command -v git &> /dev/null; then
    git_version=$(git --version | awk '{print $3}')
    echo "   ✅ Git found: $git_version"
else
    echo "   ❌ Git not found. Please install Git first."
    exit 1
fi

# Check for GitHub CLI
if command -v gh &> /dev/null; then
    gh_version=$(gh --version | head -n 1 | awk '{print $3}')
    echo "   ✅ GitHub CLI found: $gh_version"
    if ! gh auth status &> /dev/null; then
        echo "   ⚠️  GitHub CLI not authenticated. Run: gh auth login"
    else
        echo "   ✅ GitHub CLI authenticated"
    fi
else
    echo "   ⚠️  GitHub CLI (gh) not found. Install it for best experience:"
    echo "      Ubuntu/Debian: sudo apt install gh"
    echo "      macOS: brew install gh"
    echo "      Then run: gh auth login"
fi

# Verify Python dependencies
echo ""
echo "🔍 Verifying Python dependencies..."
python3 -c "import click, openai, pydantic, rich, tiktoken; print('   ✅ Core dependencies verified')" 2>/dev/null || {
    echo "   ❌ Some core dependencies missing. Run: pip install -r requirements.txt"
    exit 1
}

# Check for Gemini API key
echo ""
echo "🔍 Checking API configuration..."
if [ -z "$GEMINI_API_KEY" ] && [ -z "$API_KEY" ]; then
    echo "   ⚠️  GEMINI_API_KEY not set. OSS Dev Agent requires Gemini API key."
    echo "      Get your key from: https://aistudio.google.com/apikey"
    echo "      Then run: export GEMINI_API_KEY=your_key"
else
    echo "   ✅ API key configured (GEMINI_API_KEY or API_KEY)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Activate the environment: source .venv/bin/activate"
echo "   2. Set API_KEY environment variable: export API_KEY=your_key"
echo "   3. Test the setup: python main.py --help"
echo ""
echo "💡 Tip: Add this to your shell profile to auto-activate:"
echo "   alias activate-oss-dev='cd $(pwd) && source .venv/bin/activate'"
