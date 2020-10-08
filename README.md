# YaBCSOrganizer
This tool helps with editing BCS files for Xenoverse 2, which are responsible for various actions in a moveset and skill, such as animations, hitboxes, effects, sound, and more. 

This is not a guide on what each entry means.  This is just a tool to make editing them easier.  For a more comprehensive guide to that, please refer to the [BCS Manual](https://docs.google.com/document/d/1df8_Zs3g0YindDNees_CSrWVpMBtwWGrFf2FE8JruUk)

Features include:
* Copying/Pasting/Adding/Deleting entries
* Find/Replace entries by value
* Shared clipboard between different instances of the BCS organizer
* Generate XML for copying into the XV2 Costume Creator

# Credits
* Eternity - Genser source code helped with the nitty gritty technical bits of the BAC file structure.
* Atsuraelu for the BCS manual

# Changelog
```
0.1.0 - Initial Release
0.1.1 - Now can load BCS files with invalid headers, fixed XML generation mislabeling Physics files as FILES instead of STR_28
0.1.2 - Fixed part hiding to also allow unknown values, added find/replace for EMB file names
0.1.3 - Add automatic backup creation on saving
0.1.4 - Fixed bug saving BCS files with no skeleton data
0.1.5 - Fixed bug when adding single Physics/Color Selectors.  Fixed bug adding new body parts.
0.1.6 - Now supports unicode characters in names
```

