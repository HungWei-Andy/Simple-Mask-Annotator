import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np
import imghdr
import os
import os.path as osp
import cv2
from matplotlib.path import Path

class MaskProcessor(object):
    def __init__(self):
        self.prepare_func_dicts()
        self.reset()

    def prepare_func_dicts(self):
        self.click_left_funcs = {}
        self.click_left_funcs['point'] = self.put_point
        self.click_left_funcs['contour'] = self.flip_contour
        self.click_right_funcs = {}
        self.click_right_funcs['point'] = self.undo_point
        self.click_right_funcs['contour'] = self.change_contour

    def reset(self):
        self.image = None
        self.mask = None
        self.new_mask = None
        self.is_changed = False
        self.points = []
        self.state = 'point'
        self.contour_type = 'ori'
        self.color = (0, 0, 255)

    def load(self, image_path, mask_path):
        self.reset()
        self.image = cv2.imread(image_path)[:, :, :3]
        self.mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE) / 255.0
        self.new_mask = self.mask.copy()
        self.calc_params()

    def calc_params(self):
        circle_rad = int(min(self.image.shape[:2]) * 0.007)
        circle_rad = max(circle_rad, 3)
        self.circle_rad = circle_rad
        line_thick = int(circle_rad * 0.3)
        line_thick = max(line_thick, 1)
        self.line_thick = line_thick
        self.search_rad = self.circle_rad * 3

    def calc_contour(self):
        xs = [pt[0] for pt in self.points]
        ys = [pt[1] for pt in self.points]
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

        contour_mask = np.zeros((ymax-ymin+1, xmax-xmin+1, 3))
        contour_points = np.array([(x-xmin, y-ymin) for x, y in self.points])
        cv2.fillPoly(contour_mask, pts=[contour_points], color=(255, 255, 255))
        contour_mask = contour_mask[:, :, 0] * 1.0 / 255.0
        self.contour_mask = contour_mask
        print('complete find points inside')

    def put_point(self, x, y):
        print('put into array %d, %d'%(x, y))
        if len(self.points) >= 3:
            dist = np.sqrt((x-self.points[0][0])**2 + (y-self.points[0][1])**2)
            if dist <= self.search_rad:
                self.points.append((x, y))
                self.calc_contour()
                self.contour_type = 'ori'
                self.state = 'contour'
                self.color = (255, 0, 0)
                return
        self.points.append((x, y))
        
    def undo_point(self, x, y):
        if len(self.points) > 0:
            del self.points[-1]

    def flip_contour(self, x, y):
        if self.contour_type == 'ori':
            self.contour_type = 'black'
        elif self.contour_type == 'black':
            self.contour_type = 'white'
        elif self.contour_type == 'white':
            self.contour_type = 'ori'

        xmin, xmax, ymin, ymax = self.xmin, self.xmax, self.ymin, self.ymax
        if self.contour_type == 'ori':
            self.new_mask[ymin:ymax+1, xmin:xmax+1] = self.mask[ymin:ymax+1, xmin:xmax+1]
        elif self.contour_type == 'black':
            self.new_mask[ymin:ymax+1, xmin:xmax+1] *= (1.0 - self.contour_mask)
        elif self.contour_type == 'white':
            self.new_mask[ymin:ymax+1, xmin:xmax+1] *= (1.0 - self.contour_mask)
            self.new_mask[ymin:ymax+1, xmin:xmax+1] += self.contour_mask


    def change_contour(self, x, y):
        if self.contour_type != 'ori':
            self.is_changed = True
        self.points = []
        self.state = 'point'
        self.contour_type = 'ori'
        self.color = (0, 0, 255)

    def replace(self):
        self.mask = self.new_mask.copy()
        self.is_changed = False

    def restore(self):
        self.new_mask = self.mask.copy()    
        self.is_changed = False

    def click_left(self, x, y):
        self.click_left_funcs[self.state](x, y)

    def click_right(self, x, y):
        self.click_right_funcs[self.state](x, y)

    def click_mid(self, x, y):
        pass


    @property 
    def size(self):
        return (self.image.shape[1], self.image.shape[0])

    @property
    def image_shown(self):
        mask_prod = np.expand_dims(np.minimum(1.0, self.new_mask + 0.3), axis=-1)
        res = self.image.copy() * mask_prod
        for pt in self.points:
            cv2.circle(res, pt, self.circle_rad, self.color, -1)
        for pt_idx in range(1, len(self.points)):
            cv2.line(res, self.points[pt_idx-1], self.points[pt_idx], self.color, self.line_thick)
        return Image.fromarray(res[:, :, ::-1].round().astype(np.uint8))
    
