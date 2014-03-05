# Copyright (C) 2012 SCS srl <info@scsitaly.com>

""" The **Workflow Manager** is a core *Hypermodel* Application.
    It maps workflows and users, manages sessions, serializes workflows and logs.
    Is the frontend for all other hypermodel application. """

import sys
import os
import smtplib
from datetime import datetime, timedelta
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
import requests

# requirements for createOutputFolders
import xmltodict
import string
import base64
from cyfronet import easywebdav
from cfinterface import CloudFacadeInterface
import time

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
# create the Cloud server connector
serverManager = CloudFacadeInterface(app.config["CLOUDFACACE_URL"])

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


    """

    workflowRunId = db.Column(db.String(80), primary_key=True)
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
    outputfolder = db.Column(db.String(2048), primary_key=False)

    def __init__(self, username, workflowId, title, outputfolder, status = "Initialized", createTime = "", startTime="", finishTime="",
                 expiry="", exitcode="", stdout="", stderr=""):
        self.username = username
        self.workflowRunId = workflowId
        self.title = title
        self.status = status
        self.createTime = createTime
        self.startTime = startTime
        self.finishTime = finishTime
        self.expiry = expiry
        self.exitcode = exitcode
        self.stdout = stdout
        self.stderr = stderr
        self.outputfolder = outputfolder

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
               'outputfolder': self.outputfolder
        }

        return ret

    def update(self, d):
        """ update the worfklow according to the given dictionary """

        for key in dir(self):
            if d.has_key(key):
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


class Execution(db.Model):
    username = db.Column(db.String(80), primary_key=False)
    eid = db.Column(db.Integer(), primary_key=True)
    status = db.Column(db.Integer(), primary_key=False)
    tavernaId = db.Column(db.String(80), primary_key=False)
    workflowRunId = db.Column(db.String(80), primary_key=False)
    error = db.Column(db.Boolean(), primary_key=False)
    error_msg = db.Column(db.String(80), primary_key=False)


    def __init__(self, username, eid, status=0, tavernaId='', workflowRunId=''):
        self.username = username
        self.eid = eid
        self.status = status
        self.tavernaId = tavernaId
        self.workflowRunId = workflowRunId
        self.error = False
        self.error_msg = ''

class TavernaServer(db.Model):
    """ This class represents a Taverna Server workflow (i.e. a workflow containing an AS running a Taverna Server) in the database
        
        Fields:
            **username** (string): the user identifier (primary key)
            **url** (string): url for the web endpoint of the server
            **workflowId** (string): id of the workflow containing the Taverna Server
            **asConfigId** (string): configuration id of the atomic service running the server
            **count** (integer): number of workflows running in the server at a given time

    """
    username = db.Column(db.String(80), primary_key=True)
    url = db.Column(db.String(80), primary_key=True)
    workflowId = db.Column(db.String(80), primary_key=True)
    asConfigId = db.Column(db.String(80), primary_key=True)
    userAndPass = db.Column(db.String(80), primary_key=True)
    tavernaServerCloudId = db.Column(db.String(80), primary_key=True)

    def __init__(self, username, endpoint, workflowId, asConfigId, tavernaServerCloudId , tavernaUser='taverna', tavernaPass='taverna'):

        self.username = username
        self.url = endpoint
        self.workflowId = workflowId
        self.asConfigId = asConfigId
        self.userAndPass = base64.b64encode(tavernaUser + ":" + tavernaPass)
        self.tavernaServerCloudId = tavernaServerCloudId

    def isAlive(self):
        response = requests.get(self.url,
                                 headers={
                                     'Authorization': 'Basic %s' % self.userAndPass,
                                     'Accept': 'application/json'
                                 },
                                 verify=False)

        if response.status_code == 200:
            return True
        return False

    def isWorkflowAlive(self, wfRunId):
        response = requests.get("%s/%s" % (self.url, wfRunId),
                                 headers={
                                     'Authorization': 'Basic %s' % self.userAndPass,
                                     'Accept': 'application/json'
                                 },
                                 verify=False)

        if response.status_code == 200:
            return True
        return False

    def getWorkflowRunNumber(self):
        response = requests.get("%s" % (self.url),
                                 headers={
                                     'Authorization': 'Basic %s' % self.userAndPass,
                                     'Accept': 'application/json'
                                 },
                                 verify=False)

        if response.status_code == 200:
            ret = response.json()
            if ret['runList'] == "":
                return 0
            listWf = ret['runList'].get('run', False)
            if listWf:
                if type(listWf) is list:
                    return len(listWf)
                else:
                    return 1
        return 0

    def createWorkflow(self, workflowDefinition):
        """ Create a new workflow according to the given definition string.

        Arguments:
            workflowDefinition (string): the workflow definition file string buffer

        Returns:
            dictionary::

                Success -- 'workflow run id'
                Failure -- raise Exception with possible error message

        """

        wf = workflowDefinition

        response = requests.post(self.url, data=wf,
                                 headers={
                                     'Content-type': 'application/vnd.taverna.t2flow+xml',
                                     'Authorization': 'Basic %s' % self.userAndPass,
                                     #'Accept': 'application/json'
                                 },
                                 allow_redirects=False,
                                 verify=False)

        if response.status_code in [201, 200]:
            # workflow has been correctly created
            wfRunId = response.headers['location'].split("/")[-1]
            #wfRunId = response.url.split("/")[-1]

            return wfRunId

        raise Exception("Submitting workflow failed " + response.text)


    def setPlugins(self, wfRunId, pluginDefinition):
        """ Takes the contents of a plugin.xml file, and then creates this file in the server

        Arguments:
            workflowId (string): the workflow unique identifier

            pluginDefinition (string): the plugin definition file string buffer

        Returns:
            dictionary::

                Success -- True
                Failure -- raise errors with message

        """

        plugins = """<t2sr:upload t2sr:name="plugins.xml" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">%s</t2sr:upload>""" % base64.b64encode(
            pluginDefinition)

        response = requests.post("%s/%s/wd/plugins" % (self.url, wfRunId), data=plugins,
                                 headers={
                                     "Content-type": "application/xml",
                                     'Authorization': 'Basic %s' % self.userAndPass
                                 },
                                 allow_redirects=True,
                                 verify=False)

        if response.status_code == 201:
            return True

        raise Exception("Plugin setting failed " + response.text)

    def setPluginProperties(self, wfRunId, propertiesFileName, propertiesDefinition):
        """ Creates a properties file with the specified filename and content, and uploads the file to the server

        Arguments:
            workflowId (string): the workflow unique identifier

            propertiesFileName (string): the name of the properties file to be created

            propertiesDefinition (string): the content of the properties file

        Returns:
            dictionary::

                Success -- True
                Failure -- Raise exception with message

        """
        properties = """<t2sr:upload t2sr:name="%s" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">%s</t2sr:upload>""" % (
            propertiesFileName, base64.b64encode(propertiesDefinition))

        response = requests.post("%s/%s/wd/conf" % (self.url, wfRunId), data=properties,
                                 headers={
                                     "Content-type": "application/xml",
                                     'Authorization': 'Basic %s' % self.userAndPass
                                 },
                                 allow_redirects=True,
                                 verify=False)

        if response.status_code == 201:
            return True

        raise Exception("Plugin properties setting failed " + response.text)

    def setTicket(self, wfRunId, ticket):
        """ Stores the specified ticket in the working directory of the workflow with the specified id

        Arguments:
            workflowId (string): the workflow unique identifier

            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- True
                Failure -- raise Exception with message

        """

        credential = """<t2sr:upload t2sr:name="ticket" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">%s</t2sr:upload>""" % base64.b64encode(
            ticket)

        response = requests.post("%s/%s/wd/conf" % (self.url, wfRunId), data=credential,
                                 headers={
                                     "Content-type": "application/xml",
                                     'Authorization': 'Basic %s' % self.userAndPass
                                 },
                                 allow_redirects=True,
                                 verify=False)

        if response.status_code == 201:
            return True

        raise Exception("Ticket setting failed " + response.text)

    def setTrustedIdentity(self, wfRunId, identityFileName, identityDefinition):
        """ Takes the name of the certificate file, reads the contents of the file and submits the file contents to the server

        Arguments:
            workflowId (string): the workflow unique identifier

            identityFileName (string): name of the certificate file

            identityDefinition (string): contents of the certificate file

        Returns:
            dictionary::

                Success -- True
                Failure -- raise Exception with message

        """
        identity = """<t2sr:trustedIdentity xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/" xmlns:t2s="http://ns.taverna.org.uk/2010/xml/server/"><t2s:certificateFile>%s</t2s:certificateFile><t2s:certificateBytes>%s</t2s:certificateBytes></t2sr:trustedIdentity>""" % (
            base64.b64encode(identityFileName), base64.b64encode(identityDefinition))

        response = requests.post("%s/%s/security/trusts" % (self.url, wfRunId), data=identity,
                                 headers={
                                     "Content-type": "application/xml",
                                     'Authorization': 'Basic %s' % self.userAndPass
                                 },
                                 allow_redirects=True,
                                 verify=False)

        if response.status_code == 201:
            return True

        raise Exception("Trusted Identity setting failed " + response.text)

    def setWorkflowInputs(self, wfRunId, inputDefinition):
        """ Take the inputs definition string and create a baclava.xml file for the workflow with the given id.

        Arguments:
            workflowId (string): the workflowd unique identifier

            workflowDefinition (string): the workflow definition file string buffer

            inputDefinition (string):  the input definition file string buffer:param workflowId: the id unique identifier

            defaultInputMap (map): a map with the default inputs to be added to all  (i.e. defaultInputMap = {'sessionTicket': <sessionTicket<, 'workflowId': >workflowId>, ...}

        Returns:
            dictionary::

                Success -- True
                Failure -- Raise Exception with message
        """
        try:
            baclava = """<t2sr:upload xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/" t2sr:name="baclava.xml">%s</t2sr:upload>""" % base64.b64encode(inputDefinition)

            response = requests.post("%s/%s/wd" % (self.url, wfRunId), data=baclava,
                                     headers={
                                         "Content-type": "application/xml",
                                         'Authorization': 'Basic %s' % self.userAndPass
                                     },
                                     allow_redirects=True,
                                     verify=False)

            if response.status_code == 201:
                # PUT baclava
                response2 = requests.put("%s/%s/input/baclava" % (self.url, wfRunId ),
                             headers={
                                 "Content-type": "text/plain" ,
                                 'Authorization' : 'Basic %s' %  self.userAndPass
                             },
                            data="baclava.xml",
                            )


                if response2.status_code == 200:
                    return True

            raise Exception("Workflow input setting failed " + response.text)
        except Exception, e:
            print e
            raise Exception("Workflow input setting failed " + response.text)

    def getWorkflowInputs(self, wfRunId):
        """
            Retrieve the workflow inputs file from taverna  server

        :param workflowId:
        :return:
        """
        response = requests.get("%s/%s/wd/baclava.xml" % (self.url, wfRunId),
                                headers={
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Authorization': 'Basic %s' % self.userAndPass
                                },
                                allow_redirects=True,
                                verify=False)

        if response.status_code == 200:
            return response.text
        return ""

    def getWorkflowDefinition(self, wfRunId):
        """
            Retrieve the workflow file from taverna  server

        :param workflowId:
        :return:
        """

        response = requests.get("%s/%s/workflow" % (self.url, wfRunId),
                                headers={
                                    "Content-type": "text/plain",
                                    'Authorization': 'Basic %s' % self.userAndPass
                                },
                                allow_redirects=True,
                                verify=False)

        if response.status_code == 200:
            return response.text
        return ""

    def getRunInformations(self, wfRunId = ''):
        """ return the basic information associated to the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {
                'status': '',
                'createTime': '',
                'startTime': '',
                'finishTime': '',
                'expiry': '',
                'exitcode': '',
                'stdout': '',
                'stderr': '',
                'outputfolder': '',
                'endpoint': '',
                'workflowId': '',
                'asConfigId': '',
                'tavernaRunning': '',
                'owner': '',
                'wfRunning': ''
        }

        ret['endpoint'] = self.url
        ret['workflowId'] = self.workflowId
        ret['asConfigId'] = self.asConfigId
        ret['tavernaRunning'] = self.isAlive()
        ret['owner'] = self.username
        if wfRunId:
            wfJob = Workflow.query.filter_by(workflowRunId=wfRunId).first()
            ret['wfRunning'] = self.isWorkflowAlive(wfRunId)
            if wfJob:
                ret['outputfolder'] = wfJob.outputfolder
        else:
            ret['wfRunning'] = False
            return ret
        if ret['wfRunning']:
            infos = ["status", "createTime", "expiry", "startTime", "finishTime"]
            for info in infos:
                ret[info] = self.getInfo(wfRunId, info)

            additional_info = {'stderr': "listeners/io/properties/stderr",
                               'stdout': "listeners/io/properties/stdout",
                               'exitcode': "listeners/io/properties/exitcode"}

            for info in additional_info.keys():
                ret[info] = self.getInfo(wfRunId, additional_info[info])
            wfJob.update(ret)
            db.session.commit()
        elif wfJob:

            ret.update({
                'status': wfJob.status,
                'createTime': wfJob.createTime,
                'startTime': wfJob.startTime,
                'finishTime': wfJob.finishTime,
                'expiry': wfJob.expiry,
                'exitcode': wfJob.exitcode,
                'stdout': wfJob.stdout,
                'stderr': wfJob.stderr,
                'outputfolder': wfJob.outputfolder
            })

        return ret

    def getInfo(self, wfRunId, info):
        """ return the workflow id requested info as a string

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            string. The requested info as a string

        """

        headers = {"Content-type": "text/plain", 'Authorization': 'Basic %s' % self.userAndPass}
        response = requests.get('%s/%s/%s' % (self.url, wfRunId, info), headers=headers, verify=False)
        if response.status_code == 200:
            return response.content
        return ""

    def startWorkflow(self, wfRunId):
        """ start the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- Ture
                Failure -- False

        """
        response = requests.put("%s/%s/status" % (self.url, wfRunId ), data="Operating",
                                headers={
                                    "Content-type": "text/plain",
                                    'Authorization': 'Basic %s' % self.userAndPass
                                },
                                verify=False
        )
        if response.status_code in [200,201,202]:
            return True
        raise Exception('Error starting workflow on Taverna Server %s'%response.status_code )

    def setExpiry(self, wfRunId, expiry):
        """ set a new expiry date

        Arguments:
            wfRunId (string): the workflow run unique identifier

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        response = requests.put("%s/%s/expiry" % (self.url, wfRunId ), data=expiry,
                                headers={
                                    "Content-type": "text/plain",
                                    'Authorization': 'Basic %s' % self.userAndPass},
                                verify=False
        )
        if response.status_code in [200,201,202]:
            return True
        return False

    def deleteWorkflow(self, wfRunId):
        """ delete the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- True
                Failure -- False

        """
        if self.isWorkflowAlive(wfRunId):
            response = requests.delete("%s/%s" % (self.url, wfRunId),
                                       headers={
                                           "Content-type": "text/plain",
                                           'Authorization': 'Basic %s' % self.userAndPass
                                       },
                                       verify=False
            )

            if response.status_code == 204:
                return True
        else:
            return True

        return False

    def toDictionary(self):
        """ return a dictionary with object properties"""

        return {'username': self.username,
                'url': self.url,
                'workflowId': self.workflowId,
                'asConfigId': self.asConfigId,
                'count': self.count
        }

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

