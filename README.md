# CatEye - SF250 byPiranYaa

CatEye is a football scouting demo with player profiles, player similarity, role ranking, and event heatmaps. The interface loads the season summary, player metadata, and Parquet files from Render PostgreSQL through the web service.

Configure a Python web service on Render in the same region as the database. Use `pip install -r requirements.txt` to build and `gunicorn --bind 0.0.0.0:$PORT app:app` to start. Set `DATABASE_URL` to the Render internal database URL in the service environment settings.

Set `DATABASE_URL` to the external database URL in your local environment for the initial import. Install the requirements, then run `python import_data.py <summary-directory> <parquet-directory>`. The first folder must contain the extended season summary gzip, player birthdays JSON, and market values JSON. The second folder must contain the 60 Big Five event Parquets and `players.parquet`. The importer skips unchanged files, so interrupted uploads can resume.

Match data is from [Openplay](https://github.com/nlbair/openplay), CC BY 4.0. Market estimates are from the [Transfermarkt dataset snapshot](https://github.com/dcaribou/transfermarkt-datasets).
