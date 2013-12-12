#!/usr/bin/python

from datetime import datetime, timedelta
from httplib import BadStatusLine # This keeps happening but is not a problem on the code's end
import httplib2
import mongokit
from optparse import OptionParser
from pymongo import MongoClient
from random import random
import time

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run_flow

class MessageCannotHaveBoth(Exception):
    pass

class ContentTypeNotAllowed(Exception):
    pass

class DatabaseNameRequired(Exception):
    pass

class YouTubeResponse:
    """ Convert a response dict into an object to play with """
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __repr__(self):
        return "<YouTubeResponse kind: '%s'>" % self.__dict__.get("kind", "^\o_O/^")

def convert_to_new_response(convert_this, convert_to_object = False):
    """Convert all dictionaries to objects"""

    if not convert_to_object:
        return convert_this

    if type(convert_this) == dict:
        new_object = YouTubeResponse()
        for key,value in convert_this.items():
            value = convert_to_new_response(value, convert_to_object = convert_to_object)
            new_object.__dict__.update( {key: value} )

        return new_object

    if type(convert_this) in (list, tuple):
        temp = []
        for e1 in convert_this:
            e1 = convert_to_new_response(e1, convert_to_object = convert_to_object)
            temp.append(e1)

        if type(convert_this) == tuple:
            temp = tuple(temp)

        return temp

    else:
        return convert_this


class MongoConnection(object):
    """ General Handler for Mongo connections """

    connections = {}

    def __init__(self):
        pass

    def get_connection(self, database = "", host = "127.0.0.1", port = 27017, username = "", password = ""):
        if not database:
            raise DatabaseNameRequired()

        # If the connection has already been made, don't make a new one
        if self.connections.get(database):
            return self.connections[database]

        # MongoDB Connection
        if username and password:
            conn_string = "mongodb://{0}:{1}@{2}:{3}/{4}".format(username, password, host, port, database)
        else:
            conn_string = "mongodb://{0}:{1}/{2}".format(host, port, database)

        connection = MongoClient(conn_string)
        self.connections[database] = connection

        return connection

mongo_connections = MongoConnection()


