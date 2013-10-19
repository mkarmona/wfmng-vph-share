__author__ = 'm.balasso@scsitaly.com'

import os
import time
from xmlrpclib import ServerProxy

from auth import getAuthTicket

from serverman import TavernaServerManager
import time 
from wfmng import TavernaServer
from wfmng import db

wfmng = ServerProxy("http://localhost:5000/api")

ticket = getAuthTicket('ecoto', 'ecoto123')

#print "=== getWorkflowsList"
#print wfmng.getWorkflowsList({}, ticket) # {} is a query

print "=== createTavernaServerWorkflow"
server = TavernaServer.query.filter_by(username='ecoto').first()
if server is None:
    serverManager = TavernaServerManager("51ded4da86648825040093fe")
    ret = serverManager.createTavernaServerWorkflow(ticket)
    workflowId = ret["workflowId"]
    if workflowId:
        serverManager.startTavernaServer(ticket)
        ret = serverManager.getTavernaServerWebEndpoint(ticket)
        serverURL = ret["endpoint"]
        if serverURL:
            print "Taverna Server created at " + serverURL+"/taverna-server/"
            server = TavernaServer('ecoto', serverURL, workflowId, serverManager.atomicServiceConfigId)
            db.session.add(server)
            db.session.commit()
            print "Wait for server to be ready"
            serverURL = serverURL[(serverURL.find("//")+2):]  # remove http:// or https://
            path = serverURL[(serverURL.find("/")+1):]        # split path 
            serverURL = serverURL[:serverURL.find("/")]       # split server base URL
            wfmng.setTavernaServerURL(serverURL)
            wfmng.setTavernaServerServicePath("/"+path+"/taverna-server/rest/runs")
            while serverManager.isWebEndpointReady(ticket)!=True:  # wait a bit until the server is ready.
                time.sleep(5)
else:
    serverManager = TavernaServerManager("51ded4da86648825040093fe", server.workflowId, server.url, server.asConfigId)
    print "Taverna Server found at " + server.url+"/taverna-server/"


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
ret = wfmng.submitWorkflow(wf_title, wf_definition, input_definition, plugin_definition, certificate_file, plugin_properties_file, ticket)
print ret

# increase number of workflows running in this server
server.count = server.count + 1 
db.session.commit()


if 'workflowId' in ret and ret['workflowId']:
    wf_id = ret['workflowId']
    print "=== startWorkflow"
    print wfmng.startWorkflow(wf_id)

    print "=== getWorkflowInformation"
    info = wfmng.getWorkflowInformation(wf_id)
    print info

    while info['status'] != 'Finished':
        print "=== sleeping for 5..."
        time.sleep(5)
        print "=== getWorkflowInformation"
        info = wfmng.getWorkflowInformation(wf_id)
        print info

    print "=== deleteWorkflow"
    ret = wfmng.deleteWorkflow(wf_id)
    # decrease number of workflows running in this server
    server = TavernaServer.query.filter_by(username='ecoto').first()
    server.count = server.count - 1
    db.session.commit()
    print ret

server = TavernaServer.query.filter_by(username='ecoto').first()
if server.count==0: # if there are no more workflows running, delete the server
    print "=== deleteTavernaServerWorkflow"
    ticket = getAuthTicket('ecoto', 'ecoto123') # get a fresh ticket, just in case the TS has been running for a long time
    ret = serverManager.deleteTavernaServerWorkflow(ticket)
    print ret
    db.session.delete(server)
    db.session.commit()