class Controller(object):
    def __init__(self, app):
        self.exts = ('.jpg', 'png', 'jpeg')
        self.mask_processor = MaskProcessor()
        self.app = app
        self.reset()

    def reset(self):
        self.images = []
        self.masks = []
        self.image_index = -1
        self.change_title('Mask Annotator')


    @property
    def num_images(self):
        return len(self.images)

    def load_images(self, image_dir):
        self.reset()
        for root, dirs, files in os.walk(image_dir):
            for f in files:
                path = osp.join(root, f)
                if path.lower().endswith(self.exts) and '_mask' not in path:
                    base, ext = osp.splitext(path)
                    mask_path = base + '_mask.jpg'
                    if osp.exists(mask_path):
                        self.images.append(path)
                        self.masks.append(mask_path)
        self.app.update_list(self.images)
        self.app.clear_canvas()
        self.change_title('Mask Annotator')

    def double2im(self, arr):
        return (arr * 255.0).round().astype(np.uint8)

    def save_image(self):
        if self.image_index >= 0:
            self.mask_processor.replace()
            cv2.imwrite(self.masks[self.image_index], self.double2im(self.mask_processor.mask))
            self.change_title(self.images[self.image_index])


    def change_title(self, name=None):
        if name is not None:
            self.title = name
        self.app.winfo_toplevel().title(self.title)

    def calc_scale(self, orisize, newsize):
        w, h = orisize
        self.scale = min(1.*newsize[0]/w, 1.*newsize[1]/h)
        neww, newh = int(w*self.scale), int(h*self.scale)
        self.delta = ((newsize[0]-neww)//2, (newsize[1]-newh)//2)

    def canvas_coord_to_image_coord(self, x, y):
        return int((x-self.delta[0])/self.scale), int((y-self.delta[1])/self.scale)

    def select(self, index):
        # save image before switch to next image
        if self.image_index >= 0 and self.mask_processor.is_changed:
            self.save_image()
        self.image_index = index
        self.change_title(self.images[index])
        self.mask_processor.load(self.images[index], self.masks[index])
        self.calc_scale(self.mask_processor.size, self.app.img_canvas_size)
        self.app.update_canvas(self.mask_processor.image_shown, scale=self.scale)
        print('select index %d, image %s'%(index, self.images[index]))

    def restore_mask(self):
        if self.image_index >= 0:
            self.mask_processor.restore()
            self.app.update_canvas(self.mask_processor.image_shown, scale=self.scale)
            self.change_title(self.images[self.image_index])
        print('restore mask')

    def click_left(self, x, y):
        if self.image_index >= 0:
            imgx, imgy = self.canvas_coord_to_image_coord(x, y)
            self.mask_processor.click_left(imgx, imgy)
            self.app.update_canvas(self.mask_processor.image_shown, scale=self.scale)
        print('click left at (%d, %d)'%(x, y))

    def click_right(self, x, y):
        if self.image_index >= 0:
            imgx, imgy = self.canvas_coord_to_image_coord(x, y)
            self.mask_processor.click_right(imgx, imgy)
            self.app.update_canvas(self.mask_processor.image_shown, scale=self.scale)
            if not self.title.endswith('* ') and self.mask_processor.is_changed is True:
                self.change_title('* '+self.images[self.image_index])
        print('click right at (%d, %d)'%(x, y))

    def click_mid(self, x, y):
        if self.image_index >= 0:
            imgx, imgy = self.canvas_coord_to_image_coord(x, y)
            self.mask_processor.click_mid(imgx, imgy)
        print('click mid at (%d, %d)'%(x, y))

class Application(tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        tk.Frame.__init__(self, master)
        self.master = master
        
        self.prepare_events()
        self.prepare_widgets()
        self.prepare_controller()
        self.bind_top_events()
        self.reset()

    def prepare_events(self):
        self.events = {}
        self.events['canvas_left_mouse_down'] = self.on_click_left
        self.events['canvas_right_mouse_down'] = self.on_click_right
        self.events['canvas_mid_mouse_down'] = self.on_click_mid
        self.events['listbox_selection'] = self.on_select_image
        self.events['load'] = self.on_load
        self.events['save'] = self.on_save
        self.events['restore'] = self.on_restore

    def prepare_widgets(self):
        self.grid(row=0, column=0)

        # create image canvas
        self.img_canvas_size = (550, 850)
        self.imgCanvas = tk.Canvas(self, bg='black', height=self.img_canvas_size[1], width=self.img_canvas_size[0])
        self.imgCanvas.bind('<Button-1>', self.events['canvas_left_mouse_down'])
        self.imgCanvas.bind('<Button-2>', self.events['canvas_mid_mouse_down'])
        self.imgCanvas.bind('<Button-3>', self.events['canvas_right_mouse_down'])
        self.imgCanvas.grid(row=1, column=0, rowspan=1, columnspan=2)
        self.image_shown = None

        # create image list
        self.imgs_listbox_size = (40, 47)
        self.imgsListbox = tk.Listbox(self, height=self.imgs_listbox_size[1], width=self.imgs_listbox_size[0])
        self.imgsListbox.bind('<<ListboxSelect>>', self.events['listbox_selection'])
        self.imgsListbox.grid(row=1, column=2, columnspan=2, sticky='WN')

        # create load button
        self.loadButton = tk.Button(self)
        self.loadButton['text'] = 'Load'
        self.loadButton['command'] = self.events['load']
        self.loadButton.grid(row=0, column=2)

        # create save button
        self.saveButton = tk.Button(self)
        self.saveButton['text'] = 'Save'
        self.saveButton['command'] = self.events['save']
        self.saveButton.grid(row=0, column=3)

        # create restore button 
        self.restoreButton = tk.Button(self)
        self.restoreButton['text'] = 'Restore'
        self.restoreButton['command'] = self.events['restore']
        self.restoreButton.grid(row=0, column=0)

    def prepare_controller(self):
        self.controller = Controller(self)

    def bind_top_events(self):
        pass

    def reset(self):
        self.controller.reset()



    def on_click_left(self, event):
        self.controller.click_left(event.x, event.y)

    def on_click_mid(self, event):
        self.controller.click_mid(event.x, event.y)

    def on_click_right(self, event):
        self.controller.click_right(event.x, event.y)

    def on_select_image(self, event):
        widget = event.widget
        index = widget.curselection()[0]
        self.controller.select(index)

    def on_load(self):
        image_dir = filedialog.askdirectory(initialdir='.')
        if image_dir is not None:
            self.controller.load_images(image_dir)
        
    def on_save(self):
        self.controller.save_image()

    def on_restore(self):
        self.controller.restore_mask()



    def clear_list(self):
        self.imgsListbox.delete(0, tk.END)

    def clear_canvas(self):
        if self.image_shown is not None:
            self.imgCanvas.delete(self.image_shown)
            self.image_shown = None

    def update_list(self, images):
        self.clear_list()    
        for im in images:
            self.imgsListbox.insert(tk.END, '%s (%s)'%(osp.basename(im), osp.dirname(im)))

    def update_canvas(self, image, scale = None):
        # resize image
        w, h = image.size
        scale = min(1.*self.img_canvas_size[0]/w, 1.*self.img_canvas_size[1]/h)
        neww, newh = int(w*scale), int(h*scale)
        image = image.resize((neww, newh))

        # clear image
        self.clear_canvas()

        # paste image
        self.image_tk = ImageTk.PhotoImage(image) # remember to save the Image Tk as an attribute; otherwise, the image will not be shown
        delta_w, delta_h = (self.img_canvas_size[0]-neww)//2, (self.img_canvas_size[1]-newh)//2
        self.image_shown = self.imgCanvas.create_image(delta_w, delta_h, anchor=tk.NW, image=self.image_tk)

if __name__ == '__main__':
    root = tk.Tk()
    app = Application(root)
    app.mainloop()