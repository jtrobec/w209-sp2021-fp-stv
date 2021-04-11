#!/usr/bin/env python3

import argparse
import json
import numpy as np
import pandas as pd
import pathlib
import sys

from os import listdir
from os.path import isfile, join

# parse command line arguments
parser = argparse.ArgumentParser(description='Convert zipkin2 json traces into csv.')
parser.add_argument('source_json', 
                    type=pathlib.Path,
                    help='A file containing zipkin json.')
parser.add_argument('dest_errors_csv', 
                    type=pathlib.Path,
                    help='The target errors CSV file.')
parser.add_argument('dest_waterfall_csv', 
                    type=pathlib.Path,
                    help='The target waterfall CSV file.')
args = parser.parse_args()


def import_file(file_path):
    data = None
    print(f'Loading traces from: {file_path}')

    try:
        with open(file_path) as f:
          data = pd.json_normalize(json.load(f))
    except OSError:
        print(f'Cannot open file: {file_path}')
    except:
        print(f'Unexpected exception loading json file: {sys.exc_info()[0]}')

    return data

def import_directory(dir_path):
    directories = listdir(dir_path)

    traces = []
    for directory in directories:
        this_directory = dir_path + '/' + directory
        print(this_directory)
        data = import_file(this_directory)
        traces.append(data)

    traces_df = pd.concat(traces, axis=0)
    return traces_df

def save_as_csv(traces_df, csv_path):
    traces_df.to_csv(path_or_buf = csv_path)

def preprocess_errors(traces):
    sorted_traces = traces.copy(deep=True)
    sorted_traces.sort_values(by=['traceId','timestamp'],ascending=True)
    sorted_traces["error"] = sorted_traces["tags.error"]
    return sorted_traces

def preprocess_waterfall(file_path):
    print(f'Loading traces from: {file_path}')

    try:
        with open(file_path) as f:
          data = json.load(f)
    except OSError:
        print(f'Cannot open file: {file_path}')
    except:
        print(f'Unexpected exception loading json file: {sys.exc_info()[0]}')
    traces = data

    names, durations, traceIDs, parentIDs, ids, traceErrors = [], [], [], [], [], []

    for element in traces:
        traceIDs.append(element['traceId'])
        ids.append(element['id'])
        try:
            parentIDs.append(element['parentId'])
        except:
            parentIDs.append('Na')
        try:
            traceErrors.append(element['tags']['error'])
        except:
            traceErrors.append('false')
            
        names.append(element['name'])
        durations.append(element['duration'])

    traceDf = pd.DataFrame({'Resource Name' : names,
                            'Duration':durations, 
                            'Trace_ID': traceIDs, 
                            'ID': ids, 
                            'Parent_ID': parentIDs, 
                            'Error?':traceErrors})
    
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

        tes
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

if args.source_json.exists():
    traces = None
    if args.source_json.is_dir():
        traces = import_directory(args.source_json)
    else:
        traces = import_file(args.source_json)

    traces_errors = preprocess_errors(traces)
    save_as_csv(traces_errors, args.dest_errors_csv)

    traces_aggs = preprocess_waterfall(args.source_json)
    save_as_csv(traces_aggs, args.dest_waterfall_csv)

else:
    print(f'File {args.source_json} does not exist, exiting.')
