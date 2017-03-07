# Sample chat bot on App Engine

This is a sample YouTube chat bot that's designed to run on Google App Engine. It leverages Task Queues to simulate a long-running background process which polls the YouTube LiveChatMessages API for the specified video.

It'll respond in a personalized way to specific commands and depart the channel if asked to do so by a mod or the channel owner.

# Deploying the sample code

These instructions are a quick overview of cloning this project to your local development environment and deploying to a new App Engine instance.

Ensure you have the following set up in your environment before you begin:

* Python 2.7
* Google Cloud SDK

To try the bot, you'll need to clone the repository to your local machine:

    git clone https://github.com/youtube/youtubechatbot

Create a new project in the [Google Cloud Console](http://console.cloud.google.com). Note your **project ID**, as we'll need it soon.

Create a set of OAuth credentials for your application, and set up your client_secrets.json.
* In the Cloud Console, click the menu in the top left and switch to API Manager.
* Click Credentials.
* Click Create Credentials, then choose OAuth client ID.
* Choose "Web application", then fill out the flow.
* For "Authorized redirect URLs," add the following:
    * https://\[your project id\].appspot.com/oauth2callback
    * Note the use of _your project ID_ -- replace this with the project ID you chose when setting up your Cloud project.
* Save your credential.
* From the list of OAuth 2.0 client IDs, choose the option to download your credentials.
* Move the downloaded file into the root directory of the cloned repository (the directory that contains app.yaml) and rename it to client_secrets.json

Install the required vendor libraries.
* In a Terminal or Command Prompt, switch to the directory that you cloned the repository into.
* Use pip to install the required libraries. This is required for deployment to App Engine.

    pip install -t lib -r requirements.txt

Deploy the sample project to App Engine.

    gcloud app deploy app.yaml worker.yaml

# Trying the bot

Once deployment is finished, visit the App Engine URL to ensure the app is running.

## Usage:

    http://yourprojectid.appspot.com/?videoId=xxxxx

Set videoId to the ID of an upcoming or active live event on YouTube. If the bot joins successfully, you should see a success message in the browser and the bot should say hello in chat.

The first time you visit the URL, you'll be asked to authenticate. You should use the YouTube channel you want the bot to use when chatting.

# Coming soon

A code lab that walks you through the details of how this bot is built.

# Author information

Marc Chambers

_Special thanks to Christopher Schmidt for review & testing support_

Copyright 2017 Google, Inc.