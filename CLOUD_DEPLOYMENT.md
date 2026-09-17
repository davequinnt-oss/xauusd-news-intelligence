# Cloud deployment

## Google Colab
Install:
!pip install -q -r requirements.txt streamlit

For the command-line engine:
!python xau_news_engine_v2.py --analyze sample_event.json

## Streamlit
The included app.py is designed to become the iPhone dashboard.
A Streamlit-compatible cloud host can expose it as a web page.

## Important data sources
CME FedWatch is the market-implied source for FOMC rate probabilities.
FRED provides DGS2, DGS10 and DFII10 Treasury series.
For production, use licensed/API-accessed consensus data rather than scraping
web pages.
