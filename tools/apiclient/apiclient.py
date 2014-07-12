#!/usr/bin/python

"""
The MIT License

Copyright (c) 2012 Matthew Neale

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

A command-line utility for invoking the Resighting API.

Use the options to specify the correct parameters for the API method you wish to invoke.
To see which options are required for the API method, see the API documentation at
http://resighting.wikia.com/wiki/API.

For more documentation of this script and examples see
http://resighting.wikia.com/wiki/Apiclient.py.

Requires Python 2.7.

Usage: apiclient.py server-url method [options]

Arguments:
  server-url            The url of the server where the API is running,
                        e.g. https://resighting-api.appspot.com
  method                The name of the API to invoke. See list below.

Methods:
  CreateLocator
  CreateLocatorSighting
  CreateSighting
  GetDailySighting
  GetSighting
  GetUser
  GetUserStatistics
  ListLocators
  ListLocatorSightings
  ListResightings
  ListSightingLocators
  ListSightings
  ListUserCountryStatistics
  ListUserLocators
  ListUserSightings
  Meta
  RemoveLocatorSighting
  ResightSighting
  UpdateSighting
  Upload
  UploadUrl
  User

Options:
  -h, --help            show this help message and exit
  --access-token=ACCESS_TOKEN
                        An API access token
  --accuracy=ACCURACY   The accuracy of a latitude and longitude in metres
  --altitude=ALTITUDE   An altitude in metres
  --altitude-accuracy=ALTITUDE_ACCURACY
                        The accuracy of an altitude reading in metres
  --blobtracker-id=BLOBTRACKER_ID
                        A blobtracker id returned by the Upload API
  --closed              A closed locator requiring approval to join
  --cursor=CURSOR       A cursor returned by a previous call to the method
                        marking the point where listing should continue from
  --date=DATE           A date in the format YYYY-MM-DD
  --description=DESCRIPTION
                        A description
  --fetch-size=FETCH_SIZE
                        The number of results to retrieve
  --filename=FILENAME   A file to upload
  --heading=HEADING     A heading
  --hold                Place a Sighting on hold
  --latitude=LATITUDE   A latitude
  --list-type=LIST_TYPE
                        The type of list to request: latest or nearest
                        Sightings
  --locator-id=LOCATOR_ID
                        A Locator id. Multiple can be specified.
  --longitude=LONGITUDE
                        A longitude
  --name=NAME           A name
  --no-hold             Do not place a Sighting on hold
  --no-publish-to-facebook
                        Do not publish a Sighting to the user's Facebook wall
  --no-tweet-sighting   Do not tweet a Sighting
  --options             Send an OPTIONS HTTP request to the server
  --publish-to-facebook
                        Publish a Sighting to the user's Facebook wall
  --sandbox             Invoke the API in sandbox mode
  --sighting-id=SIGHTING_ID
                        A Sighting id
  --speed=SPEED         A speed
  --tweet-sighting      Tweet a Sighting
  --tz-offset=TZ_OFFSET
                        The number of minutes that the user's timezone is
                        offset from UTC. Valid values are from -720
                        (UTC-12:00) to 840 (UTC+14:00).
  --upload-url=UPLOAD_URL
                        The url to upload the file to
  --user-id=USER_ID     A user's id
"""

import datetime
import httplib
import json
import socket
import sys
import urllib
import urllib2
import urlparse

from optparse import OptionParser

# The base path to version 1 of the API
_API_ROOT_PATH = 'api/1'

class Error(Exception):
    """Exception for raising all errors within the module.
    """
    pass

