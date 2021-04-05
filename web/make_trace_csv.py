#!/usr/bin/env python3

import json
from os import listdir
from os.path import isfile, join
import pandas as pd

baseDirectory = '../data/synthetic/20210302-hipster-shop'
directories = listdir(baseDirectory)

traces = []
for directory in directories:
    thisDirectory = baseDirectory + '/' + directory
    print(thisDirectory)
    try:
        with open(thisDirectory) as f:
          data = pd.json_normalize(json.load(f))
    except:
        print('err')
        continue
    traces.append(data)

traces_df = pd.concat(traces, axis=0)

traces_df.to_csv(path_or_buf = '../data/synthetic/20210302-hipster-shop.csv')
