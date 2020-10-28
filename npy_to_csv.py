"""
Convert npy files to csv for clinical analysation

Currently support:
    - extract incident with True (in csv_to_npy.py)

Input Data structure:
    A list contains two arrays
    - [data, info]
        -> data shape (N, 8, 24)
        -> info shape contains [date, symptoms, validation]
"""

import os
import pandas as pd
from util import save_mkdir, save_obj, load_obj


def _iter_directory(directory):
    file_list = []
    for filename in os.listdir(directory):
        if filename.endswith(".pkl") and not filename.startswith("total"):
            file_list.append(filename)
        else:
            continue
    return file_list

def _iter_csv(directory):
    file_list = []
    for filename in os.listdir(directory):
        if filename.endswith(".csv") and not filename.startswith("total"):
            file_list.append(filename)
        else:
            continue
    return file_list


def to_separate_csv():
    DIRPATH = './npy_data/tihm15/Agitation_mike/'
    SAVE_PATH = './csv_data/analysation/mike/agitation/'
    INDEX = ['Fridge',
             'living room',
             'Bathroom',
             'Hallway',
             'Bedroom',
             'Kitchen',
             'Microwave',
             'Kettle']

    filenames = _iter_directory(DIRPATH)
    data = []
    info = []
    for f in filenames:
        a = load_obj(DIRPATH + f)
        data.append(a[0])
        info.append(a[1])

    for i, patient in enumerate(info):
        for j, day in enumerate(patient):
            filename = filenames[i].split('.')[0] + '_' + day[0] + '_' + str(day[2]) + '.csv'
            p_data = data[i][j]
            df = pd.DataFrame(p_data, index=INDEX)
            df.to_csv(SAVE_PATH + filename)


def to_one_csv():
    DIRPATH = ['./npy_data/tihm15/UTI_mike/', './npy_data/tihmdri/UTI_test/']
    SAVE_PATH = './csv_data/one_csv/data.csv'
    data = {'Patient_id': [], 'Date':[], 'Symptoms':[], 'Validation': []}
    for path in DIRPATH:
        filenames = _iter_directory(path)
        for f in filenames:
            validations = load_obj(path + f)
            for valid in validations[1]:
                data['Patient_id'].append(f.split('.')[0])
                data['Date'].append(valid[0])
                data['Symptoms'].append(valid[1])
                data['Validation'].append(valid[2])
    df = pd.DataFrame(data)
    df.to_csv(SAVE_PATH)


def check_data():
    DIRPATH = './csv_data/tihmdri/env/data/'
    filenames = _iter_csv(DIRPATH)
    for f in filenames:
        data = pd.read_csv(DIRPATH + f)
        data['datetimeObserved'] = pd.to_datetime(data['datetimeObserved'])
        try:
            if f.split('_')[0] in ['1313', '1077']:
                print(f, sorted(data['datetimeObserved'])[-1])
        except IndexError:
            pass

to_one_csv()