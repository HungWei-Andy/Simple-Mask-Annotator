# **Mask Calibration Tool**
This project is a simple tool to modify mask annotations.

### Dataset Format
The format of the dataset is as follows:
1. Images and masks are stored under **the same directory**.
2. The mask of an image **"name.jpg"** is **"name_mask.jpg"**.
3. The image extensions only support ".jpg", ".jpeg", and ".png". The mask extension only supports ".jpg".

### Requirements
1. Python3
2. Pillow
3. numpy
4. OpenCV2
5. matplotlib

```
pip install Pillow numpy opencv-python matplotlib
```

### Getting Started
- Run the python script

```
python mask_annotator.py
```

- Load a directory of images and masks.

<img src='images/1.png' width=50% height=50%>

- Click on the list to switch between images

<img src='images/2.png' width=50% height=50%>

- Left-click image to enclose a polygon. Right-click on the image to delete points. When a polygon is encolsed, the color turns from red to blue.

<img src='images/3.png' width=120% height=120%>
<img src='images/4.png' width=120% height=120%>

- When the polygon is enclosed, left-clicking the image prompts the mask inside the polygon to switch among three modes: (1) original mask (2) all 0s (3) all 1s; right-clicking the image changes the mask to the mode chosen.

<img src='images/5.png' width=100% height=100%>

- Switching into another image automatically replaces the original mask by the modified one. To save the mask manually, press "Save" button. (If the mask is modified and not saved, a "* " will be marked on the title bar)

<img src='images/6.png' width=50% height=50%>

- Press "Restore" button will restore the mask to the original one.

<img src='images/7.png' width=50% height=50%>
