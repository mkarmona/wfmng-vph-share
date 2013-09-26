__author__ = 'm.balasso@scsitaly.com'

import os
import time
from xmlrpclib import ServerProxy

from auth import getAuthTicket

wfmng = ServerProxy("http://localhost:5000/api")

ticket = getAuthTicket('testuser', '6w8DHF')

print "=== getWorkflowsList"
print wfmng.getWorkflowsList({}, ticket)

print "=== submitWorkflow"
abs_path = os.path.abspath(os.path.dirname(__file__))
wf_definition = open(os.path.join(abs_path, 'sample_workflow.t2flow'), 'r').read()
input_definition = open(os.path.join(abs_path, 'sample_input.xml'), 'r').read()
wf_title = 'test workflow'
ret = wfmng.submitWorkflow(wf_title, wf_definition, input_definition, ticket)
print ret

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
    print ret