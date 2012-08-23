__author__ = 'ohaas'

import numpy as ny
import matplotlib
import matplotlib.pyplot as pp
import model
from scipy.signal import convolve2d
import pop_code as pc
import ConfigParser as cp
import math
from matplotlib.mlab import bivariate_normal

def get_gauss_kernel(sigma, samples):
    """
    return a two dimesional gausian kernel of shape (size*(1/resolution),size*(1/resolution))
    with a std deviation of std
    """
    p = ny.ceil (2*ny.sqrt(2*ny.log(2))*sigma)
    r = ny.linspace(-p, p, samples)
    x,y = ny.meshgrid(r, r)
    b=bivariate_normal(x,y,sigma,sigma)
    A=(1/ny.sum(b))
    B=A*b
    return x,y,B

class Mexican_hat(object):
    def __init__(self, cfg_file):

        cfg = cp.RawConfigParser()

        cfg.read(cfg_file)

        self.main_size = cfg.getint('Input', 'main_size')
        self.square_size = cfg.getint('Input', 'square_size')
        self.time_frames = cfg.getint('Input', 'time_frames')
        self.angle_outside = cfg.getint('Input', 'angle_outside')
        self.angle_inside = cfg.getint('Input', 'angle_inside')
        self.gauss_width = cfg.getfloat('PopCode', 'neuron_sigma')
        self.N_number=cfg.getint('PopCode','number_of_neurons')
        N_angle=ny.zeros(self.N_number)
        for i in ny.arange(len(N_angle)):
            N_angle[i]=cfg.getfloat('PopCode','neuronal_tuning_angle_%i' %i)
        angle_num=ny.arange(0,self.N_number)
        self.N_angles=[N_angle[num] for num in angle_num]
        self.mt_kernel_sigma =  cfg.getfloat('MT', 'kernel_sigma')
        self.kernel_sigma1 =  cfg.getfloat('MT', 'kernel_sigma1')
        self.kernel_sigma2 =  cfg.getfloat('MT', 'kernel_sigma2')
        self.kernel_samples =  cfg.getfloat('MT', 'kernel_samples')
        self.kernel2_sigma1 =  cfg.getfloat('MT', 'kernel2_sigma1')
        self.kernel2_sigma2 =  cfg.getfloat('MT', 'kernel2_sigma2')
        self.kernel2_samples =  cfg.getfloat('MT', 'kernel2_samples')
        self.kernel_scale =  cfg.getfloat('MT', 'kernel_scale')
#        self.vec = ny.matrix(((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)))
        angle=self.N_angles
        #angle = ny.arange(0.0, 360, 360.0/self.N_number)
        self.vec = ny.matrix([[ny.cos(fi*(ny.pi/180)), ny.sin(fi*(ny.pi/180))] for fi in angle])
        self.x,self.y,self.mt_gauss = get_gauss_kernel(self.mt_kernel_sigma, self.kernel_samples)


    def get_dog_kernel(self, sigma1, sigma2, samples):

        # return a 2d DoG Kernel

        x1,y1,DoG1 = model.get_gauss_kernel(sigma1, samples)
        x2,y2,DoG2 = model.get_gauss_kernel(sigma2, samples)
        A=10
        DoG=A*(DoG1 - (self.kernel_scale*DoG2))