def encode_post_data(params, files=None):
    """Create POST data for an HTTP request.
    
    If the files argument is None then the parameters specified in the params
    argument are added to the post data in x-www-form-urlencode form. If the
    files argument is not None then a multipart/form-data post is constructed
    containing the files and parameters.
    
    Arguments:
    params - A dictionary containing any required HTTP parameters. The key is used
             as the parameter name and the value is the parameter value. If the
             parameter value is a list or a tuple then multiple parameters are
             added to the request each with the same name, one for each value in
             the list/tuple.
    files - (optional) A dictionary containing files to be added to the request.
            The key is used as the parameter name and filename in the request and the
            value is the file data. If the parameter value is a list or a tuple then
            multiple files are added to the request each with the same name, one for
            each value (file data) in the list/tuple.
    
    Returns:
    A tuple containing first the POST data and second the content type.
    """
    data = None
    content_type = None

    if files is None:
        # application/x-www-form-urlencoded
        data = ''
        content_type = 'application/x-www-form-urlencoded charset=utf-8'

        if params is not None:
            for name, value in params.viewitems():
                # The value can be a list or tuple of multiple values.
                # In this case we added multiple parameters to the request, each with the
                # same name.
                if isinstance(value, (list, tuple)):
                    multi_value = value
                else:
                    multi_value = [value]
            
                for i_value in multi_value:
                    if len(data) > 0:
                        data += '&'

                    if i_value is None:
                        data += '%s=' % (urllib.quote_plus(name))
                    else:
                        data += '%s=%s' % (urllib.quote_plus(name), urllib.quote_plus(i_value))
    else:
        # multipart/form-data
        boundary = 'c281a12c-c3e2-4c17-969b-9dbf859af2ee'
        data = ''
        content_type = 'multipart/form-data; boundary=%s' % boundary

        # Add HTTP parameters
        if params is not None:
            for name, value in params.viewitems():
                # The value can be a list or tuple of multiple values.
                # In this case we added multiple parameters to the request, each with the
                # same name.
                if isinstance(value, (list, tuple)):
                    multi_value = value
                else:
                    multi_value = [value]
            
                for i_value in multi_value:
                    data += '\r\n--%s\r\n' % boundary
                    data += 'Content-Disposition: form-data; name="%s"\r\n\r\n' % urllib.quote_plus(name)
                    
                    if i_value is not None:
                        data += urllib.quote_plus(i_value)

        # Add any files to be uploaded
        if files is not None:
            for name, file_data in files.viewitems():
                # The file data can be a list or tuple of data from multiple files.
                # In this case we added multiple files to the request, each with the
                # same name.
                if isinstance(file_data, (list, tuple)):
                    multi_file_data = file_data
                else:
                    multi_file_data = [file_data]
            
                for i_file_data in multi_file_data:
                    data += '\r\n--%s\r\n' % boundary
                    data += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (urllib.quote_plus(name), urllib.quote_plus(name))
                    data += 'Content-Type: application/octet-stream\r\n\r\n'
                    
                    if i_file_data is not None:
                        data += i_file_data

        # Add final boundary
        data += '\r\n--%s--\r\n' % boundary

    return data, content_type

# The following api_* functions take the url of the server where the API is
# running and the options specified on the command-line and return a tuple
# containing the url for the particular API method, the POST data to send
# with the request and the POST data content type. For GET requests the latter
# two are None.

