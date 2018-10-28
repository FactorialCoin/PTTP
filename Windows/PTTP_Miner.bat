if exist installed.pttp goto :installed
echo Installing PTTP..
echo.
call PTTP_Install.bat 1
:installed
cd miner
perl pttpminer.cgi
cd ..
