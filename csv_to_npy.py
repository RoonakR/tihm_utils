import numpy as np
import pandas as pd
from abc import abstractmethod
import datetime
import sys
from configuration import Conf
import argparse
import os
from util import save_mkdir, save_obj, parser_bool

# TODO
"""
- read clinical data
"""


def get_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='TIHM', help='TIHM | DRI', choices=('TIHM', 'DRI'))
    parser.add_argument('--data_type', type=str, default='env', help='env | clinical', choices=('env', 'clinical'))
    parser.add_argument('--patient_id', type=int, default=None, nargs="+", help='list of patients to read')
    parser.add_argument('--incident', type=str, default='UTI', help='UTI | Agitation | all',
                        choices=('UTI', 'Agitation', 'all'))
    parser.add_argument('--patient_test_date', type=str, default=None, nargs="+", help='infection date')
    parser.add_argument('--verbose', type=bool, default=False, help='insert the patient id and date into the data')
    parser.add_argument('--save_per_patient', type=bool, default=False, help='save the data per patient')
    parser.add_argument('--extract_incident', type=bool, default=False, help='extract incident only')
    parser.add_argument('--save_dir', type=str, default=None, help='folder to save the data')
    parser.add_argument('--label_previous_day', type=bool, default=True,
                        help='label previous day as UTI infection or not')
    parser.add_argument('--split_label', type=bool, default=False,
                        help='split labelled data from unlabelled data or not')
    parser.add_argument('--freq', type=str, default='H', help='frequency to sum the data.')
    parser.add_argument('--extract_uti_phase', type=bool, default=False, help='extract the pre and post phase of UTI')
    parser.add_argument('--test_date', type=str, default=None, help='extract the data after the test date as test '
                                                                    'data, format: year-month-day')

    args = parser.parse_args(argv)
    return args


