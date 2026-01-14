@echo off

REM RunMe_ExtractOrganizationInformation $username $password $site $search $mode $file"

TITLE ExtractOrganizationInformation

pushd "..\scripts\"
call envTC14.bat
pushd "..\RoboTc\"

echo procedure launched on %date% %time% CET > ../log/RoboTC/semaphore_ExtractOrganizationInformation.out
echo procedure launched on %date% %time% CET > ../log/RoboTC/semaphore_%6.out

%JAVA_PATH_BIN%java.exe it.maneat.soa.ExtractOrganizationInformation.ExtractOrganizationInformation -classpath %CLASSPATH% -prop_file=%config% -u=%1 -p=%2 -search=%4 -site=%3 -mode=%5 -output=../log/RoboTC/output/%6 > ../log/RoboTC/output/%6_out.log

pushd "mail"
%XAMPP%\php -f _index.php taskID="%7" > ../log/RoboTC/message_taskID_%7.out
pushd "..\"


del ..\log\RoboTC\semaphore_ExtractOrganizationInformation.out
del ..\log\RoboTC\semaphore_%6.out
exit