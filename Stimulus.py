__author__ = 'ohaas'

import Image, ImageDraw
import matplotlib.pyplot as pp
from matplotlib.patches import FancyBboxPatch as fbp
import numpy as ny


class image(object):

    def __init__(self,main_size,square_size):
        self.main_size=main_size
        self.square_size=square_size
        self.i=Image.new("RGB",(self.main_size,self.main_size),color=(255,255,255))

    def pic(self, angle_outside=135 , angle_inside=180):
        C = ny.genfromtxt("Colormatrix.txt")
        t_out=ny.round((angle_outside*(2*ny.pi/360))/(1/60.0)).astype(int)
        t_in=ny.round((angle_inside*(2*ny.pi/360))/(1/60.0)).astype(int)
        (r_out, g_out, b_out)=C[t_out,:]
        (r_in, g_in, b_in)=C[t_in,:]
        i=Image.new("RGB",(self.main_size+1,self.main_size+1),color=(ny.round(r_out*255).astype(int),ny.round(g_out*255).astype(int),ny.round(b_out*255).astype(int)))
        draw = ImageDraw.Draw(i)
        draw.rectangle([(((self.main_size/2)-(self.square_size/2)), (self.main_size/2)-(self.square_size/2)),
            ((self.main_size/2)+(self.square_size/2), (self.main_size/2)+(self.square_size/2))],fill=(ny.round(r_in*255).astype(int),ny.round(g_in*255).astype(int),ny.round(b_in*255).astype(int)))
        pp.imshow(i, interpolation="nearest", origin = 'lower')
        pp.xlabel('pixel')
        pp.ylabel('pixel')


    def pix_wise(self, x, y, angle):
        C = ny.genfromtxt("Colormatrix.txt")
        t=ny.round((angle*(2*ny.pi/360))/(1/60.0)).astype(int)
        #im = self.i
        im =Image.open("Stimulus.png")
        pix = im.load()
        pix[x,y]=tuple(ny.round(255*C[t, :]).astype(int))
        im.save("Stimulus.png")
        pp.imshow(im, interpolation="nearest")
        pp.ylim(0, 29)




if __name__ == '__main__':
    I=image(30,10)
    I.pic(135,90)
    #I.pix_wise(29,29,135)
    pp.show()
    # 0.32243642,  0.67756358,  0.85197259  in: 0.25000442,  0.74999558,  0.49702585