class Data_loader(object):
    """docstring for Data_loader"""

    def __init__(self, args):
        super(Data_loader, self).__init__()
        print(args)
        self.conf = Conf(args)
        self.args = args
        self.patient_id = args.patient_id
        self.patient_test_date = args.patient_test_date
        self.data = {}
        self.verbose = args.verbose
        self.save_per_patient = args.save_per_patient
        self.extract_incident = args.extract_incident
        self.save_dir = args.save_dir
        self.label_previous_day = args.label_previous_day
        if self.patient_id is not None and self.patient_test_date is None:
            raise ValueError('test date must be provided')
        self.env_feat_list = {
            0: ['Fridge'],
            1: ["living room", 'Lounge'],
            2: ['Bathroom'],
            3: ['Hallway'],
            4: ['Bedroom'],
            5: ['Kitchen'],
            6: ['Microwave', 'Toaster'],
            7: ['Kettle'],
        }
        if args.incident == 'all':
            self.incident = ['UTI symptoms', 'Agitation']
        elif args.incident == 'UTI':
            self.incident = ['UTI symptoms']
        elif args.incident == 'Agitation':
            self.incident = ['Agitation']

        assert not (self.label_previous_day and self.args.extract_uti_phase), 'only one of them can be True'

        path = self.conf.npy_data
        if self.save_dir is not None:
            path = path + '/' + self.save_dir
        save_mkdir(path)

        self.load_env()
        self.save_data()

    def load_body_temp(self, filename, date_his):
        try:
            bt_df = pd.read_csv(self.conf.data_path['clinical'] + filename)
        except KeyError:
            return None
        bodytemp = []
        bt_sub_df = bt_df[bt_df['type'].isin(['bodytemp', 'Body temperature'])]
        bt_date = pd.to_datetime(bt_sub_df['datetimeObserved']).dt.strftime("%Y-%m-%d").to_numpy().tolist()
        bt_date.append(np.nan)
        bt_values = bt_sub_df['value'].astype('float').to_list()

        # If no body temperature is measured, take 37 degree
        if len(bt_values) == 0:
            bt_values = [37.0]
            bt_date.append(np.nan)

        # If no body temperature is measured someday, use the temperature of the nearest day
        bodytemp_idx = 0
        for i in range(len(date_his)):
            if bt_date[bodytemp_idx + 1] == date_his[i]:
                bodytemp_idx += 1
            bodytemp.append(bt_values[bodytemp_idx])

        return bodytemp

    def load_env(self):
        result = []
        bodytemp = []
        label = []
        info_date = []
        info_id = []
        filenames = self._iter_directory(self.conf.data_path['env'])

        for f in filenames:
            if self.patient_id is not None and int(f.split('_')[0]) not in self.patient_id:
                continue
            df = pd.read_csv(self.conf.data_path['env'] + f)

            # Clean the data
            drop_indices = df[df['datetimeObserved'] == 'datetimeObserved'].index
            df = df.drop(drop_indices)
            df['datetimeObserved'] = pd.to_datetime(df['datetimeObserved'])

            # Initialise the data, merge the data per day
            date_his = df["datetimeObserved"].dt.normalize().unique()
            date_his = pd.to_datetime(date_his).strftime("%Y-%m-%d").to_numpy().tolist()
            if self.args.freq == '15min':
                data = np.zeros([len(date_his), 8, 24 * 4])
            elif self.args.freq == 'H':
                data = np.zeros([len(date_his), 8, 24])
            elif self.args.freq == '1min':
                data = np.zeros([len(date_his), 8, 24 * 60])
            else:
                raise NotImplementedError

            for key, values in self.env_feat_list.items():
                for feat in values:
                    # Get the data of specific features
                    indices = df['location'] == feat
                    sub_df = df[indices]
                    if indices.sum() == 0:
                        continue
                    sub_df['value'] = sub_df['value'].astype('float')
                    sub_df = sub_df.groupby(pd.Grouper(key='datetimeObserved', freq=self.args.freq))
                    sub_df = sub_df['value'].agg('sum')

                    # Fill the data into the results
                    sample_index = sub_df.index.strftime("%Y-%m-%d").to_numpy().tolist()
                    hour_index = sub_df.index.time
                    for idx in range(len(sample_index)):
                        try:
                            day = date_his.index(sample_index[idx])
                        except ValueError:
                            pass
                        if self.args.freq == '15min':
                            hour = hour_index[idx].hour * 4 + hour_index[idx].minute // 15
                        elif self.args.freq == 'H':
                            hour = hour_index[idx].hour
                        elif self.args.freq == '1min':
                            hour = hour_index[idx].hour * 60 + hour_index[idx].minute
                        else:
                            raise NotImplementedError
                        data[day][key][hour] += sub_df[idx]

            data = np.array(data)
            bt_data = self.load_body_temp(f, date_his)
            # if self.verbose:
            #    data = [data, date_his, int(f.split('_')[0])]

            if self.patient_id is not None:
                test_id = int(f.split('_')[0])
                self.data[test_id] = []
                cur_date = self.patient_test_date[self.patient_id.index(test_id)]
                for date_time in self.get_consecutive_date(cur_date, 7):
                    day = date_his.index(date_time)
                    self.data[test_id].append((data[day], bt_data[day]))
            elif self.save_per_patient:
                test_id = int(f.split('_')[0])
                if self.extract_incident:
                    patient_label, incident_info = self.load_label(f, date_his)
                    label.append(patient_label)
                    result.append(data)
                    data = data[patient_label < 4 if self.args.extract_uti_phase else patient_label < 2]
                    if np.sum(patient_label < 4 if self.args.extract_uti_phase else patient_label < 2) > 0:
                        incident_info = incident_info[
                            patient_label < 4 if self.args.extract_uti_phase else patient_label < 2]
                        self.data[test_id] = [data, incident_info]
                elif self.verbose:
                    self.data[test_id] = [data, bt_data, date_his, self.load_label(f, date_his)[0]]
                else:
                    self.data[test_id] = [data, date_his]
            else:
                result.append(data)
                l, patient_info = self.load_label(f, date_his)
                label.append(l)
                info_date += patient_info[0]
                info_id += patient_info[1]
                bodytemp.append(bt_data)

        if self.save_per_patient or self.patient_id is not None:
            pass
        elif self.patient_id is None:
            if not self.verbose:
                self.data['env_data'] = np.concatenate(result)
            self.data['_label'] = np.concatenate(label)
            try:
                self.data['bodytemp'] = np.concatenate(bodytemp)
            except ValueError:
                pass
            if self.args.test_date is not None:
                self.data['Patient_id'] = np.array(info_id)
                self.data['Date'] = np.array(info_date)
            if self.args.split_label:
                self.split_label_unlabel()
        if self.args.extract_uti_phase:
            self.data['_label'] = np.concatenate(label)
            self.data['env_data'] = np.concatenate(result)
            self.data['uti_data'] = self.data['env_data'][self.data['_label'] == 1]
            for incident in [2, 3]:
                indices = self.data['_label'] == incident
                self.data['pre_uti' if incident == 2 else 'post_uti'] = self.data['env_data'][indices]


    def save_data(self):
        for key, value in self.data.items():
            if key not in ['env_data', 'bodytemp', '_label']:
                # np.save(self.conf.npy_data + '/' + str(key) + '.npy', value)
                path = self.conf.npy_data
                if self.save_dir is not None:
                    path = path + '/' + self.save_dir
                save_obj(value, path + '/' + str(key))

    def _iter_directory(self, directory):
        file_list = []
        for filename in os.listdir(directory):
            if filename.endswith(".csv") and not filename.startswith("total"):
                file_list.append(filename)
            else:
                continue
        return file_list

    def get_consecutive_date(self, today, date_range, previous_day=True):
        today = datetime.date(*map(int, today.split('-')))
        for i in range(date_range):
            today = today - datetime.timedelta(1) if previous_day else today + datetime.timedelta(1)
            yield str(today)

    @abstractmethod
    def load_label(self, file, date_his):
        pass

    @abstractmethod
    def split_label_unlabel(self):
        pass

    def mark_incident(self, df, p_id):
        # Validated patient symptoms but not occurs in the flag files
        patient_data = {
            1077: [('2020-10-06', True)],
            1313: [('2020-01-24', True), ('2020-10-06', True)],
            1021: [('2020-04-20', True)],
            1126: [('2020-04-20', True)],
            1287: [('2020-10-21', True)],
        }
        # patient_id = [1313, 1021, 1126, ]
        # patient_id = [1313]
        # date = ['2020-01-24', '2020-04-20', '2020-04-20']
        element = 'UTI symptoms'
        flag_type = 'Clinical'
        valid = [True, True, True, True]
        if p_id in patient_data:
            for validation in patient_data[p_id]:
                #  idx = patient_id.index(p_id)
                df.loc[len(df)] = ['test', validation[0], element, flag_type, validation[1]]
        return df