def api_createlocator(server_url, opts):
    """Construct the url and POST data for a call to the CreateLocator API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    method_url = u'{0}/{1}/locators'.format(server_url, _API_ROOT_PATH)

    params = {}
    
    if opts.access_token is not None:
        params[u'access_token'] = opts.access_token

    if opts.closed:
        params[u'closed'] = 'true'

    if opts.description is not None:
        params[u'description'] = opts.description

    if opts.name is not None:
        params[u'name'] = opts.name

    if opts.sandbox:
        params[u'sandbox'] = 'true'

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_createlocatorsighting(server_url, opts):
    """Construct the url and POST data for a call to the CreateLocatorSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    # The url requires a locator_id so this is mandatory
    if opts.locator_id is None:
        raise Error('A locator-id is required for this API method')
    
    method_url = '%s/%s/locators/%s/sightings' % (server_url, _API_ROOT_PATH, opts.locator_id[0])
    
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.sandbox:
        params['sandbox'] = 'true'

    if opts.user_id is not None:
        params['user_id'] = opts.user_id
        
    if opts.sighting_id is not None:
        params['sighting_id'] = opts.sighting_id

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_createsighting(server_url, opts):
    """Construct the url and POST data for a call to the CreateSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    method_url = '%s/%s/sightings' % (server_url, _API_ROOT_PATH)

    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.accuracy is not None:
        params['accuracy'] = opts.accuracy

    if opts.altitude is not None:
        params['altitude'] = opts.altitude

    if opts.altitude_accuracy is not None:
        params['altitude_accuracy'] = opts.altitude_accuracy

    if opts.blobtracker_id is not None:
        params['blobtracker_id'] = opts.blobtracker_id

    if opts.description is not None:
        params['description'] = opts.description

    if opts.heading is not None:
        params['heading'] = opts.heading

    if opts.hold:
        params['hold'] = 'true'

    if opts.latitude is not None:
        params['latitude'] = opts.latitude

    if opts.locator_id is not None:
        params['locator_id'] = opts.locator_id

    if opts.longitude is not None:
        params['longitude'] = opts.longitude

    if opts.publish_to_facebook:
        params['publish_to_facebook'] = 'true'

    if opts.sandbox:
        params['sandbox'] = 'true'

    if opts.speed is not None:
        params['speed'] = opts.speed

    if opts.tweet_sighting:
        params['tweet_sighting'] = 'true'

    if opts.tz_offset is not None:
        params['tz_offset'] = opts.tz_offset

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_getdailysighting(server_url, opts):
    """Construct the url for a call to the GetDailySighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no date was specified on the command-line or if the date is not
    a valid date.
    """
    # The url requires a date so this is mandatory
    if opts.date is None:
        raise Error('A date is required for this API method')
    
    # Check the date is a valid date
    d = None
    try:
        d = datetime.datetime.strptime(opts.date, '%Y-%m-%d')
    except ValueError:
        raise Error('The date is invalid')
    
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    method_url = '%s/%s/dailysightings/%04d/%02d/%02d?%s' % (server_url, _API_ROOT_PATH, d.year, d.month, d.day, urllib.urlencode(params))

    return method_url, None, None

def api_getsighting(server_url, opts):
    """Construct the url for a call to the GetSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id or sighting_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')
        
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    method_url = '%s/%s/sightings/%s/%s?%s' % (server_url, _API_ROOT_PATH, opts.user_id, opts.sighting_id, urllib.urlencode(params))

    return method_url, None, None

def api_getuser(server_url, opts):
    """Construct the url for a call to the GetUser API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
    
    params = {}
    if opts.access_token is not None:
        params['access_token'] = opts.access_token
    
    method_url = '%s/%s/users/%s?%s' % (server_url, _API_ROOT_PATH, opts.user_id, urllib.urlencode(params))
    
    return method_url, None, None

def api_getuserstatistics(server_url, opts):
    """Construct the url for a call to the GetUserStatistics API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
    
    params = {}
    if opts.access_token is not None:
        params['access_token'] = opts.access_token
    
    method_url = '%s/%s/users/%s/statistics?%s' % (server_url, _API_ROOT_PATH, opts.user_id, urllib.urlencode(params))
    
    return method_url, None, None

def api_listlocators(server_url, opts):
    """Construct the url for a call to the ListLocators API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    """
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    method_url = '%s/%s/locators?%s' % (server_url, _API_ROOT_PATH, urllib.urlencode(params))

    return method_url, None, None

def api_listlocatorsightings(server_url, opts):
    """Construct the url for a call to the ListLocatorSightings API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no locator_id was specified on the command-line.
    """
    # The url requires a locator_id so this is mandatory
    if opts.locator_id is None:
        raise Error('A locator-id is required for this API method')
    
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    if opts.latitude is not None:
        params['latitude'] = opts.latitude

    if opts.list_type is not None:
        params['list_type'] = opts.list_type

    if opts.longitude is not None:
        params['longitude'] = opts.longitude

    method_url = '%s/%s/locators/%s/sightings?%s' % (server_url, _API_ROOT_PATH, opts.locator_id[0], urllib.urlencode(params))

    return method_url, None, None

