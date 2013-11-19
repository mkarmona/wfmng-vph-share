# Copyright (C) 2012 SCS srl <info@scsitaly.com>

""" This module defines the TavernaServerConnector a wrapper for the Taverna Server functions."""

import httplib
import base64
import thread

import forward

class TavernaServerConnector():
    """ The TavernaServerConnector allows the Workflow Manager to contact the Taverna Server application, directly
    trough http or tunneled trough a ssh connection.

    Arguments:
        tunneling (boolean): True if connection goes trough a ssh tunnel

        url (string): the server url

        localPort (int): the local port number

        remoteHost (string): the remoteHost name

        remotePort (int): the remote port number

        username (string): the username to access to the remote system

        password (string): the password to access to the remote system

    """

    def __init__(self, tunneling, url, localPort=8080, remoteHost='', remotePort=8080, username='', password=''):
        """ initialize the connector with the given taverna server url
        """

        if tunneling:
            self.tunneling = True
            self.tunneler = thread.start_new_thread(forward.start,
                                                    (localPort, remoteHost, remotePort, username, password))
            self.server_url = '127.0.0.1:%s' % localPort
        else:
            self.tunneling = False
            self.server_url = url
        self.service_url = "/taverna-server/rest/runs"
        self.userAndPass = base64.b64encode(username + ":" + password)
        self.CREATE_WORKFLOW_MAX_NUMBER_OF_ATTEMPTS = maxAttempts

    def createWorkflow(self, workflowDefinition):
        """ Create a new workflow according to the given definition string.

        Arguments:
            workflowDefinition (string): the workflow definition file string buffer

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        self.connection = httplib.HTTPConnection(self.server_url)
        self.connection = httplib.HTTPSConnection(self.server_url)

        ret = {}

        wf = workflowDefinition

        # if not wf.count("""<workflow xmlns="http://ns.taverna.org.uk/2010/xml/server/">"""):
        #    wf = """<workflow xmlns="http://ns.taverna.org.uk/2010/xml/server/"> %s </workflow>""" % wf

        # post workflow definition file 
        headers = {"Content-type": "application/vnd.taverna.t2flow+xml"}
        self.connection.request("POST", self.service_url, wf, headers)
        workflowCreatedSucessfully = False
        counter = 0
        while (not workflowCreatedSucessfully) and counter < self.CREATE_WORKFLOW_MAX_NUMBER_OF_ATTEMPTS:

            try:

                # increase attempt counter
                counter = counter + 1

                # post workflow definition file 
                headers = {"Content-type": "application/vnd.taverna.t2flow+xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
                self.connection.request("POST", self.service_url, wf, headers)

                # get and handle response
                response = self.connection.getresponse()
                o = response.read()

                if response.status == 201:

                    workflowCreatedSucessfully = True
                    # workflow has been correctly created              
                    ret["workflowId"] = response.msg["Location"].split("/")[-1]

                    # get brand new created workflow information            
                    info = self.getWorkflowInformation(ret["workflowId"])

                    ret.update(info)

                else:
                    ret["workflowId"] = ""
                    ret["error.description"] = "Error Creating Workflow: " + o
                    if counter == self.CREATE_WORKFLOW_MAX_NUMBER_OF_ATTEMPTS:
                        ret["error.description"] = ret["error.description"] + ". Maximum number of attempts reached !" 
                    ret["error.code"] = "%s %s" % ( response.status, response.reason)

            except Exception as e:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Workflow! %s" % str(e)
                ret["error.code"] = ""

            # close previous connection
            self.connection.close()

        return ret
        
    def setServerURL(self, url):
        """ Sets the base URL of the Taverna Server

        Arguments:
            url (string): the base URL of the Taverna Server

        """ 
        self.server_url = url

    def setServicePath(self, path):
        """ Sets the path to the Taverna Server, with respect to the base URL

        Arguments:
            url (string): the path to the Taverna Server, with respect to the base URL

        """ 
        self.service_url = path
        
    def setPlugins(self, workflowId, pluginDefinition):
        """ Takes the contents of a plugin.xml file, and then creates this file in the server

        Arguments:
            workflowId (string): the workflow unique identifier

            pluginDefinition (string): the plugin definition file string buffer

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        
        self.connection = httplib.HTTPSConnection(self.server_url)
        
        ret = {}
        
        plugins = """<t2sr:upload t2sr:name="plugins.xml" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">%s</t2sr:upload>""" % base64.b64encode(pluginDefinition)

        try:

            ret["workflowId"] = workflowId

            # POST plugin.xml file
            headers = {"Content-type": "application/xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
            self.connection.request('POST',
                "%s/%s/wd/plugins" % (self.service_url, workflowId),
                 plugins,
                 headers)
            response = self.connection.getresponse()
            o = response.read()

            if response.status != 201:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Plugin File!"
                ret["error.code"] = "%s %s" % (response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error Creating Plugin File!"
            ret["error.code"] = "500 Internal Server Error"

        self.connection.close()

        return ret

    def setPluginProperties(self, workflowId, propertiesFileName, propertiesDefinition):
        """ Creates a properties file with the specified filename and content, and uploads the file to the server

        Arguments:
            workflowId (string): the workflow unique identifier

            propertiesFileName (string): the name of the properties file to be created

            propertiesDefinition (string): the content of the properties file

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        
        self.connection = httplib.HTTPSConnection(self.server_url)
        
        ret = {}
        
        properties = """<t2sr:upload t2sr:name="%s" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">%s</t2sr:upload>""" % (propertiesFileName,base64.b64encode(propertiesDefinition))

        try:

            ret["workflowId"] = workflowId

            # POST properties file
            headers = {"Content-type": "application/xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
            self.connection.request('POST',
                "%s/%s/wd/conf" % (self.service_url, workflowId),
                 properties,
                 headers)
            response = self.connection.getresponse()
            o = response.read()

            if response.status != 201:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Properties File!"
                ret["error.code"] = "%s %s" % (response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error Creating Properties File!"
            ret["error.code"] = "500 Internal Server Error"

        self.connection.close()

        return ret

    def setTicket(self, workflowId, ticket):
        """ Stores the specified ticket in the working directory of the workflow with the specified id

        Arguments:
            workflowId (string): the workflow unique identifier

            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        ret = {}

        credential = """<t2sr:upload t2sr:name="ticket" xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/">"""
        credential = credential + base64.b64encode(ticket)
        credential = credential + """</t2sr:upload>"""

        try:

            ret["workflowId"] = workflowId

            # POST credentials
            headers = {"Content-type": "application/xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
            self.connection.request('POST',
                 "%s/%s/wd/conf" % (self.service_url, workflowId),
                 credential,
                 headers)
            response = self.connection.getresponse()
            o = response.read()

            if response.status != 201:
                ret["workflowId"] = ""
                ret["error.description"] = "Error setting authentication ticket in workflow working directory!"
                ret["error.code"] = "%s %s" % (response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error setting authentication ticket in workflow working directory!"
            ret["error.code"] = "500 Internal Server Error"

        self.connection.close()

        return ret

    def setTrustedIdentity(self, workflowId, identityFileName, identityDefinition):
        """ Takes the name of the certificate file, reads the contents of the file and submits the file contents to the server

        Arguments:
            workflowId (string): the workflow unique identifier

            identityFileName (string): name of the certificate file

            identityDefinition (string): contents of the certificate file

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        ret = {}

        identity = """<t2sr:trustedIdentity xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/" xmlns:t2s="http://ns.taverna.org.uk/2010/xml/server/">"""
        identity = identity + """<t2s:certificateFile>%s</t2s:certificateFile>""" % base64.b64encode(identityFileName)
        identity = identity + """<t2s:certificateBytes>%s</t2s:certificateBytes></t2sr:trustedIdentity>""" % base64.b64encode(identityDefinition)

        try:

            ret["workflowId"] = workflowId

            # POST identity file
            headers = {"Content-type": "application/xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
            self.connection.request('POST',
                "%s/%s/security/trusts" % (self.service_url, workflowId),
                 identity,
                 headers)
            response = self.connection.getresponse()
            o = response.read()

            if response.status != 201:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Trusted Identity!"
                ret["error.code"] = "%s %s" % (response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error Creating Trusted Identity!"
            ret["error.code"] = "500 Internal Server Error"

        self.connection.close()

        return ret

    def setWorkflowInputs(self, workflowId, inputDefinition):
        """ Take the inputs definition string and create a baclava.xml file for the workflow with the given id.

        Arguments:
            workflowId (string): the workflowd unique identifier

            workflowDefinition (string): the workflow definition file string buffer

            inputDefinition (string):  the input definition file string buffer:param workflowId: the id unique identifier

            defaultInputMap (map): a map with the default inputs to be added to all  (i.e. defaultInputMap = {'sessionTicket': <sessionTicket<, 'workflowId': >workflowId>, ...}

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        ret = {}

        self.connection = httplib.HTTPSConnection(self.server_url)

        baclava = """<t2sr:upload xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/" t2sr:name="baclava.xml">%s</t2sr:upload>""" % base64.b64encode(inputDefinition)

        headers = {"Content-type": "application/xml" , 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request('POST',
                                "%s/%s/wd" % (self.service_url, workflowId),
                                baclava,
                                headers)
        response = self.connection.getresponse()
        o = response.read()

        try:

            ret["workflowId"] = workflowId

            # PUT baclava
            headers = {"Content-type": "text/plain" , 'Authorization' : 'Basic %s' %  self.userAndPass}
            self.connection.request('PUT',
                                    "%s/%s/input/baclava" % (self.service_url, workflowId ),
                                    "baclava.xml",
                                    headers)
            response = self.connection.getresponse()
            o = response.read()

            if response.status != 200:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Input File!"
                ret["error.code"] = "%s %s" % (response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error Creating Input File!"
            ret["error.code"] = "500 Internal Server Error"

        self.connection.close()

        return ret

    def getWorkflowInputs(self, workflowId):
        """
            Retrieve the workflow inputs file from taverna  server

        :param workflowId:
        :return:
        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request("GET", "%s/%s/wd/baclava.xml" % (self.service_url, workflowId), "", headers)
        response = self.connection.getresponse()
        ret = response.read()

        self.connection.close()

        return ret

    def getWorkflowDefinition(self, workflowId):
        """
            Retrieve the workflow file from taverna  server

        :param workflowId:
        :return:
        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        headers = {"Content-type": "text/plain" , 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request("GET", "%s/%s/workflow" % (self.service_url, workflowId), "", headers)
        response = self.connection.getresponse()
        ret = response.read()

        self.connection.close()

        return ret

    def getWorkflowInformation(self, workflowId):
        """ return the basic information associated to the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        ret = {'workflowId': workflowId}

        infos = ["status", "createTime", "expiry", "startTime", "finishTime", "owner"]

        for info in infos:
            try:
                ret[info] = self.getWorkflowInfo(workflowId, info)
            except Exception as e:
                ret[info] = ""
                ret["error.description"] = "Error Getting Workflow Information ( %s ) " % info
                ret["error.code"] = type(e)
                self.connection.close()

        if ret["status"] == 'Finished':

            additional_info = {'stderr': "listeners/io/properties/stderr",
                               'stdout': "listeners/io/properties/stdout",
                               'exitcode': "listeners/io/properties/exitcode"}

            for info in additional_info.keys():

                try:
                    ret[info] = self.getWorkflowInfo(workflowId, additional_info[info])
                except Exception as e:
                    ret[info] = ""
                    ret["error.description"] = "Error Getting Workflow Information ( %s ) " % info
                    ret["error.code"] = type(e)
                    self.connection.close()
        else:
            ret["stderr"] = ""
            ret["stdout"] = ""
            ret["exitcode"] = ""

        return ret

    def getWorkflowInfo(self, workflowId, info):
        """ return the workflow id requested info as a string

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            string. The requested info as a string

        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        headers = {"Content-type": "text/plain" , 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request("GET", "%s/%s/%s" % (self.service_url, workflowId, info), "", headers)
        response = self.connection.getresponse()
        ret = response.read()

        self.connection.close()

        return ret

    def startWorkflow(self, workflowId):
        """ start the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """

        self.connection = httplib.HTTPSConnection(self.server_url)

        headers = {"Content-type": "text/plain" , 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request('PUT',
                                "%s/%s/status" % (self.service_url, workflowId ),
                                "Operating",
                                headers)
        result = self.connection.getresponse()
        result.read()

        self.connection.close()

        return self.getWorkflowInformation(workflowId)

    def deleteWorkflow(self, workflowId):
        """ delete the workflow with the given workflow id

        Arguments:
            workflowId (string): the workflow unique identifier

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value', 'info01':'a string value', 'info02':'a string value',..}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        # recover information
        info = self.getWorkflowInformation(workflowId)

        # send delete commmand
        self.connection = httplib.HTTPSConnection(self.server_url)

        headers = {"Content-type": "text/plain" , 'Authorization' : 'Basic %s' %  self.userAndPass}
        self.connection.request('DELETE',
                                "%s/%s" % (self.service_url, workflowId),
                                "",
                                headers)
        response = self.connection.getresponse()
        response.read()

        self.connection.close()

        info['status'] = 'Deleted'

        return info


