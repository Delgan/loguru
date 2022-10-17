# Loguru
Enables 'logs' to be written and available from disk and network.
It handles snarky logs, static JSON logs, and DER logs without the need to stress specific servers, thanks to the real time logifiying engine.
Logs can be formatted in a newline by following options, for example ***SNARK**, ***.***, ***.*—\-*** etc.
Preferable standard colors (red/green/yellow/blue), and levels (low/medium/high) can be added to log output by using the auto colorizer or explicitly adding the colors.

# Features
- support for snarky Unicode: *STACKFRAME,*,***SNARK*** and *EXTENDED* log types
- standard colors (red/green/yellow/blue) for logs, colors for renderer
- optional formatting formats (those used in the log tozer defaults)
- optional addon - log format icon
- optional aid to log format (eg, **convert regular **to **snark**)
- editable log types (with their edit icons), readable by everyone (ior people)
- tags for some log type, tag and color (eg, *debug**, *warning**, *info** for Server and child logs)
- keywords (kw) for log data

# Example log panel
To see a minimal sample log tozer(version 0.4.1), run
``win -tm loguru <Local Directory> /path/to/path.log``

or run from the command line
``python loguru.py logfile_name.logfile``

Up to 2 logs can be printed, so they all cross your window like so (1 re prints data, 1 irá instruir o processing)
``python loguru.py logfile1.logfile1 x-sleep sec1 command msg1 ***msg2****``

To formize logs:
``python loguru.py logfile.logfile monitor_format.on_namecol red,yellow <formattedformat(logfile.logfile,antformat(logfile.logfile,amplify))
    red_off\,green_off\,yellow_off\,blue_off\,red_off\,green_off\,yellow_off\
    red_in\,green_in\,yellow_in\,blue_in\,red_in\,green_in\,yellow_in\
    red>computer\,green>computer\,yellow>computer\todo\,yellow>todo comment\**all***/\,
antformat(logfile.logfile) red_timeout\,green_timeout\,yellow_timeout\,blue_timeout\,red_timeout\
red_in\,green_in\,yellow_in\,blue_in\,red_in\,green_in\,yellow_in\,blue_in\,red_in\
    normal_format(logfile.logfile,anti-format(logfile.logfile)) red_off\,green_off\,yellow_off\,blue_off\
    \,red timeout\,yellow timeout\,blue timeout\,red timeout\,yellow timeout\,blue timeout\
    \,red monitoring_origin,\,green monitoring_origin,\,yellow monitoring_origin,\
    blue monitoring_origin,\,red monitoring_origin,\,green monitoring_origin\
``