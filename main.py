#!/usr/bin/env python

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Our web application's entry point."""

import os
import webapp2

from google.appengine.api import memcache, taskqueue
from google.appengine.ext import ndb

from apiclient.discovery import build
from oauth2client.contrib.appengine import (CredentialsNDBProperty,
                                            OAuth2DecoratorFromClientSecrets,
                                            StorageByKeyName)

AUTH_ARGS = {'access_type':'offline'}

OAUTH_DECORATOR = OAuth2DecoratorFromClientSecrets(
    os.path.join(os.path.dirname(__file__), 'client_secrets.json'),
    'https://www.googleapis.com/auth/youtube',
    **AUTH_ARGS)

class CredentialsModel(ndb.Model):
    """Test"""
    credentials = CredentialsNDBProperty()

class MainHandler(webapp2.RequestHandler):
    """Entry point for our web app."""
    @OAUTH_DECORATOR.oauth_required
    def get(self):
        """Handler for GET requests to the app."""
        http = OAUTH_DECORATOR.http()
        if not self.request.get('videoId'):
            self.response.write("""Please supply the video ID of a YouTube live stream as a query
                                parameter, i.e. ?videoId=xxx.""")
            return

        youtube = build('youtube', 'v3', http=http)
        channel = youtube.channels().list(mine=True, part='id').execute()
        channel_id = channel['items'][0]['id']

        storage = StorageByKeyName(CredentialsModel, channel_id, 'credentials')
        storage.put(OAUTH_DECORATOR.credentials)

        video_id = self.request.get('videoId')
        videos = youtube.videos().list(id=video_id, part="liveStreamingDetails").execute()
        video = videos['items'][0]
        live_chat_id = video['liveStreamingDetails']['activeLiveChatId']

        # See if the bot's already in the channel.
        in_chat = memcache.get("{}:in_chat".format(live_chat_id))
        if in_chat:
            self.response.write("""The bot's already in that chat! Try saying .hi to
             it, or asking it to .leave! If the bot isn't in chat, wait 4 minutes
            then try adding it again""")
        else:
            taskqueue.add(url='/spawnbot', target='worker', params=
                          {'channel_id':channel_id,
                           'live_chat_id':live_chat_id})

            self.response.write("Created the bot task for live chat "+live_chat_id
                                +" on channel "+channel_id+
                                "! The bot should join the channel soon and say hello :)")

app = webapp2.WSGIApplication([("/", MainHandler),
                               (OAUTH_DECORATOR.callback_path, OAUTH_DECORATOR.callback_handler())],
                              debug=True)
