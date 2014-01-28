import requests
import json

class CloudFacadeInterface():
    """ The CloudFacadeInterface allows the creation, managements and destruction of workflows in the cloudfacade """
   
    def __init__(self, cfURL):
        """ Initializes the manager

        Arguments:
            cfURL (string): the url of the cloudfacade API

        """
        self.CLOUDFACACE_URL = cfURL

    def createWorkflow(self, ticket):
        """ Creates a new workflow in the cloudfacade

        Arguments:
            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            body = json.dumps({'name': "Taverna Server Workflow", 'appliance_set_type':  "workflow"})
            headers = {'Content-type': 'application/json', 'MI-TICKET': ticket}
            con = requests.post(
                "%s/appliance_sets" % self.CLOUDFACACE_URL,
                headers=headers,
                data = body, 
                verify = False
            )

            if con.status_code in [201, 200]:
                return con.json()['appliance_set']['id']

        except Exception as e:
            print e
            pass

        raise Exception('Problem to create the workflow instance')


    def deleteWorkflow(self,  workflowId, ticket):
        """ Deletes the workflow with id workflowId from the cloudfacade

        Arguments:
            workflowId (string): a valid id for a workflow in the cloudfacade

            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            ret["workflowId"] = workflowId
            headers = { 'MI-TICKET': ticket}
            con = requests.delete(
                "%s/appliance_sets/%s" % (self.CLOUDFACACE_URL, workflowId),
                headers=headers,
                verify = False
            )
            if con.status_code in [200, 201, 204]:
                return True

        except Exception as e:
            print e
            pass
        return False


    def getAtomicServiceConfigId(self, atomicServiceId, ticket):
        """ Retrieves the service configuration Id of an AS

        Arguments:
            atomicServiceId (string): a valid id for an atomic service in the cloudfacade

            ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'asConfigId':'a string value'}
                Failure -- {'asConfigId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            headers = {'MI-TICKET': ticket}
            con = requests.get(
                "%s/appliance_configuration_templates?appliance_type_id=%s" % (self.CLOUDFACACE_URL, atomicServiceId),
                headers=headers,
                verify = False
            )
            if con.status_code in [200, 201, 204]:
                json = con.json()
                return json['appliance_configuration_templates'][0]['id']

        except Exception as e:
            print e
            pass



    def startAtomicService(self, atomicServiceConfigId, workflowId, ticket):
        """ Adds an atomic service to a workflow 

        Arguments:
           workflowId (string): a valid id for a workflow in the cloudfacade

           atomicServiceConfigId (string): a valid atomic service configuration id in the cloudfacade

           ticket (string): a valid authentication ticket

        Returns:
            dictionary::

                Success -- {'workflowId':'a string value'}
                Failure -- {'workflowId':'', 'error.description':'', error.code:''}

        """
        ret = {}
        try:
            ret["workflowId"] = workflowId
            ret["endpointId"] = ''
            headers = {'Content-type': 'application/json', 'MI-TICKET': ticket}
            body = json.dumps( { 'appliance': { 'appliance_set_id' : workflowId, 'configuration_template_id':  atomicServiceConfigId } } )
            con = requests.post(
                "%s/appliances" % self.CLOUDFACACE_URL,
                headers=headers,
                data = body, 
                verify = False
            )

            if con.status_code in [200, 201, 204]:
                response = con.json()
                return response['appliance']['id']

        except Exception as e:
            print e
            pass
        raise Exception('Atomic service start error')




    # def getASwebEndpoint(self, atomicServiceConfigId, workflowId, ticket):
        # """ Retrieves the web endpoint URL of an atomic service 

        # Arguments:
           # workflowId (string): a valid id for a workflow in the cloudfacade

           # atomicServiceConfigId (string): a valid atomic service configuration id in the cloudfacade

           # ticket (string): a valid authentication ticket

        # Returns:
            # dictionary::

                # Success -- {'endpoint':'a string value'}
                # Failure -- {'endpoint':'', 'error.description':'', error.code:''}

        # """
        # ret = {}
        # try:
            # ret["workflowId"] = workflowId
            # url = "null"
            # while url.find("null")!=-1:
                # con = requests.get(
                    # "%s/workflows/%s/atomic_services/%s/redirections" % (self.CLOUDFACACE_URL, workflowId, atomicServiceConfigId ),
                    # auth=("", ticket),
                    # verify = False
                    # )
                # json = con.json()
                # if json["http"][0]["urls"][0].find("null")==-1:
                    # url = json["http"][0]["urls"][0]

                # print con

            # ret["endpoint"] = url

        # except Exception as e:
            # ret["endpoint"] = ""
            # ret["error.description"] = "Error getting Taverna Server endpoint in workflow " + workflowId
            # ret["error.code"] = e

        # return ret



    def isWebEndpointReady(self, url, username, password):
        """ Checks if the web endpoint at URL is reachable

        Arguments:
            url (string): a valid endpoint url 

            ticket (string): a valid authentication ticket

        Returns:
            True is a successful connection was made to the endpoint. It returns False otherwise.
            

        """
        if url:
            con = requests.get( 
                url,
                auth=(username, password),
                verify = False
                )
            if con.status_code in [200,201,204]:
                return True
        return False;