#        pp.figure(1)
#        pp.plot(DoG)
#        pp.figure(2)
#        pp.imshow(DoG)
#        pp.colorbar()
#        pp.show()
        return DoG

    def create_input(self, angle_outside, angle_inside):
        """
        definition of initial population codes for different time steps (is always the same one!!!)
        """
        j = pc.Population(self.main_size, self.square_size, self.gauss_width, self.N_number, self.N_angles, angle_outside, angle_inside)
        I= j.initial_pop_code()
        return I

    def do_v1(self, net_in, net_fb):
        v1_t= net_in + (1*net_fb * net_in)

        #v1_t /= ny.max(ny.absolute(v1_t))
        return v1_t

    def do_v2(self, v1_t, Gx, iteration):

        x = v1_t#**2
        v2_t = ny.zeros_like(v1_t)
        y = ny.zeros_like(v1_t)

        if not len (Gx):
            for n in ny.arange(0, v1_t.shape[2]):
                #y[:,:,n]= x[:,:,n]
                y[:,:,n]= convolve2d (x[:,:,n], self.get_dog_kernel(self.kernel_sigma1, self.kernel_sigma2, self.kernel_samples), 'same',boundary='symm')
            return y

        #for a in ny.arange(0,self.main_size):
         #   v2_t[a,:,:] = convolve2d (x[a,:,:], self.get_dog_kernel(), 'same',boundary='symm')
        #for b in ny.arange(0,self.main_size):
         #   v2_t[:,b,:] = convolve2d (x[:,b,:], Gx, 'same',boundary='symm')
        for n in ny.arange(0, v1_t.shape[2]):
            v2_t[:,:,n] = x[:,:,n]
            #v2_t[:,:,n] = convolve2d (x[:,:,n], self.get_dog_kernel(self.kernel2_sigma1, self.kernel2_sigma2, self.kernel2_samples), 'same',boundary='symm')
            #v2_t[:,:,n] = convolve2d (x[:,:,n], Gx, 'same',boundary='symm')
            #v2_t[:,:,n] = convolve2d(convolve2d (x[:,:,n], Gx, 'same',boundary='symm'), self.get_dog_kernel(self.kernel2_sigma1, self.kernel2_sigma2, self.kernel2_samples), 'same',boundary='symm')

        #v2_t/=ny.max(ny.absolute(v2_t))
        return v2_t



    def maxima(self, v2_t, v2_t_pre):

        v3_t=ny.zeros_like(v2_t)
        pop = pc.Population(self.main_size, self.square_size, self.gauss_width, self.N_number, self.N_angles, self.angle_outside, self.angle_inside)
        two_d_sum=ny.zeros_like(v2_t)
        Angles=ny.zeros((self.main_size,self.main_size, 2))
        POP=ny.zeros((self.main_size,self.main_size,self.N_number,2))
        POP[:,:,:,0]=v2_t_pre
        POP[:,:,:,1]=v2_t

        for j in ny.arange(0,2):
            for x in ny.arange(0,self.main_size):
                for y in ny.arange(0,self.main_size):
                    multiple=ny.multiply(POP[x,y,:,j],ny.transpose(self.vec))

                    x1=ny.sum(multiple[0,:])
                    y1=ny.sum(multiple[1,:])

                    if x1<0:
                        Angles[x,y,j]=(ny.arctan(y1/x1)+ny.pi)
                    elif x1>0 and y1>=0:
                        Angles[x,y,j]=ny.arctan(y1/x1)
                    elif x1>0 and y1<0:
                        Angles[x,y,j]=(ny.arctan(y1/x1)+(2*ny.pi))
                    elif x1==0 and y1>0:
                        Angles[x,y,j]=ny.pi/2.0
                    else:
                        Angles[x,y,j]=3*ny.pi/2


        Shift=(Angles[:,:,1]*180/ny.pi)-(Angles[:,:,0]*180/ny.pi)
        v2_angles=Angles[:,:,1]*180/ny.pi
       # Shift=v2_t-v2_t_pre
        for x in ny.arange(0,self.main_size):
            for y in ny.arange(0,self.main_size):
               # for k in ny.arange(self.N_number):
                if Shift[x,y]>180.0:
                    Shift[x,y]=(Shift[x,y]-360.0)
                elif Shift[x,y]<-180.0:
                    Shift[x,y]=(360.0+Shift[x,y])
        #Shift_max=ny.max(v2_angles)
        #Shift_min=ny.min(v2_angles)
        Shift_max=ny.max(Shift)
       # print 'max_shift=', Shift_max
        Shift_min=ny.min(Shift)
       # print 'min_shift=',Shift_min

        for x in ny.arange(0,self.main_size):
            for y in ny.arange(0,self.main_size):
 #               for k in ny.arange(sef.N_number):
                if Shift[x,y]==Shift_max:
                    self.maximum=v2_t[x,y,:]
                    self.x_max=x
                    self.y_max=y
                elif Shift[x,y]==Shift_min:
                    self.minimum=v2_t[x,y,:]
                    self.x_min=x
                    self.y_min=y
        max_deg=(pop.pop_degree(v2_t, self.x_max,self.y_max)*180/ny.pi)
        min_deg=(pop.pop_degree(v2_t, self.x_min,self.y_min)*180/ny.pi)
        return self.x_max,self.y_max,self.x_min,self.y_min, max_deg, min_deg, self.maximum, self.minimum
