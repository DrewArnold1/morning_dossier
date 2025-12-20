# Morning Dossier

A Python script that fetches specific emails from Gmail, formats them using AI, and compiles them into a magazine-style PDF.

## Prerequisites

1.  **Python 3.8+**
2.  **Gmail API Credentials**:
    *   Go to [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a project and enable the **Gmail API**.
    *   Create OAuth 2.0 Client IDs (Desktop App).
    *   Download the JSON file and rename it to `credentials.json` in this directory.
    *   Add your email (`andrewstephenarnold@gmail.com`) to the Test Users list if the app is in "Testing" mode.
3.  **OpenAI API Key**:
    *   Get an API key from [OpenAI](https://platform.openai.com/).

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1.  Create a `.env` file (copy from `env.example`):
    ```bash
    cp env.example .env
    ```
2.  Edit `.env` and add your OpenAI API Key:
    ```
    OPENAI_API_KEY=sk-...
    ```

## Usage

1.  Label the emails you want to read in Gmail with the label `morning-dossier`.
2.  Run the script:
    ```bash
    python main.py
    ```
3.  On the first run, a browser window will open for you to authorize access to your Gmail account.
4.  The script will generate a PDF file (e.g., `Morning_Dossier_drew.pdf`) and open it.

## Troubleshooting

-   **Images not showing**: Ensure the `images` directory exists (the script creates it).
-   **No emails found**: Ensure you have created the label `morning-dossier` in Gmail and applied it to some emails.
-   **Authentication errors**: Delete `token.json` to force re-authentication.

