from sftocsv import Sftocsv
from sftocsv import utils
from unittest.mock import Mock, patch, call 
import requests
import json
from unittest import TestCase
import os
import csv
class test_sftocsv(TestCase):
    if os.path.isfile("/tmp/sf_token_store.json"):
        os.remove('/tmp/sf_token_store.json') #this can't be kept forever. Tests should never affect production

    ### --- __init__ tests --- 
    def test_init_no_access_token(self):
        """
        #### Function: 
            - Sftocsv.__init__
        #### Inputs: 
            -@base_url: 'https://examplecompany.my.salesforce.com'
            -@api_version: 58.0
            -@access_token: Not passed in 
            -@tokenless: not passed in
        #### Expected Behaviour:    
            - Because no access_token is passed in and tokenless isn't True, an exception is raised
        #### Assertions: 
            - the expected exception is thrown
        """
        with self.assertRaises(Exception) as context: 
            Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0)
        assert(str(context.exception) == 'Access Token missing. If you want to use non-query functions pass in tokenless = True')

    def test_init(self):
        """
        #### Function:
            - Sftocsv.__init__
        #### Inputs: 
            -@base_url: 'https://examplecompany.my.salesforce.com'
            -@api_version: 58.0
            -@access_token: 'test_token'
            -@tokenless: not passed in 
        #### Expected Behaviour: 
            - Because access_token is passed in, all attributes are set and no exceptions are thrown
        #### 
            - the expected attributes are set on the instance of Sftocsv
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        assert(resource.base_url == 'https://examplecompany.my.salesforce.com')
        assert(resource.api_version == 'v58.0')
        assert(resource.access_token == 'test_token')


    ### --- query_records tests ---
    @patch("requests.get")
    def test_query_records_single_200(self, mock_get):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs:
            -@querystring: 'select id, field from opportunity' (request is patched so string not important)
            -@nested: False
        #### Expected Behaviour: 
            - The resp.status_code is mocked to 200 so the json is loaded in,
                the next_url is not found, and nested is false, so attributes are removed
                from each record
            - the records are returned
        #### Assertions: 
            - the returned records are the same as the mocked data, minus the 'attributes' sections in each
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        mock_response = requests.Response()
        mock_response._content = b"""{"totalSize":1,"done":true,"records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id1", "field": "value1"},
                                                                         {"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id2", "field": "value2"}]}"""
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        resp = resource.query_records("select id, field from opportunity", nested=False)
        expected_value = [{"Id" : "Id1", "field": "value1"}, {"Id": "Id2", "field": "value2"}]
        assert resp == expected_value

    @patch("requests.get")
    def test_query_records_error(self, mock_get):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs:
            -@querystring: 'select id, field from opportunity'
            -@nested: False
        #### Expected Behaviour: 
            - The mocked response is non-200 so an exception is raised and the querystring is
                present in the error message 
        #### Assertions: 
            - the expected exception is raised
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        mock_get_response = requests.Response()
        mock_get_response.status_code = 400
        mock_get_response._content = "error"
        mock_get.return_value = mock_get_response
        with self.assertRaises(Exception) as context:
            resource.query_records("select id, field from opportunity")
        assert(f'Query of -->select+id%2C+field+from+opportunity<-- raised error: \n error' == str(context.exception)) 

    @patch("requests.get")
    def test_query_records_empty(self, mock_get):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs: 
            -@querystring: 'select id, field from opportunity
            -@nested: False
        #### Expected Behaviour:   
            - The mocked response is an empty list of records, so an empty list of records is returned
        #### Assertions: 
            - The returned list is empty
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        mock_get_response = requests.Response()
        mock_get_response.status_code = 200
        mock_get_response._content = b'{"totalSize":1,"done":true,"records":[]}'
        mock_get.return_value = mock_get_response
        resp = resource.query_records('select id, field from opportunity')
        assert resp == []

    @patch("requests.get")
    def test_query_records_long(self, mock_get):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs: 
            -@querystring: 'select id from opportunity' 
            -@nested: False
        #### Expected Behaviour: 
            - The first mocked response has a nextRecordsUrl so another request is sent, 
                same with the second mocked response 
            - The third mocked response has no nextRecordsUrl so the requests finish, 
            - The retrieved records from each call are collated and returned
        Assert that when a nextRecordsUrl is returned it will loop through to collect them all 
        """
        response_1 = requests.Response()
        response_1.status_code = 200
        response_1._content =  b'{"totalSize":1,"done": false, "nextRecordsUrl": "fake_url", "records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id1"}]}'
        response_2 = requests.Response()
        response_2.status_code = 200
        response_2._content = b'{"totalSize":1,"done": false, "nextRecordsUrl": "fake_url", "records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id2"}]}'
        response_3 = requests.Response()
        response_3.status_code = 200
        response_3._content = b'{"totalSize":1,"done": true, "records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id3"}]}'
        mock_get.side_effect = [response_1, response_2,response_3]
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        resp = resource.query_records('select id from opportunity')
        expected_result = [{'Id': 'Id1'}, {'Id' : 'Id2'}, {'Id': 'Id3'}]
        assert resp == expected_result

    @patch("requests.get")
    def test_query_records_long_error(self, mock_get):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs: 
            -@querystring: 'select id from opportunity' 
            -@nested: False
        #### Expected Behaviour: 
            - The first mocked response has a nextRecordsUrl so another request is sent, 
                same with the second mocked response
            - The third mocked response has a 400 status code, so an exception is thrown with the content of the message
        #### Assertions: 
            - The expected Exception is thrown
        """
        response_1 = requests.Response()
        response_1.status_code = 200
        response_1._content =  b'{"totalSize":1,"done": false, "nextRecordsUrl": "fake_url", "records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id1"}]}'
        response_2 = requests.Response()
        response_2.status_code = 200
        response_2._content = b'{"totalSize":1,"done": false, "nextRecordsUrl": "fake_url", "records":[{"attributes":{"type":"Opportunity","url":"/services/data/v58.0/sobjects/Opportunity/fake_id"},"Id":"Id2"}]}'
        response_3 = requests.Response()
        response_3.status_code = 400
        response_3._content = 'error'
        mock_get.side_effect = [response_1, response_2,response_3]
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        with self.assertRaises(Exception) as context:
            resp = resource.query_records('select id from opportunity')
        assert(f'Query of -->select+id+from+opportunity<-- on nextUrl -->fake_url<-- raised error: \n error' == str(context.exception)) 

    @patch.object(utils, 'split_nested_record_list')
    @patch("requests.get")
    def test_query_records_nested(self, mock_get, mock_split_nested_record_list):
        """
        #### Function: 
            - Sftocsv.query_records
        #### Inputs: 
            -@querystring: 'select name, (select lastname from contacts) from account'
            -@nested: True
        #### Expected Behaviour: 
            - The resp.status_code is mocked to 200 so the json is loaded in, the next_url is not found,
            - nested is true, so attributes are not removed from each record
            - split_nested_record is called on the response records
            - the dict returned by split_nested_recored is returned
        #### Assertions: 
            - split_nested_record_list is called once with the response from the query 
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        mock_response = requests.Response()
        mock_response._content = b'{"totalSize": 1, "done": true, "records": [{"attributes":{"type":"Account","url":"contact_url"},"Name":"Test Name","Id":"test_id","Contacts":{"totalSize":1,"done":true,"records":[{"attributes":{"type":"Contact","url":"contact_url"},"AccountId":"test_a_id","Id":"t_id","LastName":"Test"}]}}]}'
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        resp = resource.query_records("select name, (select lastname from contacts) from account", nested=True)
        expected_value = [{"attributes":{"type":"Account","url":"contact_url"},"Name":"Test Name","Id":"test_id","Contacts":{"totalSize":1,"done":True,"records":[{"attributes":{"type":"Contact","url":"contact_url"},"AccountId":"test_a_id","Id":"t_id","LastName":"Test"}]}}]
        mock_split_nested_record_list.assert_called_once_with(expected_value)


    ### --- large_in_query tests --- 
    def test_large_in_query_errors(self):
        """
        #### Function: 
            - Sftocsv.large_in_query
        #### Inputs: 
            2 calls
            1. -@querystring: 'select id from opportunity' (has no <in> in it )
                -@in_list: list of size one 
            2. -@querystring: 'select name from opportunity where id in <in> 
                -@in_list: empty list
        #### Expected Behaviour: 
            - One the first call the condition regarding missing <in> substring is true, so an exception is thrown
            - on the second call the condition regarding the empty in_list list is true, so an exception is thrown 
        #### Assertions: 
            - The expected exception is raised in each case 
        """
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        with self.assertRaises(Exception) as context:
            resp = resource.large_in_query(querystring='select id from opportunity', in_list=['testing'])
        assert(str(context.exception) == "No <in> found in query -->select id from opportunity<--")
        with self.assertRaises(Exception) as context:
            resp = resource.large_in_query(querystring='select name from oppportunity where id in <in>', in_list=[])
        assert(str(context.exception) == 'in_list is empty')

    @patch('sftocsv.Sftocsv.query_records')
    @patch.object(utils, 'build_in_querystring')
    def test_large_in_query_not_nested(self, mock_build_in_querystring, mock_query_records):
        """
        #### Function: 
            - Sftocsv.large_in_query
        #### Inputs: 
            -@querystring 'select id from opportunity where id in <in>
            -@in_list: non empty list (both not important as it's mocked)
        #### Expected Behaviour:
            - The first call to build_in_querystring returns a remaining_list that is non empty,
                so the while loop is entered. query_records returns a mocked response which is appended to
                the current_records list 
            - the second call to build_in_querystring returns an empty remaining_list,
            - the second call to query_records returns a different set of mocked records, these are appended to the current_records
            - current_records is returned
        #### Assertions: 
            - Build_in_querystring is called twice, with the expected reduction in the remaining_list between them 
            - query_records is called with the expected querystring returned by build_in_querystring
        """
        first_build = ("select id from opportunity where id in ('Id1', 'Id2', 'Id3')", ['Id4', 'Id5', 'Id6'])
        second_build = ("select id from opportunity where id in ('Id4', 'Id5', 'Id6')", [])
        mock_build_in_querystring.side_effect = [first_build, second_build]

        first_result = [{'Id': 'Id1'}, {'Id' : 'Id2'}, {'Id': 'Id3'}]
        second_result = [{'Id': 'Id4'}, {'Id' : 'Id5'}, {'Id': 'Id6'}]
        mock_query_records.side_effect = [first_result, second_result]
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        resp = resource.large_in_query('select id from opportunity where id in <in>', ['Id1', 'Id2', 'Id3', 'Id4', 'Id5', 'Id6'])
        assert resp == [{'Id': 'Id1'}, {'Id' : 'Id2'}, {'Id': 'Id3'},{'Id': 'Id4'}, {'Id' : 'Id5'}, {'Id': 'Id6'}]
        expected_build_calls = [call('select id from opportunity where id in <in>', ['Id1', 'Id2', 'Id3', 'Id4', 'Id5', 'Id6']),
                                call('select id from opportunity where id in <in>', ['Id4', 'Id5', 'Id6'])]
        mock_build_in_querystring.assert_has_calls(expected_build_calls)
        mock_query_records.assert_has_calls([call("select id from opportunity where id in ('Id1', 'Id2', 'Id3')"), 
                                             call("select id from opportunity where id in ('Id4', 'Id5', 'Id6')")])
        
    @patch('sftocsv.Sftocsv.query_records')
    @patch.object(utils, 'build_in_querystring')
    def test_large_in_query_nested(self, mock_build_in_querystring, mock_query_records):
        """
        #### Function: 
            - Sftocsv.large_in_query
        #### Inputs:    
            -@querystring: 'select id from opportunity where id in <in>
            -@in_list: non empty list (both not important as it's mocked)
            -@nested: True
        #### Expected Behaviour: 
            - The first call to build_in_querystring returns a remaining_list that is not empty, 
                so the while loop is entered. query_records returns a mocked response that is combined into current_records
            - the second call to the build_in_querystring returns an empty remaining_list 
            - the second call to query_records returns a different set of mocked records, these are also combined into the current_records
            - current_records is returned as expected
        #### Assertions: 
            - build_in_querystring is called twice, with the expected retuduction in the remaining_list between them 
            - query_records is called with the expected querystring returned by build_in_querystring 
            - the returned records are as expected
        """
        first_build = ("select id from opportunity where id in ('Id1', 'Id2', 'Id3')", ['Id4', 'Id5', 'Id6'])
        second_build = ("select id from opportunity where id in ('Id4', 'Id5', 'Id6')", [])
        mock_build_in_querystring.side_effect = [first_build, second_build]

        first_response = {'Account': [{'Name': 'Test Name', 'Id': 'test_id'}],
                          'Contact': [{'AccountId': 'test_a_id', 'Id': 't_id', 'LastName': 'Test'}]}
        second_response = {'Account': [{'Name': 'Test Name2', 'Id': 'test_id2'}],
                           'Contact': [{'AccountId': 'test_a_id2', 'Id': 't_id2', 'LastName': 'Test2'}]}
        mock_query_records.side_effect = [first_response, second_response]
        resource = Sftocsv(base_url='https://examplecompany.my.salesforce.com', api_version=58.0, access_token='test_token')
        resp = resource.large_in_query('select id from opportunity where id in <in>', ['Id1', 'Id2', 'Id3', 'Id4', 'Id5', 'Id6'], nested=True)
        expected_resp = {'Account': [{'Name': 'Test Name', 'Id': 'test_id'}, {'Name': 'Test Name2', 'Id': 'test_id2'}], 
                         'Contact': [{'AccountId': 'test_a_id', 'Id': 't_id', 'LastName': 'Test'}, {'AccountId': 'test_a_id2','Id': 't_id2', 'LastName': 'Test2'}]}
        assert(resp == expected_resp)
        mock_build_in_querystring.assert_has_calls([call('select id from opportunity where id in <in>', ['Id1', 'Id2', 'Id3', 'Id4', 'Id5', 'Id6']),
                                                    call('select id from opportunity where id in <in>', ['Id4', 'Id5', 'Id6'])])
        mock_query_records.assert_has_calls([call("select id from opportunity where id in ('Id1', 'Id2', 'Id3')"), 
                                             call("select id from opportunity where id in ('Id4', 'Id5', 'Id6')")])

    ### --- records_to_csv tests ---
    @patch.object(utils, 'record_list_dict_to_csv')
    @patch.object(utils, 'record_list_to_csv')
    def test_records_to_csv(self, mock_record_list_to_csv, mock_record_list_dict_to_csv):
        """
        #### Function: 
            - Sftocsv.records_to_csv
        #### Inputs: 
            2 calls
            1. - a list of dicts (representing a non-nested result)
            2. - a dict of list (representing a nested result)
        #### Expected Behaviour: 
            - 1st call, record_list_to_csv is called 
            - 2nd call, record_list_dict_to_csv is called 
        #### Assertions: 
            -1st call record_list_to_csv is called 
            -2nd call record_list_dict_to_csv is called
        """
        Sftocsv.records_to_csv([{}], output_filename='test')
        mock_record_list_to_csv.assert_called_once()
        Sftocsv.records_to_csv({'try': [{}]}, output_filename='test')
        mock_record_list_dict_to_csv.assert_called_once()
    

    ### --- inner_join tests ---
    def test_inner_join_shared_key_single_no_preserve(self):
        """
        #### Function:
            - Sftocsv.inner_join
        #### Inputs:
            -@left_list: a list with dict inside 
            -@right_list: a list with dict inside, it shares a value in a column with left_list
            -@left_key: 'customer_id'
            -@right_key: 'cust_id'
            -@preserve_right_key: False
        #### Expected Behaviour: 
            - the dicts share a value on their respective keys, so they are combined,
            - then because the preserve_right_key is False, the right_key is deleted from 
                the resulting dict 
        #### Assertions:
            - The returned list[dict] is a combination of input_1's dict and input_2's dict, 
                and does not contain the right key
        """
        input_1 = [{"customer_id" : "value1", "key2": "value2", "key3": "value3"}]
        input_2 = [{"cust_id": "value1", "key4": "value4", "key5": "value5"}]
        resp = Sftocsv.inner_join(input_1, input_2, 'customer_id', 'cust_id')
        assert resp == [{"customer_id" : "value1", "key2": "value2", "key3": "value3", "key4" : "value4", "key5": "value5"}]
    
    def test_inner_join_shared_key_single_preserve(self):
        """
        ### Function:
            - Sftocsv.inner_join
        #### Inputs:
            -@left_list: a list with dict inside 
            -@right_list: a list with dict inside, it shares a value in a column with left_list
            -@left_key: 'customer_id'
            -@right_key: 'cust_id'
            -@preserve_right_key: True
        #### Expected Behaviour: 
            - the dicts share a value on their respective keys, so they are combined,
            - then because the preserve_right_key is True, the right_key is maintained in the result
        #### Assertions: 
            - The returned list[dict] is a combination of input_1's dict and input_2's dict, 
                and does contain the right key
        """
        input_1 = [{"customer_id" : "value1", "key2": "value2", "key3": "value3"}]
        input_2 = [{"cust_id": "value1", "key4": "value4", "key5": "value5"}]
        resp = Sftocsv.inner_join(input_1, input_2, 'customer_id', 'cust_id', preserve_right_key=True)
        assert resp == [{"customer_id" : "value1", "key2": "value2", "key3": "value3",
                          "cust_id": "value1", "key4" : "value4", "key5": "value5"}]

    def test_inner_join_empties(self):
        """
         ### Function:
            - Sftocsv.inner_join
        #### Inputs:
            2 calls
            -@left_list: 1st call, a list with a dict inside, second call empty
            -@right_list: 1st call, empty, 2nd call, a list with a dict inside
            -@left_key: 1st call 'customer_id' (found in left_list), 2nd call, 'cust_id' 
            -@right_key: 1st call 'cust_id', 2nd call 'customer_id' (found in right list)
            -@preserve_right_key: True
        #### Expected Behaviour: 
            - Because one dict is present in each case, there is no match on any key, so the returned dict is empty 
        #### Assertions: 
            - The returned list is empty both calls 
        Assert that when inner_join is passed a non-empty left list and an empty right list,
        it will return an empty list
        """
        example_dict = {"customer_id": "value1", "key4": "value4", "key5": "value5"}
        resp = Sftocsv.inner_join([example_dict], [], "customer_id", "cust_id")
        assert resp == []
        resp = Sftocsv.inner_join([], [example_dict], 'cust_id', 'customer_id')
        assert(resp == [])
    
    def test_inner_join_incorrect_keys(self):
        """
        #### Function: 
            - Sftocsv.inner_join
        #### Inputs: 
            2 calls 
            -@left_list: list with 1 dict element
            -@right_list: list with 1 dict element 
            -@left_key: 1st call, a key not found in the left list, 2nd call, a key found in the left list 
            -@right_key: 1st call, a key found in the right list, 2nd call, a key not found in the right list
        #### Expected Behaviour: 
            - On each call the inability to find the key means there is no way the associated values can match,
                so there is no join and the returned list is empty 
        #### Assertions:
            - The returned dict in each case is empty 
        """
        input_1 = [{"customer_id" : "value1", "key2": "value2", "key3": "value3"}]
        input_2 = [{"cust_id": "value1", "key4": "value4", "key5": "value5"}]
        resp = Sftocsv.inner_join(input_1, input_2, "other_id", "never_checked")
        assert resp == []
        resp = Sftocsv.inner_join(input_1, input_2, 'customer_id', 'not_id')
        assert resp == []
        
    def test_inner_join_duplicates(self):
        """
        #### Function: 
            - Sftocsv.inner_join
        #### Inputs: 
            -@left_list: a list with duplicate values in the left_key
            -@right_list: a list with duplicate values in the right_key
            -@left_key: value found in left_list
            -@right_key: value found in right_list
        #### Expected Behaviour: 
            - Because there are 2 rows matching 2 rows on the left/right key, they combine to produce 4 rows
        #### Assertions: 
            - The returned list has 4 rows 
        """
        input_1 = [
            {"customer_id": "value1", "key2": "value2", "key3": "value3"},
            {"customer_id": "value1" , "key4" : "value4", "key5": "value5"}
        ]
        input_2 = [
            {"cust_id": "value1", "key6": "value6", "key7": "value7"},
            {"cust_id": "value1", "key8": "value8", "key9": "value9"}
        ]
        resp = Sftocsv.inner_join(input_1, input_2, "customer_id", "cust_id")
        expected_response = [
            {'customer_id': 'value1', 'key2': 'value2', 'key3': 'value3', "key6": "value6", "key7": "value7"},
            {'customer_id': 'value1', "key2": "value2", "key3": "value3", "key8": "value8", "key9": "value9"},
            {'customer_id': 'value1', "key4": "value4", "key5": "value5", "key6": 'value6', 'key7': 'value7'},
            {'customer_id': 'value1', 'key4': 'value4', 'key5': 'value5', 'key8': 'value8', 'key9' : 'value9'}
        ]
        assert resp == expected_response


    ### --- natural_join tests ---
    def test_natural_join_empties(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs: 
            3 calls
            -@left_list: 1st call, empty, 2nd call, non-empty, 3rd call, empty
            -@right_list: 1st call, non-empty, 2nd all, empty, 3rd call, empty
        #### Expected Behaviour: 
            - In each call, because an empty list cannot have any fields to join on the resulting list should be empty
        #### Assertions: 
            - Each response is an empty list
        """
        resp = Sftocsv.natural_join([], [{'customer_id': 'id1', 'key1': 'value1'}])
        assert resp == []
        resp = Sftocsv.natural_join([{'customer_id': 'id1', 'key1': 'value1'}], [])
        assert resp == []
        resp = Sftocsv.natural_join([],[])
        assert resp == []

    #### --- Inclusive section 
    def test_natural_join_single_match_inclusive(self):
        """
        #### Function:
            - Sftocsv.natural_join
        #### Inputs: 
            -@left_list: list[dict] with one column name shared with matching value with right_list 
            -@right_list: list[dict] with one column name shared with matching value with left list
            -@exclusive: False
        #### Expected Behaviour: 
            - These records have one shared column and it has a matching value, so they are combined and added to the returned list 
        #### Assertions: 
            - The returned list has the one combined result in it 
        """
        input_1 = [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value"}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "matched_value"}]
        resp = Sftocsv.natural_join(input_1, input_2)
        assert resp == [{'customer_id': 'id1', 'key1': "value1", 'key2' : 'value2', 'matched_key': 'matched_value',
                         'cust_id': 'id1', 'key3': 'value3', 'key4': 'value4'}]
    
    def test_natural_join_single_miss_inclusive(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs: 
            -@left_list: list[dict] with no shared columns with right_list
            -@right_list: list[dict] with no shared columns with left_list 
        #### Expected Behaviour: 
            - These records share no column names, no attempt to combine is made, returned list is never 
                added to, it's empty when returned 
        #### Assertions: 
            - The returned list is empty 
        """
        input_1 =  [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "unmatched_value"}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "other_value"}]
        resp = Sftocsv.natural_join(input_1, input_2)
        assert resp == []
         
    def test_natural_join_multi_match_inclusive(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs:
            -@left_list: list[dict], 1 item with 2 column names shared with matching values with right list
            -@right_list: list[dict], 1 item with 2 column names shared with matching values with left list
            -@exclusive: False
        #### Expected Behaviour: 
            - These records have 2 shared columns and the values in these columns match, because it's inclusive only a single value 
                needs to match, so as soon as the matching value is found they're combined and added to the returned list 
        #### Assertions: 
            - The returned list has one combined result in it 
        """
        input_1 = [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2'}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2'}]
        resp = Sftocsv.natural_join(input_1, input_2)
        assert resp == [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2',
                         'cust_id': 'id1', "key3" : "value3", "key4" : "value4"}]


    #### --- Exclusive section 
    def test_natural_join_single_match_exclusive(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs: 
            -@left_list: list[dict], 1 item with 1 column name shared with right list, the value matches in this column
            -@right_list: list[dict] 1 item with 1 column name shared with left list, the value matches in this column 
            -@exclusive: True
        #### Expected Behaviour: 
            - Because it's running in exclusive mode, all matching columnn names are found and it's checked that the values 
                match across these columns. They do, so it combines the records and adds the resulting record to the returned list 
        #### Assertions:
            - the returned list has one combined result in it
        """
        input_1 = [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value"}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "matched_value"}]
        resp = Sftocsv.natural_join(input_1, input_2, exclusive=True)
        assert resp == [{'customer_id': 'id1', 'cust_id': 'id1', 'key1': "value1", 'key2' : 'value2', 'matched_key': 'matched_value',
                         'cust_id': 'id1', 'key3': 'value3', 'key4': 'value4'}]
    
    def test_natural_join_single_miss_exclusive(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs: 
            -@left_list: list[dict] with no shared columns with right_list
            -@right_list: list[dict] with no shared columns with left_list 
            -@exclusive: True
        #### Expected Behaviour: 
            - These records share no column names, no attempt to combine is made, returned list is never 
                added to, it's empty when returned. It being exclusive has no effect on this 
        #### Assertions: 
            - The returned list is empty 
        """
        input_1 =  [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "unmatched_value"}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "other_value"}]
        resp = Sftocsv.natural_join(input_1, input_2, exclusive=True)
        assert resp == []
        
    def test_natural_join_multi_match_exclusive(self):
        """
        #### Function: 
            - Sftocsv.natural_join
        #### Inputs:
            -@left_list: list[dict], 1 item with 2 column names shared with matching values with right list
            -@right_list: list[dict], 1 item with 2 column names shared with matching values with left list
            -@exclusive: True
        #### Expected Behaviour: 
            - These records have 2 shared columns and the values in these columns match, because it's Exclusive it's checked that 
                all values in these shared columns match, they do, so the records are combined and the combined record is   
                added to the returned list 
        #### Assertions: 
            - The returned list has one combined result in it 
        """
        input_1 = [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2'}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2'}]
        resp = Sftocsv.natural_join(input_1, input_2, exclusive=True)
        assert resp == [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value", 'matched_key_2': 'matched_value2',
                         'cust_id': 'id1', "key3" : "value3", "key4" : "value4"}]
    
    def test_natural_join_multi_semimatch_exclusive(self):
        """
        #### Function:
            - Sftocsv.natural_join
        #### Inputs: 
            -@left_list: list[dict], 1 item with 2 column names shared with right_list, only 1 value shared
            -@right_list: list[dict], 1 item with 2 column names shared with left_list, only 1 value shared
            -@exclusive: True
        #### Expected Behaviour: 
            - These records have 2 shared column names, not all of these values match in the shared columns, 
                so the records are not combined, the returned list is empty
        #### Assertions: 
            - the returned list is empty  
        """
        input_1 = [{'customer_id': 'id1', "key1": "value1", "key2": "value2", 'matched_key': "matched_value", 'matched_key_2': 'no_match'}]
        input_2 = [{'cust_id': 'id1', "key3" : "value3", "key4" : "value4", 'matched_key': "matched_value", 'matched_key_2': 'not_here'}]
        resp = Sftocsv.natural_join(input_1, input_2, exclusive=True)
        assert resp == []   


    ### --- outer join tests --- 
    def test_outer_join_exception(self):
        """
        #### Function: 
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: empty (not necessary)
            -@right_list: empty,
            -@left_key: 'test key'
            -@right_key: 'test key'
            -@side: 'other'
        #### Expected Behaviour: 
            - Because the entered 'side' value is not recognised an exception is thrown 
        #### Assertions: 
            - The expected exception is thrown 
        """
        with self.assertRaises(Exception) as context:
            resp = Sftocsv.outer_join([], [], 'test key', 'test key', 'other')
        assert(str(context.exception) == 'outer_join requires one of ("left", "right", "full") in "side" argument')
    
    def test_outer_join_left(self):
        """
        #### Function: 
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: 'lkey' 
            -@right_key: 'rkey' 
            -@side: 'left'
            -@preserve_inner_key: False
        #### Expected Behaviour: 
            - The left_list is selected as the outer list, the right_list as the inner. 
            - the lists are looped through, the first record in the outer list matches the second in the inner, 
                these are combined and added the returned list. 
            - the second record in the outer list doesn't match anything, so it's just added the resulting list 
            - the third record in the outer matches 2 records in the inner, this results in 2 records added to the resulting list 
            - because preserve_inner_key is False, the inner matching key is not kept 
        #### Assertions: 
            - The returned list is as expected
        """
        input_left = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c'}]
        input_right = [{'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, 
                                  left_key='lkey', right_key='rkey', side='left')
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a', 'key3': 'val1e', 'key4': 'val2e'},
                           {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1f', 'key4': 'val2f'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1g', 'key4': 'val2g'}]
        assert resp == expected_result
    
    def test_outer_join_left_preserve(self):
        """
        #### Function: 
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: 'lkey' 
            -@right_key: 'rkey' 
            -@side: 'left'
            -@preserve_inner_key: True
        #### Expected Behaviour: 
            - The left_list is selected as the outer list, the right_list as the inner. 
            - the lists are looped through, the first record in the outer list matches the second in the inner, 
                these are combined and added the returned list. 
            - the second record in the outer list doesn't match anything, so it's just added the resulting list 
            - the third record in the outer matches 2 records in the inner, this results in 2 records added to the resulting list 
            - because preserve_inner_key is true, it keeps the inner key in each resulting record 
        #### Assertions: 
            - The returned list is as expected
        """
        input_left = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c'}]
        input_right = [{'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, 
                                  left_key='lkey', right_key='rkey', side='left', preserve_innner_key=True)
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a', 'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                           {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'}]
        assert resp == expected_result

    def test_outer_join_right(self):
        """
        #### Function: 
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: 'lkey' 
            -@right_key: 'rkey' 
            -@side: 'right'
            -@preserve_inner_key: False
        #### Expected Behaviour: 
            - The right_list is selected as the outer list, the left_list as the inner. 
            - the lists are looped through, the first record in the outer list matches the second in the inner, 
                these are combined and added the returned list. 
            - the second record in the outer list doesn't match anything, so it's just added the resulting list 
            - the third record in the outer matches 2 records in the inner, this results in 2 records added to the resulting list 
            - because preserve_inner_key is False, the inner matching key is not kept 
        #### Assertions: 
            - The returned list is as expected
        """
        input_right = [{'key1': 'val1a', 'key2': 'val2a', 'rkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'rkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c'}]
        input_left = [{'key3': 'val1d', 'key4': 'val2d', 'lkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'lkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'lkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'lkey': 'c'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, 
                                  left_key='lkey', right_key='rkey', side='right')
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'rkey': 'a', 'key3': 'val1e', 'key4': 'val2e'},
                           {'key1': 'val1b', 'key2': 'val2b', 'rkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c', 'key3': 'val1f', 'key4': 'val2f'},
                           {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c', 'key3': 'val1g', 'key4': 'val2g'}]
        assert resp == expected_result

    def test_outer_join_right_preserve(self):
        """
        #### Function: 
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict] 
            -@left_key: 'lkey' 
            -@right_key: 'rkey' 
            -@side: 'left'
            -@preserve_inner_key: True
        #### Expected Behaviour: 
            - The right_list is selected as the outer list, the left_list as the inner. 
            - the lists are looped through, the first record in the outer list matches the second in the inner, 
                these are combined and added the returned list. 
            - the second record in the outer list doesn't match anything, so it's just added the resulting list 
            - the third record in the outer matches 2 records in the inner, this results in 2 records added to the resulting list 
            - because preserve_inner_key is true, it keeps the inner key in each resulting record 
        #### Assertions: 
            - The returned list is as expected
        """
        input_right = [{'key1': 'val1a', 'key2': 'val2a', 'rkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'rkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c'}]
        input_left = [{'key3': 'val1d', 'key4': 'val2d', 'lkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'lkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'lkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'lkey': 'c'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, 
                                  left_key='lkey', right_key='rkey', side='right', preserve_innner_key=True)
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'rkey': 'a', 'key3': 'val1e', 'key4': 'val2e', 'lkey': 'a'},
                           {'key1': 'val1b', 'key2': 'val2b', 'rkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c', 'key3': 'val1f', 'key4': 'val2f', 'lkey': 'c'},
                           {'key1': 'val1c', 'key2': 'val2c', 'rkey': 'c', 'key3': 'val1g', 'key4': 'val2g', 'lkey': 'c'}]
        assert resp == expected_result

    def test_outer_join_full(self):
        """
        #### Function:
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: 'lkey'
            -@right_key: 'rkey'
            -@side: 'full'
            -@preserve_inner_key: False
        #### Expected Behaviour: 
            - the 'outer' list is set to the left_list, it then goes through and matches against records in the right_list, 
                any match removes the right_list record index from the unmatched_inner set. 
            - After this matching process, the return_list should contain all left_list records and their matches against right_list,
                any unmatched records from the right_list then need to be added, and they are found using the indexes stored in the unmatched_inner
                set. They're appended the return_list and returned 
        #### Assertions: 
            - The returned lsit is as expected 
        """
        input_left = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c'}]
        input_right = [{'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'},
                       {'key3': 'val1h', 'key4': 'val2h', 'rkey': 'z'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, left_key='lkey', right_key='rkey', side='full')
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a', 'key3': 'val1e', 'key4': 'val2e'},
                           {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1f', 'key4': 'val2f'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1g', 'key4': 'val2g'},
                           {'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                           {'key3': 'val1h', 'key4': 'val2h', 'rkey': 'z'}]
        assert resp == expected_result

    def test_outer_join_full_preserve(self):
        """
        #### Function:
            - Sftocsv.outer_join
        #### Inputs: 
            -@left_list: list[dict]
            -@right_list: list[dict]
            -@left_key: 'lkey'
            -@right_key: 'rkey'
            -@side: 'full'
            -@preserve_inner_key: True
        #### Expected Behaviour: 
            - the 'outer' list is set to the left_list, it then goes through and matches against records in the right_list, 
                any match removes the right_list record index from the unmatched_inner set. 
            - After this matching process, the return_list should contain all left_list records and their matches against right_list,
                any unmatched records from the right_list then need to be added, and they are found using the indexes stored in the unmatched_inner
                set. They're appended the return_list and returned 
            - because the preserve_inner_key is true, it keeps the right_list key
        #### Assertions: 
            - The returned list is as expected 
        """
        input_left = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a'},
                      {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                      {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c'}]
        input_right = [{'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                       {'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                       {'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                       {'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'},
                       {'key3': 'val1h', 'key4': 'val2h', 'rkey': 'z'}] 
        resp = Sftocsv.outer_join(left_list=input_left, right_list=input_right, left_key='lkey', right_key='rkey', side='full', preserve_innner_key=True)
        expected_result = [{'key1': 'val1a', 'key2': 'val2a', 'lkey': 'a', 'key3': 'val1e', 'key4': 'val2e', 'rkey': 'a'},
                           {'key1': 'val1b', 'key2': 'val2b', 'lkey': 'b'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1f', 'key4': 'val2f', 'rkey': 'c'},
                           {'key1': 'val1c', 'key2': 'val2c', 'lkey': 'c', 'key3': 'val1g', 'key4': 'val2g', 'rkey': 'c'},
                           {'key3': 'val1d', 'key4': 'val2d', 'rkey': 'd' },
                           {'key3': 'val1h', 'key4': 'val2h', 'rkey': 'z'}]
        assert resp == expected_result

 