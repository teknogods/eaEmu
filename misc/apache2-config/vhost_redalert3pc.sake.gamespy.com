<VirtualHost *:80>
	ServerName redalert3pc.sake.gamespy.com
        RewriteEngine On
        RewriteRule /(.*) http://localhost:8001/$1 [P]
</VirtualHost>
