<p align="middle">
    <a href="README.md">繁體中文</a> |
    <a href="README.en.md">English</a>
</p>

# Epic Seven 5 Speed Maker

## Introduction

(translated by ChatGpt 5.5. The author is too lazy to make a English version on his own.)

This is a small tool for **Epic Seven**.

In case you do not know, **Astral Forge** can produce gear with **5 Speed**. However, the chance of getting Speed is only **0.332%**. For necklaces and rings, this means you need to refresh around **750 times on average**. Each attempt takes a lot of time and effort, and sometimes you may even miss a 5-Speed result when you lose focus! This is much worse than bookmarks.

This tool was made to solve that problem.

The GUI of this tool is built with **customtkinter**.

It connects to **BlueStacks** through **ADB** and can run in the background.

According to tests done by the author and friends, there have been no false detections so far. However, this does not guarantee that the tool will never miss a 5-Speed result on your setup. If you are concerned, you can modify the detection logic in the code yourself to reduce the possibility of this happening. In theory, the chance should be very low.

---

## Environment

* Windows 11
* BlueStacks

  * Version: Should not matter
  * Resolution: 1920 x 1080
    If your resolution is different, you can update the images yourself. This will be explained later.
* Epic Seven

  * I only enabled `High Quality Media Pack`
    I am not sure whether this option still exists now.
* Python 3.12.13
* config.json

  * You do not need to edit it manually. The real file is inside the `_internals` folder.
  * All settings can be changed through the program. You do not need to edit the JSON file yourself.
  * Except for points, all settings will be preserved the next time you open the program.

---

## How to Use

### Launching the Program

First, download the program by using one of the following methods:

* `git clone`
* Download ZIP
* Download `E7 5 speed maker.zip`

Extract `E7 5 speed maker.zip`, open the `E7 5 speed maker` folder, then double-click `5 speed maker.exe` to launch the program.

![app](assets/app.png)

### Language and Theme

You can use the dropdown menu in the upper-left corner to change the language. Traditional Chinese and English are supported, and the selected language should match the language shown in the game screen.

You can use the switch in the upper-right corner to change the theme color. Light mode and dark mode are supported.

### Addr

After opening the program, first check whether the IP address in `addr` is correct. You can find it in BlueStacks under:

**Settings > Advanced**

#### Remember to enable ADB in BlueStacks.

### Points

Enter your current points into the input box.

### Start

Click the start button. The program will begin detecting and automatically refreshing.

### Stop

Click the stop button. The program will perform one final refresh before stopping. It will not stop immediately.

---

## Modifying the Program

This program detects 5 Speed by using OpenCV’s `matchTemplate` and checking the highest confidence value.

By default, the tool treats the result as found when the confidence is above `90%`.

If you are worried that this threshold is too high, you can lower it to `0.85` or `0.8`.

If the threshold is too low, the program may stop frequently. It is recommended not to go below `0.8`. You can observe the highest confidence values printed in the message box and adjust the threshold based on that.

Open `main.py` with Notepad, any text editor, or an IDE, then modify `line:340`.

After modifying it, run the command in `pack_script.txt` to repackage the program, or simply launch the program with `main.py` from then on.

![code](assets/code_5speed.png)

The matching method used is `cv2.TM_CCOEFF_NORMED`.

You can try other methods, but there is no guarantee that they will work better. This method was chosen after some very simple testing and comparison.

---

## Updating Images

Since the game UI may change from time to time, this program includes built-in screenshot and image-updating features. This saves you the trouble of manually taking screenshots, moving files into folders, renaming them, and so on.

![update](assets/update_TW.png)

After entering this page, you will see a screenshot of BlueStacks.

![update\_show](assets/update_show.png)

You can click and hold on the screen, then release to draw a rectangle.

You can:

* Resize the rectangle by dragging the 8 points around the selection box
* Use the mouse wheel to zoom in or out
* When zoomed in, left-click and drag on an empty area to move the whole view
* When zoomed in, left-click and drag the selection box to move it
* When zoomed in, middle-click and drag to move the whole view
* Click the clear button in the upper-right corner to reset the selection box
* Click the dropdown menu in the upper-left corner to change the image
  However, this tool only uses one image that may be affected by UI changes.
* Click the save button in the upper-right corner. The program will save the image based on the language you selected at the beginning.

### BlueStacks Resolution

If the issue is caused by using a resolution different from the default resolution of this tool, it is recommended that you change your BlueStacks resolution.

If you insist on using your original resolution, you can try updating the image through this feature. However, there is no guarantee that 5-Speed detection will not be affected. Please use it at your own risk. I have not tested this.

---

## Refresh Count

By default, the program assumes that no properties are locked. Also, under normal circumstances, you should not lock any property if you are trying to get 5 Speed.

Therefore, the program always treats each refresh as costing 20 points.

The program does not have a maximum refresh count setting, except when your points run out. I personally do not need this feature, and I got lazy. If you need it, you can add it yourself or fork the project.

---

## Notes

Once again, **image-matching-based techniques may always produce errors to some extent. Users should understand the risks before using this tool.**
