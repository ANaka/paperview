# paperview

This project is aimed at making it easier to quickly extract and summarize information from scientific manuscripts, especially preprints.

It is also intended as a learning project for me to experiment with collaboratively coding with copilot/ChatGPT, and perhaps for messing around with LLMs in other ways

It is currently in a very early stage of development, and is not yet ready for use.

# Installation

This project requires poetry to be installed. See instructions [here](https://python-poetry.org/docs/#installation). Also recommend using pyenv to manage python versions.

Once poetry is installed, run the following commands to install the dependencies:

`pyenv shell 3.10`
`poetry env use python3.10`
`poetry install`

# Development

## `pre-commit`

When developing, it is recommended to use the pre-commit hooks to ensure that code is formatted correctly. To install the hooks, run the following command: `poetry run pre-commit install`

## Tests

To run the tests, run the following command: `poetry run pytest`
