from util import parser_bool


class Conf(object):
    def __init__(self, args):
        self.args = args
        self.dataset = args.dataset

    def _set_path(self, dataset_type):
        if self.dataset == 'TIHM':
            return './{}/tihm15'.format(dataset_type)
        elif self.dataset == 'DRI':
            return './{}/tihmdri'.format(dataset_type)

    @property
    def raw_data(self):
        return self._set_path('raw_data')

    @property
    def csv_data(self):
        return self._set_path('csv_data')

    @property
    def npy_data(self):
        return self._set_path('npy_data')

    @property
    def data_path(self):
        data_path = {
            'env': self._set_path('csv_data') + '/env/data/',
            'flag': self._set_path('csv_data') + '/env/flag/',
            'clinical': self._set_path('csv_data') + '/clinical/data/',
        }
        return data_path

    def reading_settings(self, validation):
        validation = parser_bool(validation)
        return {
            'label': True if validation else False,
            'extend_label_range': 1 if validation else 1,
            'valid': True if validation else False,
            'uti_pre_post_range': 3 if validation else 3,  # 10 days: 15,
            'extra_uti_range': 1 if validation else 1,  # 10 days: 5,
        }


# Validated UTI, may not in the flags files

def validated_date():
    patient_data = {
        1077: [('2020-10-06', True), ('2020-11-17', True)],
        1313: [('2020-01-24', True), ('2020-10-06', True)],
        1021: [('2020-04-20', True)],
        1126: [('2020-04-20', True)],
        1287: [('2020-10-21', True)],

    }
    return patient_data
