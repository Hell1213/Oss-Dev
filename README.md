# OSS Dev Agent

> **Built for Gemini 3 Hackathon** - An AI-powered CLI tool that automates open source contributions using Google's Gemini 2.0 Flash Experimental model.

## 🎯 What is OSS Dev Agent?

OSS Dev Agent is an autonomous AI agent that automates the entire open source contribution workflow. Give it a GitHub issue URL, and it handles everything from codebase analysis to pull request creation—all powered by **Google's Gemini 2.0 Flash Experimental** model.

Instead of spending hours manually understanding codebases, creating branches, writing code, testing, and creating PRs, you run one command:

```bash
python3 main.py oss-dev fix https://github.com/owner/repo/issues/123
```

The agent works through a structured 7-phase workflow, leveraging Gemini's advanced reasoning capabilities to understand issues, plan fixes, implement code, and create production-ready contributions.

## 🚀 Why OSS Dev Agent Exists

### The Problem

Open source maintainers face a scaling challenge: they can typically handle 5-10 issues per day, but most repositories receive far more. Issues accumulate, contributors get discouraged, and projects slow down. Meanwhile, developers who want to contribute often struggle with workflow overhead—understanding codebases, following contribution guidelines, and creating properly formatted PRs.

### The Solution

OSS Dev Agent automates the mechanical aspects of contribution while preserving the quality standards maintainers expect. By handling workflow complexity, it enables:

- **Maintainers** to process more issues because contributions arrive in a consistent, reviewable format
- **Contributors** to focus on problem-solving rather than learning project-specific workflows
- **Projects** to scale contribution throughput without sacrificing quality

## 🧠 How Gemini 3 Powers OSS Dev Agent

OSS Dev Agent is **purpose-built for Gemini 3** and leverages Gemini 2.0 Flash Experimental's capabilities throughout the workflow:

### 1. **Repository Understanding** (Phase 1)
Gemini analyzes repository structure, identifies key components, and creates documentation artifacts. Its large context window (1M tokens) allows understanding entire codebases in a single pass.

### 2. **Issue Analysis** (Phase 2)
Gemini parses GitHub issues, extracts requirements, and identifies affected components. Its natural language understanding ensures accurate interpretation of issue descriptions and requirements.

### 3. **Strategic Planning** (Phase 3)
Gemini reasons about code locations, forms implementation strategies, and identifies dependencies—all before making any code changes. Its planning capabilities ensure fixes are well-thought-out.

### 4. **Code Implementation** (Phase 4)
Gemini generates minimal, focused code changes that solve the issue without introducing unrelated modifications. Its code generation is guided by maintainer best practices.

### 5. **Verification & Validation** (Phases 5-6)
Gemini understands test results, validates fixes, and ensures changes match issue scope. Its reasoning capabilities prevent scope creep and maintain code quality.

### 6. **PR Creation** (Phase 7)
Gemini generates conventional commit messages, writes clear PR descriptions, and links issues properly. Its natural language generation creates maintainer-friendly documentation.

### Why Gemini 3 is Perfect for This

- **Large Context Window**: Gemini 2.0's 1M token context allows understanding entire codebases
- **Advanced Reasoning**: Multi-step reasoning for complex issue analysis and planning
- **Code Understanding**: Deep comprehension of code structure and relationships
- **Quality Generation**: Produces maintainer-quality code and documentation
- **Fast Inference**: Flash model provides quick responses for interactive workflows

## 🔄 How It Works End-to-End

### The 7-Phase Workflow

```
Repository Understanding → Issue Intake → Planning → Implementation → Verification → Validation → Commit & PR
```

**Phase 1: Repository Understanding**
- Gemini analyzes repository structure
- Identifies key files and patterns
- Creates `START_HERE.md` guide for future reference

**Phase 2: Issue Intake**
- Fetches GitHub issue details via API
- Gemini parses and understands requirements
- Identifies affected components
- No code changes yet—pure analysis

**Phase 3: Planning**
- Gemini locates relevant code files
- Forms implementation strategy
- Identifies dependencies and edge cases
- Still no code—planning only