def api_listresightings(server_url, opts):
    """Construct the url for a call to the ListResightings API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id or sighting_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')
        
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    method_url = '%s/%s/sightings/%s/%s/resightings?%s' % (server_url, _API_ROOT_PATH, opts.user_id, opts.sighting_id, urllib.urlencode(params))

    return method_url, None, None

def api_listsightinglocators(server_url, opts):
    """Construct the url for a call to the ListSightingLocators API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id or sighting_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')
        
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    method_url = '%s/%s/sightings/%s/%s/locators?%s' % (server_url, _API_ROOT_PATH, opts.user_id, opts.sighting_id, urllib.urlencode(params))

    return method_url, None, None

def api_listsightings(server_url, opts):
    """Construct the url for a call to the ListSightings API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    """
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    if opts.latitude is not None:
        params['latitude'] = opts.latitude

    if opts.list_type is not None:
        params['list_type'] = opts.list_type

    if opts.longitude is not None:
        params['longitude'] = opts.longitude

    method_url = '%s/%s/sightings?%s' % (server_url, _API_ROOT_PATH, urllib.urlencode(params))

    return method_url, None, None

def api_listusercountrystatistics(server_url, opts):
    """Construct the url for a call to the ListUserCountryStatistics API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
    
    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    method_url = '%s/%s/users/%s/statistics/countries?%s' % (server_url, _API_ROOT_PATH, opts.user_id, urllib.urlencode(params))

    return method_url, None, None

def api_listuserlocators(server_url, opts):
    """Construct the url for a call to the ListUserLocators API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
    
    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    method_url = '%s/%s/users/%s/locators?%s' % (server_url, _API_ROOT_PATH, opts.user_id, urllib.urlencode(params))

    return method_url, None, None

