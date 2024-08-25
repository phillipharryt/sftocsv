import requests
import json
import urllib
from .utils import *

class Sftocsv:

    def __init__(self, base_url: str, api_version: float, access_token: str = '', tokenless: bool=False):
        """
        #### Inputs:
            -@base_url: Salesforce org url (i.e 'https://examplecompany.my.salesforce.com') 
            -@api_version: salesforce api version in float format (i.e 58.0)
            -@access_token: client credentials flow access token 
            -@tokenless: disables missing token exception. Useful if you want the joins and don't need to query
        """
        self.base_url = base_url
        self.api_version = f'v{str(api_version)}' ## 58.0
        if not access_token and not tokenless:
            raise Exception('Access Token missing. If you want to use non-query functions pass in tokenless = True')
        self.access_token = access_token 

  
    def query_records(self, querystring: str, nested: bool=False) -> list[dict] | dict[str, list[dict]]: 
        """
        #### Inputs:
            -@queryString: soql of form 'SELECT ... from ... where ...'
            -@nested: If you're using this function for a nested query, set to True 
        #### Expected Behaviour: 
            - the input string is url-parsed and the request is sent
            - the results are paginated through if required and records are read into a list of dicts 
            - if 'nested' is true, the 'attributes' section of each record is kept so that child records 
                can inheret a parent record id and save it in a field of the parent type. 
                If it's not nested, the attributes section is removed. 
        ##### Returns:
            - list[dict]: in the case of nested=False, returns a list of dicts, each dict being a record from the query 
            - dict[str, list[dict]]: in the case of nested=True, list of records are stored against a key of their type in the dict
        #### Side Effects:  
            - None 
        #### Exceptions: 
            - If status_code returned by query != 200, re-raises the error as an exception
        """
        querystring = urllib.parse.quote_plus(querystring)
        urlstring = f"{self.base_url}/services/data/{self.api_version}/query/?q={querystring}"
        header_dict = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.get(url=urlstring, headers=header_dict)
        if resp.status_code != 200:
            raise Exception(f'Query of -->{querystring}<-- raised error: \n {str(resp.content)}')
        resp_json = json.loads(resp.content)
        records = resp_json['records']
        next_url = resp_json.get('nextRecordsUrl', None)
        while next_url: 
            resp = requests.get(url=f"{self.base_url}{next_url}", headers=header_dict)
            if resp.status_code != 200:
                raise Exception(f'Query of -->{querystring}<-- on nextUrl -->{next_url}<-- raised error: \n {str(resp.content)}')
            resp_json = json.loads(resp.content)
            records += resp_json['records']
            next_url = resp_json.get('nextRecordsUrl', None)
        if(not nested): 
            for record in records:
                del(record['attributes'])
        else: 
            records = utils.split_nested_record_list(records)
        return records
            
            
    def large_in_query(self, querystring: str, in_list:list, nested: bool=False) -> list[dict] | dict[str, list[dict]]: 
        """
        #### Inputs:
            -@querystring: soql of form 'SELECT ... from ... where ... <in> ...'
            -@in_list: a list to substitute into the spot of <in> 
            -@nested: If you're using this function for a nested query, set to True
        #### Expected Behaviour: 
            - This is for use in avoiding hitting the 20,000 character limit on a query. You're likely to only hit this if you have a 
                very large list of values in a 'in' query. This function splits the 'in_list' into amounts that will fit into the 
                query limit, sends the requests and then combines the results and returns.
            - if the querystring doesn't contain a '<in>' substring an exception will be thrown
        #### Returns:   
            - list[dict]: Returned in the case of nested=True; a list of dicts, each dict being a record from the query 
            - dict[str, list[dict]]: Returned in the case of nested=False; list of records are stored against a key of their type in the dict
        #### Side Effects: 
            - None 
        #### Exceptions:
            - No '<in>' found...: Raised if the querystring has no <in> substring
            - in_list is empty: Raised if in_list is empty
        """
        if('<in>' not in querystring):
            raise Exception(f'No <in> found in query -->{querystring}<--')
        if(len(in_list) == 0):
            raise Exception('in_list is empty')
        
        built_querystring, remaining_list = utils.build_in_querystring(querystring, in_list)
        current_records = [] 
        if(nested):
            current_records = {}
        while len(remaining_list) > 0:
            resp = self.query_records(built_querystring)
            if(nested):
                current_records = utils.combine_nested_result_dicts(source_dict=resp, destination_dict=current_records)
            else:
                current_records += resp
            built_querystring, remaining_list = utils.build_in_querystring(querystring, remaining_list)
        resp = self.query_records(built_querystring)
        if(nested):
            current_records = utils.combine_nested_result_dicts(source_dict=resp, destination_dict=current_records)
        else:
            current_records += resp
        return(current_records)


    @staticmethod
    def records_to_csv(records: list[dict] | dict[str, list[dict]] , output_filename: str, append: bool=False): #tested #need to make this work for nested as well 
        """
        #### Inputs: 
            -@records: either a list of dicts (representing a non-nested query result), 
                        of a dict with lists of dicts as values, (representing a nested query result)
            -@output_filename: string to use as the filename. (.csv format is optional on the end) 
                In the case of a nested query result this string will become a prefix and the record type will be appended (i.e _Account.csv)
            -@append: if True, will attempt to append to the file, rather than write new ones
        #### Expected Behaviour: 
            - First checks that .csv wasn't passed in, trims it if it was, so that it can be used as a 
                prefix if needed in record_list_dict_to_csv
            - then depending on the type of records parameter passed in, either calls 
                utils.record_list_to_csv or record_list_dict_to_csv 
            
        Takes in a list of records (dicts) and a filename ending with csv,
        Each record will be saved as a row in the csv output
        Each unique key will become a header in the csv
        """
        output_filename = output_filename.rpartition('.csv')[0]
        if(type(records) == list):
            utils.record_list_to_csv(record_list=records, output_filename=output_filename, append=append)
        elif(type(records) == dict):
            utils.record_list_dict_to_csv(record_list_dict=records, filename_prefix=output_filename, append=append)

    
    @staticmethod
    def inner_join(left_list: list[dict], right_list: list[dict], left_key: str, right_key:str, preserve_right_key:bool=False) -> list[dict]:
        """
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: the key you want to match with from the left_list
            -@right_key: the key you want to match with from the right_lis
            -@preserve_right_key: If true, will keep the right key in the resulting dicts, otherwise 
                just preserves the left key 
        #### Expected Behaviour: 
            -will produce a list of records equivalent to an INNER JOIN 
                (exclusively rows that have a key found in both lists are combined and output)
            - i.e, for each value in left_list, if left_key matches any record in right_list on the right_key, 
                those records are combined into the output. 
        #### Returns: 
            - The resulting dict
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        resulting_list = []
        for left_record in left_list:
            if left_key not in left_record.keys():
                continue
            for right_record in right_list:
                if right_key not in right_record.keys():
                    continue
                if right_record[right_key] == left_record[left_key]:
                    combined_record = utils.combine_records(left_record, right_record)
                    if not preserve_right_key:
                        del combined_record[right_key]
                    resulting_list.append(combined_record)
        return(resulting_list)
    

    @staticmethod
    def natural_join(left_list: list[dict], right_list: list[dict], exclusive:bool=False):     
        """
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@exclusive: If False -> any single matching column name + value will create a join
                         If True -> all shared column names must match on value for a row to join 
        #### Expected Behaviour: 
            - for each record in both: 
                - if it's an inclusive method (exclusive = False), it looks for any key that is shared and 
                    if two records share a value they are combined and returned. Any matching keys that don't 
                    share a value wil result in having the right_list value  
                - if it's an exclusive method (exclusive = True), it looks for records in which all shared columns 
                    share values 
            - Return combined list result
        #### Returns: 
            - List of dicts resulting from join
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - None 
        """
        resulting_list = []
        for left_record in left_list:
            for right_record in right_list:
                match = False
                retrieved = [left_record.get(key) == right_record.get(key) for key in left_record.keys() if key in right_record.keys()]
                #inclusive method, if any of these match it's all good 
                if not exclusive and True in retrieved:  
                    match = True                        
                #exclusive method, all must match on shared keys 
                elif exclusive and False not in retrieved:
                    match = True 
                if(match == True):                    
                    combined_record = utils.combine_records(left_record, right_record)
                    resulting_list.append(combined_record)
                    break
        return(resulting_list)
    

    @staticmethod
    def outer_join(left_list: list[dict], right_list: list[dict], left_key: str, right_key: str,
                    side: str, preserve_innner_key:bool=False):
        """
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: key to match upon from the left_list 
            -@right_key: key to match upon from the right_list
            -@side: on of ['left', 'right', 'full'], to designate the type of outer join
        #### Expected Behaviour: 
            - if the 'side' is entered, it fills the outer, inner, outer_key, inner_key accordingly 
                for each record in the outer list, it is checked against all elements of the inner list,
                anny inner record that matches results in a new combined record being created and added to the return list
            - if an outer record is not matched on any inner record, it is still appended to the return list 
            - for the inner list, a set of indexes of records that are unmatched is kept. In the case of a full outer join,
                even if the inner list record is never matched against an outer record, it should still be added to the list. 
                if it is matched, it doesn't need adding to the list again, hence the unmatched_inner storage. 
        #### Returns: 
            - List of records resulting from the join 
        #### Side Effects: 
            - None 
        #### Exceptions: 
            - 'outer_join requires one of..' If the 'side' doesn't match one of the valid values 
        """
        side_map = {'left': {'outer' : left_list, 'outer_key': left_key, 'inner': right_list, 'inner_key': right_key},
                    'right': {'outer':right_list, 'outer_key':  right_key, 'inner': left_list, 'inner_key': left_key},
                    'full': {'outer' : left_list, 'outer_key': left_key, 'inner': right_list, 'inner_key': right_key}}
        if side not in side_map.keys():
            raise Exception('outer_join requires one of ("left", "right", "full") in "side" argument')
       
        #outer and inner 
        outer_key = side_map[side]['outer_key']
        outer = side_map[side]['outer']
        inner_key = side_map[side]['inner_key']
        inner = side_map[side]['inner']
        return_list = []
        unmatched_inner = set(list(range(len(inner))))
        for outer_record in outer: 
            matched = False
            for inner_i, inner_record in enumerate(inner):
                if outer_record.get(outer_key) == inner_record.get(inner_key):
                    matched = True
                    combined_record = utils.combine_records(outer_record, inner_record)
                    if(not preserve_innner_key):
                        del(combined_record[inner_key])
                    return_list.append(combined_record)
                    if(inner_i in unmatched_inner):
                        unmatched_inner.remove(inner_i)
            if not matched:
                return_list.append(outer_record)
        if side == 'full':
            for x in unmatched_inner:
                return_list.append(inner[x])
        return(return_list)
