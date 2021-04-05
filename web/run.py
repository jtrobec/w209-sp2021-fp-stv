import altair as alt
import pandas as pd
import json

from flask import Flask, request, send_from_directory
from os import listdir
from os.path import isfile, join
from scipy import stats

# set the project root directory as the dist folder
app = Flask(__name__)

@app.route("/")
def index():
  return dist('index.html')

@app.route("/data/<path:path>")
def data(path):
  return send_from_directory('../data', path)

@app.route("/<path:path>")
def dist(path):
  return send_from_directory('dist', path)

@app.route("/error_chart/<traceID>")
def error_chart(traceID):
    #Filter to trace with error
    traceWithError = load_trace(traceID)
    traceWithError = traceWithError.sort_values(by=['traceId','timestamp'],ascending=True).reset_index()
    traceWithErrorSpans = traceWithError.loc[traceWithError['error'] == True]

    traceWithError["start"] = 0
    traceWithError["end"] = 0

    spanCount = len(traceWithError)
    traceWithError.loc[0,'end'] = traceWithError.loc[0,'duration']

    for i in range(1,spanCount):
      traceWithError.loc[i,'start'] = traceWithError.loc[i,'timestamp'] - traceWithError.loc[0,'timestamp']
      traceWithError.loc[i,'end'] = traceWithError.loc[i,'start'] + (traceWithError.loc[i,'duration'])

    bars = alt.Chart(traceWithError,title="Trace with Errors").mark_bar().encode(
        x='start:Q',
        x2='end:Q',
        y=alt.Y('name:N',sort='x'),
        color=alt.condition(
            alt.datum.error == 'true',  # If there is an span error this test returns true
            alt.value('red'),     # which sets the bar orange.
            alt.value('steelblue')   # And if it's not true it sets the bar steelblue.
        ),
        tooltip=['name', 'start', 'end', 'duration']
    ).interactive()

    point = alt.Chart(traceWithError).mark_point(filled=True, color='black').encode(
        x='start:Q',
        x2='end:Q',
        y=alt.Y('name:N',sort='x'),
    ).transform_filter(
        (alt.datum.error == 'true')
    )

    combined = bars + point
    
    return combined.to_json()

def load_trace(tid):
  traces = []

  baseDirectory = '../data/synthetic/20210302-hipster-shop'
  thisDirectory = join(baseDirectory, f'{tid}.json')

  with open(thisDirectory) as f:
    data = pd.json_normalize(json.load(f))
    traces.append(data)

  tdf = pd.concat(traces, axis=0)
  tdf = tdf.sort_values(by=['traceId','timestamp'],ascending=True)
  tdf["error"] = tdf["tags.error"]
  return tdf

if __name__ == "__main__":
  app.run(debug=True)
