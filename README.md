# CatEye - SF250 byPiranYaa

CatEye is a football scouting demo with player profiles, player similarity, role ranking, and event heatmaps. The `index.html` interface loads the season summary, player metadata, and pitch-zone event counts from Render PostgreSQL through the web service. No manual CSV upload is required.

Configure a Python web service on Render in the same region as the database. Use `pip install -r requirements.txt` to build and `gunicorn --bind 0.0.0.0:$PORT app:app` to start. Set `DATABASE_URL` to the Render internal database URL in the service environment settings. For local runs, install the requirements and run `python -m flask --app app run`; the app loads `DATABASE_URL` from a local `.env` file automatically, and `.env` is excluded from Git.

For the initial import, install the requirements and DuckDB locally. Run `python build_heatmaps.py <parquet-directory> <heatmap-directory>` with the 60 Big Five event Parquets. Set `DATABASE_URL` to the external database URL in your local environment, then run `python import_data.py <summary-directory> <heatmap-directory>`. The summary directory must contain the extended season summary gzip, player birthdays JSON, and market values JSON. To additionally store the original Openplay event Parquet files, pass `--event-dir <Openplay_Event-directory>`; the full source set is about 868 MB before PostgreSQL overhead and WAL, so check the database disk capacity first. The importer skips unchanged files, so interrupted uploads can resume.

Match data is from [Openplay](https://github.com/nlbair/openplay), CC BY 4.0. Market estimates are from the [Transfermarkt dataset snapshot](https://github.com/dcaribou/transfermarkt-datasets).
