create the directory tree like this
```
|`- root
    |` - python files
    |`- raw_data
        |`- tihm15
        |`- tihmdri
    |`- npy_data
        |`- tihm15
        |`- tihmdri
    |`- csv_data
        |`- tihm15
            |`- env
            |`- clinical
        |`- tihmdri
            |`- env
            |`- clinical
```
run
`python split_raw_to_csv.py` to split the raw data into data per patient. It can read the environmental and clinical data. Thanks for Ronnak's help.

run `python csv_to_npy.py` to process and convert the csv data into npy data. It can split the test patient out of the data, save data per patient, save data 
by UTI/Agitation/All. 

Use `python split_raw_to_csv.py / csv_to_npy.py -h` to check the details.

