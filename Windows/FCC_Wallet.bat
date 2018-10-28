if exist installed.fcc goto :installed
echo Installing FCC..
echo.
call FCC_Install.bat 1
:installed
cd wallet
perl wallet.cgi
cd ..
