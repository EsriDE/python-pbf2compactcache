# Compact Cache V2 sample code

## pbf2compactcache.py

Convert individual .pbf files to the [Esri Compact Cache V2](../CompactCacheV2.md) format bundles.  It only builds individual bundles, not a completely functional cache.

While operational, this code is only provided as an example of how a bundle file is created and updated.
This Python script takes two arguments, the input {x}/{y}/{z}.pbf folder and the output folder. It assumes that the input folder contains folders of the form: ```{x}/{y}/{z}.pbf```.

The script does not check the input tile format, and assumes that all the files under the source contain valid pbf files. 
The algorithm loops over files, inserting each tile in the appropriate bundle. It keeps one bundle open in case the next tile fits in the same bundle.  In most cases this combination results in good performance.

The [sample_pbf](../sample_pbf) folder contains example [pbfs](../sample_pbf/README.md) for the first seven levels of the Federal Agency for Cartography and Geodesy & Working Committee of the Surveying Authorities of the Laender of the Federal Republic of Germany (AdV) - Basemap.de vector cache in Web Mercator projection.  The [sample_cache](../sample_cache) folder contains a Compact Cache V2 cache produced from these individual pbfs using the pbf2compactcache.py script. The commands used to generate the bundles for each level are:

processing:
```console
python sample_code\pbf2compactcache.py -s sample_pbf -d sample_cache\p12\tile -l 7
```

## Licensing

Copyright 2025 Esri Deutschland GmbH

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

A copy of the license is available in the repository's LICENSE file.

