# -*- coding: utf-8 -*-
#!/usr/bin/env python
'''
    Gmvault: a tool to backup and restore your gmail account.
    Copyright (C) <since 2011>  <guillaume Aubert (guillaume dot aubert at gmail do com)>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Module for doing test with the Gmail API

'''
from __future__ import print_function
from apiclient.http import BatchHttpRequest
from apiclient.discovery import build
from apiclient import errors
from httplib2 import Http
from oauth2client import file, client, tools
import sys

CLIENT_SECRET = '/home/gmv/gmail_api_secrets.json'
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

def next_token_callback(response_id,  response, exception):
  """
     
  """
  print("In next token callback.\n")
  print("response_id = %s\n" % (response_id))
  print("response = %s\n" % (response))

  
def get_message_callback(response_id, response, exception):
  """
  """
  print("In get message callback.\n")
  print("response_id = %s\n" % (response_id))
  print("response = %s\n" % (response))

def get_mail_messages():
  """
     Get email
  """
  store = file.Storage('storage.json')
  creds = store.get()
  if not creds or creds.invalid:
     flow = client.flow_from_clientsecrets(CLIENT_SECRET, SCOPES)
     creds = tools.run_flow(flow, store)
  GMAIL = build('gmail', 'v1', http=creds.authorize(Http()))
  print("Before to call GMAIL API\n")

  try:
    response = GMAIL.users().messages().list(userId='me', q=None, maxResults=4).execute()

    print("response = %s\n."%(response))

    print("len(response.messages) = %s\n"%(len(response["messages"])))
    #sys.exit()

    msg_ids = []
    if 'messages' in response:
      for message in response['messages']:
          msg_ids.append(message['id'])
    
    #create a batch request
    batch = BatchHttpRequest()

    #add new get id request
    if 'nextPageToken' in response:
      page_token = response['nextPageToken']
      batch.add(GMAIL.users().messages().list(userId='me', q=None, pageToken=page_token, maxResults=1000), callback=next_token_callback)
    
    for msg_id in msg_ids:
      #batch.add(GMAIL.users().messages().get(userId='me', id=msg_id, fields='id,internalDate,payload/headers,historyId'), callback=get_message_callback)
      batch.add(GMAIL.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders="Subject"), callback=get_message_callback)

    batch.execute()

    #while 'nextPageToken' in response:
    #  page_token = response['nextPageToken']
    #  response = GMAIL.users().messages().list(userId='me', q=None, pageToken=page_token, maxResults=1000).execute()
      #print("response = %s\n."%(response))
      #print("len(response.messages) = %s\n"%(len(response["messages"])))
    #  messages.extend(response['messages'])

    #print("Retrieved %s messages\n" %( len(messages)))

    #return messages
  except errors.HttpError, error:
    print('An error occurred: %s'%(error))

   
if __name__ == "__main__":
   get_mail_messages()