def api_listusersightings(server_url, opts):
    """Construct the url for a call to the ListUserSightings API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    
    Raises:
    Error if no user_id was specified on the command-line.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
    
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.cursor is not None:
        params['cursor'] = opts.cursor

    if opts.fetch_size is not None:
        params['fetch_size'] = opts.fetch_size

    if opts.latitude is not None:
        params['latitude'] = opts.latitude

    if opts.list_type is not None:
        params['list_type'] = opts.list_type

    if opts.longitude is not None:
        params['longitude'] = opts.longitude

    method_url = '%s/%s/users/%s/sightings?%s' % (server_url, _API_ROOT_PATH, opts.user_id, urllib.urlencode(params))

    return method_url, None, None

def api_meta(server_url, opts):
    """Construct the url for a call to the Meta API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    """
    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    method_url = '%s/%s/meta?%s' % (server_url, _API_ROOT_PATH, urllib.urlencode(params))

    return method_url, None, None

def api_removelocatorsighting(server_url, opts):
    """Construct the url and POST data for a call to the RemoveLocatorSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    # The url requires a locator_id so this is mandatory
    if opts.locator_id is None:
        raise Error('A locator-id is required for this API method')
        
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')

    method_url = '{0}/{1}/locators/{2}/sightings/{3}/{4}/remove'.format(server_url, _API_ROOT_PATH, opts.locator_id[0], opts.user_id, opts.sighting_id)
    
    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.sandbox:
        params['sandbox'] = 'true'

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_resightsighting(server_url, opts):
    """Construct the url and POST data for a call to the ResightSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')
    
    method_url = '%s/%s/sightings/%s/%s/resightings' % (server_url, _API_ROOT_PATH, opts.user_id, opts.sighting_id)

    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.accuracy is not None:
        params['accuracy'] = opts.accuracy

    if opts.altitude is not None:
        params['altitude'] = opts.altitude

    if opts.altitude_accuracy is not None:
        params['altitude_accuracy'] = opts.altitude_accuracy

    if opts.blobtracker_id is not None:
        params['blobtracker_id'] = opts.blobtracker_id

    if opts.description is not None:
        params['description'] = opts.description

    if opts.heading is not None:
        params['heading'] = opts.heading

    if opts.hold:
        params['hold'] = 'true'

    if opts.latitude is not None:
        params['latitude'] = opts.latitude

    if opts.locator_id is not None:
        params['locator_id'] = opts.locator_id

    if opts.longitude is not None:
        params['longitude'] = opts.longitude

    if opts.publish_to_facebook:
        params['publish_to_facebook'] = 'true'

    if opts.sandbox:
        params['sandbox'] = 'true'

    if opts.speed is not None:
        params['speed'] = opts.speed

    if opts.tweet_sighting:
        params['tweet_sighting'] = 'true'

    if opts.tz_offset is not None:
        params['tz_offset'] = opts.tz_offset

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_updatesighting(server_url, opts):
    """Construct the url and POST data for a call to the UpdateSighting API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    # The url requires a user_id so this is mandatory
    if opts.user_id is None:
        raise Error('A user-id is required for this API method')
        
    # The url requires a sighting_id so this is mandatory
    if opts.sighting_id is None:
        raise Error('A sighting-id is required for this API method')
    
    method_url = '%s/%s/sightings/%s/%s' % (server_url, _API_ROOT_PATH, opts.user_id, opts.sighting_id)

    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.blobtracker_id is not None:
        params['blobtracker_id'] = opts.blobtracker_id

    if opts.description is not None:
        params['description'] = opts.description

    if opts.hold is not None:
        # We can either set or unset the hold flag
        if opts.hold:
            params['hold'] = 'true'
        else:
            params['hold'] = 'false'

    if opts.publish_to_facebook is not None:
        # We can either set or unset the publish to Facebook flag
        if opts.publish_to_facebook:
            params['publish_to_facebook'] = 'true'
        else:
            params['publish_to_facebook'] = 'false'

    if opts.sandbox:
        params['sandbox'] = 'true'

    if opts.tweet_sighting is not None:
        # We can either set or unset the tweet Sighting flag
        if opts.tweet_sighting:
            params['tweet_sighting'] = 'true'
        else:
            params['tweet_sighting'] = 'false'

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_upload(server_url, opts):
    """Construct the url and POST data for a call to the Upload API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    
    Raises:
    Error if no upload_url was specified on the command-line.
    """
    # The upload_url is mandatory
    if opts.upload_url is None:
        raise Error('An upload-url is required for this API method')

    params = {}

    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.sandbox:
        params['sandbox'] = 'true'

    files = {}
    
    if opts.filename is not None:
        try:
            with open(opts.filename, 'rb') as f:
                files['file'] = f.read()
        except IOError as e:
            raise Error(str(e))

    data, content_type = encode_post_data(params, files=files)
    
    return opts.upload_url, data, content_type

def api_uploadurl(server_url, opts):
    """Construct the url and POST data for a call to the UploadUrl API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method, the POST data
    to be sent and the POST data content type.
    """
    method_url = '%s/%s/uploadurl' % (server_url, _API_ROOT_PATH)

    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    if opts.sandbox:
        params['sandbox'] = 'true'

    data, content_type = encode_post_data(params)
    
    return method_url, data, content_type

def api_user(server_url, opts):
    """Construct the url for a call to the User API method.
    
    Arguments:
    server_url - The url of the server where the API is running.
    opts - The command-line options.
    
    Returns:
    A tuple containing the full url for invoking the API method and None for
    the POST data and content type as this is a GET request.
    """
    params = {}
    
    if opts.access_token is not None:
        params['access_token'] = opts.access_token

    method_url = '%s/%s/user?%s' % (server_url, _API_ROOT_PATH, urllib.urlencode(params))

    return method_url, None, None