def notify_user_by_mi():
    """
    send a notification message that will be shown to the Master interface
    """

def submition_work_around(execution, server, ticket, tavernaURL, workflowDefinition):

    workflow_worker_built_failed = True
    while workflow_worker_built_failed:
        serverManager.deleteWorkflow(server.workflowId, ticket)
        tavernaServerId = serverManager.createWorkflow(ticket)
        atomicServiceConfigId = serverManager.getAtomicServiceConfigId(server.tavernaServerCloudId, ticket)
        if tavernaServerId and atomicServiceConfigId:
            print "retry::Taverna Server id %s, atomic config id  %s" %(str(tavernaServerId), str(atomicServiceConfigId))
            appliance_configuration_instance_id = serverManager.startAtomicService(atomicServiceConfigId, tavernaServerId, ticket)
            if appliance_configuration_instance_id:
                endpoint = app.config["CLOUDFACACE_PROXY_ENDPOINT"] % str(appliance_configuration_instance_id)
                if endpoint:
                    if tavernaURL is not "":
                        endpoint = tavernaURL
                    print "retry::Taverna Server endpoint %s" % endpoint
                    # now it can be created Taverna server instance
                    server.url = endpoint
                    server.workflowId = tavernaServerId
                    server.asConfigId = atomicServiceConfigId
                    execution.tavernaId = tavernaServerId
                    db.session.commit()
                else:
                    raise Exception('Error booting Taverna server')
            else:
                raise Exception('Error starting Atomic service')
        else:
            raise Exception('Error contacting cloud facade service')
        timeout = 20
        while server.isAlive() is not True and timeout > 0:
            timeout -= 1
            time.sleep(5)
        if timeout == 0:
            raise Exception('Taverna Server is not reachable.')

        try:
            return server.createWorkflow(workflowDefinition)
        except Exception, e:
            ## here start the implementation of the workaround
            # the workaround restart anytime the Taverna Server in the cloud
            # until the WM is not able to submit the workflow.
            workflow_worker_built_failed = (e.message=="Submitting workflow failed failed to build workflow run worker")
    raise Exception("Submitting workflow failed")



