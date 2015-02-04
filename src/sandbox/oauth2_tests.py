__author__ = 'Aubert'

import httplib2
from six.moves import input
from oauth2client.client import OAuth2WebServerFlow

CLIENT_ID = "some-ids"
CLIENT_SECRET = "secret"
SCOPES = ['https://mail.google.com/', # IMAP/SMTP client access
              'https://www.googleapis.com/auth/email'] # Email address access (verify token authorized by correct account

def test_oauth2_with_google():
    """
    Do something
    :return:
    """

    flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, " ".join(SCOPES))

    # Step 1: get user code and verification URL
    # https://developers.google.com/accounts/docs/OAuth2ForDevices#obtainingacode
    flow_info = flow.step1_get_device_and_user_codes()
    print "Enter the following code at %s: %s" % (flow_info.verification_url,
                                                  flow_info.user_code)
    print "Then press Enter."
    input()

    # Step 2: get credentials
    # https://developers.google.com/accounts/docs/OAuth2ForDevices#obtainingatoken
    credentials = flow.step2_exchange(device_flow_info=flow_info)
    print "Access token:", credentials.access_token
    print "Refresh token:", credentials.refresh_token

#Get IMAP Service

if __name__ == '__main__':
    test_oauth2_with_google()