__author__ = 'm.balasso@scsitaly.com'
import time
import os
from xmlrpclib import ServerProxy

from auth import getAuthTicket

wfmng = ServerProxy("http://wfmng.vph-share.eu/api")
#user = 'testuser'
#passwd = ''

tavernaServerASid = "528a3b948664880b2b00f0cf" # (Taverna server secured - SUN JDK)
#"526a78538664880543005f6b" # (Taverna server insecured - SUN JDK)
#"51ded4da86648825040093fe" # (Taverna server secured - OpenJDK)
ticket = getAuthTicket( user, passwd )

#print "=== getWorkflowsList"
#print wfmng.getWorkflowsList({}, ticket) # {} is a query

print "=== createTavernaServerWorkflow"
ret = wfmng.createTavernaServerWorkflow(user, ticket)

if ret:
    tavernaServerWorkflowId = ret["tavernawfId"]
    print "Using Taverna Server in workflow " + tavernaServerWorkflowId
    print "Server URL: " + ret["tavernaURL"]
    print "=== submitWorkflow"    
    abs_path = os.path.abspath(os.path.dirname(__file__))
    wf_definition = open(os.path.join(abs_path, 'SimpleWorkflow.t2flow'), 'r').read()
    input_definition = open(os.path.join(abs_path, 'SimpleWorkflowInputs.xml'), 'r').read()
    wf_title = 'test workflow'

    # set workflow initialization parameters
    plugin_definition = open(os.path.join(abs_path, 'plugins.xml'), 'r').read()
    certificate_file = "vph.cyfronet.crt"
    plugin_properties_file = "vphshare.properties"

    # submit worflow
    ret = wfmng.submitWorkflow(wf_title, wf_definition, input_definition, ticket)
    print ret    

    if 'workflowId' in ret and ret['workflowId']:
        wf_id = ret['workflowId']

        print "=== startWorkflow"
        print wfmng.startWorkflow(wf_id)

        print "=== getWorkflowInformation"
        info = wfmng.getWorkflowInformation(wf_id,ticket)
        print info

        while info['status'] != 'Finished':
            print "=== sleeping for 5..."
            time.sleep(5)
            print "=== getWorkflowInformation"
            info = wfmng.getWorkflowInformation(wf_id,ticket)
            print info

        print "=== deleteWorkflow"
        ret = wfmng.deleteWorkflow(wf_id)
        print ret
        

    print "=== deleteTavernaServerWorkflow"
    ticket = getAuthTicket(user, passwd) # get a fresh ticket, just in case the TS has been running for a long time
    ret = wfmng.deleteTavernaServerWorkflow(tavernaServerWorkflowId, user, ticket)
    print ret
