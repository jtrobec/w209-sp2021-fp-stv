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
parser.add_argument('dest_aggs_csv', 
                    type=pathlib.Path,
                    help='The target aggs CSV file.')
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

def load_waterfall_df(file_path):
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

    return pd.DataFrame({'Resource Name' : names,
                            'Duration':durations, 
                            'Trace_ID': traceIDs, 
                            'ID': ids, 
                            'Parent_ID': parentIDs, 
                            'Error?':traceErrors})

def preprocess_waterfall(file_path):
    traceDf = load_waterfall_df(file_path)
    
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
    updatedTraces['depth'] = updatedTraces['loc start']//100000
    return updatedTraces

def process_aggs(waterfall_df):
    rootTraces = waterfall_df[waterfall_df['Parent_ID'] == 'Na']
    roots = list(set(rootTraces['Resource Name']))
    avgDurations = []
    errorPercentage = []
    aggregateTraceDf = pd.DataFrame()
    for root in roots:
        traces = rootTraces[rootTraces['Resource Name'] == root]
        ids = list(set(traces['Trace_ID']))
        waterfall_df['keep'] = [True if x in ids else False for x in waterfall_df['Trace_ID']]
        thisRootTraces = waterfall_df[waterfall_df['keep']]
        thisRootTraces['intErrors?'] = [1 if x =='true' else 0 for x in thisRootTraces['Error?']]
        grouped = thisRootTraces.groupby('Resource Name').agg({'Duration': ['mean'], 'intErrors?':['sum','count'], 'Data Transfered':['mean'], 'loc start': 'mean','loc end': 'mean', 'order':'mean' })
        grouped = grouped.reset_index()
        grouped['root'] = [root] * len(grouped)
        cols = []
        for x in grouped.columns:
            if x[1] =='mean':
                grouped[x] = round(grouped[x],1)
                cols.append('Average ' + x[0])
            elif x[1] != '':
                cols.append(x[1])
            else:
                cols.append(x[0])
        grouped.columns = cols
        grouped['Error Rate'] = round(grouped['sum']/grouped['count'],3)
        grouped = grouped.rename(columns = {'mean': 'Average Duration', 'count':'Error Count'})
        cols = ['root','Resource Name', 'Average Duration','Error Count','Error Rate','Average Data Transfered', 'Average loc start', 'Average loc end',
            'Average order']
        grouped = grouped[cols]
        aggregateTraceDf = aggregateTraceDf.append(grouped)
    return aggregateTraceDf

if args.source_json.exists():
    traces = None
    if args.source_json.is_dir():
        traces = import_directory(args.source_json)
    else:
        traces = import_file(args.source_json)

    traces_errors = preprocess_errors(traces)
    save_as_csv(traces_errors, args.dest_errors_csv)

    traces_wf = preprocess_waterfall(args.source_json)
    save_as_csv(traces_wf, args.dest_waterfall_csv)

    aggs_df = process_aggs(traces_wf)
    save_as_csv(aggs_df, args.dest_aggs_csv)

else:
    print(f'File {args.source_json} does not exist, exiting.')
