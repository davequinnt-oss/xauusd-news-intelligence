XAU NEWS PROBABILITY ENGINE V2

iPHONE USE:
Run the Python engine in Google Colab (or another cloud Python service) and
control it from Safari on your iPhone. The heavy process does not need to run
locally on the phone.

FIRST TEST:
1. Open Google Colab in Safari.
2. Upload xau_news_engine_v2.py, sample_event.json and requirements.txt.
3. Run: !pip install -q -r requirements.txt
4. Run: !python xau_news_engine_v2.py --analyze sample_event.json

HISTORICAL CALIBRATION:
Fill historical_events_template.csv with real event observations and target_down.
Then:
python xau_news_engine_v2.py --history historical_events.csv --train-only
or:
python xau_news_engine_v2.py --history historical_events.csv --analyze event.json

LIVE MARKET SNAPSHOT:
python xau_news_engine_v2.py --live

The initial heuristic is NOT a proven edge. The production version should use
out-of-sample/walk-forward testing and a real economic-calendar/consensus feed.
The engine intentionally separates pre-release probability from post-release
confirmation. It does not place trades.
