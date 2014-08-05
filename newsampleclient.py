__author__ = 'm.balasso@scsitaly.com'
import time
import os
from wfmng import *
from auth import getAuthTicket
import random
user = 'asagli'
passwd = 'selvagg.86'

tavernaServerCloudId = "404"

ticket = getAuthTicket( user, passwd )

print "=== createTavernaServerWorkflow"
eid = random.randint(90000, 100000)
abs_path = os.path.abspath(os.path.dirname(__file__))
wf_definition = open(os.path.join(abs_path, 'SimpleWorkflow.t2flow'), 'r').read()
input_definition = open(os.path.join(abs_path, 'SimpleWorkflowInputs.xml'), 'r').read()
workflow_worker_built_failed = True
#while workflow_worker_built_failed:
ret = execute_workflow(ticket, eid, "Execution Test %s" % str(eid), tavernaServerCloudId, wf_definition, input_definition, submitionWorkAround=True)
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
#workflow_worker_built_failed = (info['error'] == True) and (info['error_msg']=="Submitting workflow failed failed to build workflow run worker")
#if workflow_worker_built_failed:
#    print "===  Failed to build workflow run worker, retrying ..."
#    ticket = getAuthTicket( user, passwd ) # renew ticket before retrying