# Spotify Playlist Bingo Card Generator

## Overview

This Python project generates bingo cards using track titles from a Spotify playlist. It includes features like customizable delimiters for title trimming, duplicate detection, and heatmap analysis of card content. The output is a PDF containing bingo cards and a detailed duplicate analysis.

---

## Features

1. **Spotify Integration**:
   - Fetch tracks from a Spotify playlist using `spotipy`.
   - Supports client credentials for authentication.

2. **Bingo Card Generation**:
   - Generates bingo cards with a 5x5 grid.
   - Includes a central "FREE" space.
   - Allows multiple card creation in a single PDF.

3. **Customizable Options**:
   - Trim track titles based on user-defined delimiters.
   - Choose whether to trim text before the first delimiter.

4. **Duplicate Analysis**:
   - Analyzes card content for duplicate tracks.
   - Generates a heatmap highlighting duplicate positions.

5. **Streamlit Interface**:
   - User-friendly web app for entering playlist URLs and settings.
   - Supports PDF download of generated bingo cards.
   - Requires Spotify Developer API Tokens.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/spotify-bingo.git
   cd spotify-bingo
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Streamlit Interface

1. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Open the app in your browser and:
   - Enter your Spotify playlist URL.
   - Configure custom delimiters for title trimming.
   - Enter Spotify client credentials in the style of CLIENT_ID+CLIENT_SECRET (any delimited can be used so long as not hexadecimal.)
   - Generate and download bingo cards.

---

## Requirements

- Python 3.8+
- Required Libraries:
  - `streamlit`
  - `spotipy`
  - `matplotlib`
  - `seaborn`
  - `reportlab`
  - `numpy`

---

## Output

The output is a downloadable PDF containing:
1. Bingo cards with track titles.
2. A heatmap highlighting duplicate track positions.
3. A summary of duplicate analysis.

---

## Notes

- Spotify API credentials (client ID and secret) are required.
- Ensure the playlist contains at least 24 distinct tracks.
- Customize card titles and other parameters through the Streamlit interface.

---

## License

This project is licensed under the [MIT License](LICENSE).
