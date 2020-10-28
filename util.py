import os
import pickle


def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open(name, 'rb') as f:
        return pickle.load(f)


def save_mkdir(path):
    try:
        os.stat(path)
    except:
        os.mkdir(path)


def parser_bool(flag):
    if flag == 'True' or True:
        return True
    elif flag == 'False' or False:
        return False
    return None
