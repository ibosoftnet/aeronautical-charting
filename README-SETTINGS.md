## Importing Symbols into QGIS

### For QGIS Desktop

* Add the directories of the symbol folders that come with the project to your computer under Settings > System > SVG Paths.
![](Images%20About%20Project/image-124.png)

### For QGIS Server

1. Create a folder with any name you prefer in a location of your choice to host the QGIS configuration file.
2. Inside this folder, create a directory named QGIS, and within it create an empty text file named QGIS3.ini.
![](Images%20About%20Project/image-123.png)
3. Using a text editor, add the server paths of the symbol folders included with the project, similar to the example below.  
```
[svg]
searchPathsForSVG=E:/qgis-projects/aeronautical-charting/Symbols/Ibosoft-Exclusive-Symbols, E:/qgis-projects/aeronautical-charting/Symbols/ICAO-Annex-4-SVG-Symbols, E:/qgis-projects/aeronautical-charting/Symbols/Other-Symbols, E:/qgis-projects/aeronautical-charting/Symbols/Annex-4-Colored/000000, E:/qgis-projects/aeronautical-charting/Symbols/Annex-4-Colored/5E5E5E, E:/qgis-projects/aeronautical-charting/Symbols/Annex-4-Colored/41DDF0
```
4. (For installations performed using the OSGeo4W Apache package according to the steps in the QGIS guide.)  
Register the configuration directory you created by adding the following line to an appropriate location in Apache httpd.conf or httpd_qgis.conf (OSGeo4W\httpd.d):  
```DefaultInitEnv QGIS_OPTIONS_PATH "YOUR PATH/qgis-config"```
5. Restart the Apache server to apply the changes.