import pandas as pd
import json
from model import LLM
import sqlite3


class Schema():

    def __init__(self, schema, type = 'csv'):

        self.schema = schema
        self.format_type = type
        if self.format_type == 'sqlite':
            self.connection = sqlite3.connect('outputs/sqlite_database.db')
            self.cursor = self.connection.cursor()

    def __call__(self, json_data):

        if self.schema == 'i2b2':
            return self.i2b2_schema(json_data)
        if self.schema == 'default':
            return self.default_schema(json_data)

        else:
            raise NotImplementedError()

    def default_schema(self, json_data):

            
        self.output_format(json_data)



    def i2b2_schema(self, json_data):

        output_data = []
        for item in json_data:
            tmp = []
            value, route, freq = item.get('value', None), item.get('route', None), item.get('freq', None)
            template = {
                'patient_num': item.get('patient_num', None),
                'birth_date': item.get('birth_date', None),
                'death_date': item.get('death_date', None),
                'sex_cd': item.get('gender', None),
                'race_cd': item.get('race', None),
                'ethnicity_cd': item.get('ethnicity', None),
                'zip_cd': item.get('zip_code', None),
                'encounter_num': item.get('key', None),
                'start_date': item.get('begin_date', None),
                'end_date': item.get('end_date', None),
                'concept_cd': item.get('code', None),
                'name_char': item.get('mention', None),
                'observation_blob': item.get('context', None), # Holds any raw or miscellaneous data that exists, often encrypted PHI or additional information in a parseable format like XML
                
                'modifier_cd': item.get('patient_num', '@'), # Code for modifier of interest (i.e. "ROUTE", "DOSE"). Note that the value columns are often used to hold the amounts such as "100" (mg) for the modifier of DOSE or "PO" for the modifier of ROUTE.
                
                'instance_num': 1 + (value != None) + (route != None) + (freq != None), # Encoded instance number that allows more than one modifier to be provided for each CONCEPT_CD. Each row will have a different MODIFIER_CD but a similar INSTANCE_NUM.
                
                'valtype_cd': None, # N = Numeric, T = Text (enums / short messages), B = Raw Text (notes / reports)
                'tval_char': None, # Stores the text value of the value Used in conjunction with VALTYPE_CD = "T" or "N"
# When the VALTYPE_CD = "T"
# Stores the text value

# When VALTYPE_CD = "N"
# E = Equals
# NE = Not equal
# L = Less than
# LE = Less than and Equal to
# G = Greater than
# GE = Greater than and Equal to
                'nval_num': None, # Used in conjunction with VALTYPE_CD = "N" to store a numerical value
                'valueflag_cd': None, # An optional flag for outlier or abnormal values
                'units_cd': None, # Units of measurement for the value in the NVAL_NUM column. Optional. If unit conversions are turned on, this is used to scale results in the query tool.
                'unitflag_cd': None, # whether the unit is inferred or extracted
            }

            tmp.append(dict(template))

            if value is not None:
                tmp.append(dict(template))
                try:
                    float(value)
                    is_num = True
                except:
                    is_num = False

                tmp[-1]['valtype_cd'] = 'N' if is_num else 'T'
                if is_num: 
                    tmp[-1]['nval_num'] = float(value)
                    tmp[-1]['tval_char'] = item.get('note', None)
                else:
                    tmp[-1]['tval_char'] = value
                tmp[-1]['modifier_cd'] = 'DOSE'
                tmp[-1]['units_cd'] = item.get('unit', None)
                tmp[-1]['unitflag_cd'] = item.get('infer', None)

            if route is not None:
                tmp.append(dict(template))
                tmp[-1]['modifier_cd'] = 'ROUTE'
                tmp[-1]['tval_char'] = route

            if freq is not None:
                tmp.append(dict(template))
                tmp[-1]['modifier_cd'] = 'FREQ'
                tmp[-1]['tval_char'] = freq

            output_data += tmp
            
            self.output_format(output_data)

    def output_format(self, json_data):

        if self.format_type == 'csv':
            
            df_data = pd.DataFrame(json_data)
            df_data = df_data.replace('(?i)none', pd.NA, regex = True)
            if "encounter_num" in json_data[0]:
                encounter_num = json_data[0]["encounter_num"]
            elif "key" in json_data[0]:
                encounter_num = json_data[0]["key"]
            else:
                NotImplementedError
            df_data.to_csv(f"outputs/{encounter_num}_{self.schema}.csv")
            
        elif self.format_type == 'sqlite':

            self.write_sqlit(json_data)

        elif self.format_type == 'json':
            encounter_num = json_data[0]["encounter_num"]
            with open(f"outputs/{encounter_num}.json", 'w'):
                json.dump(json_data, f)
        
    def write_sqlit(self, json_data):
        
        # tables = {'"ehr_id"': "TEXT", 
        #           '"admission_date"': "TEXT",
        #           '"discharge_date"': "TEXT"}
        for key in json_data[0]:
            tables[f'"{key}"'] =  "TEXT"
        create_table_query = [f'{k}'+' '+v for k, v in tables.items()]
        create_table_query = f"CREATE TABLE IF NOT EXISTS data ({', '.join(create_table_query)});"
        self.cursor.execute(create_table_query)
        self.connection.commit()

        insert_query = f"INSERT INTO data ({', '.join(tables)}) VALUES ({', '.join(['?' for _ in tables])})"
        data_batch = []
        for item in json_data:
            row = []
            for key in item:
                row.append(item[key] if key != 'related' else json.dumps(item[key]))
            data_batch.append(row)

        self.cursor.executemany(insert_query, data_batch)
        self.connection.commit()  # Commit in batches
        data_batch.clear()
        




