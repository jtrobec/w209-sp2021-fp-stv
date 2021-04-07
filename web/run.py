import altair as alt
import numpy as np
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

def get_john_trace_df():
  traces = load_traces()
  names = []
  durations = []
  traceIDs = []
  parentIDs = []
  ids = []
  traceErrors = []
  for index, row in traces.iterrows():
    traceIDs.append(row['traceId'])
    ids.append(row['id'])
    try:
        parentIDs.append(row['parentId'])
    except:
        parentIDs.append('Na')
    try:
        traceErrors.append(row['tags']['error'])
    except:
        traceErrors.append('false')
              
    names.append(row['name'])
    durations.append(row['duration'])

  traceDf = pd.DataFrame({'Resource Name' : names, 'Duration':durations, 'Trace_ID': traceIDs, 'ID': ids, 'Parent_ID': parentIDs, 'Error?':traceErrors})
  traceSum = 0 
  currTraceID = ''
  duration_starts = []
  duration_ends = []
  duration_start = 0
  duration_end = 0
  for i in range(len(traceDf)):
      val = traceDf.iloc[i]
      if val['Trace_ID'] != currTraceID:
          duration_start = 0
          currTraceID = val['Trace_ID']
      else:
          duration_start = duration_end
      duration_end = duration_start +  val['Duration']
      duration_starts.append(duration_start)
      duration_ends.append(duration_end)
  traceDf['duration_start'] = duration_starts
  traceDf['duration_end'] = duration_ends
  traceDf['Data Transfered'] = [round(np.random.uniform(4,10000),1) for i in range(len(traceDf))]
  updatedTraces = pd.DataFrame()
  for traceID in set(traceDf['Trace_ID']):
    tes = traceDf[traceDf['Trace_ID'] == traceID]
    root = list(tes['Trace_ID'])[0]
    tes['order'] = [100 for x in range(len(tes))]
    tes['loc start'] = [100 for x in range(len(tes))]
    tes['loc end'] = [100 for x in range(len(tes))]

    order = []
    root = list(tes['Trace_ID'])[0]
    startLoc = 0
    order = 0
    for i in range(len(tes)):
        t = tes.iloc[i]
        if t['ID'] == root:
            t['order'] = order
            t['loc start'] = startLoc
            t['loc end'] = t['loc start'] + t['Duration']
            tes.iloc[i] = t
    c = 0
    currentRoot = root
    startLoc += 100000
    lastRoot = root
    lastRoots = []
    while c < len(tes) - 1:
        startLoc = tes[tes['ID'] == currentRoot]['loc start'] + 100000
        order = tes[tes['ID'] == currentRoot]['order']
        for i in range(len(tes)):
            t = tes.iloc[i]
            if t['Parent_ID'] == currentRoot:
                t['order'] = order + .5
                order = order + 1
                t['loc start'] = startLoc
                t['loc end'] = t['loc start'] + t['Duration']
                tes.iloc[i] = t
                lastRoots.append(t['ID'])
                c += 1
        currentRoot = lastRoots.pop(0)
        updatedTraces = updatedTraces.append(tes)
  return updatedTraces

def plotTrace(traceID, traceDf):
    source = traceDf[traceDf['Trace_ID'] == traceID]
    return alt.Chart(source, title='Trace: ' + traceID).mark_bar().encode(
        y=alt.Y('Resource Name', type='nominal', sort=None),
        x = alt.X("duration_start:Q", title= "Duration"),
        x2 = "duration_end:Q",
        color = 'Resource Name:N',
        tooltip = ['Duration:Q', 'Data Transfered:Q','Error?:N']
    )

def plotTraceTree(traceID, traceDf):
    source = traceDf[traceDf['Trace_ID'] == traceID]
    return alt.Chart(source, title='Trace: ' + traceID).mark_bar().encode(
        y=alt.Y('Resource Name', type='nominal', sort=alt.SortField('order')),
        x = alt.X("loc start:Q", title= "Duration"),
        x2= "loc end:Q",
        color = 'Resource Name:N',
        tooltip = ['ID:N', 'Parent_ID:N', 'Duration:Q','Error?:N']
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