# A dictionary containing all the API methods and the function to call to
# construct the url and optional POST data.
methods = {
    'createlocator': api_createlocator,
    'createlocatorsighting': api_createlocatorsighting,
    'createsighting': api_createsighting,
    'getdailysighting': api_getdailysighting,
    'getsighting': api_getsighting,
    'getuser': api_getuser,
    'getuserstatistics': api_getuserstatistics,
    'listlocators': api_listlocators,
    'listlocatorsightings': api_listlocatorsightings,
    'listresightings': api_listresightings,
    'listsightinglocators': api_listsightinglocators,
    'listsightings': api_listsightings,
    'listusercountrystatistics': api_listusercountrystatistics,
    'listuserlocators': api_listuserlocators,
    'listusersightings': api_listusersightings,
    'meta': api_meta,
    'removelocatorsighting': api_removelocatorsighting,
    'resightsighting': api_resightsighting,
    'updatesighting': api_updatesighting,
    'upload': api_upload,
    'uploadurl': api_uploadurl,
    'user': api_user,
}

def parse_command_line():
    """Parse the command-line arguments and options.
    
    Returns:
    A tuple containing the API server url, the name of the API method to call
    and the command-line options object returned by the options parser.
    """
    parser = OptionParser(usage="""%prog server-url method [options]

Arguments:
  server-url            The url of the server where the API is running,
                        e.g. https://resighting-api.appspot.com
  method                The name of the API to invoke. See list below.

Methods:
  CreateLocator
  CreateLocatorSighting
  CreateSighting
  GetDailySighting
  GetSighting
  GetUser
  GetUserStatistics
  ListLocators
  ListLocatorSightings
  ListResightings
  ListSightingLocators
  ListSightings
  ListUserCountryStatistics
  ListUserLocators
  ListUserSightings
  Meta
  RemoveLocatorSighting
  ResightSighting
  UpdateSighting
  Upload
  UploadUrl
  User""")
    
    parser.add_option('--access-token', help='An API access token')
    parser.add_option('--accuracy', help='The accuracy of a latitude and longitude in metres')
    parser.add_option('--altitude', help='An altitude in metres')
    parser.add_option('--altitude-accuracy', help='The accuracy of an altitude reading in metres')
    parser.add_option('--blobtracker-id', help='A blobtracker id returned by the Upload API')
    parser.add_option('--closed', action='store_true', help='A closed locator requiring approval to join')
    parser.add_option('--cursor', help='A cursor returned by a previous call to the method marking the point where listing should continue from')
    parser.add_option('--date', help='A date in the format YYYY-MM-DD')
    parser.add_option('--description', help='A description')
    parser.add_option('--fetch-size', help='The number of results to retrieve')
    parser.add_option('--filename', help='A file to upload')
    parser.add_option('--heading', help='A heading')
    parser.add_option('--hold', action='store_true', help='Place a Sighting on hold')
    parser.add_option('--latitude', help='A latitude')
    parser.add_option('--list-type', help='The type of list to request: latest or nearest Sightings')
    parser.add_option('--locator-id', action='append', help='A Locator id. Multiple can be specified.')
    parser.add_option('--longitude', help='A longitude')
    parser.add_option('--name', help='A name')
    parser.add_option('--no-hold', action='store_false', help='Do not place a Sighting on hold', dest='hold')
    parser.add_option('--no-publish-to-facebook', action='store_false', help='Do not publish a Sighting to the user\'s Facebook wall', dest='publish_to_facebook')
    parser.add_option('--no-tweet-sighting', action='store_false', help='Do not tweet a Sighting', dest='tweet_sighting')
    parser.add_option('--options', action='store_true', help='Send an OPTIONS HTTP request to the server')
    parser.add_option('--publish-to-facebook', action='store_true', help='Publish a Sighting to the user\'s Facebook wall')
    parser.add_option('--sandbox', action='store_true', help='Invoke the API in sandbox mode')
    parser.add_option('--sighting-id', help='A Sighting id')
    parser.add_option('--speed', help='A speed')
    parser.add_option('--tweet-sighting', action='store_true', help='Tweet a Sighting')
    parser.add_option('--tz-offset', help='The number of minutes that the user\'s timezone is offset from UTC. Valid values are from -720 (UTC-12:00) to 840 (UTC+14:00).')
    parser.add_option('--upload-url', help='The url to upload the file to')
    parser.add_option('--user-id', help='A user\'s id')
    
    opts, args = parser.parse_args()

    # Make sure the mandatory arguments were provided
    if len(args) != 2:
        parser.error('Incorrect number of arguments')

    server_url = args[0]
    method = args[1]
    
    # Check the API method exists
    if method.lower() not in methods:
        parser.error('Invalid method')

    return (server_url, method, opts)