class Youtube(object):

    def __init__(self, auth_host_name = "localhost", auth_host_port = [8080], noauth_local_webserver = False, logging_level = "DEBUG", client_secrets_file = "client_secrets.json", storage_file = "oauth2.json"):
        """ Returns a Youtube connection through the Google APIs using the OAuth2 method """
        parser = OptionParser()

        (flags, args) = parser.parse_args()
        flags.auth_host_name = auth_host_name
        flags.auth_host_port = auth_host_port
        flags.noauth_local_webserver = noauth_local_webserver # This means use the local server for authing
        flags.logging_level = logging_level # "DEBUG, CRITICAL, ERROR, FATAL",

        YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"

        flow = flow_from_clientsecrets(client_secrets_file, scope=YOUTUBE_SCOPE, message="Missing or Bad client secrets file.")

        storage = Storage(storage_file)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, flags)

        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, http=credentials.authorize(httplib2.Http()))

        # MongoDB Connection, Database, Collections setup
        self.connection = mongo_connections.get_connection(database = "mytube")
        self.database = self.connection.mytube

        # Collections
        self.channels = self.database.channels
        self.videos = self.database.videos
        self.user_data = self.database.user_data

    # def call(resource, action, parameters, failures = 0):
    #     """ This is a work in progress, it's going to consume all google API calls and try to handle any strange exceptions """
    #     try:
    #         self.youtube.resource().action(**parameters)
    #     except BadStatusLine, e:
    #         if failures >= 2:
    #             raise # It just keeps failing
    #         else:
    #             time.wait(1)
    #             self.call(resource = resource, action = action, parameters = parameters, failures = failures + 1)

    def get_uploads(self):
        channels_response = self.youtube.channels().list(mine=True, part="contentDetails").execute()

        for channel in channels_response["items"]:
            uploads_list_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

            print("Videos in list %s" % uploads_list_id)

            playlistitems_list_request = self.youtube.playlistItems().list(
                playlistId=uploads_list_id,
                part="snippet",
                maxResults=50
            )

            while playlistitems_list_request:
                playlistitems_list_response = playlistitems_list_request.execute()

                for playlist_item in playlistitems_list_response["items"]:
                    title = playlist_item["snippet"]["title"]
                    video_id = playlist_item["snippet"]["resourceId"]["videoId"]
                    print("%s (%s)" % (title, video_id))

                playlistitems_list_request = self.youtube.playlistItems().list_next(
                    playlistitems_list_request, playlistitems_list_response)

            print()

    def post_bulletin(self, message, video_id = None, playlist_id = None):
        """ You may post any message with a video id or playlist id, not both """
        if video_id and playlist_id:
            raise MessageCannotHaveBoth("video_id and playlist_id")

        body = dict( snippet=dict(description=message) )

        if video_id:
            body["contentDetails"] = dict( bulletin=dict(resourceId=dict(
                kind="youtube#video",
                videoId=video_id)) )

        if playlist_id:
            body["contentDetails"] = dict( bulletin=dict(resourceId=dict(
                kind="youtube#playlist",
                playlistId=playlist_id)) )

        self.youtube.activities().insert( part=",".join(body.keys()), body=body ).execute()

        return "Success"

    def get_subscriptions(self, convert_response_to_object = False):
        full_list = []
        details = self.youtube.subscriptions().list(
            mine=True, 
            part="id,snippet,contentDetails",
            maxResults = 50
        ).execute()

        full_list.extend(details["items"])
        total_subscriptions = details["pageInfo"]["totalResults"]
        
        while details.get("nextPageToken"):
            details = self.youtube.subscriptions().list(
                mine=True, 
                part="id,snippet,contentDetails", 
                pageToken = details["nextPageToken"], 
                maxResults = 50
            ).execute()
            full_list.extend(details["items"])

        return convert_to_new_response(full_list, convert_to_object = convert_response_to_object)

    def get_activities_for(self, channel_id, since = None, content_type = "all", convert_response_to_object = False):
        """ Docs: https://developers.google.com/youtube/v3/docs/activities
            snippet.type may be :
                bulletin
                channelItem
                comment
                favorite
                like
                playlistItem
                recommendation
                social
                subscription
                upload

            content_type = "all" # Gives back everything
        """
        if content_type not in ("bulletin",
                "channelItem",
                "comment",
                "favorite",
                "like",
                "playlistItem",
                "recommendation",
                "social",
                "subscription",
                "upload",
                "all"):
            raise ContentTypeNotAllowed(content_type)

        full_list = []
        details = self.youtube.activities().list(
            part="id,snippet,contentDetails", 
            channelId = channel_id, 
            maxResults = 50, 
            publishedAfter = since.strftime("%Y-%m-%dT%T-0600")
        ).execute()

        if content_type == "all":
            full_list.extend(details["items"])
        else:
            for item in details["items"]:
                if item["snippet"]["type"] == content_type:
                    full_list.append(item)

        while details.get("nextPageToken"):
            details = self.youtube.activities().list(
                part="id,snippet,contentDetails", 
                channelId = channel_id, 
                maxResults = 50, 
                publishedAfter = since.strftime("%Y-%m-%dT%T-0600"), 
                pageToken = details["nextPageToken"]
            ).execute()

            if content_type == "all":
                full_list.extend(details["items"])
            else:
                for item in details["items"]:
                    if item["snippet"]["type"] == content_type:
                        full_list.append(item)

        return convert_to_new_response(full_list, convert_to_object = convert_response_to_object)

    def get_uploads_from_subscriptions(self, since = None):
        subs = self.get_subscriptions()
        for sub in subs:
            # print(sub.snippet.resourceId.channelId)
            sub.activities = self.get_activities_for(
                sub.snippet.resourceId.channelId, 
                since = since,
                content_type = "upload")

        return subs

    def get_categories(self):
        user = self.user_data.find_one({"user": "Kusinwolf"})

        return {"categories": user["categories"]}

    def get_uploads_from_category(self, category):
        user = self.user_data.find_one({"user": "Kusinwolf"})
        
        if category not in user["categories"]:
            raise Exception("Bad Category")

        new_uploads = []

        for sub_cat in user["subscription_to_category"]:
            channel_id = sub_cat.get("channel_id")
            channel_category = sub_cat.get("category")
            last_checked = sub_cat.get("last_checked")

            if channel_category == category:
                new_uploads.extend( self.get_activities_for(
                    channel_id = channel_id, 
                    since = last_checked,
                    content_type ="upload") )

        return new_uploads