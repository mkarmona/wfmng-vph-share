workflowmanager-vph-share
========================

The workflow manager application is located into the wfmng directory.


------------
Installation
------------

Python installation requirements
++++++++++++++++++++++++++++++++

    First of all you need to have python installed, please refer to the previous section.
    Using pip or easy_install install all packages into requirements.txt (with pip use the command "pip -r requirements.txt")

Local configuration
+++++++++++++++++++

    The wfmng will use a cfg file for the configuration.
    The *wfmng.cfg* file is intended to be used into a production environment, don't modify this file unless you are The President.
    To customize your local configuration create a file *local.wfmng.cfg* in the same directory, the wfmng will use that.
    The *local.wfmng.cfg* is ignored by git, it means you don't have to commit your local configuration ;-)

Database Syncronization
+++++++++++++++++++++++

    Open a unix shell and go into the wfmng directory and open a python shell.
    The wfmng uses a sqlite databse.

    Run the following ::

        >> from wfmng import db
        >> db.drop_all() # optional, use it if you want to erase a previous database
        >> db.create_all()
        >> db.session.commit()

Start and Stop the wfmng app
++++++++++++++++++++++++++++

    From the */wfmng/* directory, simply run the command ::

        python wfmng.py -p 5000

    The wfmng app will be reachable at http://locahost:5000

    To stop the service, simply kill the process.

Use the wfmng under apache
++++++++++++++++++++++++++++

    the production deployment of the wfmng should be done under apache web application.
    In the wfmng folder you can find the -sample-wfmng-vhost.com- redefine in according with your configuration the follow parameters:

        <wfmng-domain> : your wfmng domain.
        <wfmng-folder> : your wfmng folder.

    After that you can copy it in your apache site-enable folder.

