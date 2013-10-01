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

        ret = {}

        wf = workflowDefinition

        # if not wf.count("""<workflow xmlns="http://ns.taverna.org.uk/2010/xml/server/">"""):
        #    wf = """<workflow xmlns="http://ns.taverna.org.uk/2010/xml/server/"> %s </workflow>""" % wf

        # post workflow definition file 
        headers = {"Content-type": "application/vnd.taverna.t2flow+xml"}
        self.connection.request("POST", self.service_url, wf, headers)

        try:
            # get and handle response
            response = self.connection.getresponse()
            o = response.read()

            if response.status == 201:

                # workflow has been correctly created              
                ret["workflowId"] = response.msg["Location"].split("/")[-1]

                # get brand new created workflow information            
                info = self.getWorkflowInformation(ret["workflowId"])

                ret.update(info)

            else:
                ret["workflowId"] = ""
                ret["error.description"] = "Error Creating Workflow!"
                ret["error.code"] = "%s %s" % ( response.status, response.reason)

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error Creating Workflow! %s" % str(e)
            ret["error.code"] = ""

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

        self.connection = httplib.HTTPConnection(self.server_url)

        baclava = """<t2sr:upload xmlns:t2sr="http://ns.taverna.org.uk/2010/xml/server/rest/" t2sr:name="baclava.xml">%s</t2sr:upload>""" % base64.b64encode(inputDefinition)

        headers = {"Content-type": "application/xml"}
        self.connection.request('POST',
                                "%s/%s/wd" % (self.service_url, workflowId),
                                baclava,
                                headers)
        response = self.connection.getresponse()
        o = response.read()

        try:

            ret["workflowId"] = workflowId

            # PUT baclava
            headers = {"Content-type": "text/plain"}
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

        self.connection = httplib.HTTPConnection(self.server_url)

        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
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

        self.connection = httplib.HTTPConnection(self.server_url)

        headers = {"Content-type": "text/plain"}
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

        self.connection = httplib.HTTPConnection(self.server_url)

        headers = {"Content-type": "text/plain"}
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

        self.connection = httplib.HTTPConnection(self.server_url)

        headers = {"Content-type": "text/plain"}
        self.connection.request('PUT',
                                "%s/%s/status" % (self.service_url, workflowId),
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
        self.connection = httplib.HTTPConnection(self.server_url)

        headers = {"Content-type": "text/plain"}
        self.connection.request('DELETE',
                                "%s/%s" % (self.service_url, workflowId),
                                "",
                                headers)
        response = self.connection.getresponse()
        response.read()

        self.connection.close()

        info['status'] = 'Deleted'

        return info

    #ERNESTO
    # 2
    # write the code to contact the taverna server in this class method
    def mySampleMethod(self, workflowId, sample_parameter):
        """
         This method makes a sample operation
        """

        # create the return map (we are happy map users :)
        ret = {}

        # open the connection to the taverna server
        self.connection = httplib.HTTPConnection(self.server_url)

        # specify headers
        headers = {"Content-type": "application/xml"}

        # hint, howto base64 encode a string
        b64_encoded_sample_parameter = base64.b64encode(sample_parameter)

        # send the request
        self.connection.request('POST',  # request method
                                "%s/%s/wd/plugins" % (self.service_url, workflowId),  # request url
                                b64_encoded_sample_parameter,  # request message
                                headers)  # request headers

        # get the response object from the server
        response = self.connection.getresponse()

        # hint, check the reponse status
        if response.status != 200:
            print "I'm not happy!"

            # always add the error details into the return map so the caller can understand what happened
            ret['returnValue'] = 'ko'
            ret["error.description"] = "Error executing my sample method!"
            ret["error.code"] = "%s %s" % (response.status, response.reason)

        else:
            print "I'm happy!"

            # hint, howto read the response body
            print response.read()

            # we just need to know everything is fine, nothing more
            ret['returnValue'] = 'ok'

        # always close the connection to the taverna server
        self.connection.close()

        # return to the workflow manager
        return ret
