#!/usr/bin/env python3

import argparse
import json
import pandas as pd
import pathlib
import sys

from os import listdir
from os.path import isfile, join


parser = argparse.ArgumentParser(description='Convert zipkin2 json traces into csv.')
parser.add_argument('source_json', 
                    type=pathlib.Path,
                    help='A file containing zipkin json.')
parser.add_argument('dest_csv', 
                    type=pathlib.Path,
                    help='The target CSV file.')
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
        thisDirectory = dir_path + '/' + directory
        print(thisDirectory)
        data = import_file(thisDirectory)
        traces.append(data)

    traces_df = pd.concat(traces, axis=0)

def save_as_csv(traces_df, csv_path):
    traces_df.to_csv(path_or_buf = csv_path)


if args.source_json.exists():
    traces = None
    if args.source_json.is_dir():
        traces = import_directory(args.source_json)
    else:
        traces = import_file(args.source_json)

    traces = traces.sort_values(by=['traceId','timestamp'],ascending=True)
    traces["error"] = traces["tags.error"]
    
    save_as_csv(traces, args.dest_csv)
else:
    print(f'File {args.source_json} does not exist, exiting.')