def invoke_api(server_url, method, opts):
    """Invoke a Resighting API method and return the response.
    
    Arguments:
    server_url - The url of the server where the API is running.
    method - The name of the API method to invoke.
    opts - The command-line options.
    
    Returns:
    A tuple containing the response body, the HTTP status code and the
    response headers.
    
    Raises:
    Error if an errors occurs. HTTP errors (i.e. a non 200 response) are
    not raised an an exception but the function returns with the response
    body and HTTP status code.
    """
    # Get the API method function
    method_fn = methods[method.lower()]
    
    # Get the API method url and optional POST data and content type
    method_url, data, content_type = method_fn(server_url, opts)

    # Open the API method url and get the response
    status_code = 200
    headers = None
    f = None
    connection = None
    
    try:
        if opts.options:
            # Make an OPTIONS request
            url = urlparse.urlparse(method_url)
            
            connection = httplib.HTTPConnection(url.netloc)
            connection.request('OPTIONS', url.path)
            
            http_response = connection.getresponse()
            
            status_code = http_response.status
            headers = http_response.getheaders()
            response = http_response.read()
            
            connection.close()
        else:
            # Make a GET or a POST request
            request = urllib2.Request(method_url, data=data)
            
            if content_type is not None:
                request.add_header('Content-Type', content_type)
            
            f = urllib2.urlopen(request)
            response = f.readline()
            headers = f.info().headers 
            f.close()
    except urllib2.HTTPError as e:
        status_code = e.code
        response = e.readline()
        headers = e.info().headers 
        e.close()
    except urllib2.URLError:
        if f is not None:
            f.close()
        raise Error('Failed to connect to API at %s' % method_url)
    except httplib.HTTPException:
        if connection is not None:
            connection.close()
        raise Error('Failed to connect to API at %s' % method_url)
    except socket.error:
        if connection is not None:
            connection.close()
        raise Error('Failed to connect to API at %s' % method_url)

    return response, status_code, headers
    
def main():
    """The main function.
    
    Returns:
    0 on success and non-zero otherwise.
    -1 indicates a connection error or that the url for the connection
       could not be constructed from the specified command-line parameters.
    -2 indicates that a response code other than 200 was received.
    2 indicates a command-line syntax error
    """
    server_url, method, opts = parse_command_line()

    try:
        response, status_code, headers = invoke_api(server_url, method, opts)
    except Error as e:
        print >> sys.stdout, 'error: %s' % e.message
        return -1

    if status_code != 200:
        print >> sys.stderr, 'HTTP Response Code: %d' % status_code

    print >> sys.stderr, 'Headers: %s' % headers
    
    # Output the response
    try:
        # Pretty-print the JSON response
        json_response = json.loads(response)
        print json.dumps(json_response, indent=4)
    except ValueError:
        # Not a JSON response
        # Could be blob upload error message directly from App Engine
        print response

    if status_code == 200:
        return 0
    else:
        return -2

if __name__ == '__main__':
    exit(main())