############################################################################
# xmlrpc methods
def execute_workflow(ticket, eid, workflowTitle, tavernaServerCloudId, workflowDefinition, inputDefinition, tavernaURL="", submitionWorkAround = False):
    user = extractUserFromTicket(ticket)

    execution = Execution.query.filter_by(username=user['username'], eid=eid).first()
    if execution is not None:
        #reset execution before start
        deleteExecution(eid, ticket)
    execution = Execution(user['username'], eid)
    db.session.add(execution)
    db.session.commit()
    #Now we don't have a stable taverna server then we have to create a new one for every execution
    server = TavernaServer.query.filter_by(username=user['username'], tavernaServerCloudId=tavernaServerCloudId).first()
    # remeber try execept
    try:
        if server is None:
            #if the server is not avaible ask to the cloud to start a new one
            tavernaServerId = serverManager.createWorkflow(ticket)
            atomicServiceConfigId = serverManager.getAtomicServiceConfigId(tavernaServerCloudId, ticket)
            if tavernaServerId and atomicServiceConfigId:
                execution.status = 1
                print "Taverna Server id %s, atomic config id  %s" %(str(tavernaServerId), str(atomicServiceConfigId))
                db.session.commit()
                appliance_configuration_instance_id = serverManager.startAtomicService(atomicServiceConfigId, tavernaServerId, ticket)
                if appliance_configuration_instance_id:
                    execution.status = 2
                    db.session.commit()
                    endpoint = app.config["CLOUDFACACE_PROXY_ENDPOINT"] % str(appliance_configuration_instance_id)
                    if endpoint:
                        if tavernaURL is not "":
                            endpoint = tavernaURL
                        print "Taverna Server endpoint %s" % endpoint
                        # now it can be created Taverna server instance
                        server = TavernaServer(user['username'], endpoint, tavernaServerId, atomicServiceConfigId, tavernaServerCloudId)
                        execution.tavernaId = tavernaServerId
                        execution.status = 3
                        db.session.add(server)
                        db.session.commit()
                    else:
                        raise Exception('Error booting Taverna server')
                else:
                    raise Exception('Error starting Atomic service')
            else:
                raise Exception('Error contacting cloud facade service')
        else:
            execution.status = 3
            execution.tavernaId = server.workflowId
            db.session.commit()
        #wait Taverna endpoint is ready
        timeout = 20
        while server.isAlive() is not True and timeout > 0:
            timeout -= 1
            time.sleep(5)
        if timeout == 0:
            raise Exception('Taverna Server is not reachable.')
        execution.status = 4
        db.session.commit()
        # create worfklow object
        try:
            wfRunid = server.createWorkflow(workflowDefinition)
        except Exception, e:
            ## here start the implementation of the workaround
            # the workaround restart anytime the Taverna Server in the cloud
            # until the WM is not able to submit the workflow.
            workflow_worker_built_failed = (e.message=="Submitting workflow failed failed to build workflow run worker")
            if workflow_worker_built_failed and submitionWorkAround:
                wfRunid = submition_work_around(execution, server, ticket, tavernaURL, workflowDefinition)
            else:
                raise Exception(e)
            pass
        print "Workflow submited - workflow run id: %s" % str(wfRunid)
        execution.workflowRunId = wfRunid
        execution.status = 5
        db.session.commit()
        abs_path = os.path.abspath(os.path.dirname(__file__))
        # pluginDefinition (string): the plugin specification file string buffer
        pluginDefinition = open(os.path.join(abs_path, 'plugins.xml'), 'r').read()
        # certificateFileName (string): filename of the certificate of the cloud provider
        certificateFileNameCyfronet = "vph.cyfronet.crt"
        certificateContentCyfronet = open(os.path.join(abs_path, certificateFileNameCyfronet), 'r').read()
        certificateFileNamePortal = "portal.vph-share.eu.crt"
        certificateContentPortal = open(os.path.join(abs_path, certificateFileNamePortal), 'r').read()
        # pluginPropertiesFileName (string): filename of the plugin properties file
        pluginPropertiesFileName = "vphshare.properties"
        ## set up the ticket in the plugin configuration
        server.setTicket(wfRunid, ticket)
        # set up cloud provider identity certificate
        server.setTrustedIdentity(wfRunid, certificateFileNameCyfronet, certificateContentCyfronet)
        server.setTrustedIdentity(wfRunid, certificateFileNamePortal, certificateContentPortal)
        # set up plugins
        server.setPlugins(wfRunid, pluginDefinition)
        if os.path.exists(os.path.join(abs_path, pluginPropertiesFileName)):
            propertiesFileContent = open(os.path.join(abs_path, pluginPropertiesFileName), 'r').read()
            # set up properties file
            server.setPluginProperties(wfRunid, pluginPropertiesFileName, propertiesFileContent)
        # process baclava file to create output folders
        #TODO code optimization of createOutputfolder method
        ret_o = createOutputFolders(wfRunid, inputDefinition, user['username'], ticket)
        if not 'inputDefinition' in ret_o or ret_o['inputDefinition'] == "":
            raise Exception('Error creating output folder')
        else:
            inputDefinition = ret_o['inputDefinition']
            outputFolder = ret_o['outputFolder']
            print "Outputfolder created: %s" % str(outputFolder)
        server.setWorkflowInputs(wfRunid, inputDefinition)
        server.setExpiry(wfRunid, (datetime.now()+timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000+01:00"))
        workflow = Workflow(user['username'], wfRunid, workflowTitle, outputFolder)
        db.session.add(workflow)
        execution.status = 6
        db.session.commit()
        server.startWorkflow(wfRunid)
        workflow.status = "Operating"
        print "Workflow running"
        execution.status = 7
        db.session.commit()
        try:
            alert_user_by_email(app.config['MAIL_FROM'], user['email'], '[VPH-Share] Workflow Started', 'mail.html',{'workflowId': wfRunid})
            print "Mail Sent"
        except Exception, e:
            pass
    except Exception, e:
        execution.error = True
        execution.error_msg = str(e)
        db.session.commit()
        stopWorkflow(eid, ticket)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print e
        return 'False'
    return 'True'


def stopWorkflow(eid, ticket):

    try:
        execution = Execution.query.filter_by(eid=eid).first()
        if execution.status >= 3:
            server = TavernaServer.query.filter_by(workflowId=execution.tavernaId).first()
            if server and execution.status >= 5:
                workflow = Workflow.query.filter_by(workflowRunId=execution.workflowRunId).first()
                if server.isWorkflowAlive(execution.workflowRunId):
                    server.deleteWorkflow(execution.workflowRunId)
                if workflow:
                    workflow.status = "Deleted"
                db.session.commit()
            if server and server.getWorkflowRunNumber() == 0:
                try:
                    serverManager.deleteWorkflow(server.workflowId, ticket)
                except Exception, e:
                    print e
                    pass
        return True
    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print e
        pass
    return False


def deleteExecution(eid, ticket):
    execution = Execution.query.filter_by(eid=eid).first()
    if stopWorkflow(eid, ticket):
        if execution.tavernaId != '':
            server = TavernaServer.query.filter_by(workflowId=execution.tavernaId).first()
            if server:
                db.session.delete(server)
                db.session.commit()
        if execution.workflowRunId != '':
            workflow = Workflow.query.filter_by(workflowRunId=execution.workflowRunId).first()
            if workflow:
                db.session.delete(workflow)
                db.session.commit()
        db.session.delete(execution)
        db.session.commit()
    return 'True'


def getWorkflowInformation(eid, ticket):
    """ return all information related to the workflow with the given id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'status': '', 'createTime': '', 'startTime': '', 'finishTime': '', 'expiry': '', 'exitcode': '', 'stdout': '', 'stderr': '', 'outputfolder': '', 'endpoint': '', 'workflowId': '', 'asConfigId': '', 'tavernaRunning': '', 'owner': '', 'wfRunning': ''}
                Failure -- False
    """
    try:
        ret = {'executionstatus':'', 'error': '', 'error_msg': '', 'status': '', 'createTime': '', 'startTime': '', 'finishTime': '', 'expiry': '', 'exitcode': '', 'stdout': '', 'stderr': '', 'outputfolder': '', 'endpoint': '', 'workflowId': '', 'asConfigId': '', 'tavernaRunning': '', 'owner': '', 'wfRunning': ''}
        execution = Execution.query.filter_by(eid=eid).first()
        ret['executionstatus'] = execution.status
        ret['error'] = execution.error
        ret['error_msg'] = execution.error_msg
        if execution.tavernaId:
            server = TavernaServer.query.filter_by(workflowId=execution.tavernaId).first()
            if server and  execution.workflowRunId:
                ret.update(server.getRunInformations(execution.workflowRunId))
                if ret['status'] == 'Finished':
                    execution.status = 8
                    db.session.commit()
                    ret['executionstatus'] = execution.status
                    stopWorkflow(eid, ticket)
                if execution.status == 7 and not ret['wfRunning'] and not ret['tavernaRunning'] :
                    execution.error = True
                    execution.error_msg = "Taverna process died"
                    db.session.commit()
                    stopWorkflow(eid, ticket)
            elif server:
                ret.update(server.getRunInformations(execution.workflowRunId))

        return ret
    except Exception, e:
        print e
        return False

def createOutputFolders(workflowId, inputDefinition, user, ticket):
    """
        Parses a baclava input definition file, create an output folder for the workflow with id workflowId,
        creates subfolders on it in case the input specifies a list of values, copy the input files into the newly
        created folders and finally modifies the input definition with the new pat of the input files
        
        Arguments:
            workflowId (string): the workflow id

            inputDefinition (string): the input definition file string buffer

            user (string): current user name

            ticket (string): a valid authentication ticket      
    """
    LOBCDER_ROOT_IN_WEBDAV = app.config["LOBCDER_ROOT_IN_WEBDAV"]
    LOBCDER_ROOT_IN_FILESYSTEM = app.config["LOBCDER_ROOT_IN_FILESYSTEM"]
    LOBCDER_PATH_PREFIX = app.config["LOBCDER_PATH_PREFIX"]
    namespaces = {'b': 'http://org.embl.ebi.escience/baclava/0.1alpha'}
    ret = {'workflowId': workflowId}
    ret['inputDefinition'] = ""
    try:
        # open LOBCDER connection
        webdav = easywebdav.connect(app.config["LOBCDER_URL"], app.config["LOBCDER_PORT"], username=user,
                                    password=ticket)
        workflowFolder = LOBCDER_ROOT_IN_FILESYSTEM + workflowId + '/'
        try:
            if webdav.exists(LOBCDER_ROOT_IN_WEBDAV + workflowId) == False:
                webdav.mkdir(LOBCDER_ROOT_IN_WEBDAV + workflowId)
        except Exception as e:
            # This is done to skip an erratic behaviour of the webdav, that is triggering an exception
            # even after the directory is successfully created
            if webdav.exists(LOBCDER_ROOT_IN_WEBDAV + workflowId) == False:
                raise e
            # parse input definition
        baclavaContent = xmltodict.parse(inputDefinition.encode('utf-8'))
        for dataThing in baclavaContent['b:dataThingMap']['b:dataThing']:
            myGridDataDocument = dataThing.get('b:myGridDataDocument', None)
            partialOrder = myGridDataDocument.get('b:partialOrder', None)
            # if partialOrder tag is not found, the input corresponds to a single value
            if partialOrder is None:
                dataElement = myGridDataDocument.get('b:dataElement', None)
                copySource = copyDestination = ''
                elementData = dataElement['b:dataElementData']
                decodedString = base64.b64decode(elementData)
                decodedString = string.replace(decodedString, LOBCDER_PATH_PREFIX, LOBCDER_ROOT_IN_FILESYSTEM)
                splittedString = string.split(decodedString, '/')
                elementData = workflowFolder + splittedString[len(splittedString) - 1]
                copySource = string.replace(decodedString, LOBCDER_ROOT_IN_FILESYSTEM, LOBCDER_ROOT_IN_WEBDAV)
                copyDestination = string.replace(elementData, LOBCDER_ROOT_IN_FILESYSTEM, LOBCDER_ROOT_IN_WEBDAV)
                inputDefinition = inputDefinition.replace(dataElement['b:dataElementData'], base64.b64encode(elementData), 1)
                webdav.copy(copySource, copyDestination)
            else:
            # if partialOrder tag is found, the input corresponds to a list of values
                if u'@type' in partialOrder and partialOrder[u'@type'] == "list":
                    itemList = partialOrder.get('b:itemList', None)
                    for dataElement in itemList.items()[0][1]:
                        # take the input file string, decode it, insert the new folder name on it an modify the input definition XML
                        elementData = dataElement['b:dataElementData']
                        decodedString = base64.b64decode(elementData)
                        decodedString = string.replace(decodedString, LOBCDER_PATH_PREFIX, LOBCDER_ROOT_IN_FILESYSTEM)
                        splittedString = string.split(decodedString, '/')
                        index = dataElement[u'@index']
                        # include the index of the element on the folder name
                        destinationFolder = LOBCDER_ROOT_IN_WEBDAV + workflowId + '/' + index
                        if webdav.exists(destinationFolder) == False:
                            webdav.mkdir(LOBCDER_ROOT_IN_WEBDAV + workflowId + '/' + index)
                        elementData = workflowFolder + index + '/' + splittedString[len(splittedString) - 1]
                        copySource = string.replace(decodedString, LOBCDER_ROOT_IN_FILESYSTEM, LOBCDER_ROOT_IN_WEBDAV)
                        copyDestination = string.replace(elementData, LOBCDER_ROOT_IN_FILESYSTEM, LOBCDER_ROOT_IN_WEBDAV)
                        webdav.copy(copySource, copyDestination)
                        inputDefinition = inputDefinition.replace(dataElement['b:dataElementData'], base64.b64encode(elementData), 1)
        ret['inputDefinition'] = inputDefinition
        ret['outputFolder'] = '/%s/' % workflowId
    except Exception as e:
        raise Exception('Error creating output folder')

    return ret

############################################################################
# register xmlrpc callback
xmlrpc.register(hello, "hello")
xmlrpc.register(execute_workflow, "execute_workflow")
xmlrpc.register(stopWorkflow, 'stopWorkflow')
xmlrpc.register(deleteExecution, 'deleteExecution')
xmlrpc.register(getWorkflowInformation, "getWorkflowInformation")
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

    app.run(threaded=True, **app_options)
