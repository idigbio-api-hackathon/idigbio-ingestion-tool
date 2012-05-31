#!/bin/bash
# Given base.png and base32.png, makes the various sizes of icons needed for
# OS X and Windows, and puts them into .icns and .ico files, respectively.
# To run this script, make sure you have png2icns (icnsutils) and imagemagick
# installed. On Debian, that means you should run:
#     sudo aptitude install icnsutils imagemagick

echo "Setting Up"
rm -rf osx_icon win_icon
mkdir -p osx_icon win_icon

echo "Rescaling OS X Icons"
convert base.png -resize 512x512 osx_icon/icn512.png
convert base.png -resize 256x256 osx_icon/icn256.png
convert base.png -resize 128x128 osx_icon/icn128.png
convert base.png -resize 48x48 osx_icon/icn48.png
convert base32.png -resize 32x32 osx_icon/icn32.png
convert base32.png -resize 16x16 osx_icon/icn16.png

echo "Building OS X .icns File"
png2icns osx_icon/icon.icns osx_icon/*.png > /dev/null # quiet, you!


echo "Rescaling Windows Icons"
convert base.png -resize 256x256 win_icon/icn256.bmp
convert base.png -resize 48x48 win_icon/icn48.bmp
convert base32.png -resize 32x32 win_icon/icn32.bmp
convert base32.png -resize 16x16 win_icon/icn16.bmp

echo "Building Windows .ico File"
convert win_icon/*.bmp win_icon/icon.ico


echo "Cleaning Up"
rm osx_icon/*.png win_icon/*.bmp
