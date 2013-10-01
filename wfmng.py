# Copyright (C) 2012 SCS srl <info@scsitaly.com>

""" The **Workflow Manager** is a core *Hypermodel* Application.
    It maps workflows and users, manages sessions, serializes workflows and logs.
    Is the frontend for all other hypermodel application. """

import os
import smtplib

import argparse
from email.mime.text import MIMEText

from flask import Flask, render_template, request

try:
    from flaskext.xmlrpc import XMLRPCHandler
except ImportError, e:
    from flask.ext.xmlrpc import XMLRPCHandler

try:
    from flaskext.sqlalchemy import SQLAlchemy
except ImportError, e:
    from flask.ext.sqlalchemy import SQLAlchemy

try:
    from flaskext.login import *
except ImportError, e:
    from flask.ext.login import *
    from flask.ext.login import UserMixin, login_required

from auth import extractUserFromTicket
from taverna import TavernaServerConnector

############################################################################
# create and configure main application
app = Flask(__name__)

# read configuration file
if os.path.exists("local.wfmng.cfg"):
    app.config.from_pyfile("local.wfmng.cfg")
else:
    app.config.from_pyfile("wfmng.cfg")

############################################################################
# connect xmlrpc handler to app
xmlrpc = XMLRPCHandler("xmlrpc")
xmlrpc.connect(app, '/api')


############################################################################
# create the taverna server connector

tavernaServer = TavernaServerConnector(
    app.config["TAVERNA_SSH_TUNNELING"],
    app.config["TAVERNA_URL"],
    app.config["TAVERNA_SSH_LOCAL_PORT"],
    app.config["TAVERNA_SSH_REMOTE_HOST"],
    app.config["TAVERNA_SSH_REMOTE_PORT"],
    app.config["TAVERNA_SSH_USERNAME"],
    app.config["TAVERNA_SSH_PASSWORD"])


############################################################################
# configure database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tiger:scot@localhost/wfmng'
## SQLAlchemy Database Connector
db = SQLAlchemy(app)


class Workflow(db.Model):
    """
        This class represents a Workfow into the database

        Fields:

            **workflowId** (string): the workflow unique identifier (primary key)

            username (string): the workflow owner

            title (string): the workflow title

            status (string): the workflow status

            createTime (string): the creation time iso-format string

            startTime (string): the start time iso-format string

            finishTime (string): the finish time iso-format string

            expiry (string): the expiration time iso-format string

            exitcode (string): the taverna command line exit code

            stdout (string): the taverna command line standard out stream

            stderr (string): the taverna command line standard error stream

            complete (boolean): True if the workflow is finished and all the related log cached

    """

    workflowId = db.Column(db.String(80), primary_key=True)
    username = db.Column(db.String(80), primary_key=False)
    title = db.Column(db.String(120), primary_key=False)
    status = db.Column(db.String(20), primary_key=False)
    createTime = db.Column(db.String(30), primary_key=False)
    startTime = db.Column(db.String(30), primary_key=False)
    finishTime = db.Column(db.String(30), primary_key=False)
    expiry = db.Column(db.String(30), primary_key=False)
    exitcode = db.Column(db.String(5), primary_key=False)
    stdout = db.Column(db.String(2048), primary_key=False)
    stderr = db.Column(db.String(2048), primary_key=False)
    complete = db.Column(db.Boolean(), primary_key=False)

    def __init__(self, username, workflowId, title, status, createTime, startTime="", finishTime="",
                 expiry="", exitcode="", stdout="", stderr=""):
        self.username = username
        self.workflowId = workflowId
        self.title = title
        self.status = status
        self.createTime = createTime
        self.startTime = startTime
        self.finishTime = finishTime
        self.expiry = expiry
        self.exitcode = exitcode
        self.stdout = stdout
        self.stderr = stderr
        self.complete = False

    def __repr__(self):
        return '<Workflow %r-%r>' % (self.username, self.workflowId)

    def toDictionary(self):
        """ return a dictionary with the given workflow """

        ret = {'workflowId': self.workflowId,
               'status': self.status,
               'title': self.title,
               'createTime': self.createTime,
               'startTime': self.startTime,
               'finishTime': self.finishTime,
               'expiry': self.expiry,
               'exitcode': self.exitcode,
               'stdout': self.stdout,
               'stderr': self.stderr,
               'owner': self.username,
               'complete': self.complete
        }

        return ret

    def update(self, d):
        """ update the worfklow according to the given dictionary """

        for key in dir(self):
            if d.has_key(key) and key not in ['stdout', 'stderr']:
                setattr(self, key, d[key])


class SessionCache(db.Model):
    """ This class caches a session item into the database.
        It is not used for authentication purpose, it only caches useful information.

        Fields:
            **username** (string): the user identifier (primary key)
            email (string): the user email address
            tkt (string): the authentication ticket

    """
    username = db.Column(db.String(80), primary_key=True)
    email = db.Column(db.String(80), primary_key=False)
    tkt = db.Column(db.String(), primary_key=False)

    def __init__(self, username, email, tkt):
        self.username = username
        self.email = email
        self.tkt = tkt

    def __repr__(self):
        return '<UserCache %r-%r>' % (self.username, self.tkt)


