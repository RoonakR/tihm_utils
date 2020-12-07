import pandas as pd
import sys
from configuration import Conf
import argparse
from copy import deepcopy
from util import save_mkdir


def get_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='TIHM', help='TIHM | DRI', choices=('TIHM', 'DRI'))
    parser.add_argument('--data_type', type=str, default='env', help='env | clinical', choices=('env', 'clinical'))
    args = parser.parse_args(argv)
    return args


def split_data(args):
    data_type = args.data_type
    conf = Conf(args)
    base_path = conf.raw_data
    save_path = conf.csv_data
    save_mkdir(save_path + '/' + data_type + '/data/')
    save_mkdir(save_path + '/' + data_type + '/flag/')

    patients = pd.read_csv(base_path + '/Patients.csv')
    ids = patients['subjectId']
    id_index = patients['sabpId']
    a = id_index[ids == ids[0]]

    observ_types = pd.read_csv(base_path + '/Observation-type.csv')
    types = {}
    for i in range(0, len(observ_types)):
        types[observ_types.loc[i]['code']] = observ_types.loc[i]['display']

    observ_devices = pd.read_csv(base_path + '/Observation-device.csv')
    devices = {}
    for i in range(0, len(observ_devices)):
        devices[observ_devices.loc[i]['code']] = observ_devices.loc[i]['display']

    observ_locs = pd.read_csv(base_path + '/Observation-location.csv')
    locs = {}
    for i in range(0, len(observ_locs)):
        locs[observ_locs.loc[i]['code']] = observ_locs.loc[i]['display']

    data = pd.read_csv(base_path + '/observations.csv')
    if data_type == 'env':
        data = data.loc[data['device'] == 408746007]  # env
    elif data_type == 'clinical':
        data = data.loc[data['device'] != 408746007]  # Clinical

    data['datetimeObserved'] = pd.to_datetime(data['datetimeObserved'])
    data_new = pd.DataFrame(columns=['subject', 'datetimeObserved', 'type', 'location', 'value'])
    data_new['subject'] = data['subject']
    data_new['datetimeObserved'] = data['datetimeObserved']
    data_new['type'] = data['type'].map(types)
    data_new['location'] = data['location'].map(locs)

    if data_type == 'env':
        data_new['value'] = data['valueBoolean']
        data_new = data_new.loc[data_new['type'].isin(['Movement', 'Door', 'Does turn on domestic appliance', 'Light'])]
        bools = {True: 1, False: 0}
        data_new['value'] = data_new['value'].map(bools)
    elif data_type == 'clinical':
        data_new['value'] = data['valueQuantity']
        data_new = data_new[data_new.value.notna()]

    for i in range(0, len(ids)):
        idx = ids[i]
        name_data = str(id_index[idx == ids][i]) + "_observation.csv"
        if data_type == 'env':
            d = data_new.loc[data_new['subject'] == idx, ['datetimeObserved', 'location', 'value']]
        elif data_type == 'clinical':
            d = data_new.loc[data_new['subject'] == idx, ['datetimeObserved', 'type', 'value']]
        d.to_csv(save_path + '/' + data_type + '/data/' + name_data)

    env_data = deepcopy(data_new)
    #if data_type == 'clinical':
    #    return
    d = pd.read_csv(base_path + '/Flag-category.csv')
    flag_types = {}
    for i in range(0, len(d)):
        flag_types[d.loc[i]['code']] = d.loc[i]['display']
    d = pd.read_csv(base_path + '/Flag-type.csv')
    flag_elements = {}
    for i in range(0, len(d)):
        flag_elements[d.loc[i]['code']] = d.loc[i]['display']
    data = pd.read_csv(base_path + '/Flags.csv')
    data['datetimeRaised'] = pd.to_datetime(data['datetimeRaised'])
    data_new = pd.DataFrame(columns=['flagId', 'subject', 'datetimeObserved', 'element', 'type'])
    data_new['subject'] = data['subject']
    data_new['datetimeObserved'] = data['datetimeRaised']
    data_new['type'] = data['category'].map(flag_types)
    data_new['element'] = data['type'].map(flag_elements)
    data_new['flagId'] = data['flagId']
    d = pd.read_csv(base_path + '/FlagValidations.csv')
    val_df = pd.DataFrame(columns=['flagId', 'valid'])
    val_df['flagId'] = d['flag']
    val_df['valid'] = d['valid']
    data_new = pd.merge(data_new, val_df, on='flagId')
    flag_data = deepcopy(data_new)
    for i in range(0, len(ids)):
        idx = ids[i]
        name_data = str(id_index[idx == ids][i]) + "_flags.csv"
        d = data_new.loc[data_new['subject'] == idx, ['datetimeObserved', 'element', 'type', 'valid']]
        d.to_csv(save_path + '/' + data_type + "/flag/" + name_data)

    summation = []
    for i in range(0, len(ids)):
        idx = ids[i]
        name_data = str(id_index[idx == ids][i]) + "obs_flag.csv"
        f_data = flag_data.loc[flag_data['subject'] == idx, ['datetimeObserved', 'element', 'type', 'valid']]
        e_data = env_data.loc[env_data['subject'] == idx, ['datetimeObserved', 'location', 'value']]
        f_data['datetimeObserved'] = f_data['datetimeObserved'].dt.date
        e_data['date'] = e_data['datetimeObserved'].dt.date
        e_data = e_data.loc[e_data['date'].isin(f_data['datetimeObserved'])]
        e_data['Patient id'] = int(id_index[idx == ids][i])
        e_data['element'] = None
        e_data['type'] = None
        e_data['valid'] = None
        for sub_date in f_data['datetimeObserved']:
            e_data.loc[e_data['date'] == sub_date, 'element'] = f_data.loc[f_data['datetimeObserved'] == sub_date][
                'element'].values[0]
            e_data.loc[e_data['date'] == sub_date, 'type'] = f_data.loc[f_data['datetimeObserved'] == sub_date][
                'type'].values[0]
            e_data.loc[e_data['date'] == sub_date, 'valid'] = f_data.loc[f_data['datetimeObserved'] == sub_date][
                'valid'].values[0]
        summation.append(e_data)
        # e_data.to_csv(save_path + '/' + data_type + "/all_in_one/" + name_data)
    summation = pd.concat(summation)
    summation.to_csv(save_path + '/' + data_type + "/merged.csv")


if __name__ == '__main__':
    args = get_args(sys.argv[1:])
    split_data(args)
    args.data_type = 'env'
    split_data(args)