#
#        max_deg=(pop.pop_degree(v2_t, self.x_max,self.y_max)*180/ny.pi)
#       #print 'max_deg', max_deg
#        #print 'x=', self.x_max, 'y=', self.y_max
#        min_deg=(pop.pop_degree(v2_t, self.x_min,self.y_min)*180/ny.pi)
#        #print 'min_deg', min_deg
# #       #print 'x=', self.x_min, 'y=', self.y_min
#
#        for x in ny.arange(0,self.main_size):
#            for y in ny.arange(0,self.main_size):
#                x_y_deg=(pop.pop_degree(v2_t, x,y)*180/ny.pi)
#                for k in ny.arange(self.N_number):
#                    distance=ny.sqrt(((x-self.x_max)**2)+((y-self.y_max)**2))
#                    if v3_t[x,y,k]==0 and distance>0 and max_deg-x_y_deg<7:
#                        v3_t[x,y,:]=v2_t[x,y,:]+(self.maximum*ny.exp(-(ditance-1)))
#                        #print ny.max(ny.absolute(v3_t[x,y,:]))
#                        #print (ny.absolute(v2_t[x,y,:]))
#                        #v3_t[x,y,:]/=ny.max(ny.absolute(v3_t[x,y,:]))
#                        #print v3_t[x,y,:]
#                    elif v3_t[x,y,k]==0 and distance>0 and x_y_deg-min_deg<7:
#                        v3_t[x,y,:]==v2_t[x,y,:]+(self.minimum*ny.exp(-(distance-1)))
#                        #print (ny.absolute(v3_t[x,y,:]))
#                        #v3_t[x,y,:]/=ny.max(ny.absolute(v3_t[x,y,:]))
#                        #if y==19:
#                          #  print 'x_in_max_region=',x,'y_in_max_region=',y
##
#
#
#        for x in ny.arange(0,self.main_size):
#            for y in ny.arange(0,self.main_size):
#                for k in ny.arange(self.N_number):
#                    if v3_t[x,y,k]==0.0:
##                        if y==19:
##                            print 'x=',x,'y=', y
#                        v3_t[x,y,:]=v2_t[x,y,:]


#                        max_neurons=v2_t[x,y,:]
#                        max_angle=(Angles[x,y,1]*180/ny.pi)
#                        max_angle_d_deg_less=(Angles[x,y,1]*180/ny.pi)-d
#                        if max_angle_d_deg_less<0:
#                            max_angle_d_deg_less+=360
#                        elif max_angle_d_deg_less>360:
#                            max_angle_d_deg_less-=360
#                        elif max_angle<0:
#                            max_angle+=360
#                        elif max_angle>360:
#                            max_angle-=360


#                if v2_angles[x,y]==Shift_min:
#                    x_min=x
#                    y_min=y
#                    min_neurons=v2_t[x,y,:]
#                    min_angle=(Angles[x,y,1]*180/ny.pi)
#                    min_angle_d_deg_more=(Angles[x,y,1]*180/ny.pi)+d
#                    if min_angle_d_deg_more<0:
#                        min_angle_d_deg_more+=360
#                    elif min_angle_d_deg_more>360:
#                        min_angle_d_deg_more-=360
#                    elif min_angle<0:
#                        min_angle+=360
#                    elif min_angle>360:
#                        min_angle-=360


