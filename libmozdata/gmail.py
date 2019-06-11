import argparse
import base64
import os
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from os.path import basename

import httplib2
import oauth2client
from apiclient import discovery
from oauth2client import client, tools

from . import config

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_PATH = os.path.expanduser(config.get("Gmail", "credentials", ""))


def send(To, Subject, Body, Cc=[], Bcc=[], html=False, files=[]):
    """Send an email
    """
    subtype = "html" if html else "plain"
    message = MIMEMultipart()
    message["To"] = ", ".join(To)
    message["Subject"] = Subject
    message["Cc"] = ", ".join(Cc)
    message["Bcc"] = ", ".join(Bcc)

    message.attach(MIMEText(Body, subtype))

    for f in files:
        with open(f, "rb") as In:
            part = MIMEApplication(In.read(), Name=basename(f))
            part["Content-Disposition"] = 'attachment; filename="%s"' % basename(f)
            message.attach(part)

    message = {"raw": base64.urlsafe_b64encode(message.as_string())}

    credentials = oauth2client.file.Storage(CREDENTIALS_PATH).get()
    Http = credentials.authorize(httplib2.Http())
    service = discovery.build("gmail", "v1", http=Http)

    message = service.users().messages().send(userId="me", body=message).execute()


def create_credentials(client_secret_path):
    """Gets valid user credentials from storage.

    Args:
        path (str), path to client_secret.json file
    """
    flow = client.flow_from_clientsecrets(client_secret_path, " ".join(SCOPES))
    flow.user_agent = "Clouseau"
    flow.params["access_type"] = "offline"
    flow.params["approval_prompt"] = "force"
    store = oauth2client.file.Storage(CREDENTIALS_PATH)
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args(
        ["--noauth_local_webserver"]
    )

    tools.run_flow(flow, store, flags)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create credentials to be able to send mail in using Gmail account"
    )
    parser.add_argument(
        "--client-secret-path",
        dest="cs_path",
        action="store",
        default="",
        help="path to client_secret.json",
    )
    args = parser.parse_args()

    if not args.cs_path:
        raise Exception("You must provide the paths to client_secret.json")

    create_credentials(args.cs_path)
