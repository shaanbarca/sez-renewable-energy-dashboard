# Python Modelling Template

Template repository for Python modelling projects.

### Overview

This project provides a boilerplate template for setting up new Python models.

### Folder Structure

```
├── .github/workflows # Github Actions workflows (ie. publishing Sphinx documentation)
├── config/           # Project-level configurations
├── data/             # Input data (not versioned)
├── docs/             # Sphinx documentation
├── notebooks/        # Jupyter notebooks for exploration or analysis
├── outputs/          # Output incl. data and charts
├── src/              # Core project modules (ie. primary model logic)
├── tests/            # Unit tests
├── utils/            # Reuseable, generic helper functions
├── .env_template     # Environment variables (to be replaced be .env, if needed)
├── README.md         # Project overview
├── requirements.txt  # Python dependencies
└── pyproject.toml    # (optional) project metadata
```

### Getting Started

Create a project from the template using the GitHub UI, create a virtual environment, install dependencies:

```bash
cd project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### How We Write READMEs

To ensure all projects are easy to navigate and reuse, we follow these guidelines:

- Start with a brief summary of what the project is and why it exists
- Clearly describe folder layout and where key logic lives
- Include setup instructions that work on any machine
- Link or reference additional documentation as needed
- Keep it concise and update when major changes occur

### Contact

Maintainer: [Your Name]  
Email: your.email@systemiq.earth
