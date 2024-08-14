from unittest.mock import Mock, patch, call
import requests
import json
from unittest import TestCase
import os
import csv
from sftocsv.utils import utils
import shutil
class test_utils(TestCase):
    
    ### check_token_store tests 
    def test_check_token_store(self):
        """
        #### Function: 
            - utils.check_token_store
        #### Inputs: 
            3 Calls: 
            1. -@key_tag: not entered ('default'): this is in the token store
            2. -@key_tag: 'missing': this is not in the token store
            --- then the token store is deleted
            3. -@key_tag: not entered ('default')
        #### Expected Behaviour: 
            -1. the access token is found in the token store and returned
            -2. the key tag isn't found so the access token isn't found, so None is returned
            -3. the token store isn't found, so None is returned
        #### Assertions: 
            - first call returns 'test_token'
            - second call returns None 
            - third call returns None 
        """
        ### setup
        test_token_store = {'default': {'access_token': 'test_token'}}
        with open('/tmp/sf_token_store.json', 'w') as token_file:
            json.dump(test_token_store, token_file)
        ### 
        assert(utils.check_token_store() == 'test_token')
        assert(utils.check_token_store(key_tag='missing') == None)
        os.remove('/tmp/sf_token_store.json')
        assert(utils.check_token_store() == None)
        

    ### --- get_access_token tests 
    @patch("requests.post")
    def test_get_access_token(self, mock_post):
        """
        #### Function: 
            - utils.get_access_token
        #### Inputs: 
            -@base_url: 'https://localhost/ (not important as post is mocked)
            -@c_key: test string 
            -@c_secret: test string
            -@token_store_path: not passed in
            -@key_tag: not passed in
        #### Expected Behaviour:
            - Callout is made, returns 200 and an access_token in the response body
            - access_token is saved to the token_store_path under the key_tag ('default')
            - access token is returned
        #### Assertions: 
            - access token returned from the request is stored in the token_store_path
            - value returned is the access token
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        ### 
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = b"""{"access_token":"fake_token",
                                       "signature":"fake_signature",
                                       "scope":"chatter_api api",
                                       "instance_url":"fake_instance_url",
                                       "id":"fake_id",
                                       "token_type":"Bearer","issued_at":"1687833980742"}"""

        mock_post.return_value = mock_response
        resp = utils.get_access_token(base_url='https://localhost/', c_key='test_key', c_secret='test_secret')
        with open('/tmp/sf_token_store.json', 'r') as token_file:
            loaded_json = json.load(token_file)
            file_access_token = loaded_json['default']["access_token"]
            assert file_access_token == "fake_token"
        assert(resp == 'fake_token')
        os.chdir('..')
        shutil.rmtree('testing_folder')

    @patch("requests.post")
    def test_get_access_token_error(self, mock_post):
        """
        #### Function: 
            - utils.get_access_token
        #### Inputs: 
            -@base_url: 'https://localhost/' (not important as post is mocked)
            -@c_key: test string 
            -@c_secret: test string 
            -@token_store_path: not passed in
            -@key_tag: not passed in
        #### Expected Behaviour: 
            - callout is made, the mocked response code is 400 so the exception is thrown
        #### Assertions: 
            - the exception is raised with the expected content
        """
        mock_response = requests.Response()
        mock_response.status_code = 400
        json_string = {"error": "invalid_client", "error_description": "invalid client credentials"}
        mock_response._content = json.dumps(json_string)
        mock_post.return_value = mock_response
        with self.assertRaises(Exception) as context:
            utils.get_access_token(base_url='https://localhost/', c_key='test key', c_secret='test_secret')
        assert str(context.exception) == f'Token Request Error: {json.dumps(json_string)}'

    
    ### --- collect_token tests
    @patch.object(utils, 'get_access_token')
    @patch.object(utils, 'check_token_store')
    def test_collect_token_none_check_token(self, mock_check_token_store, mock_get_access_token):
        """
        #### Function: 
            - utils.collect_token
        #### Inputs:
            -@base_url: 'https://localhost/' (not important as functions using it are mocked)
            -@c_key: test key
            -@c_secret: test_secret
            -@token_store_path: not passed in
        #### Expected Behaviour:
            - utils.check_token_store is mocked to return None, so the following condition is true
            utils.get_access_token returns a value, which becomes access_token, which is returned
        #### Assertions: 
            - the returned value is the string returned by utils.get_access_token
        """
        mock_check_token_store.return_value = None
        mock_get_access_token.return_value = 'access_token'
        assert(utils.collect_token(base_url='https://localhost/', c_key='test key', c_secret='test secret') == 'access_token')

    @patch.object(utils, 'check_token_store')
    def test_collect_token_check_token_returned(self, mock_check_token_store):
        """
        #### Function:
            - utils.collect_token
        #### Inputs: 
            -@base_url: 'https://localhost/ (not important as functions using it are mocked)
            -@c_key: test key
            -@c_secret: test_secret
            -@token_store_path: not passed_in
        #### Expected Behaviour: 
            - check_token_store is mocked to return a non-None value, so it is passed to access_token,
                which is then returned
        #### Assertions: 
            - The returned value is the mocked access token response
        """
        mock_check_token_store.return_value = 'test_token'
        assert(utils.collect_token(base_url='https://localhost/', c_key='test key', c_secret='test secret') == 'test_token')


    ### --- flush_token_store tests --- 
    def test_flush_token_store(self):
        """
        #### Function: 
            - utils.flush_token_store
        #### Inputs: 
            - none passed in on first call
            - 'test_path.json' passed in on second call
        #### Expected Behaviour: 
            - 2 calls: 
            1. No file is found in the token path, nothing is done 
            2. file is found in token path, it's removed
        #### Assertions: 
            - The directory is unchanged after the first call,
            - the token store is deleted after the second call
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        with open('test_path.json', 'w') as w:
            w.write('t')
        ###
        utils.flush_token_store()
        assert(os.listdir() == ['test_path.json'])
        utils.flush_token_store('test_path.json')
        assert(os.listdir() == [])
        os.chdir('..')
        shutil.rmtree('testing_folder')

    
    ### --- delete_single_access_token tests --- 
    def test_delete_single_access_token(self):
        """
        #### Function:
            - utils.delete_single_access_token
        #### Inputs:
            -@key_tag: 'default'
            -@token_store_path: 'test_store.json'
        #### Expected Behaviour:
            - the test_store.json has multiple keys stored in it, 
                the file is opened and only the 'default' key is removed
        #### Assertions: 
            - the file is the same as before the function call, minus the 'default' key. 
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        example_store = {
            'default': {'access_token': 'default_key', 'timestamp': 'test'},
            'other_key': {'access_token': 'other_key', 'timestamp': 'test'}
        }
        with open('test_store.json', 'w') as w:
            json.dump(example_store, w)
        ### 
        utils.delete_single_access_token(key_tag='default', token_store_path='test_store.json')
        with open('test_store.json', 'r') as r:
            data = json.load(r)
            assert(data == {'other_key': {'access_token': 'other_key', 'timestamp': 'test'}})
        os.chdir('..')
        shutil.rmtree('testing_folder')

    
    ### --- retrieve_full_token_store --- 
    def test_retrieve_full_token_store_exception(self):
        """
        #### Function: 
            - utils.retrieve_full_token_store
        #### Inputs: 
            -@token_store_path: 'test_store.json' (no file is present here)
        #### Expected Behaviour: 
            - Because the token path file is not found, an exception is thrown
        #### Assertions: 
            - The expected exception is thrown
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        ### 
        with self.assertRaises(Exception) as context:
            utils.retrieve_full_token_store('test_store.json')
        assert(str(context.exception) == 'No file found in token_store_path')
        os.chdir('..')
        shutil.rmtree('testing_folder')

    def test_retrieve_full_token_store(self):
        """
        #### Function: 
            - utils.retrieve_full_token_store
        #### Inputs: 
            -@token_store_path: 'test_store.json' (file is present here)
        #### Expected Behaviour: 
            - The file is found and opened, then the loaded json is returned
        #### Assertions: 
            - the contents of test_store.json are returned.
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        example_store = {
            'default': {'access_token': 'default_key', 'timestamp': 'test'},
            'other_key': {'access_token': 'other_key', 'timestamp': 'test'}
        }
        with open('test_store.json', 'w') as w:
            json.dump(example_store, w)
        ### 
        resp = utils.retrieve_full_token_store('test_store.json')
        assert(resp == example_store)
        ### Cleanup
        os.chdir('..')
        shutil.rmtree('testing_folder')
        ###


    ### --- get_z_time tests ---
    def test_get_z_time(self): 
        """
        #### Function:
            - utils.get_z_time
        #### Inputs:
            -@year: 2005
            -@month: 10
            -@day: 08
        #### Expected Behaviour: 
            - the input year month and date will be converted into a datettime, which will then be formated to zero-offset time
            and returned
        #### Assertions: 
            - the returned string is as expected
        """
        returned_time = utils.get_z_time(2005, 10, 8)
        assert(returned_time == '2005-10-08T00:00:00Z')

    
    ### --- split_nested_record tests ---
    def test_split_nested_record_flat(self):
        """
        #### Function: 
            - utils.split_nested_record_list
        #### Input/s:
            - a list of dicts that have no further nesting, they are also all of the same type 'example'
        #### Expected Behaviour: 
            - For each record split_record will be called, none of the values are dicts (other than attributes,
            which is skipped),
            so the items are copied into one list and this is stored in the returned dict under the key 'example'
        #### Assertions:
            - the returned dict has the one key 'example' which stores the expected list of dicts
        """
        input_list = [
            {'Id': 'id1',
             'attributes': {'type': 'example'},
             'key1': 'valuea1',
             'key2': 'valuea2'
             },
            {'Id': 'id2',
             'attributes': {'type': 'example'},
             'key1': 'valueb1',
             'key2': 'valueb2'
            },
            {'Id': 'id3',
             'attributes': {'type': 'example'},
             'key1': 'valuec1',
             'key2': 'valuec2'
            }
        ]
        expected_result = [
            {'Id': 'id1',
             'key1': 'valuea1',
             'key2': 'valuea2'
             },
            {'Id': 'id2',
             'key1': 'valueb1',
             'key2': 'valueb2'
            },
            {'Id': 'id3',
             'key1': 'valuec1',
             'key2': 'valuec2'
            }
        ]
        resp_dict = utils.split_nested_record_list(input_list)
        assert(len(resp_dict) == 1)
        assert(resp_dict['example'] == expected_result)
    
    def test_split_nested_record_no_type_no_id(self):
        """
        #### Function: 
            - utils.split_nested_record_list
        #### Input/s:
            - first call it with a list, the only element is a dict with an Id but NO type key
            in the attributes,
            - second call with a list, the only element is a dict with a type key in attributes, 
            but no Id key anywhere
        #### Expected Behaviour:
            - Both calls should be caught in the first and second lines respectively in the try-except of 
            split_record function
        #### Assertions:
            - Both calls result in the same exception
        """
        type_missing_input = [
            {'Id': 'id1',
             'attributes': {'none': 'none'},
             'key1': 'value1',
             'key2': 'value2'}
        ]
        with self.assertRaises(Exception) as context:
            utils.split_nested_record_list(type_missing_input)
        assert(str(context.exception) == 'record Type or Id not found')
        id_missing_input = [
            {'key1': 'value1',
             'attributes': {'type': 'example'},
             'key2': 'value2'}
        ]
        with self.assertRaises(Exception) as context:
            utils.split_nested_record_list(id_missing_input)
        assert(str(context.exception)) == 'record Type or Id not found'

    def test_split_nested_record_2d(self):
        """
        #### Function: 
            - utils.split_nested_record_list
        #### Input/s:
            - a list of dicts that have a dict as a value in them,
                this dict has a 'records' key and the value is a list of dicts, 
        #### Expected Behaviour:
            - Each of the dicts found in 'records' is added to their corresponding type key 
            and returned, as are the outer. 
            The id1 and id4 records are added under the 'outer1' key, 
            the key 'inners' has a dict value and the 'records' key is within, 
            3 of these records are of type 'inner1' and are added to this key in the return dict
            the key 'inners2' has a records list as well, both records are type 'inner2' and are added to this key. 
        #### Assertions: 
            - The returned dict has 2 records in the list stored in 'outer1', they should only have Id and key1 items inside
            - it should have 3 records in the list stored in 'inner1', they should have id and key1 items 
            - it should have 2 records in the list stored in 'inner2, with id and key1 items
            - inner1 and inner2 records will have a key in them 'outer1' with the id of their parent in this value 
        """
        input_list = [
            {'Id': 'id1',
            'key1': 'valueA',
             'attributes':{'type': 'outer1'},
             'inners': {'records': [{'Id': 'id2',
                          'key1': 'valueB',
                          'attributes': {'type': 'inner1'}},
                          {'Id': 'id3',
                           'key1': 'valueC',
                           'attributes': {'type': 'inner1'}}]}
            },
            {'Id': 'id4',
            'key1': 'valueD',
             'attributes':{'type': 'outer1'},
             'inners': {'records': [{'Id': 'id5',
                          'key1': 'valueE',
                          'attributes': {'type': 'inner1'}}]},
            'inners2': {'records': [{'Id': 'id6',
                          'key1': 'valueF',
                          'attributes': {'type': 'inner2'}},
                          {'Id': 'id7',
                           'key1': 'valueG',
                           'attributes': {'type': 'inner2'}}]}
            }]
        resp = utils.split_nested_record_list(input_list)
        assert(len(resp) == 3)
        assert(resp['outer1'] == [{'Id': 'id1', 'key1': 'valueA'},
                                {'Id': 'id4', 'key1': 'valueD'}])
        assert(resp['inner1'] == [{'outer1': 'id1', 'Id': 'id2', 'key1': 'valueB'},
                                  {'outer1': 'id1','Id': 'id3', 'key1': 'valueC'},
                                  {'outer1': 'id4','Id': 'id5', 'key1': 'valueE'}])
        assert(resp['inner2'] == [{'outer1': 'id4', 'Id': 'id6', 'key1': 'valueF'},
                                  {'outer1': 'id4', 'Id': 'id7', 'key1': 'valueG'}])
        
    def test_split_nested_record_3d(self):
        """
        #### Function:
            - utils.split_nested_record_list
        #### Input/s:
            - a list of dicts, the one dict inside has a nested list of records, a record in the list 
            has a nested list of records itself .
        #### Expected Behaviour: 
            - the outer dict is saved into 'outer' key, 
            - the records nested 1 deep are saved into 'middle' key, it has the outer key saved in 'outer'
            - the records nested 2 deep are saved into 'inner' key, they have the middle key saved in 'middle'
        #### Assertions:
            - The returned dict has the keys 'outer', 'middle', 'inner'
            - outer has 1, middle 2, inner 2
            - outer, middle, inner all match expected values
        """
        input_list = [{'Id': 'id1',
                       'attributes': {'type': 'outer'},
                       'key1': 'valueA',
                       'inners': {'records': [
                            {'Id': 'id2',
                             'attributes': {'type': 'middle'},
                             'key1': 'valueB',
                             'inners': {'records': [
                                 {'Id': 'id4',
                                  'attributes': {'type': 'inner'},
                                  'key1': 'valueD'},
                                 {'Id': 'id5',
                                  'attributes': {'type': 'inner'},
                                  'key1': 'valueE'}
                             ]}},
                            {'Id': 'id3',
                             'attributes': {'type': 'middle'},
                             'key1': 'valueC'}]
                                }
                        }]
        resp = utils.split_nested_record_list(input_list)
        assert(len(resp) == 3)
        assert(resp['outer'] == [{'Id': 'id1', 'key1': 'valueA'}])
        assert(resp['middle'] == [{'outer' : 'id1', 'Id': 'id2', 'key1': 'valueB'},
                                  {'outer' : 'id1', 'Id': 'id3', 'key1': 'valueC'}])
        assert(resp['inner'] == [{'middle': 'id2', 'Id': 'id4', 'key1': 'valueD'},
                                 {'middle': 'id2', 'Id': 'id5', 'key1': 'valueE'}])
        
    def test_split_nested_record_list_linked(self):
        """
        #### Function:
            - utils.split_nested_record_list
        #### Input:
            -@input_list: a dict with a nested list of records under 'linkage', 
                there is 1 linkage record and it has a 'linked' record as a single child, not in a 
                records list. An example of how a record like LoanContactRole would be returned, a
                one-to-one relation of nesting
        #### Expected Behaviour:
            - the outer dict is saved to the 'outer' key, 
            - the record found in the 'records' key of 'linkage' type is added to the 'linkage' key,
            - the record found in the 'inner__r' key of the linkage record is of type 'inner' and is added to this key
        #### Assertions:
            - returned dict has 1 record in 'outer' key list
            - 1 record in 'linkage' , it has 'id1' in the 'outer' key (its parent's id)
            - 1 record in 'inner', it has 'id2' in the 'linkage' key (its parent's id)
        """
        input_list = [{'Id': 'id1', 
                        'attributes': {'type': 'outer'},
                        'key1': 'valueA',
                        'linkage': {'records': [
                            {'Id': 'id2',
                            'attributes': {'type': 'linkage'},
                            'key1': 'valueB',
                            'inner__r': {
                                'Id': 'id3',
                                'attributes': {'type': 'inner'},
                                'key1': 'valueC'
                            }}
                        ]}
                    }]
        resp = utils.split_nested_record_list(input_list)
        assert(len(resp) == 3)
        assert(resp['outer'] == [{'Id': 'id1', 'key1': 'valueA'}])
        assert(resp['linkage'] == [{'Id': 'id2', 'key1': 'valueB', 'outer': 'id1'}])
        assert(resp['inner'] == [{'Id': 'id3', 'key1': 'valueC', 'linkage': 'id2'}])

    
    ### --- build_in_querystring tests ---
    def test_build_in_querystring_smaller(self):
        """
        #### Function: 
            - utils.build_in_querystring
        #### Inputs: 
            -@querystring: a string with <in> present in it 
            -@in_list: a list of 100 elements, which total a length of < 1000 (and therefore less than 20,000)
        #### Expected Behaviour: 
            - The while loop increments and the second condition is never true, so it goes until the 
                the first increment is false (reaches the end of the list), then returns the querystring and an empty remaining list
        #### Assertions: 
            - the returned string contains all of the elements of the in_list
            - the returned list of remaning elements is empty 
            - Assert the section of the query before the (in) part matches the input of that part
        """
        ### Setup
        input_list = [str(x) for x in range(50,151)]
        ###
        returned_query, remaining_elements = utils.build_in_querystring(querystring='select name from numbers__c where id in <in>', in_list = input_list)
        in_section = returned_query.partition('(')[2]
        in_section = in_section.partition(')')[0]
        assert(in_section.split(',') == input_list)
        assert(remaining_elements == [])
        assert('select name from numbers__c where id in ' == returned_query.partition('(')[0])
    
    def test_build_in_querystring_bigger(self):
        """
        #### Function: 
            - uitls.build_in_querystring
        #### Inputs: 
            -@querstring: a string with <in> present in it
            -@in_list: a list of 10000 elements with a total length > 20,000 (they're all >=3 digits)
        #### Expected Behaviour: 
            - The while loop increments until the second condition is true, (which it will be at some point due to the length of the in_list),
                then the resulting string is returned, and the remaining unused elements are returned in a list as well 
        #### Assertions: 
            - The returned string could not accomodate 1 more value (+ a comma), i.e it's  >= 19996 characters long but less than 20000  
            - the combination of elements inside the query and returned sum to equal the in_list
        """
        ### Setup
        input_list = [str(x) for x in range(100, 10101)]
        ###
        returned_query, remaining_elements = utils.build_in_querystring(querystring='select name from numbers__c where id in <in>', in_list=input_list)
        in_section = returned_query.partition('(')[2]
        in_section = in_section.partition(')')[0]
        assert(in_section.split(',') + remaining_elements == input_list)
        assert(20000 > len(returned_query) >= 19996)


    ### --- combine_nested_result_dicts tests ---
    def test_combine_nested_result_dicts(self):
        """
        #### Function: 
            - utils.combine_nested_result_dicts
        #### Inputs: 
            -@source_dict: a non-empty dict 
            -@destination_dict: a non-empty dict with some overlap of keys 
        #### Expected Behaviour: 
            - the keys that are common between the dicts will result in a combined list of dicts in the values,
                 the keys only in the source dict will be added as new keys and value in the destination
        #### Assertions: 
            - the output dict matches expected value 
        """
        source = {'key1': [{'record1': '1', 'name': 'test'}, {'record2': '2', 'name': 'test2'}],
                  'key2': [{'record3': '3', 'name': 'test3'}]}
        destination = {'key2': [{'record4': '4', 'name': 'test4'}],
                       'key3': [{'record5': '5', 'name': 'test5'}, {'record6': '6', 'name': 'test6'}]}
        resp = utils.combine_nested_result_dicts(source_dict=source, destination_dict=destination)
        assert resp == {'key1': [{'record1': '1', 'name': 'test'}, {'record2': '2', 'name': 'test2'}],
                  'key2': [{'record4': '4', 'name': 'test4'}, {'record3': '3', 'name': 'test3'}],
                  'key3': [{'record5': '5', 'name': 'test5'}, {'record6': '6', 'name': 'test6'}]}
        

    ### --- build_key_list tests --- 
    def test_build_key_list(self):
        """
        #### Function: 
            - utils.build_key_list
        #### Inputs: 
            -@dict_list: a list of dicts with some overlapping and some shared keys
        #### Expected Behaviour: 
            - the list is looped through and each unique key is added to the returned list 
        #### Assertions: 
            - the returned list has a list of 1 instance of each key in the dict list 
        """
        input_list = [{'key1': 'value1', 'key2': 'value2', 'key3': 'value3'},
                      {'key3': 'value3', 'key4': 'value4', 'key5': 'value5'},
                      {'key1': 'value1', 'key4':'value4', 'key6':'value6'}]
        assert(utils.build_key_list(input_list) == ['key1', 'key2', 'key3', 'key4', 'key5', 'key6'])

    
    ### --- record_list_to_csv tests --- 
    def test_record_list_to_csv_write(self):
        """
        #### Function:
            - utils.record_list_to_csv
        #### Inputs: 
            -@record_list: a list of records
            -@output_filename: 'test_file.csv' 
            -@append: false
        #### Expected Behaviour: 
            - Because append is false, only the new record_list is used to build the fieldnames,
            - each dict in the list is written as a row to the file using csv.DictWriter
        #### Assertions: 
            - The output_filename when opened and read back into a dict list contains all of the values of record_list
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        ### 
        input_list = [{'key1': 'value11', 'key2': 'value21', 'key3': 'value31'},
                      {'key1': 'value12', 'key2': 'value22', 'key3': 'value32'},
                      {'key1': 'value13', 'key2': 'value23', 'key3': 'value33', 'key4': 'value34'}]
        utils.record_list_to_csv(record_list=input_list, output_filename='test_file')
        expected_list = [{'key1': 'value11', 'key2': 'value21', 'key3': 'value31', 'key4': ''},
                      {'key1': 'value12', 'key2': 'value22', 'key3': 'value32', 'key4': ''},
                      {'key1': 'value13', 'key2': 'value23', 'key3': 'value33', 'key4': 'value34'}]
        output_list = []
        with open('test_file.csv', 'r') as r:
            reader = csv.DictReader(r)
            for row in reader: 
                output_list.append(row)
        assert(output_list == expected_list)
        os.chdir('..')
        shutil.rmtree('testing_folder')

    def test_record_list_to_csv_append(self):
        """
        #### Function:
            - utils.record_list_to_csv
        #### Inputs: 
            -@record_list: a list of records 
            -@output_filename: 'test_file.csv'
            -@append: True
        #### Expected Behaviour: 
            - because append is true, the output_filename is read first to build the fieldnames, 
                then the incoming record_list is used with build_key_list and combined with fieldnames 
            - each dict in the list is added as a row to the file 
        #### Assertions: 
            - the output_filename when opened and read back into a dict list contains all the expected values
        """
        ### Setup
        os.mkdir('testing_folder')
        os.chdir('testing_folder')
        prior_list = [{'key1': 'value11', 'key2': 'value12', 'key3': 'value13'},
                          {'key1': 'value21', 'key2': 'value22', 'key3': 'value23'}]
        utils.record_list_to_csv(record_list=prior_list, output_filename='test_file')
        ### 
        added_list = [{'key1': 'value31', 'key2': 'value32', 'key3': 'value33', 'key4': 'value34'},
                           {'key1': 'value41', 'key2': 'value42', 'key3': 'value43'}] 
        utils.record_list_to_csv(record_list=added_list, output_filename='test_file', append=True)
        output_list = []
        with open('test_file.csv', 'r') as r:
            reader = csv.DictReader(r)
            for row in reader:
                output_list.append(row)
        expected_list = [{'key1': 'value11', 'key2': 'value12', 'key3': 'value13', 'key4': ''},
                         {'key1': 'value21', 'key2': 'value22', 'key3': 'value23', 'key4': ''},
                         {'key1': 'value31', 'key2': 'value32', 'key3': 'value33', 'key4': 'value34'},
                         {'key1': 'value41', 'key2': 'value42', 'key3': 'value43', 'key4': ''}]
        assert(output_list == expected_list)
        os.chdir('..')
        shutil.rmtree('testing_folder')

    
    ### --- record_list_dict_to_csv tests
    @patch.object(utils, 'record_list_to_csv')
    def test_record_list_dict_to_csv(self, mock_record_list_to_csv):
        """
        #### Function: 
            - utils.record_list_dict_to_csv 
        #### Inputs: 
            -@record_list_dict: dict of lists, of dicts 
            -@filename_prefix: 'test_file'
        #### Expected Behaviour: 
            - for each key in the list, pass the value through to record_list_to_csv
        #### Assertions: 
            - record_list_to_csv is called the right number of times with the right parameters 
        """
        input_list_dict = {'key1': [{'first': 'call'}],
                           'key2': [{'second': 'call'}],
                           'key3': [{'third': 'call'}]}
        utils.record_list_dict_to_csv(input_list_dict, 'test_file')
        expected_calls = [call(records_list=[{'first': 'call'}], output_filename='test_file_key1.csv', append=False),
                            call(records_list=[{'second': 'call'}], output_filename='test_file_key2.csv', append=False),
                            call(records_list=[{'third': 'call'}], output_filename='test_file_key3.csv', append=False)]
        mock_record_list_to_csv.assert_has_calls(expected_calls)


    ### --- combine_records tests --- 
    def test_combine_records(self):
        """
        #### Function: 
            - uils.combine_records
        #### Inputs: 
            -@record_one: a dict
            -@record_two, a dict with no overlapping keys from record_one
        #### Expected Behaviour: 
            - for each key in record_two, it's not found in the return_record, so 
                it gets added to it with the value, 
            - the return_record is returned
        #### Assertions: 
            - The expected dict is returned
        """
        record_one = {'key1' : 'value1', 'key2': 'value2', 'key3': 'value3'}
        record_two = {'key4': 'value4' , 'key5': 'value5', 'key6': 'value6'}
        resp = utils.combine_records(record_one, record_two)
        expected_result = {'key1': 'value1', 'key2' : 'value2', 'key3' : 'value3', 
                           'key4': 'value4', 'key5': 'value5', 'key6': 'value6'}
        assert resp == expected_result
    
    def test_combine_records_empty(self):
        """
        #### Function: 
            - utils.combine_records
        #### Inputs: 
            -@record_one: empty dict 
            -@record_two: empty dict 
        #### Expected Behaviour: 
            - there aren't any values to loop through, nothing is added to record_one, which is
                already empty, so it returns empty
        #### Assertions:
            - The returned dict is empty
        """
        assert utils.combine_records({}, {}) == {}

    def test_combine_records_single_collision_overwrite(self):
        """
        #### Function: 
            - utils.combine_records
        #### Inputs: 
            -@record_one: a dict
            -@record_two: a dict with a shared key with record_one
        #### Expected Behaviour: 
            - when the collision is found on key1, the value from record_two is discarded
        #### Assertions:
            - the returned dict is as expected, with no value4 in it 
        """
        record_one = {'key1' : 'value1', 'key2': 'value2', 'key3': 'value3'}
        record_two = {'key1': 'value4' , 'key5': 'value5', 'key6': 'value6'}
        resp = utils.combine_records(record_one, record_two)
        expected_result = {'key1': 'value1', 'key2' : 'value2', 'key3' : 'value3', 
                             'key5': 'value5', 'key6': 'value6'}
        assert resp == expected_result




        