**Phase 4: Implementation**
- Creates feature branch automatically
- Gemini generates minimal, focused code changes
- Only modifies files necessary for the fix
- Maintains code style and conventions

**Phase 5: Verification**
- Runs tests to verify fix works
- Gemini analyzes test results
- Checks for regressions
- Validates fix solves the issue

**Phase 6: Validation**
- Gemini verifies changes match issue scope
- Ensures no unrelated changes
- Validates commit message format
- Checks PR description quality

**Phase 7: Commit & PR**
- Creates conventional commit message (Gemini-generated)
- Pushes branch to remote
- Opens pull request with proper description
- **Asks user for confirmation** before push/PR

### Architecture

```
User Command → CLI → OSS Workflow → Gemini Agent → Tools → GitHub/Repository
```

- **Workflow Orchestrator**: State machine managing phase transitions
- **Gemini Agent**: Uses Gemini 2.0 Flash for reasoning and code generation
- **Tool System**: Modular tools for Git, GitHub API, and repository analysis
- **Memory System**: Branch-level memory for context and resume functionality

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.12 or higher
- Git installed
- GitHub CLI (optional but recommended)
- **Gemini API key** (get from [Google AI Studio](https://aistudio.google.com/apikey))

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd ai-coding-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key
export GEMINI_API_KEY=your_api_key_here

# Set GitHub token (for OSS features)
export GITHUB_TOKEN=your_github_token_here

# Test the installation
python3 main.py oss-dev --help
```

### Configuration

Copy `env.example` to `.env` or set environment variables:

```bash
# Primary: Gemini API (required)
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub token (required for OSS features)
GITHUB_TOKEN=your_github_token_here
```

## 📖 Usage

### Fix a GitHub Issue

```bash
# From any cloned repository
cd /path/to/repo

# Fix an issue
python3 main.py oss-dev fix https://github.com/owner/repo/issues/123
```

### Other Commands

```bash
# Review an issue (when already in repo)
python3 main.py oss-dev review 123

# Check status
python3 main.py oss-dev status

# List active branches/issues
python3 main.py oss-dev list

# Resume interrupted work
python3 main.py oss-dev resume
```

## 🎯 Built for Gemini 3 Hackathon

OSS Dev Agent was **purpose-built for the Gemini 3 Hackathon**. It's not a retrofit—Gemini is the core architecture choice because:

1. **Gemini's reasoning capabilities** are essential for understanding complex codebases and planning fixes
2. **Large context window** (1M tokens) allows analyzing entire repositories
3. **Code understanding** enables generating maintainer-quality contributions
4. **Fast inference** (Flash model) provides responsive interactive workflows
5. **Natural language generation** creates clear commit messages and PR descriptions

The agent leverages Gemini throughout the workflow—from initial repository analysis to final PR creation. Every decision, every code change, every documentation artifact is powered by Gemini's advanced AI capabilities.

## 🔧 Technical Stack

- **Language**: Python 3.12+
- **AI Model**: Google Gemini 2.0 Flash Experimental (primary)
- **CLI Framework**: Click
- **UI**: Rich (beautiful terminal output)
- **Git Integration**: GitPython
- **GitHub API**: REST API + GitHub CLI
- **Configuration**: TOML

## 📝 Features

- ✅ **Autonomous Workflow**: Complete automation from issue to PR
- ✅ **Scope Discipline**: Only modifies files related to the issue
- ✅ **User Control**: Confirmation prompts for sensitive operations
- ✅ **Resume Capability**: Continue interrupted work seamlessly
- ✅ **Quality Assurance**: Automated validation at each phase
- ✅ **Best Practices**: Enforces conventional commits and PR standards

## 🤝 Contributing

This project was built for the Gemini 3 Hackathon. Contributions are welcome! See the project structure and codebase for details on how to extend the agent.

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

Built with **Google Gemini 2.0 Flash Experimental** for the Gemini 3 Hackathon. The agent showcases Gemini's capabilities in autonomous code contribution workflows.

---

**Get your Gemini API key**: [Google AI Studio](https://aistudio.google.com/apikey)
