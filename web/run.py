import altair as alt
import pandas as pd
import json

from flask import Flask, request, Response, send_from_directory
from os import listdir
from os.path import dirname, isfile, join, realpath
from scipy import stats

# set the project root directory as the dist folder
app = Flask(__name__)

app_dir = dirname(realpath(__file__))
data_dir = join(app_dir, '../data')
dist_dir = join(app_dir, 'dist')
trace_csv_path = join(data_dir, 'synthetic', '20210302-hipster-shop.csv')

alt.data_transformers.disable_max_rows()

@app.route("/")
def index():
  return dist('index.html')

@app.route("/data/<path:path>")
def data(path):
  return send_from_directory(data_dir, path)

@app.route("/<path:path>")
def dist(path):
  return send_from_directory(dist_dir, path)

@app.route("/error_chart/<traceID>")
def error_chart(traceID):
    #Filter to trace with error
    traces = load_traces()
    traceWithError = traces.loc[traces['traceId'] == traceID]
    traceWithError = traceWithError.sort_values(by=['traceId','timestamp'],ascending=True).reset_index()
    traceWithErrorSpans = traceWithError.loc[traceWithError['error'] == True]

    traceWithError["start"] = 0
    traceWithError["end"] = 0

    spanCount = len(traceWithError)
    print(traceWithError.loc[0])
    traceWithError.loc[0,'end'] = traceWithError.loc[0,'duration']

    for i in range(1,spanCount):
      traceWithError.loc[i,'start'] = traceWithError.loc[i,'timestamp'] - traceWithError.loc[0,'timestamp']
      traceWithError.loc[i,'end'] = traceWithError.loc[i,'start'] + (traceWithError.loc[i,'duration'])

    bars = alt.Chart(traceWithError,title="Trace with Errors").mark_bar().encode(
        x='start:Q',
        x2='end:Q',
        y=alt.Y('name:N',sort='x'),
        color=alt.condition(
            alt.datum.error == True,  # If there is an span error this test returns true
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



@app.route("/error_span_durations/<traceID>")
def error_span_durations(traceID):
  traces = load_traces()
  traceWithError = traces.loc[traces['traceId'] == traceID]
  traceWithError = traceWithError.sort_values(by=['traceId','timestamp'],ascending=True).reset_index()
  traceWithErrorSpans = traceWithError.loc[traceWithError['error'] == True]

  traceWithError["start"] = 0
  traceWithError["end"] = 0

  spanCount = len(traceWithError)
  print(traceWithError.loc[0])
  traceWithError.loc[0,'end'] = traceWithError.loc[0,'duration']

  for i in range(1,spanCount):
    traceWithError.loc[i,'start'] = traceWithError.loc[i,'timestamp'] - traceWithError.loc[0,'timestamp']
    traceWithError.loc[i,'end'] = traceWithError.loc[i,'start'] + (traceWithError.loc[i,'duration'])

  #Get list of span service names associated with errors
  error_spans = []
  for i in range(len(traceWithError)):
    if traceWithError.loc[i,'error'] == True:
      error_spans.append(traceWithError.loc[i,'name'])

  #Generate chart with datapoints for span with error
  error_hist = alt.Chart().mark_bar(color='red').encode(
      y=alt.Y('count()', axis=alt.Axis(title='Count')),
      x=alt.X('duration', axis=alt.Axis(title='Span Duration')),
  ).transform_filter(
      (alt.datum.error == True)
  ).transform_filter(
      (alt.datum.traceId == traceID)
  )

  #Generate histogram for all data points 
  hist = alt.Chart().mark_bar().encode(
      y=alt.Y('count()', axis=alt.Axis(title='Count')),
      x=alt.X('duration', axis=alt.Axis(title='Span Duration')),
  ).transform_filter(
      alt.FieldOneOfPredicate(field = 'name', oneOf=error_spans)
  )

  #Layer charts
  chart = alt.layer(hist, error_hist, data = traces).facet('name:N', columns=2).transform_filter(
      alt.FieldOneOfPredicate(field = 'name', oneOf=error_spans)
  ).properties(title="Span Durations with Errors")

  return chart.to_json()

@app.route("/error_span_durations_summary/<traceID>")
def error_span_durations_summary(traceID):
  traces = load_traces()
  traceWithError = traces.loc[traces['traceId'] == traceID]
  traceWithError = traceWithError.sort_values(by=['traceId','timestamp'],ascending=True).reset_index()
  traceWithErrorSpans = traceWithError.loc[traceWithError['error'] == True]

  traceWithError["start"] = 0
  traceWithError["end"] = 0

  spanCount = len(traceWithError)
  print(traceWithError.loc[0])
  traceWithError.loc[0,'end'] = traceWithError.loc[0,'duration']

  for i in range(1,spanCount):
    traceWithError.loc[i,'start'] = traceWithError.loc[i,'timestamp'] - traceWithError.loc[0,'timestamp']
    traceWithError.loc[i,'end'] = traceWithError.loc[i,'start'] + (traceWithError.loc[i,'duration'])

  #Get list of span service names associated with errors
  error_spans = []
  for i in range(len(traceWithError)):
    if traceWithError.loc[i,'error'] == True:
      error_spans.append(traceWithError.loc[i,'name'])

  summaries = []
  for name,duration in zip(traceWithErrorSpans.name,traceWithErrorSpans.duration):
      subset = traces.loc[traces['name'] == name]
      statstr = "%.1f" % (stats.percentileofscore(subset['duration'], duration,kind='weak')) 
      summaries.append(f'{statstr}% of {name} durations are less than the {name} service error.')

  return Response(json.dumps(summaries), mimetype='application/json')

def load_traces():
  traces = pd.read_csv(trace_csv_path)
  traces = traces.sort_values(by=['traceId','timestamp'],ascending=True)
  traces["error"] = traces["tags.error"]

  return traces

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
