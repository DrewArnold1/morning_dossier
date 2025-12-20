# Morning Dossier

A Python script that fetches specific emails from Gmail, cleans the content, and compiles them into a magazine-style PDF. Perfect for reading your favorite newsletters offline or on a tablet.

## Prerequisites

1.  **Python 3.8+**
2.  **Pango** (Required for PDF generation):
    *   **macOS** (using Homebrew): `brew install pango`
    *   **Windows**: You may need the GTK3 runtime. See [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).
    *   **Linux**: `sudo apt install python3-pip python3-venv libpango-1.0-0 libpangoft2-1.0-0`

## Installation

1.  Clone this repository.
2.  Create and activate a virtual environment:

    ```bash
    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Setup (The Important Part)

To read your emails, you must create a Google Cloud Project and authorize this app.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a **New Project**.
3.  Search for and Enable the **Gmail API**.
4.  Go to **Credentials** (sidebar) -> **Create Credentials** -> **OAuth Client ID**.
    *   **Application Type**: Desktop App.
    *   If prompted to configure the "OAuth Consent Screen":
        *   **User Type**: External.
        *   **Test Users**: Add **your own email address**. This is crucial for testing.
5.  Download the JSON credentials file, rename it to `credentials.json`, and place it in the root folder of this project.

## Usage

1.  **Label your emails**: Go to Gmail and create a label called `morning-dossier`. Apply this label to the emails you want to include in your daily digest.
2.  **Run the script**:
    ```bash
    python main.py
    ```
3.  **Authorize**: On the first run, a browser window will open. Log in with your Google account.
    *   *Note:* You may see a "Google hasn't verified this app" warning since you created it yourself. Click **Advanced** -> **Go to [Project Name] (unsafe)** to proceed.
4.  **Read**: The script will generate a PDF (e.g., `Morning_Dossier_YourName.pdf`) and open it automatically.

## Troubleshooting

*   **Images not showing**: Ensure the `images` directory exists (the script creates it automatically).
*   **No emails found**: Double-check that you have applied the `morning-dossier` label to emails in Gmail.
*   **Authentication errors**: Delete the `token.json` file to force a fresh login.
