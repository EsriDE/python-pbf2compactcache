# Sample Cache to Vector Tile Package (vtpk)
To convert the compact cache to a working vtpk the folders
    - esriinfo
    - p12
need to be zipped using e.g. 7zip with a compression of 0 and a file suffix of .vtpk. The resulting file can be viewed in ArcGIS Pro
and published to AGE or AGOL. A sample can be found inside ```sample_vtpk.zip```.

If your input data differs from the sample data then you may have to adjust the files inside the folder ```p12```. Important files are the ```root.json``` and the resources folder which contains the fonts, sprites and styles.