#        for x in ny.arange(0,self.main_size):
#            for y in ny.arange(0,self.main_size):
#                if max_angle>(Angles[x,y,1]*180/ny.pi)>max_angle_d_deg_less:#in range of d degree less of max neuronal configuration (but not max)
#                    v3_t[x,y,:]=v2_t[x,y,:]+(max_neurons)
#                elif min_angle_d_deg_more>(Angles[x,y,1]*180/ny.pi)>min_angle: #in range of d degree more of min neuronal configuration (but not min)
#                    v3_t[x,y,:]=v2_t[x,y,:]+(min_neurons)
#                else:
#                    v3_t[x,y,:]=v2_t[x,y,:]
#                    Angle_diff_max=ny.absolute(v2_angles[x,y]-max_angle)
#                    Angle_diff_min=ny.absolute(v2_angles[x,y]-min_angle)
#                    v3_t[x,y,:]=v2_t[x,y,:]+((1/(0.1+(1.0*Angle_diff_min)))*(ny.exp(-(ny.sqrt((x_min**2)+(y_min**2)))/2)*min_neurons))+((1/(0.1+(1.0*Angle_diff_max)))*(ny.exp(-(ny.sqrt((x_max**2)+(y_max**2)))/2)*max_neurons))


        #print 'v3 x=11:',v3_t[11,19,:]
#        print 'max=', self.maximum
#        print 'max=', Shift_max
#        max_deg=(pop.pop_degree(v2_t, x_max,y_max)*180/ny.pi)
#        print 'in degree',max_deg
#        print 'v2 x=10:',v2_t[10,19,:]
#        x_deg=(pop.pop_degree(v2_t, 1,19)*180/ny.pi)
#        print 'in degree',x_deg
#        print 'diff', max_deg-x_deg


#        v3_t/=ny.max(ny.absolute(v3_t))
#        return v3_t

#                two_d_sum[x,y,:]=Shift[x,y]*ny.pi/180
#
#        v3_t=v2_t+two_d_sum
#        v3_t/=ny.max(ny.absolute(v3_t))
#        v3_t /= 0.01-two_d_sum
#        v3_t/=0.01+(1/(0.01+ny.absolute(two_d_sum)))
#
#        two_d_sum=ny.zeros_like(v2_t)
#        shift=v2_t-v2_t_pre
#
#        for x in ny.arange(self.main_size):
#            for y in ny.arange(self.main_size):
#                two_d_sum[x,y,:]=ny.sum(shift[x,y,:])
#       # print two_d_sum[10,15,1]
#       # print two_d_sum[2,15,1]
#        v3_t=v2_t-((1.0/16.0)*two_d_sum)
#        v3_t/=0.01+(1/two_d_sum)





    def do_v3(self, v2_t, iteration):

