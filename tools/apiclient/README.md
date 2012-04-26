apiclient.py
============

A simple command-line Python script to invoke the Resighting (http://www.resighting.com) API.

See http://resighting.wikia.com/wiki/Apiclient.py for more details.

Licenced under the The MIT License

Copyright (c) 2012 Matthew Neale

Requires simplejson
-------------------

This script was written with and has been used extensively with Python 2.5 and
is still used that way due to the fact that Resighting is still using Python 2.5
on Google App Engine. Simplejson is required for Python 2.5 and so is included in
a subdirectory but if you are using Python 2.6 or above you probably won't need it.

Example
-------

$ ./apiclient.py https://resighting.appspot.com User --access_token=ACCESS_TOKEN
Headers: ['Content-Type: application/json\r\n', 'Vary: Accept-Encoding\r\n', 'Date: Thu, 26 Apr 2012 15:47:51 GMT\r\n', 'Server: Google Frontend\r\n', 'Cache-Control: private\r\n', 'Connection: close\r\n']
{
    "update_date": "2012-03-07T11:23:56.888240Z",
    "user_id": "bf10ad015e7b4ceea9279c1b9e8889a5",
    "name": "Matt",
    "settings": {
        "update_date": "2012-04-26T10:14:28.310093Z",
        "facebook_publish_by_default": false,
        "facebook_link_status": "FB_LINKED",
        "twitter_link_status": "TW_LINKED",
        "tweet_by_default": false
    },
    "avatar": {
        "avatar_width": 600,
        "avatar_height": 450,
        "avatar_serving_url": "http://lh6.ggpht.com/jEItPe0EtKFcIIeeqq_Pp8AaLHdZzp9ACT2MPurxf5I6Eln3pjpOnaAm4rR0WAEEStk9HUUIygezuYVboFxF"
    },
    "handle": "matt",
    "joined_date": "2010-03-19T15:53:04.337350Z"
}