class Env_loader(Data_loader):
    """docstring for DRI_dataloader	"""

    def __init__(self, args):
        super(Env_loader, self).__init__(args)

    def load_label(self, file, date_his):
        """
        0 - False
        1 - True
        2 - days before uti infections
        3 - days after uti infections
        4 - not valid
        5 - Test samples
        """
        filename = list(file)
        filename = ''.join(filename)
        p_id = filename.split('_')[0]
        filename = filename.split('_')[0] + '_flags.csv'
        sub_key = 'datetimeObserved'
        label_df = pd.read_csv(self.conf.data_path['flag'] + filename)
        label_df = self.mark_incident(label_df, int(file.split('_')[0]))
        label = np.zeros(len(date_his)) + 4
        patient_info = [date_his, [p_id] * len(date_his)]
        if self.args.test_date is not None:
            test_indices = pd.to_datetime(date_his) > self.args.test_date
            label[test_indices] = 5

        incident_info = [[None, None, None]] * len(label)
        indices = label_df['element'].isin(self.incident)
        if len(indices) > 0:
            sub_df = label_df[indices]
            dates = pd.to_datetime(sub_df[sub_key]).dt.strftime("%Y-%m-%d").to_numpy().tolist()
            valid = sub_df['valid'].tolist()
            for d in range(len(dates)):
                today = dates[d]
                get_idx = True
                while get_idx:
                    try:
                        idx = date_his.index(today)
                        get_idx = False
                    except ValueError:
                        today = next(self.get_consecutive_date(today, 1))
                try:
                    validation = parser_bool(valid[d])
                    if validation is None:
                        label[idx] = 4
                    else:
                        settings = self.conf.reading_settings(validation)
                        label[idx] = settings['label']
                        incident_info[idx] = [dates[d], sub_df['element'].to_numpy()[d], settings['label'],
                                              int(file.split('_')[0])]
                        if self.incident == ['UTI symptoms'] and self.label_previous_day:
                            for flag in [True, False]:  # consecutive_label
                                for new_day in self.get_consecutive_date(dates[d],
                                                                         settings['extend_label_range'], flag):
                                    try:
                                        new_idx = date_his.index(new_day)
                                        label[new_idx] = settings['label']
                                        incident_info[new_idx] = [new_day, sub_df['element'].to_numpy()[d],
                                                                  settings['label'], int(file.split('_')[0])]
                                    except ValueError:
                                        pass
                        if self.incident == ['UTI symptoms'] and self.args.extract_uti_phase:
                            uti_flags = [True, False]  # True: previous days, False: following days
                            for date_flag in uti_flags:
                                for idx, new_day in enumerate(
                                        self.get_consecutive_date(dates[d], settings['uti_pre_post_range'],
                                                                  previous_day=date_flag)):
                                    try:
                                        new_idx = date_his.index(new_day)
                                        label[new_idx] = 1 if idx < settings['extra_uti_range'] - 1 else 2 + int(
                                            date_flag)
                                        incident_info[new_idx] = [new_day, str(label[new_idx]) +
                                                                  sub_df['element'].to_numpy()[d],
                                                                  settings['label'], int(file.split('_')[0])]
                                    except ValueError:
                                        pass

                except KeyError:
                    pass

        if self.extract_incident:
            return label, np.array(incident_info)
        return label, patient_info

    def split_label_unlabel(self):
        indices = self.data['_label'] == 4
        self.data['unlabel_env'] = self.data['env_data'][indices]
        try:
            self.data['unlabel_bodytemp'] = self.data['bodytemp'][indices]
        except KeyError:
            pass

        indices = self.data['_label'] < 2
        self.data['label_env'] = self.data['env_data'][indices]
        try:
            self.data['label_bodytemp'] = self.data['bodytemp'][indices]
        except KeyError:
            pass
        self.data['label'] = self.data['_label'][indices]

        if self.args.test_date is not None:
            indices = self.data['_label'] == 5
            self.data['test_data'] = [self.data['env_data'][indices], self.data['Patient_id'][indices],
                                      self.data['Date'][indices]]
            try:
                self.data['test_body_temperature'] = self.data['bodytemp'][indices]
            except KeyError:
                pass


if __name__ == '__main__':
    args = get_args(sys.argv[1:])
    dataloader = Env_loader(args)