#        x_max,y_max,x_min,y_min, max_deg, min_deg, maximum, minimum=self.maxima(v2_t, v2_t_pre)
        s=v2_t.shape
        v3_t=ny.zeros_like(v2_t)
        N=ny.zeros_like(v2_t)
        M=N
        R=1  # CONSIDERED SURROUND (IN PIXEL) IN EACH DIRECTION
        #j=i  # model cycle

        # x,y IS THE AREA WHERE THE SURROUND R CAN BE CONSIDERED.
        a = ny.arange(R,s[0]-R)
        (x,y) = ny.meshgrid(a,a)
        (x,y) = (x.flatten(),y.flatten())

        # PURPOSE OF t1-t11: CREATES AN ARRAY (x1,y1) WHICH FORMS THE FRAME (THICKNESS=R) OUTSIDE THE AREA (x,y) WHERE THE SURROUND CANNOT BE CONSIDERED

        # t3,t4 CREATE AREA WITH X=RANGE(0:29) AND Y=RANGE(0,R). THIS AREA FORMS THE LOWER STRIP OF THE FRAME.
        t1=ny.arange(s[0])
        t2=ny.arange(R)
        t3,t4 = ny.meshgrid(t1,t2)
        t3,t4 = t3.flatten(),t4.flatten()

        # t6,t7 CREATE AREAS WITH X=RANGE(0:R, 29-R:29) AND Y=RANGE(R:29-R). THESE AREAS FORM THE SIDE STRIPS OF THE FRAME.
        t5 = ny.concatenate((ny.arange(0,R),ny.arange(s[0]-R, s[0])))
        t6,t7 = ny.meshgrid(t5,a)
        t6,t7 = t6.flatten(),t7.flatten()

        # t10,t11 CREATE AREAS WITH X=RANGE(0:29) AND Y=RANGE(29-R:29).THIS AREA FORMS THE UPPER STRIP OF THE FRAME.
        t9=ny.arange(s[0]-R, s[0])
        t10,t11 = ny.meshgrid(t1,t9)
        t10,t11 = t10.flatten(),t11.flatten()

        # ZEROS IN THE BEGINNING, SO THAT INDEX i IS AT THE CORRECT POSITION IN x1/y1 AFTER SURROUND-AVERAGE CALCULATION
        x1 = ny.concatenate((ny.tile(0.0,len(x)),t3,t6,t10))
        y1 = ny.concatenate((ny.tile(0.0,len(x)),t4,t7,t11))

        Gauss_nil=ny.ceil (2*ny.sqrt(2*ny.log(2))*self.gauss_width)
        pop = pc.Population(self.main_size, self.square_size, self.gauss_width, self.N_number, self.N_angles, self.angle_outside, self.angle_inside)

        for i in ny.arange(len(x1)):
            if i in ny.arange(len(x)):

                c1 = ny.arange(x[i]-R,x[i]+R+1)
                c2 = ny.arange(y[i]-R,y[i]+R+1)
                (m,n)=ny.meshgrid(c1,c2)
                m=m.flatten()
                n=n.flatten()
                x_y_deg=(pop.pop_degree(v2_t, x[i],y[i])*180/ny.pi)
                neighbours=ny.array((ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]-1,y[i])*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]+1,y[i])*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i],y[i]-1)*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i],y[i]+1)*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]+1,y[i]+1)*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]+1,y[i]-1)*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]-1,y[i]+1)*180/ny.pi)),
                ny.absolute(x_y_deg-(pop.pop_degree(v2_t, x[i]-1,y[i]-1)*180/ny.pi))))
                if [limit<20 for limit in neighbours]==[True, True, True, True, True, True, True, True]:

#                if x[i]!=x_max and x[i]!=x_min and y[i]!=y_max and y[i]!=y_min and max_deg-x_y_deg>4 and x_y_deg-min_deg>3.5:
#                    if y[i]==15:
#                        print 'for y=', y[i], 'for x=', x[i], 'deg=', x_y_deg, 'max-deg=',max_deg-x_y_deg,'max=',max_deg, 'deg-min=',x_y_deg-min_deg,'min=', min_deg

                    for k in ny.arange(0,self.N_number): # pixel-surround-average calculation per neuron (0-7)