############################################################################
# html methods

@app.route("/")
def hello():
    """ index method return the application title

        Routed at: "/"
    """
    return "Welcome to the VPH-Share Workflow Manager Application"


############################################################################
# utility methods
def alert_user_by_email(mail_from, mail_to, subject, mail_template, dictionary={}):
    """
        Send an email to the user with the given template
        This method will be replaced by the Master Interface notification service
    """
    msg = MIMEText(render_template(mail_template, **dictionary), 'html')
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = mail_to

    try:
        s = smtplib.SMTP(app.config.get('SMTP_HOST', '') or 'localhost')
        s.sendmail(mail_from, mail_to, msg.as_string())
        s.quit()
    except BaseException, e:
        pass



############################################################################
# xmlrpc methods
def updateAllWorkflows():
    """ update all workflows in database """

    wfs = Workflow.query.all()

    for wf in wfs:
        if wf.status != 'Finished':
            getWorkflowInformation(wf.worfklowId)

    return len(wfs)


def submitWorkflow(workflowTitle, workflowDefinition, inputDefinition, ticket):
    """ sumbit the workflow and its input definition to the taverna server

        Arguments:
            workflowTitle (string): the workflow title

            workflowDefinition (string): the workflow definition file string buffer

            inputDefinition (string): the input definition file string buffer

            ticket (string): a valid authentication ticket

        Return:
            dictionary::

                Success -- {'workflowId':'workflowId', 'status':'status', 'createTime':'createTime', 'expiry':'expiry',
                            'title':workflowTitle, 'complete':False, 'command':'submitWorkflow'}
                Failure -- {'workflowId':'', 'error.code':'code', 'error.description':'description'}
    """

    user = extractUserFromTicket(ticket)

    if user is None:
        response = app.make_response('Forbidden')
        response.status_code = 403
        return response

    # create worfklow object 
    ret = tavernaServer.createWorkflow(workflowDefinition)

    if 'workflowId' in ret and ret['workflowId'] and inputDefinition:

        ret_i = tavernaServer.setWorkflowInputs(ret['workflowId'], inputDefinition)

        if not 'workflowId' in ret_i or not ret['workflowId']:
            # if the set inputs fails 'workflowId' is not included or empty, return the error map
            return ret_i

        # create or update the session placeholder
        cache = SessionCache.query.filter_by(username=user['username']).first()
        if cache is None:
            cache = SessionCache(user['username'], user['email'], ticket)
            db.session.add(cache)
        else:
            # update only the ticket and email
            cache.email = user['email']
            cache.ticket = ticket

        # create a new worflow object and add it into the database
        wf = Workflow(user['username'], ret['workflowId'], workflowTitle, ret['status'], ret['createTime'], expiry=ret['expiry'])
        db.session.add(wf)

        # write changes to database
        db.session.commit()

    ret['title'] = workflowTitle
    ret['complete'] = False

    # allow client to retrieve this request         
    ret['command'] = 'submitWorkflow'

    return ret


def restartWorkflow(workflowId, ticket):
    """ restart the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'command':'startWorkflow', 'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'command':'startWorkflow', 'workflowId':'', 'error.description':'', 'error.code':''}
    """

    # check if workflow exists and is finished
    wf = Workflow.query.filter_by(workflowId=workflowId).first()

    if wf is not None and wf.status == 'Finished':

        # recover old workflow definition file and input file
        title = wf.title
        workflow_definition_file = tavernaServer.getWorkflowDefinition(workflowId)
        input_definition_file = tavernaServer.getWorkflowInputs(workflowId)

        # remove old workflow
        db.session.delete(wf)
        db.session.commit()

        # create a new workflow
        ret = submitWorkflow(title, workflow_definition_file, input_definition_file, ticket)

        # make it start
        if 'workflowId' in ret and ret['workflowId']:
            tavernaServer.startWorkflow(ret['workflowId'])

        return ret

    else:
        return {'command': 'restartWorkflow', 'returnValue': 'ko', 'error.code': '404',
                'error.description': 'workflowId not found or not valid'}


def startWorkflow(workflowId):
    """ start the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'command':'startWorkflow', 'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'command':'startWorkflow', 'workflowId':'', 'error.description':'', 'error.code':''}
    """

    # control if workflow id is valid
    wf = Workflow.query.filter_by(workflowId=workflowId).first()

    if wf is not None:

        ret = tavernaServer.startWorkflow(workflowId)

        # allow client to retrieve this request
        ret['command'] = "startWorkflow"
        ret['returnValue'] = "ok"

        if wf.status == 'Waiting':
            wf.status = 'Operating'

        db.session.commit()

        #send an email to the user
        session = SessionCache.query.filter_by(username=wf.username).first()
        if session is not None:
            alert_user_by_email(app.config['MAIL_FROM'], session.email, '[VPH-Share] Workflow Started', 'mail.html', {'workflowId': workflowId})

        return ret

    else:
        return {'command': 'startWorkflow', 'returnValue': 'ko', 'error.code': '404',
                'error.description': 'workflowId not found or not valid'}


