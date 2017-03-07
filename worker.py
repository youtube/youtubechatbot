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

"""The worker thread where our chatbot magic will happen."""
import time
import webapp2
import httplib2
from apiclient.discovery import build
from google.appengine.ext import ndb
from google.appengine.api import memcache, taskqueue
from google.appengine.runtime import DeadlineExceededError
from oauth2client.contrib.appengine import StorageByKeyName
from oauth2client.contrib.appengine import CredentialsNDBProperty

MEMCACHE_CHAT_PING_EXPIRY_TIME = 200

def say(message_text, live_chat_id, youtube):
    """Send a chat message to a YouTube live chat."""

    # Here, we're building a textMessageEvent to post a chat message
    # as the bot. The format is documented here:
    # https://developers.google.com/youtube/v3/live/docs/liveChatMessages
    #
    # We supply the required parameters as listed here:
    # https://developers.google.com/youtube/v3/live/docs/liveChatMessages/insert

    message_to_send = {"snippet":
                       {"liveChatId":live_chat_id, "type":"textMessageEvent",
                        "textMessageDetails":{"messageText":message_text}}}

    youtube.liveChatMessages().insert(part="snippet", body=message_to_send).execute()

class CredentialsModel(ndb.Model):
    credentials = CredentialsNDBProperty()

class Chatbot(webapp2.RequestHandler):
    """Worker class for the bot."""

    def post(self):
        """Entry point for the worker."""

        # channel_id refers to the channel that the bot is using
        # video_id refers to the live stream we want to chat in

        channel_id = self.request.get("channel_id")
        live_chat_id = self.request.get("live_chat_id")

        storage = StorageByKeyName(CredentialsModel, channel_id, 'credentials')
        credential = storage.get()
        http = credential.authorize(httplib2.Http())

        youtube = build('youtube', 'v3', http=http)

        in_chat = memcache.get("{}:in_chat".format(live_chat_id))
        if in_chat is None:
            say("Hello, I've joined the chat!", live_chat_id, youtube)

        next_page = memcache.get("{}:nextpage".format(live_chat_id))

        # This is our loop control. If we want the bot to gracefully exit,
        # we can just set this to false.
        remain_in_channel = True

        try:
            while remain_in_channel:
                memcache.set("{}:in_chat".format(live_chat_id), True,
                             MEMCACHE_CHAT_PING_EXPIRY_TIME)

                messages = youtube.liveChatMessages().list(liveChatId=live_chat_id,
                                                           part="id,snippet,authorDetails",
                                                           pageToken=next_page).execute()

                if messages is None:
                    break

                for message in messages['items']:
                    message_id = message['id']
                    message_type = message['snippet']['type']

                    # Keep track of every message we process, so we
                    # don't accidentally do it more than once.
                    already_processed = memcache.get("{}:processed".format(message_id))
                    if already_processed:
                        continue
                    else:
                        memcache.set("{}:processed".format(message_id), True)

                    # Here, we're doing the real work of the bot.
                    # Check the message type and respond appropriately.
                    # Message types are documented here:
                    # https://developers.google.com/youtube/v3/live/docs/liveChatMessages#snippet.type

                    # Before we proceed, let's pull out the author details, so we can
                    # personalize our response and do some basic permission checking.
                    author_channel_name = message['authorDetails']['displayName']
                    author_is_moderator = message['authorDetails']['isChatModerator']
                    author_is_owner = message['authorDetails']['isChatOwner']

                    if message_type == "textMessageEvent":
                        message_text = message['snippet']['textMessageDetails']['messageText']

                        if message_text == ".hi":
                            say("Well hello there, {}!".format(author_channel_name), live_chat_id,
                                youtube)
                        elif message_text == ".leave":
                            # We only want moderators or the channel owner to be able to
                            # tell the bot to leave. Let's ensure that's the case.
                            if author_is_moderator or author_is_owner:
                                say("Okay {}, I'm leaving the channel!".format(author_channel_name),
                                    live_chat_id, youtube)
                                remain_in_channel = False

                    elif type == "chatEndedEvent":
                        remain_in_channel = False
                        break

                next_page = messages['nextPageToken']
                memcache.set("{}:nextpage".format(live_chat_id), next_page)

                time.sleep(messages['pollingIntervalMillis']/1000)
        except DeadlineExceededError:
            # App Engine is terminating our task, so we need to re-queue it.
            # Tasks in Task Queues have deadlines. To learn more:
            # https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/creating-handlers
            if remain_in_channel:
                taskqueue.add(url='/spawnbot', target='worker', params=
                              {'channel_id':channel_id,
                               'live_chat_id':live_chat_id})
            else:
                # TODO: Don't duplicate the cleanup code.
                memcache.delete("{}:nextpage".format(live_chat_id))
                memcache.delete("{}:in_chat".format(live_chat_id))
            return

        memcache.delete("{}:nextpage".format(live_chat_id))
        memcache.delete("{}:in_chat".format(live_chat_id))


app = webapp2.WSGIApplication([('/spawnbot', Chatbot)], debug=True)
