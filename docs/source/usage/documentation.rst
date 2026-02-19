.. _documentation-label:

Documentation with Sphinx
=================================

This project uses `Sphinx` for documentation. This page explains how to structure Python modules and document them in a way that integrates cleanly with Sphinx and supports long-term readability, usability, and collaboration.

It uses Google-style docstrings and is aligned with SYSTEMIQ's internal standards and the Furo theme.

Module Structure
----------------

Each Python module should:

- Do **one thing well** (single-responsibility principle)
- Include a **top-level module docstring** that briefly describes its purpose
- Contain **well-named functions or classes** with clear inputs/outputs

Example:

.. code-block:: python

    """
    src/example_module.py

    Utilities for loading and analyzing raster data from cloud storage.
    """

    def load_config(path: str) -> dict:
        """Load a YAML configuration file.

        Args:
            path (str): Path to the config file.

        Returns:
            dict: Parsed configuration as a dictionary.
        """
        ...


    def compute_summary(data: np.ndarray) -> dict:
        """Compute mean, min, max from a 2D NumPy array.

        Args:
            data (np.ndarray): Input raster data.

        Returns:
            dict: Dictionary with 'mean', 'min', and 'max' values.
        """
        ...

---

Docstring Style
---------------

We use the **Google style** for clarity and compatibility with Sphinx + Napoleon.

Key components:

1. **One-line summary**: Short and descriptive.
2. **Args**: List input parameters with types and explanations.
3. **Returns**: Describe the return value and its type.
4. **Raises** (optional): Mention specific errors your function may raise.

Example:

.. code-block:: python

    def calculate_area(width: float, height: float) -> float:
        """Calculate the area of a rectangle.

        Args:
            width (float): The width of the rectangle.
            height (float): The height of the rectangle.

        Returns:
            float: The computed area.
        """

---

Best Practices
--------------

- ✘ Avoid vague names like `process()` or `do_stuff()`
- ✔ Use meaningful verbs: `load_config()`, `compute_area()`, `clip_raster()`
- ✔ Always document what the function **expects** and what it **returns**
- ✔ Keep docstrings short and focused — use full documentation pages for deep explanations

---

Setting up Sphinx documentation for a new project [New/non-boilerplate project only]
---------------------------------------------------

**This project has Sphinx already installed, but the below walks through how to set it up for a new project.**

1. Setting up Sphinx

   To set up Sphinx, run the following command in the `docs` directory:

   .. code-block:: bash

      sphinx-quickstart docs

   Follow the prompts to configure your documentation.

2. Update the configuration

   Open `docs/source/conf.py` and add the following:

    .. code-block:: bash

        import os
        import sys
        sys.path.insert(0, os.path.abspath('../..'))

        extensions = [
            'myst_parser',
            'sphinx.ext.autodoc',
            'sphinx.ext.napoleon',  # for Google or NumPy style docstrings
            'sphinx.ext.viewcode',
            'sphinx_autodoc_typehints',  # if you installed it
        ]

        html_theme = 'furo' # replace html_theme = ‘alabaster’

3. Add the README to the index
   Add the following to `docs/source/index.rst`:

    .. code-block:: rst

        .. include:: ../../README.md
            :parser: myst_parser.sphinx_
            :start-line: 3

Adding new Sphinx documentation
---------------------------------------------------

1. Document your code

   Use docstrings in your Python files to document your code as described above. 
   Sphinx will automatically extract these docstrings for modules set with autodoc when
   building the documentation.
     
2. Add documentation of autodoc modules

   To set autodoc to for all of the modules within `src` run:

    .. code-block:: bash
    
        sphinx-apidoc -o docs/source/ src

   This will create a `.rst` file for the modules in the `src` directory. Then, add the `modules` directory to the index:

    .. code-block:: bash

        .. toctree::
            :maxdepth: 2
            :caption: API Reference

            modules
    
   Update the files as needed to change titles, add descriptions, etc.

3. Add additional documentation

   For documentation pages not linked to modules (ie. Getting Started, Project Overview, etc), do this manually:

    1. Create an `.rst` file in `docs/source/` (using folders where necessary)
    2. Add the content to the `.rst` file, using reStructuredText syntax.
    3. Add your `.rst` file to `index.rst` under a `.. toctree::`


Building the Documentation
---------------------------

Build the documentation locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make clean
   make html

Publish the documentation to GitHub Pages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. [New/non-boilerplate project only] Create `docs/requirements.txt` and add the following dependencies:

   .. code-block:: bash

        # Only for Sphinx documentation generation on Github Pages
        # Add any additional dependencies here that are needed by project modules that use Sphinx autodoc/automodule.

        # Sphinx and related packages
        sphinx>=8.2.0
        furo>=2024.08.06
        myst-parser>=3.0.0
        docutils>=0.17
        jinja2>=3.1
        markupsafe>=2.1

   **Note:** If you are using any other Sphinx extensions, add them to this file.

2. Update `docs/requirements.txt` to include any dependencies needed for modules that use
   Sphinx autodocumentation. For example, for a dash application, add:

   .. code-block:: bash

        dash>=2.0.0
        dash-leaflet

   **Note:** Make sure to update the requirements.txt **within the docs/ folder**.

   To test that all necessary dependencies are included, create a new virtual environment and run:
   
        .. code-block:: bash
        
            source .venv/bin/activate  # On Windows: .venv\Scripts\activate
            pip install -r docs/requirements.txt
            make html 

   Check the logs and open the generated HTML files in `docs/build/html` to check that everything has built correctly.
   
3. [New/non-boilerplate project only] Add the Github Actions workflow

   Create a new file in your repository at `.github/workflows/sphinx.yml` with the following content:

        .. code-block:: yaml

            name: "Sphinx: Render docs"

            on: push

            jobs:
            build:
                runs-on: ubuntu-latest
                permissions:
                contents: write
                steps:
                - uses: actions/checkout@v4
                    with:
                    persist-credentials: false
                - name: Set up Python
                    uses: actions/setup-python@v5
                    with:
                    python-version: "3.12"
                - name: Build HTML
                    uses: ammaraskar/sphinx-action@8.2.0
                - name: Deploy
                    uses: peaceiris/actions-gh-pages@v3
                    if: github.ref == 'refs/heads/main'
                    with:
                    github_token: ${{ secrets.GITHUB_TOKEN }}
                    publish_dir: docs/build/html


4. Enable GitHub Pages on your repository

    1. Navigate to your repository on GitHub and go to the **Settings** tab.
    
    2. Select **Pages**, under the **Code and automation** section.

    3. For the Source select **Deploy from a branch**. 

    4. In the **Branch** dropdown, select `gh-pages` and `/ (root)` for the folder.

    5. Click **Save**.
    
    6. After a few minutes, your documentation will be available at `https://systemiqofficial.github.io/<repository-name>/`.


   This will automatically publish the documentation to GitHub Pages using the workflow at `.github/workflows/sphinx.yml`. 
   This workflow will run every time you push to the main branch. It will (from `Sphinx documentation <https://www.sphinx-doc.org/en/master/tutorial/deploying.html#id5>`_):

    1. Checkout the code
    2. Build the HTML documentation
    3. Attach the HTML output to the GitHub Actions job.
    4. If the change happens on the default branch, take the concents of the `docs/build/html`  and push it to the `gh-pages` branch. This branch will be used to host the documentation.
