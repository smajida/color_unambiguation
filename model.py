__author__ = 'ohaas'

import numpy as ny
import matplotlib.pyplot as pp
import pop_code as pc
from matplotlib.mlab import bivariate_normal
from scipy.signal import convolve2d
import ConfigParser as cp
import Neurons
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
import math


def get_gauss_kernel(sigma, size, res):
    """
    return a two dimesional gausian kernel of shape (size*(1/resolution),size*(1/resolution))
    with a std deviation of std
    """
    x,y = ny.mgrid[-size/2:size/2:res,-size/2:size/2:res]
    b=bivariate_normal(x,y,sigma,sigma)
    A=(1/ny.max(b))
    #A=1
    return x,y,A*bivariate_normal(x, y, sigma, sigma)

def gauss(sigma=0.75, x=ny.arange( 0.0, 8.0, 1), mu=0):
    return ny.exp(-(x-mu)**2/(2.0*sigma**2))


class Stage(object):
    def __init__(self, Gx, C):
        self.Gx = Gx
        self.C = C

    def do_v1(self, net_in, net_fb):
        v1_t= net_in + (self.C * net_fb * net_in)
        return v1_t

    def do_v2(self, v1_t):

        x = v1_t**2

        if not len (self.Gx):
            return x

        v2_t = ny.zeros_like (v1_t)
        for n in ny.arange(0, v1_t.shape[2]):
            v2_t[:,:,n] = convolve2d (x[:,:,n], self.Gx, 'same')

        return v2_t

    def do_v3(self, v2_t):

        s=v2_t.shape
        r=ny.reshape(v2_t,(s[0]*s[1],s[2]))
        m=ny.mean(r,axis=0)
        M=ny.zeros_like(v2_t)

        for x in ny.arange(0.0,s[0]):
            for y in ny.arange(0.0,s[0]):
                if not ny.any(v2_t[x,y,:])==0:
                    M[x,y,:]=m

        N=ny.zeros_like(v2_t)
        R=2

        for x in ny.arange(0.0,s[0]):
            for y in ny.arange(0.0,s[0]):
                if x in ny.arange(R,s[0]-R) and y in ny.arange(R,s[0]-R):
                    for a in ny.arange(x-R,x+R+1):
                        for b in ny.arange(y-R,y+R+1):
                            N[x,y,:]+=v2_t[a,b,:]
                else:
                    N[x,y,:]=(((R*2)+1)**2)*v2_t[x,y,:]
                M[x,y,:]=N[x,y,:]/(((R*2)+1)**2)
        v3_t=M
        #v3_t=ny.divide(v2_t-M,0.01+N)
        return v3_t

    def do_all(self, net_in, net_fb):
        v1_t = self.do_v1(net_in, net_fb)
        v2_t = self.do_v2(v1_t)
        v3_t = self.do_v3(v2_t)
        return v3_t


class Model(object):

    def __init__(self, cfg_file, feedback=True):

        self.do_feedback = feedback

        cfg = cp.RawConfigParser()

        cfg.read(cfg_file)

        self.main_size = cfg.getint('Input', 'main_size')
        self.square_size = cfg.getint('Input', 'square_size')
        self.time_frames = cfg.getint('Input', 'time_frames')
        self.gauss_width = cfg.getfloat('PopCode', 'neuron_sigma')

        v1_C = cfg.getint('V1', 'C')
        self.mt_kernel_sigma =  cfg.getfloat('MT', 'kernel_sigma')
        self.mt_kernel_size =  cfg.getfloat('MT', 'kernel_size')
        self.mt_kernel_res =  cfg.getfloat('MT', 'kernel_res')

        self.x,self.y,self.mt_gauss = get_gauss_kernel(self.mt_kernel_sigma, self.mt_kernel_size, self.mt_kernel_res)

        self.V1 = Stage([], v1_C)
        self.MT = Stage(self.mt_gauss, 0)


    def create_input(self):
        """
        definition of initial population codes for different time steps (is always the same one!!!)
        """
        I = ny.zeros((self.main_size, self.main_size, 8, self.time_frames))
        for i in ny.arange(0, self.time_frames):
            j = pc.Population(self.main_size, self.square_size, self.gauss_width)
            I[:,:,:,i] = j.initial_pop_code()
            #j.show_vectors(I[:,:,:,i])

        return I


    def run_model_full(self):
        self.input = self.create_input()

        X = ny.zeros((self.main_size, self.main_size, 8, self.time_frames+1))
        FB=ny.zeros((self.main_size, self.main_size, 8, self.time_frames+1))
        X[:,:,:, 0] = self.input[:,:,:,0]


        for d_t in ny.arange(1, self.time_frames+1):

            inp = self.input[:,:,:,d_t-1]
            v1 = self.V1.do_all(inp, FB[:,:,:,d_t-1])
            mt = self.MT.do_all(v1, 0)
            X[:,:,:, d_t] = mt


            if self.do_feedback:
                FB[:,:,:,d_t] = X[:,:,:,d_t]


        return X,FB


    def integrated_motion_direction(self):

        X,FB = self.run_model_full ()

        for i in ny.arange(0,self.time_frames+1):

            pop = pc.Population(self.main_size, self.square_size, self.gauss_width)

            if i>0:

                pp.figure(2)
                pop.show_vectors(self.input[:,:,:,i-1])
                pp.xlabel('Pixel')
                pp.ylabel('Pixel')
                pp.title('Model input population code for spatial kernel values: %s=%.2f, size=%.2f, \n res=%.2f and neuron kernel %s=%.2f'\
                %  (u"\u03C3",self.mt_kernel_sigma, self.mt_kernel_size, self.mt_kernel_res,u"\u03C3", self.gauss_width))

                pp.figure(2+i)
                pop.show_vectors(X[:,:,:,i])
                pp.xlabel('Pixel')
                pp.ylabel('Pixel')
                pp.title('Model output population code for spatial kernel values:%s=%.2f, size=%.2f, \n res=%.2f and neuron kernel %s=%.2f after %i model iterations'\
                % (u"\u03C3",self.mt_kernel_sigma, self.mt_kernel_size, self.mt_kernel_res,u"\u03C3", self.gauss_width, i) )

                pp.figure(1)
                pop.plot_pop(X[:,:,:,i],self.time_frames,i)

            else:
                pp.figure(1)
                pop.plot_pop(X[:,:,:,i],self.time_frames,i)

                pp.figure(2)
                pop.show_vectors(self.input[:,:,:,i])
                pp.xlabel('Pixel')
                pp.ylabel('Pixel')
                pp.title('Model input population code for spatial kernel values:\n %s=%.2f, size=%.2f, res=%.2f and neuron kernel %s=%.2f'\
                % (u"\u03C3",self.mt_kernel_sigma, self.mt_kernel_size, self.mt_kernel_res,u"\u03C3", self.gauss_width) )


            print i


if __name__ == '__main__':

    M = Model('model.cfg') # feedback=True
    #M.show_mt_gauss()
    M.integrated_motion_direction()

    #M.run_model_full()
    pp.show()

