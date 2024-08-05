## Sftocsv

## Salesforce queries made easy

## Purpose of library 
Query salesforce with a very easy interface, request results are transformed 
into a list of dicts, making list comprehension on results a breeze.  

Has built in __inner__, __natural__, and __outer__ joins with no non-standard dependencies. Perfect for creating 
reports by joining tables without needing to learn any extra data structures. 

Nested queries are even better, each record type is read into a list of its own, with the parent record id stored in it.  
No need to dive into nested json, access the results based on their data type instead. 

---

Want a CSV with just the emails from contacts on opportunities that are Parked? __It's 2 lines of code.__ 

Want 2 lists of entirely unrelated records to be joined on their shared emails, then a csv output? __It's 4 lines away.__  

Want to filter results on the content of their rich text? __1 query, 1 list comprehension, then write to csv.__  

### Getting started 
The library relies on using a credentials flow for a connected app. 
If you have a consumer key and a consumer secret you're ready to go, keep reading. If you don't have these, go [here](#1-creating-connected-app)

##
### Installation 
```pip install sftocsv```  
You're ready! It has no non-standard dependencies. 

Creating a .py file with this content is enough to test everything is set up properly.  
```from sftocsv import Sftocsv, utils
base_url = '' #put yours in
consumer_key = '' #put yours in
consumer_secret = '' #put yours in
api_v = 58.0 #replace with your float ()
### if you have an access_token from some other method, replace utils.get_access_token with it 
access_token = utils.get_access_token(base_url=base_url, c_key=consumer_key, c_secret=consumer_secret)
###
resource = Sftocsv(base_url=base_url, api_version=api_v, access_token=access_token)
resp = resource.query_records('select id, name, email from lead limit 10')
resource.records_to_csv(resp, output_filename='test.csv')
```
Assuming you have leads in your org, this will create a csv of the first 10 leads

## Appendix 
All methods use docstrings for more detailed explanation of how you _can_ use each one.   
This is more of an explanation of how you probably _want_ to use each one. 

### Sftocsv methods  
    -class methods unless otherwise specified

#### \_\_init\_\_(base_url, *str*, api_version: *float*, acces_token: *str*, tokenless: *bool*):
Simple instantiation, __base_url__ and __api_version__ are used in all request urls.  
Either pass your __access_token__ in to do requests, or pass __tokenless__=_True_ if you just want to use the joins 
#### query_records(self, querystring: *str*, nested: *bool*):
The workhorse of the library. Pass in a sql __querystring__, it will make it url safe and paginate the request for you if required.  
It requires an __access_token__ in the instance of __Sftocsv__ that uses it; __access_token__ management is handled by the utils (link to) class.  
The important differentiator is that it returns results as list of dicts. I.e
``` 
[{'Id': '001', 'Name': 'Testing', 'Email': 'Test@gmail.com'}, 
{'Id': '002', 'Name': 'Example', 'Email': 'Example@gmail.com'}]
```
This obviously makes list comprehension easy.  
Say for example I want to query leads for their notes__c which happens to be a rich text field and therefore unfilterable. It can be done thusly:
```
resource = Sftocsv(base_url=base_url, api_version=58.0, access_token=access_token)
resp = resource.query_records(querystring='select id, notes__c from lead')
resp = [x for x in resp where 'substring I want' in x]
resource.records_to_csv(resp) ## if we want it in a csv as well 
```
##### Nested queries 
The other major feature here is the handling of nested queries. The result of a nested query 
    for example 
```
select id from opportunity (select id, contact.name from opportunityContactRoles) from opportunity
```
This results in a dict of lists of dicts. Imagine the result of the simple query shown above, but it's stored in a dict under the
key of its record type. 
This means our nested query above would create a dict like this 
```
{
    'Opportunity': [...],
    'OpportunityContactRole': [...],
    'Contact': [...]
}
```
As well as them being split into these lists, each record has its parent record stored in it under the key of its type. 
So all the contacts will have a key 'OpportunityContactRole' and the value will be the Id of the parent. 


When using nested queries, we just need to pass in __nested__ : = True.   
When using __records_to_csv__: on a nested result. It will create a csv file for each of the record types. 

#### large_in_query(self, querstring: *str*, in_list: *list[]*, nested: *bool*):
This one is partially here to put the fun in function.   
Because queries are limited to 20,000 characters, building a big query that uses the in 'in' operator
can easily lead you to run up against the limits.  
This function circumvents that by splitting the 
query up and combining the results.  
And sure writing massive in queries is not optimal SQL, but sometimes you just need to do it.  
Use it by writing your in query and entering \<in\> where you want your _in\_list_ to be subbed in.  
For example 
```Select id from opportunity where name in (<in>)``` Would be the _querystring_   
and 
```['name_1', 'name_2', 'name_3']``` would be the _in\_list_.  
It works even for small in queries, it's just an easy way of building them. The results are the same as 
the normal *query_records*, and _nested_ argument has the same effect. 

### Joins
Bringing joins back to salesforce is one of the main reasons this library was written.  
I've included the most useful ones. They work on the result of the *query_records* and *large_in_query* results. That is a list of dicts. If you want to join the result of a nested query, you have to pick the record lists to use then pass it into the join.  
These all work even if you don't have a token stored in the Sftocsv instance. They're static methods. 

#### inner_join(left_list: *list[dict]*, right_list: *list[dict]*, left_key: *str*, right_key: *str, preserve_right_key: *bool*):  
This does what it says on the tin, performs an __INNER__ join on the lists.  
It joins based on shared values, left_key is used to match values on the _left_list_ with values from the _right_list_ on the _right_key_. All values of these records are pulled into the resulting record. 
The result is a list[dict] with all the combined records.  
_preserve_right_key_ will keep the right_key if you want it, but as it's going to share the value of the left_key it's not usually necessary, so it defaults to False. 

#### natural_join(left_list: *list[dict]*, right_list: *list[dict]*, exclusive: *bool*):  
This is a less-often used function because it's mostly exploratory. You basically use it if you want to find any commonality between 2 lists of records.  
It runs in 2 modes, defined by exclusive being either *True* or *False*.   
*Inclusive Mode* (exclusive = False) (default)  
In this mode, any shared key that is found between any two records in the lists that has a shared value will count as a match and will be included in the result.  
For example these 2 records will match in inclusive mode:   
```{'key_1': 'a', 'key_2': b, 'key_3': 'c'}, {'key_1', 'a', 'other_key': 'd', 'key_3': 'e'}```  
the presence of the shared value in the shared key *key_1* means its a match even though the shared key *key_3* does not have a matching value.  
*Exclusive Mode* (exclusive = True)  
In this mode, ALL shared keys must share their value between two records in the lists to be considered a match.  
The above example would not be considered a match in this mode but this example would:    
```{'key_1': 'a', 'key_2': b, 'key_3': 'c'}, {'key_1', 'a', 'other_key': 'd', 'key_3': 'c'}```  
If you're running in exclusive mode and have primary keys, you're unlikely to get any matches, you probably want to strip that off before using this function.  
Again the result is a list[dict] of combined records in both modes. 

#### outer_join(left_list: *list[dict]*, right_list: *list[dict]*, left_key: *str*, right_key: *str*, side: *str*, preserve_inner_key: *bool*):  
Performs an __OUTER__ join. Which preserves all records from the side you specify, and any matches found with the otherside.  
You specify if it's a __left__, __right__, or __full__ join by entering one of these strings in the 'side' argument.  
It joins records based on a shared value in their respective keys. 
If you set *preserve_inner_key* to True then the list not specified as the *side* will keep its key in the combined record. If it's the same key then set it to False, no point in keeping it twice.   

### Utils 

#### get_access_token: 
    This should be the first function you use from the whole library. It'll get you your access token. 
    If it works, switch to using collect_token. 

#### collect_token: 
    This _should_ be the only method you need to use from utils. It collects your token and stores it in a 
    token_store location. Either pass in your own token store 
    If your token is ever stale or you change your org, then you may use ...
#### flush_token store: 
    Clears the token_store. 

## 1. Creating Connected App
### 1.1 Go to App Manager  
![Go to App Manager](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/1.png?raw=true)
### 1.2 Create a New Connected App  
![Click 'New Connect App'](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/2.png?raw=true)  
Name it as you wish, for this I'm naming mine Sftocsv, nothing non-mandatory is required in this section.  
![Name your app](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/3.png?raw=true)
### 1.3 Adjust Connected App Settings
Make them match the details in this screenshot.  
![Adjust your settings](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/4.png?raw=true)  
Enabling OAuth settings will expand the section once ticked.  
The callback url I use is ```https://login.salesforce.com/services/oauth2/success```  
Making sure 'Enable Client Credentials Flow' is ticked and all the OAuth scopes are selected as shown.  
This is the first step of creating the connected app. 
Now we're going to create an API only user. This is the safest way of granting access. 
## 2. Creating API USER 
### 2.1 Creating the profile.
Create a profile, I've named my API ONLY. The important settings to enable are in the __Administrative Permission__ section, 
tick API Enabled and API Only User.  
![Profile Settings](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/5.png?raw=true) (check this)
### 2.2 Create a user.
Ensure they at least have a Salesforce licence and give them the profile you've just created.   
Optionally this can be done through a permission set, under System Permissions ticking the same values and assigning the permission set to your API ONLY user.   
![Optional permission set](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/6.png?raw=true)
## 3. Finishing Connected App 
### 3.1 Set Client Credentials Flow 'Run As' user: 
Go back to the app manager
Click 'Manage' on the dropdown  
Set the Client Credentials flow 'Run As' user at the bottom of the page to your API User  
![Change 'Run As' to API User](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/7.png?raw=true)
### 3.2 Get Consumer Details
Go back to app manager  
Click 'View' on the dropdown and then click 'Manage Consumer Details'.   
![Manage Consumer Details](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/8.png?raw=true)  
After authenticating you will be provided a screen with Consumer Key and Consumer Secret, these are the details required for your login.  
![Consumer Details](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/9.png?raw=true)  
The other details you'll need are your api version and your base url. Open up your dev console and run this anonyous apex 
```
String baseUrl = URL.getOrgDomainUrl().toExternalForm();
system.debug(baseUrl);
```
This will debug the base url string, and in the logs will show you'll see your api version as well. 
![Api version](https://github.com/phillipharryt/sftocsv/blob/main/.sftocsvpics/10.png?raw=true) 

--- 
From this point it's assumed you either have an __access_token__ or a __consumer_key__,__consumer secret__,__base_url__, and __api_version__. You're ready to go back to [here](#installation)