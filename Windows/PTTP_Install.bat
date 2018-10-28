@echo off
WHERE perl.exe
IF %ERRORLEVEL% EQU 0 ( goto :installed )
echo Please install Perl first
goto :end
:installed
echo Installing dependencies for Perl ..
cmd /R "cpan install Time::HiRes JSON Crypt::Ed25519 URL::Encode Browser::Open Gzip::Faster Digest::SHA"
cd install
cmd /R "perl install.cgi"
cd ..
echo.
echo.
echo PTTP is succesfully installed.
echo Doubleclick 'PTTP_Wallet' to create your first wallet.
echo 1 > installed.pttp
:end
if %1 == 1 goto :theend
echo.
set /p DUMMY=Hit ENTER to continue...
:theend