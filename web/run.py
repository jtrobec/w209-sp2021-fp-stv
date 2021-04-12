import altair as alt
import numpy as np
import pandas as pd
import json

from flask import Flask, request, Response, send_from_directory
from flask_caching import Cache
from flask_compress import Compress
from os import listdir
from os.path import dirname, isfile, join, realpath
from scipy import stats


# set the project root directory as the dist folder
app = Flask(__name__)
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})

cache.init_app(app)
Compress(app)

app_dir = dirname(realpath(__file__))
data_dir = join(app_dir, '../data')
dist_dir = join(app_dir, 'dist')
trace_csv_path = join(data_dir, 'synthetic', '20210409-hipster-shop-sl.csv')
trace_csv_path_john = join(data_dir, 'synthetic', '20210409-hipster-shop-sl-single.csv')
trace_csv_path_agg = join(data_dir, 'synthetic', '20210409-hipster-shop-sl-agg.csv')
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

@cache.cached(timeout=3000, key_prefix='john_trace')
def get_john_trace_df():
  return pd.read_csv(trace_csv_path_john)

def get_john_trace_df_agg():
  return pd.read_csv(trace_csv_path_agg)

def plotTrace(traceID, traceDf):
    source = traceDf[traceDf['Trace_ID'] == traceID]
    return alt.Chart(source, title='Waterfall View Trace: ' + traceID).mark_bar().encode(
        y=alt.Y('Resource Name', title ='Span Name', type='nominal', sort=None),
        x = alt.X("duration_start:Q", title= "Duration"),
        x2 = "duration_end:Q",
        color = alt.Color('Error?:N',legend =None),
        tooltip = ['Duration:Q', 'Data Transfered:Q','Error?:N']
    )

def plotTraceTree(traceID, traceDf):
    source = traceDf[traceDf['Trace_ID'] == traceID]
    bars = alt.Chart(source, title='Tree View Trace: ' + traceID).mark_bar().encode(
        y=alt.Y('order:N', title='Resource Name', axis = None),
        x = alt.X("loc start:Q", title= "Duration"),
        x2= "loc end:Q",
        color = alt.Color('depth:Q',sort='descending', legend = alt.Legend(title = 'Tree Depth')),
        tooltip = ['ID:N', 'Parent_ID:N', 'Duration:Q','Error?:N']
    )

    text = alt.Chart(source).mark_text(
        align='right'
    ).encode(
        y=alt.Y('order:N',title='Span Name', axis = None),
        x=alt.value(-3),
        text='Resource Name:N',
    )
    return bars + text

def plotTraceAgg(traceType,traceDf ):
    source = traceDf[traceDf ['root'] == traceType]
    return alt.Chart(source, title='Aggregate Trace: ' + traceType).mark_bar().encode(
        y=alt.Y('Resource Name',title ='Span Name', type='nominal', sort=alt.SortField('Average order')),
        x = alt.X("Average loc start:Q", title= "Duration"),
        x2 = "Average loc end:Q",
        color = alt.Color('Error Rate:Q',sort='ascending'),
        tooltip = ['Average Duration:Q', 'Average Data Transfered:Q', 'Error Rate:Q']
    )

@app.route("/trace_chart/<traceID>")
def trace_chart(traceID):
  traceDf = get_john_trace_df()
  chart = plotTrace(traceID, traceDf)
  return chart.to_json()

@app.route("/trace_tree_chart/<traceID>")
def trace_tree_chart(traceID):
  traceDf = get_john_trace_df()
  chart = plotTraceTree(traceID, traceDf)
  return chart.to_json()

@app.route("/trace_tree_chart_agg/frontend/<traceType>")
def trace_tree_chart_agg(traceType):
  traceType = "/" + traceType
  print(traceType)
  traceDf = get_john_trace_df_agg()
  chart = plotTraceAgg(traceType, traceDf)
  return chart.to_json()

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
    traceWithError.loc[0,'end'] = traceWithError.loc[0,'duration']

    for i in range(1,spanCount):
      traceWithError.loc[i,'start'] = traceWithError.loc[i,'timestamp'] - traceWithError.loc[0,'timestamp']
      traceWithError.loc[i,'end'] = traceWithError.loc[i,'start'] + (traceWithError.loc[i,'duration'])

    bars = alt.Chart(traceWithError,title="Waterfall Trace View").mark_bar().encode(
        x=alt.X('start:Q', title="Start,End"),
        x2=('end:Q'),
        y=alt.Y('name:N',sort='x',title="Span"),
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
        (alt.datum.error == True)
    )


    color=alt.condition(
        alt.datum.error == True,  # If there is an span error this test returns true
        alt.value('red'),     # which sets the bar orange.
        alt.value('steelblue')   # And if it's not true it sets the bar steelblue.
    )

    legend = alt.Chart(traceWithError).mark_point().encode(
        y=alt.Y('error:N', axis=alt.Axis(orient='right'),title="Has Error"),
        color=color
    )

    combined = bars + point | legend

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

  #Generate histogram for all data points
  hist = alt.Chart().mark_bar().encode(
      y=alt.Y('count()', axis=alt.Axis()),
      x=alt.X('duration', axis=alt.Axis(title='Span Duration')),
  ).transform_filter(
      alt.FieldOneOfPredicate(field = 'name', oneOf=error_spans)
  )

 #Generate chart with datapoints for span with error
  error_hist = alt.Chart().mark_bar(color='red').encode(
    y=alt.Y('count()', axis=alt.Axis(title='Count of Spans',format=".0f",tickMinStep=1)),
    x=alt.X('duration', axis=alt.Axis(title='Span Duration')),
    tooltip=['duration','error']
  ).interactive().transform_filter(
    (alt.datum.error == True)
  ).transform_filter(
    (alt.datum.traceId == traceID)
  )

  summaries = []
  charts = []
  for name,duration in zip(traceWithErrorSpans.name,traceWithErrorSpans.duration):
    subset = traces.loc[traces['name'] == name]
    chart = alt.layer(hist, error_hist, data = subset).properties(title=name + " Span Durations")
    percentage = ("%.1f" % (100-(stats.percentileofscore(subset['duration'], duration,kind='weak'))))
    summary = f"{percentage}% of all {name} span durations are greater than the {name} span that errored in Trace ID: {traceID}."
    summaries.append(summary)
    chart = alt.layer(hist, error_hist, data = subset).properties(title=summary)
    charts.append(chart)

  #for i in range(len(charts)):
    #  return charts[0].to_json() |
  stackCharts = alt.vconcat(*charts)
  return stackCharts.to_json()

@cache.cached(timeout=3000, key_prefix='load_traces')
def load_traces():
  traces = pd.read_csv(trace_csv_path)
  return traces


if __name__ == "__main__":
  app.run(debug=True)
