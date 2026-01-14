set PROJECT=%~dp0
pushd "..\"
set INSTANCE=%cd%\
pushd ".\scripts\"
set CLASSPATH=%PROJECT%SOA\lib\*;
set CONFIG=%PROJECT%SOA\config\config.properties
set LOGPATH=%INSTANCE%log\
rem set UGS_LICENSE_SERVER=28000@lmtcae04.iveco.com,28000@lmtcae05.iveco.com,28000@lmtcae06.iveco.com;28000@lmtcae07.iveco.com