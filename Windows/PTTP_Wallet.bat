if exist installed.pttp goto :installed
echo Installing PTTP..
echo.
call PTTP_Install.bat 1
:installed
cd wallet
perl wallet.cgi
cd ..
