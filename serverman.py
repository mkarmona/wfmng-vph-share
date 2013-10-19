import requests
import json

CLOUDFACACE_URL = "https://vph.cyfronet.pl/cloudfacade"

class TavernaServerManager():
    """ The TavernaServerManager allows the creation and destruction of a workflow with a Taverna Server AS running on it """

    test = False

    def __init__(self, atomicServiceId, workflowId = "", webendpoint="", atomicServiceConfigId="" ):
        """ Initializes a new TS Manager

        Arguments:
            atomicServiceId (string): the cloudfacade id of the AS with the Taverna Server

            workflowId (string): the workflow id of an already existing workflow with a Taverna Server, omit it if a new workflow will be created

            webendpoint (string): the web endpoint of an already existing Taverna Server, omit it if a new Taverna Server will be created

            atomicServiceConfigId (string): the configuration id of an already existing AS in a Taverna Server workflow, omit it if a new AS will be created

        """	

        self.workflowId = workflowId
        self.atomicServiceConfigId = atomicServiceConfigId
        self.atomicServiceId = atomicServiceId
        self.webendpoint = webendpoint

    def createTavernaServerWorkflow(self, ticket):
        """ Creates a new workflow, which will contain a taverna server AS

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            body = json.dumps({'name': "tavernaserverworkflow", 'type':  "workflow"})
            con = requests.post(
                "%s/workflows" % CLOUDFACACE_URL,
                auth=("", ticket),
                data = body, 
                verify = False
            )

            if con.status_code != 200:
                ret["workflowId"] = ""
                ret["error.description"] = "Error creating Taverna Server workflow"
                ret["error.code"] = con.status_code

            ret["workflowId"] = con.text
            self.workflowId = con.text

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error creating Taverna Server workflow"
            ret["error.code"] = e

        return ret


    def deleteTavernaServerWorkflow(self, ticket):
        """ Deletes the workflow containing the taverna server AS

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            ret["workflowId"] = self.workflowId
            con = requests.delete(
                "%s/workflows/%s" % (CLOUDFACACE_URL, self.workflowId),
                auth=("", ticket),
                verify = False
            )
            if con.status_code != 200 and con.status_code != 204:
                ret["workflowId"] = ""
                ret["error.description"] = "Error deleting workflow " + self.workflowId
                ret["error.code"] = con.status_code

        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error deleting workflow " + self.workflowId
            ret["error.code"] = e

        return ret



    def getTavernaServerAtomicServiceConfigId(self, ticket):
        """ Retrieves the service configuration Id of the  taverna server AS

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'asConfigId':'a string value'}
                Failure -- {'asConfigId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            con = requests.get(
                "%s/atomic_services/%s/configurations" % (CLOUDFACACE_URL, self.atomicServiceId),
                auth=("", ticket),
               verify = False
            )

            if con.status_code != 200:
                ret["asConfigId"] = ""
                ret["error.description"] = "Error getting configuration Id for AS " + self.atomicServiceId
                ret["error.code"] = con.status_code

            json = con.json()
            ret["asConfigId"] = json[0]["id"]

        except Exception as e:
            print e
            ret["asConfigId"] = ""
            ret["error.description"] = "Error getting configuration Id for AS " + self.atomicServiceId
            ret["error.code"] = e

        return ret



    def startTavernaServer(self, ticket):
        """ Adds the taverna server AS to the workflow

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            ret["workflowId"] = self.workflowId
            ret_asi = self.getTavernaServerAtomicServiceConfigId(ticket)
            self.atomicServiceConfigId = ret_asi["asConfigId"] 
            body = json.dumps( {'asConfigId':  self.atomicServiceConfigId} )
            con = requests.post(
                "%s/workflows/%s/atomic_services" % (CLOUDFACACE_URL, self.workflowId),
                auth=("", ticket),
                data = body, 
                verify = False
            )
            if con.status_code != 200:
                ret["workflowId"] = ""
                ret["error.description"] = "Error starting Taverna Server in workflow " + self.workflowId
                ret["error.code"] = con.status_code
                
        except Exception as e:
            ret["workflowId"] = ""
            ret["error.description"] = "Error starting Taverna Server in workflow " + self.workflowId
            ret["error.code"] = e

        return ret



    def getTavernaServerWebEndpoint(self, ticket):
        """ Retrieves the web endpoint URL of the taverna server AS managed by this class

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'endpoint':'a string value'}
                Failure -- {'endpoint':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            ret["workflowId"] = self.workflowId
            url = "null"
            while url.find("null")!=-1:
                con = requests.get(
                    "%s/workflows/%s/atomic_services/%s/redirections" % (CLOUDFACACE_URL, self.workflowId, self.atomicServiceConfigId ),
                    auth=("", ticket),
                    verify = False
                    )
                json = con.json()
                if json["http"][0]["urls"][0].find("null")==-1:
                    url = json["http"][0]["urls"][0]

            ret["endpoint"] = url
            self.webendpoint = url

        except Exception as e:
            ret["endpoint"] = ""
            ret["error.description"] = "Error getting Taverna Server endpoint in workflow " + self.workflowId
            ret["error.code"] = e

        return ret



    def isWebEndpointReady(self, ticket):
        """ Checks if the taverna server is running in the endpoint URL

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            True is a successful connection was made to the endpoint. It returns False otherwise.
            

        """
        if self.webendpoint:
            con = requests.get( 
                self.webendpoint,
                auth=("", ticket),
                verify = False
                )
            if con.status_code == 200:
                return True
        return False;
