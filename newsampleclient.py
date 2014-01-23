__author__ = 'm.balasso@scsitaly.com'
import time
import os
from wfmng import *
from auth import getAuthTicket
import random
user = ''
passwd = ''
# taverna 2.5.1 52d4130086648827c1000ad3
#taverna secured 2.4.1 528a3b948664880b2b00f0cf
#tavernaServerCloudId = "528a3b948664880b2b00f0cf"
tavernaServerCloudId = "40"

ticket = getAuthTicket( user, passwd )

print "=== createTavernaServerWorkflow"
eid = random.randint(90000, 100000)
abs_path = os.path.abspath(os.path.dirname(__file__))
wf_definition = open(os.path.join(abs_path, 'SimpleWorkflow.t2flow'), 'r').read()
input_definition = open(os.path.join(abs_path, 'SimpleWorkflowInputs.xml'), 'r').read()
ret = execute_workflow(ticket, eid, "Execution Test %s" % str(eid), tavernaServerCloudId, wf_definition, input_definition)
if ret=="False":
    print "=== some errors occurs"

info = getWorkflowInformation(eid, ticket)
print info
while info and info['status'] != 'Finished' and info['error'] != True:
    print "=== sleeping for 5..."
    time.sleep(5)
    print "=== getWorkflowInformation"
    info = getWorkflowInformation(eid, ticket)
    print info
deleteExecution(eid, ticket)
print "=== Workflow execution deleted from WM"