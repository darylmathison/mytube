MyTube
======
Categorize and custom display of Youtube subscriptions through authorized google API access

### Intended Goals
* Gather & save data from subscriptions
* Customizable categories
* Mobile Access

## Docs
* https://developers.google.com/youtube/v3/docs/
* https://developers.google.com/youtube/registering_an_application

## Setup

### Google Project (Required)
* Docs: https://developers.google.com/youtube/registering_an_application

```
https://cloud.google.com/console#/project

Create a Project
Give it a name and unique project id

Click on the project name (if it does not auto open)
Click on "APIs & Auth"
Scroll to the bottom and activate "YouTube Analytics API" & "YouTube Data API v3"

Click on "Registered apps"
Click on "Register App"
Give the app a name
For a local setup, select "Native"
For a web application (With DNS and app server), select "Web Application"
Click Register
Click on the newly registered app (if it did not auto open)

Click on "OAuth 2.0 Client ID"
Click Download JSON
Save the downloaded json as my_secrets.json in the same directory as this cloned repository
```

### Local Box
```
sudo apt-get install python-pip
sudo pip install virtualenv

virtualenv mytube
cd mytube
source bin/activate
pip install --upgrade google-api-python-client
pip install httplib2 pymongo tornado
```

## Usage
```python
from Youtube import Youtube

app = Youtube(storage_file = "my-oauth2.json", client_secrets_file = "my_secrets.json")

app.get_uploads()
app.get_subscriptions()
```

## Trouble Shooting
### redirect_uri does not match registered redirects
When adding redirect_uri's to the OAuth2.0 for any API, make sure the spelling is exact, purposful strict security then you must click Generate or the changes will not save

### BadStatusLine: ''
```python
app.youtube.subscriptions().list(part="contentDetails", mine = True).execute()
```
Wireless sucks at times, the connection could have dropped for any number of reasons, it's intermintent. If this persists I suggest war hammering your wireless card before it has a chance to spawn more defective cards to service other developers in their quest for holy grails.

### HttpError: 

\<HttpError 400 when requesting https://www.googleapis.com/youtube/v3/subscriptions?alt=json&part=currentDetails&mine=true returned "currentDetails"\>

```python
app.youtube.subscriptions().list(part="currentDetails", mine = True).execute()
```
"currentDetails" is not an allowed part