<VirtualHost *:80>
    DocumentRoot <wfmng-folder>
    ServerAdmin a.saglimbeni@scsitaly.com
    ServerName <wfmng-domain>
    HostnameLookups On
    UseCanonicalName Off
    ServerSignature On
    <Directory "<wfmng-folder>">
        AllowOverride None
        Order allow,deny
        Allow from all
    </Directory>

    WSGIScriptAlias / <wfmng-folder>/wfmng.wsgi

</VirtualHost>
