@echo off
WHERE perl.exe
IF %ERRORLEVEL% EQU 0 ( goto :installed )
echo Please install Perl first
goto :end
:installed
echo Installing dependencies for Perl ..
cmd /R "cpan install Time::HiRes JSON Crypt::Ed25519 URL::Encode Browser::Open Gzip::Faster Digest::SHA1"
cd install
cmd /R "perl install.cgi"
cd ..
echo.
echo.
echo FCC is succesfully installed.
echo Doubleclick 'FCC_Wallet' to create your first wallet.
echo 1 > installed.fcc
:end
if %1 == 1 goto :theend
echo.
set /p DUMMY=Hit ENTER to continue...
:theend