def getWorkflowInformation(workflowId):
    """ return all information related to the workflow with the given id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'command':'getWorkflowInformation', 'workflowId':workflowId, 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'command':'getWorkflowInformation', 'error.description':'', 'error.code':''}
    """

    ret = tavernaServer.getWorkflowInformation(workflowId)

    # allow client to retrieve this request 
    ret['command'] = "getWorkflowInformation"

    wf = Workflow.query.filter_by(workflowId=workflowId).first()

    if wf is not None:
        ret['title'] = wf.title
        ret['complete'] = wf.complete
        #TODO handle expired workflows
        wf.update(ret)
        db.session.commit()

    return ret


def deleteWorkflow(workflowId):
    """ delete the workflow with the given id, if any

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'command':'deleteWorkflow', 'returnValue':'ok'}
                Failure -- {'command':'deleteWorkflow', 'returnValue':'ko', 'error.description':'', 'error.code':''}
    """

    ret = {}

    wf = Workflow.query.filter_by(workflowId=workflowId).first()
    if wf is not None:
        # delete workflow from taverna
        ret = tavernaServer.deleteWorkflow(workflowId)
        db.session.delete(wf)
        db.session.commit()
        ret["returnValue"] = "ok"

    else:
        ret["returnValue"] = "ko"
        ret["error.description"] = "The requested workflow does not exist"
        ret["error.code"] = "404"
        # allow client to retrieve this request
    ret['command'] = "deleteWorkflow"

    return ret


def getWorkflowsList(query, ticket):
    """ return the workflows list for the authenticate user

        Arguments:
            query (dictionary): a dictionary with the query parameters (actually not used)

        Returns:
            dictionary::

                {'command':'getWorkflowsList', 'workflows':[{'workflowId':'workflowId', 'info01':'info01', }, ...] }

    """

    ret = {}

    # retrieve the user from the ticket
    user = extractUserFromTicket(ticket)

    wfs = Workflow.query.filter_by(username=user['username'])

    ret["workflows"] = []

    for wf in wfs:
        status = getattr(wf, "status", "Finished")
        if status in ["Waiting", "Finished"]:
            # if it was a builtin workflow, there will be an entry into BuiltinWorkflowResult
            ret["workflows"].append(wf.toDictionary())

        else:
            ret["workflows"].append(getWorkflowInformation(wf.workflowId))

    # allow client to retrieve this request
    ret["command"] = "getWorkflowsList"

    return ret


#ERNESTO
# 1
# write the method code, with the interface the MI will call
# put into the signature all the parameters the method needs
# always return a python dictionary
def yourSampleMethod(workflowId, sample_parameter, ticket):
    """
        This is a sample xmlrpc method
    """

    ret = {}

    # hint, howto retrieve the user from the ticket
    # will return a dictionary like user = {'username':'testuser', 'email':'email', ...}
    user = extractUserFromTicket(ticket)

    # if needed validate inputs and then invoke the TavernaConnector method

    # hint, howto check if a workflow with the given id exists
    wf = Workflow.query.filter_by(workflowId=workflowId).first()

    if wf is not None:
        ret = tavernaServer.mySampleMethod(workflowId, sample_parameter)
        # to continue with the tutorial
        # look for #ERNESTO in taverna.py module

    else:
        ret["returnValue"] = "ko"
        ret["error.description"] = "The requested workflow does not exist"
        ret["error.code"] = "404"

    return ret

############################################################################
# register xmlrpc callback
xmlrpc.register(hello, "hello")
xmlrpc.register(submitWorkflow, "submitWorkflow")
xmlrpc.register(restartWorkflow, "restartWorkflow")
xmlrpc.register(startWorkflow, "startWorkflow")
xmlrpc.register(getWorkflowInformation, "getWorkflowInformation")
xmlrpc.register(getWorkflowsList, "getWorkflowsList")
xmlrpc.register(deleteWorkflow, "deleteWorkflow")
xmlrpc.register(updateAllWorkflows, "updateAllWorkflows")

#ERNESTO
# 3
# register the callback in the xmlrpc connector
# the first parameter is the function to be called
# the second parameter is the url of the method
# in this example, the client to invoke the 'yourSampleMethod' function
# will send a request to the url http://localhost:5000/api/myNewMethod
xmlrpc.register(yourSampleMethod, "myNewMethod")

############################################################################

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Development Server Help')
    parser.add_argument("-d", "--debug", action="store_true", dest="debug_mode",
                        help="run in debug mode (for use with PyCharm)", default=False)
    parser.add_argument("-p", "--port", dest="port",
                        help="port of server (default:%(default)s)", type=int, default=5000)

    cmd_args = parser.parse_args()
    app_options = {"port": cmd_args.port}

    if cmd_args.debug_mode:
        app_options["debug"] = True
        app_options["use_debugger"] = False
        app_options["use_reloader"] = False

    app.run(**app_options)
