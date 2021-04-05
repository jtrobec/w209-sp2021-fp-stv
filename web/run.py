import pandas as pd
import altair as alt
import json

from scipy import stats
from flask import Flask, request, send_from_directory

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

@app.route("/error_chart/<id>")
def error_chart(id):
    #trace_json = load_trace(id)
    #return jchart_build(trace_json)
    pass

if __name__ == "__main__":
  app.run(debug=True)