#                        if ny.absolute(x_y_deg-max_deg)>ny.absolute(x_y_deg-min_deg):
#                            largest=minimum
#                        else:
#                            largest= maximum
                        N[x[i],y[i],k]=math.fsum(v2_t[m,n,k])
                        M[x[i],y[i],k]=(N[x[i],y[i],k]/((R+R+1)**2))-(v2_t[1,1,k]*(ny.exp(-iteration/2.0)+0.08))#+largest[k]

                else:
                    M[x[i],y[i],:]=v2_t[x[i],y[i],:]-(v2_t[1,1,:]*(ny.exp(-iteration/2.0)+0.08))


            else:
                M[x1[i],y1[i],:]=v2_t[x1[i],y1[i],:]-(v2_t[1,1,:]*(ny.exp(-iteration/2.0)+0.08))
                #v3_t[x1[i],y1[i],:]=M[x1[i],y1[i],:]



        v3_t = M #v2_t+1.0*(v2_t-M)#/ny.max(ny.absolute(v2_t-M))#+4.0)/7'$neuron$ $%i$ $(\mu=%i\degree)$\n$neuron$ $%i$ $(\mu=%i\degree)$'%(5,7,5,7)7)2_t-(0.3*M)))#(v2_t-(0.3*M))#(((ny.exp(-j/2.3)+0.00)/1.00)*(v2_t-(0.3*M)))
        v3_t /= ny.max(ny.absolute(v3_t))
        #v3_t /= 1/(0.01+ny.absolute(v2_t-M))
       # print x_max, y_max, x_min, y_min
        return v3_t


    def do_all(self, net_in, net_fb, gauss, last, iteration):
        v1_t = self.do_v1(net_in, net_fb)
        v2_t = self.do_v2(v1_t, gauss, iteration)
        v3_t = self.do_v3(v2_t, iteration)
        return v3_t

    def max_colour_induced_shift(self, color_space_step_size):
        pop = pc.Population(self.main_size, self.square_size, self.gauss_width, self.N_number, self.N_angles, self.angle_outside, self.angle_inside)

        if self.angle_outside-180>0:
            angle_inside = ny.concatenate((ny.arange(self.angle_outside-180,360,color_space_step_size),ny.arange(0,self.angle_outside-180+color_space_step_size,color_space_step_size)))
        else:
            angle_inside = ny.concatenate((ny.arange(self.angle_outside+180,360,color_space_step_size),ny.arange(0,self.angle_outside+180+color_space_step_size,color_space_step_size)))
       # print angle_inside

        rel_angle_inside=ny.arange(-180, 180+color_space_step_size, color_space_step_size)
        POP=ny.zeros((self.main_size,self.main_size,self.N_number,2*len(angle_inside)))
        Angles=ny.zeros((self.main_size,self.main_size,2*len(angle_inside)))
        Shift=ny.zeros((self.main_size,self.main_size,len(angle_inside)))

        max_shift = ny.zeros(len(rel_angle_inside))
        extrema_shift = ny.zeros(len(rel_angle_inside))
        min_shift = ny.zeros(len(rel_angle_inside))



        s=POP.shape
        before=ny.arange(0,2*len(angle_inside),2)
        i=0
        for a in angle_inside:
            print a
            POP[:,:,:,before[i]]=self.create_input(self.angle_outside, a)
            #After=self.run_convolution(POP[:,:,:,before[i]])
            POP[:,:,:,before[i]+1]=self.run_convolution(POP[:,:,:,before[i]])#self.do_v2(POP[:,:,:,before[i]],[])#After[:,:,:,self.time_frames]#self.do_v2(POP[:,:,:,before[i]], self.mt_gauss)
            i+=1
        for j in ny.arange(0,s[3]):
            for x in ny.arange(0,self.main_size):
                for y in ny.arange(0,self.main_size):
                    multiple=ny.multiply(POP[x,y,:,j],ny.transpose(self.vec))

                    x1=ny.sum(multiple[0,:])
                    y1=ny.sum(multiple[1,:])

                    if x1<0:
                        Angles[x,y,j]=(ny.arctan(y1/x1)+ny.pi)
                    elif x1>0 and y1>=0:
                        Angles[x,y,j]=ny.arctan(y1/x1)
                    elif x1>0 and y1<0:
                        Angles[x,y,j]=(ny.arctan(y1/x1)+(2*ny.pi))
                    elif x1==0 and y1>0:
                        Angles[x,y,j]=ny.pi/2.0
                    else:
                        Angles[x,y,j]=3*ny.pi/2
        for n in ny.arange(0,len(rel_angle_inside)):
            Shift[:,:,n]=((Angles[:,:,before[n]+1])*180/ny.pi)-((Angles[:,:,before[n]])*180/ny.pi)
            extrema_shift[n]=(ny.max((Angles[:,:,before[n]+1])*180/ny.pi))-(ny.max((Angles[:,:,before[n]])*180/ny.pi))
            min_shift[n]=(ny.min((Angles[:,:,before[n]+1])*180/ny.pi))-(ny.min((Angles[:,:,before[n]])*180/ny.pi))

            for x in ny.arange(0,self.main_size):
                for y in ny.arange(0,self.main_size):
                    if Shift[x,y,n]>180:
                        Shift[x,y,n]=(Shift[x,y,n]-360)
                    elif Shift[x,y,n]<-180:
                        Shift[x,y,n]=(360+Shift[x,y,n])
            if extrema_shift[n]>180:
                extrema_shift[n]=(extrema_shift[n]-360)
            elif extrema_shift[n]<-180:
                extrema_shift[n]=(360+extrema_shift[n])
            elif min_shift[n]>180:
                min_shift[n]=(min_shift[n]-360)
            elif min_shift[n]<-180:
                min_shift[n]=(360+min_shift[n])
            if abs(min_shift[n])>abs(extrema_shift[n]):
                max_shift[n]=min_shift[n]
            elif abs(extrema_shift[n])>abs(min_shift[n]):
                max_shift[n]=extrema_shift[n]
            x=ny.where(abs(Shift[:,:,n])==ny.max(abs(Shift[:,:,n])))
            max_shift[n]=Shift[x[0][0],x[1][0],n]
        fig=pp.figure(1)
        #fig.patch.set_facecolor('grey')
        ax = fig.add_subplot(111)
      #  ax.patch.set_facecolor('lightgrey')
        C = ny.genfromtxt("Colormatrix.txt")
        t=(self.angle_outside*(2*ny.pi/360))/(1/60.0)
        cm= C[t, :]
        str_list = []
        for i in ny.arange(0,len(self.N_angles)):
            str_list.append('$neuron$ $%i$ $(\mu=%.1f\degree)$\n' %(i+1,self.N_angles[i]))
        List=''.join(str_list)
        ax.scatter(rel_angle_inside,max_shift, c=cm, lw = 0, label=List)

        # Shink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.7, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        pp.grid(True)
        pp.xticks(ny.arange(-180,230,45))
        pp.xlabel('Relative angle in colour space for stimulus [$^\circ$], with a background color of %d$^\circ$. \n Convolution ' \
                  'kernel uses $\sigma1=$ %.1f and $\sigma2=$ %.1f with %.1f samples and a scaling of %.1f.'%(self.angle_outside, self.kernel_sigma1, self.kernel_sigma2, self.kernel_samples, self.kernel_scale))
        pp.ylabel('maximal shift [degree]')
        pp.title('For %i neurons with %i $\sigma$' %(self.N_number,self.gauss_width))
        #            pp.figure(2+n)
        #            pp.imshow(Angles[:,:,before[n]]*180/ny.pi)
        #            pp.title('colour inside = %i degree' %(n*90))
        #            pp.colorbar()


    def run_convolution(self, input):

        if not len(input):
            input=self.create_input(self.angle_outside, self.angle_inside)


        POP=ny.zeros((self.main_size,self.main_size,self.N_number,self.time_frames+1))
        POP1=ny.zeros((self.main_size,self.main_size,self.N_number,self.time_frames+1))
        FB=ny.zeros((self.main_size, self.main_size, self.N_number, self.time_frames+1))
        POP1[:,:,:,0]=input
        pop = pc.Population(self.main_size, self.square_size, self.gauss_width, self.N_number, self.N_angles, self.angle_outside, self.angle_inside)


        for i in ny.arange(0,self.time_frames+1):
            print i

            if i>0:
                if i==1:
                    POP[:,:,:,i]=self.do_all(input, FB[:,:,:,i-1], [], input, i)
                    POP1[:,:,:,i]=self.do_all(POP[:,:,:,i], 0, self.mt_gauss,input, i)#self.do_v2(POP[:,:,:,i],self.mt_gauss)
                    FB[:,:,:,i] = POP1[:,:,:,i]
                else:
                    POP[:,:,:,i]=self.do_all(input, FB[:,:,:,i-1], [], input, i)
                    POP1[:,:,:,i]=self.do_all(POP[:,:,:,i], 0, self.mt_gauss,input,i )#self.do_v2(POP[:,:,:,i],self.mt_gauss)
                    FB[:,:,:,i] = POP1[:,:,:,i]


#            pp.figure(1)
#            pop.plot_pop(POP1[:,:,:,i],self.time_frames,i)
#            pp.figure(2)
#            pop.plot_cartesian_pop(POP1[:,:,:,i],self.time_frames,i)
            pp.figure(3)
            pop.plot_row(1,15,POP1[:,:,:,i],i, self.time_frames)
#            pp.figure(4)
#            pop.twoD_activation(POP[:,:,:,i], i, self.time_frames)
        return POP1[:,:,:,self.time_frames]




if __name__ == '__main__':
    M=Mexican_hat('model.cfg')
    #M.run_convolution([])
    M.max_colour_induced_shift(22.5)
    #D=M.get_dog_kernel()
    #pp.imshow(D)
    #pp.figure()
    #pp.plot(D)
    pp.show()


