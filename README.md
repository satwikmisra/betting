# betting

## Setup

Need Python 3.8+, preferably Python 3.9

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Usage

To run PrizePicks scraper, get hit percentages, and update Google sheets:

```
python3 src/main.py
```

Note: Running this will spawn a browser window and scrape PrizePicks. There are time delays because page content is dynamically loaded. Don't close the window, just wait for the scraper to run and the browser will automatically close.
