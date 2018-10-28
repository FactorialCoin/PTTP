if exist installed.pttp goto :installed
echo Installing PTTP..
echo.
call PTTP_Install.bat 1
:installed
cd node
perl startnode.cgi
cd ..
