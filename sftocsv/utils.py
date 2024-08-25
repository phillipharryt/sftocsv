import os
import json
import requests
from datetime import datetime, timezone
import copy
import csv

class utils:

         
    @staticmethod
    def collect_token(base_url: str, c_key: str, c_secret: str, token_store_path: str = '/tmp/sf_token_store.json', key_tag: str = 'default') -> str: 
        """
        #### Inputs: 
            -@base_url: Salesforce org url (i.e 'https://examplecompany.my.salesforce.com')
            -@c_key: consumer key of connected app
            -@c_secret: consumer secret of connected app 
            -@token_store_path: optional, location to store resulting token
        #### Expected Behaviour:
            - Is a wrapper for check_token_store and get_access_token usage. 
            - Checks if there is a cached token locally, otherwise retrieves a new one and stashes it before returning it. 
        #### Returns: 
            - An access token 
        #### Side Effects: 
            - stores a json file in the token_store_path
        #### Exceptions: 
            - None
        """
        check_token = utils.check_token_store(key_tag=key_tag, token_store_path=token_store_path)
        if check_token == None:
            access_token = utils.get_access_token(base_url, c_key, c_secret, token_store_path)
        else:
            access_token = check_token
        return(access_token)


    @staticmethod
    def check_token_store(key_tag: str = 'default', token_store_path: str = '/tmp/sf_token_store.json',) -> str | None:  
        """
        #### Inputs: 
            -@key_tag: the tag to look under in the token store
            -@token_store_path: optional, location to check for token 
        #### Expected Behaviour: 
            - look for a token_store file in the token_store_path under the key_tag, 
            if a token is found it will be returned,
            otherwise return None
        #### Returns: 
            - str: a valid access token
            - None: if no valid access token is found 
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        if os.path.isfile(token_store_path):
            with open(token_store_path, 'r') as json_file:
                loaded_json = json.load(json_file)
                test_access_token = loaded_json.get(key_tag, {}).get("access_token", None)
                return(test_access_token)
        return None


    @staticmethod
    def get_access_token(base_url: str, c_key: str, c_secret: str, token_store_path: str = '/tmp/sf_token_store.json', key_tag: str = 'default') -> str:
        """
        #### Inputs:
            -@base_url: Salesforce org url (i.e 'https://examplecompany.my.salesforce.com') 
            -@c_key: consumer key of connected app
            -@c_secret: consumer secret of connected app
            -@token_store_path: optional, location to store token
            -@key_tag: the tag to store the key under in the token store
        #### Expected Behaviour: 
            - request an access token using the consumer key and secret. If non-200 response code
            raise an exception, otherwise save the token to the token_store_path 
            under the path [key_path]['access_token'], alongside a timestamp, and return the access token.
        #### Returns: 
            - An access token
        #### Side Effects: 
            - Save json data to token_store_path
        #### Exceptions: 
            - 'Token Request Error: ...' If the token retrieval request returns non-200, exception raised with the content. 
        """
        urlstring = f"{base_url}/services/oauth2/token?grant_type=client_credentials&client_id={c_key}&client_secret={c_secret}"
        resp = requests.post(urlstring)
        if resp.status_code != 200:
            raise Exception(f'Token Request Error: {str(resp.content)}')
        content = json.loads(resp.content)
        access_token = content["access_token"]
        with open(token_store_path, "w") as token_file:
            token_json = {key_tag: {"access_token": access_token, 'timestamp': str(datetime.now(timezone.utc))}}
            token_file.write(json.dumps(token_json))
        return(access_token)
    

    @staticmethod
    def flush_token_store(token_store_path: str = '/tmp/sf_token_store.json'):
        """
        #### Inputs: 
            -@token_store_path: optional, location of token store
        #### Expected Behaviour: 
            - Remove the file that the token is stored in if it exists
        #### Returns: 
            - None 
        #### Side Effects: 
            - Removes token_store_path file if present
        #### Exceptions: 
            - None 
        """
        if os.path.isfile(token_store_path):
            os.remove(token_store_path)


    @staticmethod
    def delete_single_access_token(key_tag: str = 'default', token_store_path: str = '/tmp/sf_token_store.json'):
        """
        #### Inputs: 
            -@key_tag: the tag associated with the access token you want to delete
            -@token_store_path: optional, location tokens are stored
        #### Expected Behaviour: 
            - if the token_store_path is found and the key_tag is in the json, delete the 
            key and save back to the token store
        #### Returns: 
            - None 
        #### Side Effects: 
            - Modifies the file stored at token_store_path 
        #### Exceptions: 
            - None 
        """
        json_data = {}
        if os.path.isfile(token_store_path): ## can't read and write at the same time
            with open(token_store_path, 'r') as store_file:
                json_data = json.load(store_file)
            json_data.pop(key_tag)
            with open(token_store_path, 'w') as w:
                json.dump(json_data, w)


    @staticmethod
    def retrieve_full_token_store(token_store_path: str = '/tmp/sf_token_store.json') -> dict:
        """
        #### Inputs: 
            -@token_store_path: optional, location tokens are stored
        #### Expected Behaviour: 
            - If the token_store_path is found then return the dict of values in it,
            if it's not found then raise an exception. 
            Useful for sanity check that you're using the right token store
        #### Returns: 
            - the dict stored in the token store
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        if not os.path.isfile(token_store_path):
            raise Exception('No file found in token_store_path')
        return_dict = {}
        with open(token_store_path, 'r') as json_file: 
            return_dict = json.load(json_file)
        return(return_dict)
    
    
    @staticmethod
    def get_z_time(year: int, month: int, day:int) -> str:
        """
        #### Input: 
            -@year: year: yyyy
            -@month: month: mm
            -@day: day: dd
        #### Expected Behaviour:
            - For use in filtering salesforce using a datetime, which requires a zero offset or 'z' time 
            format. Passing in the year, month, day it will convert to this zero offset format 
            and return the string
        #### Returns: 
            - str: the zero offset time string
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        unformatted = datetime(year, month, day, 0 ,0, tzinfo=timezone.utc)
        formatted = str(unformatted).replace('+00:00', 'Z')
        formatted = formatted.replace(' ', 'T')
        return(formatted)
    
    @staticmethod   
    def split_nested_record_list(input_list: list[dict]) -> dict[str,list[dict]]: #tesed
        """
        #### Input:    
            - a list of dicts resulting from a nested query to sf data 
        #### Expected Behaviour: 
            - for each record in the list; 
            each record is appended to a list stored in the return dict, under the key of its type
            each record will have its parent record in it as an additional field, they key being the type of the parent
            and the value being its ID 
        #### Returns:
            - a dict{str: list[dict]} key being the type of the record, value being a list of records
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None  (this isn't true)
        """
        output_dict = {}

        def split_record(record: dict, parent_id: str, parent_type: str):
            try:
                record_type = record['attributes']['type']
                record_id = record['Id']
            except:
                raise Exception('record Type or Id not found')
            current_record = {}
            if parent_id:
                current_record[parent_type] = parent_id
            for key, value in record.items():
                if key == 'attributes' or value == None:
                    continue
                elif type(value) == dict:
                    if value.get('attributes') != None: #
                        split_record(record=value, parent_id=record_id,parent_type=record_type)
                    for nested_record in value.get('records', []):
                        split_record(record=nested_record, parent_id=record_id, parent_type=record_type)
                else:
                    current_record[key] = value
            output_dict[record_type] = output_dict.get(record_type, []) + [current_record]

        for record in input_list:
            split_record(record,None,None)
        return(output_dict)
    
    
    @staticmethod
    def build_in_querystring(querystring: str, in_list: list[str]) -> tuple[str, list[str]]: 
        """
        #### Inputs: 
            -@querystring: soql query containing <in> substring 
            -@in_list: list of strings to place within the (in) part of the query
        #### Expected Behaviour: 
            - Builds the longest in query it can from the in_list, then returns the resulting 
                querystring and the remaining in_list elements  
        #### Returns: 
            -str: the built querystring 
            -list[str]: the remaining elements in the list after the maximum size query string was constructed
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """ 
        index = 0 
        while index + 1 <= len(in_list) and len(querystring.replace('<in>', f'({",".join(in_list[:index+1])})')) < 20000:
           index += 1
        return(querystring.replace('<in>', f'({",".join(in_list[:index])})'), in_list[index:])
    

    @staticmethod
    def combine_nested_result_dicts(source_dict: dict, destination_dict: dict) -> dict:
        """
        #### Inputs:
            -@source_dict: the dict to copy FROM
            -@destination_dict: the dict to copy TO
        #### Expected Behaviour: 
            - For all keys in the dict, append values from the source dict to the values in the destination dict
            - if the source dict has a key not present in the destination dict, it will create one
        #### Returns: 
            - the combined dict 
        #### Side Effects:  
            - None 
        #### Exceptions: 
            - None 
        """
        s_dict = copy.deepcopy(source_dict)
        d_dict = copy.deepcopy(destination_dict)
        for key, value in s_dict.items():
            destination_value = d_dict.get(key, [])
            destination_value.extend(value)
            d_dict[key] = destination_value
        return(d_dict)
    

    @staticmethod 
    def build_key_list(dict_list: list[dict]) -> list:
        """
        #### Inputs: 
            -@dict_list: a list of dicts
        #### Expected Behaviour: 
            - Loop through all dicts in the list, getting the unique keys in them
                all and then return the list
        #### Returns: 
            - Unique list of keys 
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        header_list = [] # set is not used because we want to preserve order
        for record in dict_list:
            for key in record.keys():
                if key not in header_list:
                    header_list.append(key)
        return(header_list)
    
    @staticmethod
    def record_list_to_csv(record_list: list[dict], output_filename: str, append: bool = False):
        """
        #### Inputs: 
            -@record_list: a list of dicts, representative of a non-nested query result
            -@output_filename: the filename to save the resulting .csv as (don't include .csv)
            -@append: if True, will append to an existing file, else writes 
        #### Expected Behaviour: 
            - if append=True, open the existing file and use the combination of the existing fieldnames 
                and any potential new fieldnames from record_list 
            - otherwise, build the fieldnames using build_key_list
            - write/append to the csv file
        #### Returns: 
            - None 
        #### Side Effects: 
            - Writes/appends to the output_filename
        #### Exceptions: 
            - None 
        """
        fieldnames = []
        records = []
        if append:
            with open(f'{output_filename}.csv', 'r') as existing_file: 
                reader = csv.DictReader(existing_file)
                for row in reader:
                    records.append(row)

        records.extend(record_list)
        fieldnames = utils.build_key_list(records)
        with open(f'{output_filename}.csv', 'w') as f:
            w = csv.DictWriter(f, fieldnames)
            w.writeheader()
            w.writerows(records)

    @staticmethod
    def record_list_dict_to_csv(record_list_dict: dict, filename_prefix: str,  append: bool = False):
        """
        #### Inputs: 
            -@record_list_dict: dict of lists of dicts, keys are used in the filename, 
            lists of dicts are saved as CSVs, each dict being a row,
            -@filename_prefix: a a prefix to prepend to each filename, which will be followed by its key
            -@append:  if True, will append to an existing file, else writes 
        #### Expected Behaviour: 
            - Each key in the dict is used to create a new csv and to call records_to_csv, 
                passing in a filename created from a combination of the filename_prefi and the corresponding 
                key in the dict used to access that dict list 
        #### Returns:
            - None 
        #### Side Effects: 
            - Creates csv files for each key in the dict 
        #### Exceptions: 
            - None 
        """
        for key, value in record_list_dict.items():
            filename = f'{filename_prefix}_{key}.csv'
            utils.record_list_to_csv(record_list=value, output_filename=filename, append=append)   


    @staticmethod
    def combine_records(record_one: dict, record_two: dict) -> dict: 
        """
        #### Inputs: 
            -@record_one: a dict
            -@record_two: a dict
        #### Expected Behaviour: 
            - Provided two dictionaries will add keys and values from record_two to record_one,
            - it only bothers about keeping record_one items in the case of a collision of keys
        #### Returns: 
            - the combined dict 
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        return_record = {}
        return_record.update(record_one)
        for key in [x for x in record_two if x not in return_record.keys()]:
            return_record[key] = record_two[key]
        return(return_record)
