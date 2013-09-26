.. Vphop Hypermodel Workflow Manager documentation master file, created by
   sphinx-quickstart on Tue Jan 17 10:09:16 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Vphop Hypermodel Workflow Manager's documentation!
*************************************************************

.. toctree::
   :maxdepth: 3

.. automodule:: __init__

Workflow Manager
================

.. automodule:: wfmng

Database Models
---------------
This section contains the database models based on **Flask-SQLAlchemy Extension**.

.. autoclass:: wfmng.Workflow

    .. automethod:: Workflow.toDictionary
    .. automethod:: Workflow.update

.. autoclass:: wfmng.Log

.. autoclass:: wfmng.Session

Login Manager
--------------
This section contains the user class used by **Flask-Login Extension**.

.. autoclass:: wfmng.User

    .. automethod:: User.is_authenticated
    .. automethod:: User.is_active
    .. automethod:: User.is_anonymous
    .. automethod:: User.get_id

Html Methods
------------
This section contains the HTML routed methods

.. autofunction:: wfmng.setWorkflowReadyToStart

XMLRPC Methods
--------------
This section contains all the XMLRPC protocol based methods.

Authentication
++++++++++++++
Authentication related xmlrpc methods.

.. autofunction:: wfmng.login
.. autofunction:: wfmng.extractUsername

Workflows
+++++++++
Workflows related xmlrpc methods.

.. autofunction:: wfmng.submitWorkflow
.. autofunction:: wfmng.submitBuiltinWorkflow
.. autofunction:: wfmng.getWorkflowsList
.. autofunction:: wfmng.getWorkflowInformation
.. autofunction:: wfmng.startWorkflow
.. autofunction:: wfmng.deleteWorkflow
.. autofunction:: wfmng.stopWorkflow

Log
++++
Log related xmlrpc methods.

.. autofunction:: wfmng.getLog
.. autofunction:: wfmng.putLog

Services
++++++++
Services related xmlrpc methods.

.. autofunction:: wfmng.getDependenceServices
.. autofunction:: wfmng.getServicesList
.. autofunction:: wfmng.getServiceInformation

OpenClinica Subjects
++++++++++++++++++++
OpenClinica Subjects related xmlrpc methods.

.. autofunction:: wfmng.getOpenClinicaSubjectsList
.. autofunction:: wfmng.getOpenClinicaSubjectRiskInfo

Management
++++++++++
Management related xmlrpc methods.

.. autofunction:: wfmng.updateAllWorkflows

Authentication
==============
.. automodule:: auth

.. autofunction:: auth.checkAuthentication
.. autofunction:: auth.requiresAuthentication
.. autofunction:: auth.getAuthTicket
.. autofunction:: auth.extractUsernameFromTicket

Connectors
==========
The workflow manager instantiated a connector for every hypermodel module it needs to contact.

TavernaServerConnector
--------------------------
.. automodule:: taverna

    .. autoclass:: taverna.TavernaServerConnector

OpenClinicaConnector
--------------------
.. automodule:: openclinica

    .. autoclass:: openclinica.OpenClinicaConnector

LogManager Connector
--------------------
.. automodule:: log

    .. autoclass:: log.LogManagerConnector

Registry Service Connector
--------------------------
.. automodule:: registry

    .. autoclass:: registry.RegistryServiceConnector

Storage Service Connector
-------------------------
.. automodule:: storage

    .. autoclass:: storage.PhysiomeSpaceConnector

